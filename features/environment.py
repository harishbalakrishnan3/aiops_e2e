import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timezone

import jwt
from dotenv import load_dotenv

from features.steps.cdo_apis import get, post
from features.steps.env import Path, get_endpoints
from features.model import Device, ScenarioEnum

timeseries = {}


class UTCFormatter(logging.Formatter):
    """Custom formatter that uses UTC timestamps in ISO 8601 format"""

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        # ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def setup_logging():
    """Configure logging with ISO 8601 UTC timestamps"""
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Create formatter with ISO 8601 UTC timestamps with line numbers
    formatter = UTCFormatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    # Set specific loggers to appropriate levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def before_all(context):
    # Setup behave's logging
    context.config.setup_logging()

    # Initialize logging with ISO 8601 UTC timestamps
    setup_logging()

    # Creating an empty timeseries dictionary - this will be populated in the due course of test execution
    context.timeseries = timeseries

    # Loading the CDO token from the .env file and adding it to the environment variables
    load_dotenv()
    cdo_token = os.getenv("CDO_TOKEN")
    os.environ["CDO_TOKEN"] = cdo_token
    # Adding the tenant_id to the context
    if cdo_token != "" and cdo_token is not None:
        decoded = jwt.decode(cdo_token, options={"verify_signature": False})
        context.tenant_id = decoded["parentId"]

    # Discover all FTD devices (does NOT require RAVPN)
    discover_devices(context)

    # Initialize map between a scenario and a device (each scenario can have an associated device)
    context.scenario_to_device_map = {}

    # Track devices used across all scenarios to maximize device diversity
    context.used_devices = set()

    # Initialize list of generated data for each scenario for bulk backfill in scenario
    context.generated_data_list = []

    # Track whether RAVPN discovery has been done (lazy initialization)
    context.ravpn_discovered = False

    # Get the remote write config for GCM
    context.remote_write_config = get_gcm_remote_write_config()


def discover_devices(context):
    """Discover all FTD devices. Does NOT check RAVPN status."""
    device_details = get(
        get_endpoints().DEVICES_DETAILS_URL + "&limit=200", print_body=False
    )
    available_devices = []
    for device in device_details:
        # Skip devices without metadata or missing required metadata fields
        if (
            "metadata" not in device
            or device["metadata"] is None
            or "deviceRecordUuid" not in device["metadata"]
            or "containerType" not in device["metadata"]
        ):
            logging.info(
                f"Skipping device {device.get('name', 'unknown')} - missing metadata or required fields"
            )
            continue
        device_obj = Device(
            device_name=device["name"],
            aegis_device_uid=device["uid"],
            device_record_uid=device["metadata"]["deviceRecordUuid"],
            container_type=device["metadata"]["containerType"],
        )
        available_devices.append(device_obj)
    context.devices = available_devices
    logging.info(f"Discovered {len(available_devices)} FTD devices")


def discover_ravpn_devices(context):
    """Discover RAVPN-enabled devices. Only called when RAVPN feature runs."""
    if context.ravpn_discovered:
        return

    # Get cdFMC UID
    resp = get(get_endpoints().FMC_DETAILS_URL, print_body=False)
    uid = ""
    for d in resp:
        uid = d["uid"]

    if uid == "":
        raise Exception("FMCE device not found")

    # Get the device id for which VPN is enabled
    req = {
        "deviceUid": uid,
        "request": {
            "commands": [
                {
                    "method": "GET",
                    "link": "/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/health/ravpngateways?limit=200",
                    "body": "",
                }
            ]
        },
    }
    resp = post(get_endpoints().DEVICE_GATEWAY_COMMAND_URL, json.dumps(req))
    logging.info(resp.json())
    ra_vpn_enabled_devices = json.loads(resp.json()["data"]["responseBody"])

    ra_vpn_devices = []
    for device in context.devices:
        if is_ra_vpn_enabled(ra_vpn_enabled_devices, device.device_record_uid):
            device.ra_vpn_enabled = True
            ra_vpn_devices.append(device)

    logging.info(
        f"{len(ra_vpn_devices)} of {len(context.devices)} devices have RA-VPN enabled"
    )
    logging.info(
        f"Devices with RA-VPN enabled: {[device.device_name for device in ra_vpn_devices]}"
    )

    if not ra_vpn_devices:
        raise Exception("RA-VPN gateway not found")

    context.ravpn_discovered = True


def is_ra_vpn_enabled(ra_vpn_enabled_devices, device_record_uid):
    for item in ra_vpn_enabled_devices:
        if "device" not in item:
            return False
        device_id = item["device"]["id"]

        if device_record_uid == device_id:
            return True
    return False


def before_feature(context, feature):
    context.feature_name = feature.name

    # Clean the feature's output directory so each run starts fresh
    feature_dir = os.path.join(
        Path.OUTPUTS_DIR, re.sub(r"[^a-zA-Z0-9_-]", "_", feature.name).strip("_")
    )
    if os.path.exists(feature_dir):
        shutil.rmtree(feature_dir)
        logging.info(f"Cleaned output directory: {feature_dir}")

    if feature.name == "Testing RA-VPN forecasting":
        # Lazily discover RAVPN devices only when this feature runs
        discover_ravpn_devices(context)
        logging.info("Updating RA-VPN forecasting module settings")
        module_settings = {
            "moduleName": "RAVPN_MAX_SESSIONS_BREACH_FORECAST",
            "enable": True,
            "severity": "AUTO",
            "forecastDurationInDays": 30,
            "maxSessionsThreshold": 100.0,
            "accuracyLevel": "LOW",
            "minimumTrainingPeriodInDays": 7,
            "historyDurationInDays": 21,
        }
        update_module_settings("ravpn-capacity-forecast", module_settings)
    elif feature.name == "Testing Anomaly Detection":
        logging.info("Updating Anomaly Detection module settings")
        module_settings = {
            "moduleName": "THROUGHPUT_ANOMALY",
            "enable": True,
            "severity": "WARNING",
            "sensitivityLevel": "HIGH",
            "sensitivityPercentage": 10.0,
            "historyDurationInDays": 14,
            "anomalyDurationInMinutes": 5,
        }
        update_module_settings("throughput-anomaly", module_settings)
        module_settings["moduleName"] = "CONNECTIONS_ANOMALY"
        update_module_settings("connections-anomaly", module_settings)


def before_scenario(context, scenario):
    try:
        context.scenario = ScenarioEnum(scenario.name)
    except:
        context.scenario = ScenarioEnum.UNKNOWN_SCENARIO

    # Initialize a list to track insights created during this scenario
    context.scenario_insights = []


def after_all(context):
    logging.info("Selected device for each scenario is as follows")
    for scenario, device in context.scenario_to_device_map.items():
        logging.info(f"{scenario}: {device}")


def get_gcm_remote_write_config():
    gcm_stack_config = get(get_endpoints().TENANT_GCM_STACK_CONFIG_URL)
    return {
        "url": "/".join([gcm_stack_config["hmInstancePromUrl"], "api/prom/push"]),
        "username": gcm_stack_config["hmInstancePromId"],
        "password": gcm_stack_config["prometheusToken"],
    }


def update_module_settings(module, settings):
    post(get_endpoints().MODULE_SETTINGS_ENDPOINT + f"/{module}", json.dumps(settings))
