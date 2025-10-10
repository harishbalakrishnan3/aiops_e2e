import json
import os
import logging
import sys
from datetime import datetime, timezone

import jwt
from behave.model_core import Status

from dotenv import load_dotenv

from features.steps.cdo_apis import get, post
from features.steps.env import get_endpoints
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

    # Create formatter with ISO 8601 UTC timestamps (no module names)
    formatter = UTCFormatter(fmt="[%(asctime)s] [%(levelname)s] %(message)s")
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

    # Update the device details such as its name, id and aegis record id in context
    update_device_details(context)

    # Initialize a flag to track failures
    context.stop_execution = False

    # Initialize map between a scenario and a device (each scenario can have an associated device)
    context.scenario_to_device_map = {}

    # Initialize list of generated data for each scenario for bulk backfill in scenario
    context.generated_data_list = []

    # Get the remote write config for GCM
    # context.remote_write_config = get_gcm_remote_write_config()


def update_device_details(context):
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
                    "link": "/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/health/ravpngateways",
                    "body": "",
                }
            ]
        },
    }
    resp = post(get_endpoints().DEVICE_GATEWAY_COMMAND_URL, json.dumps(req))
    logging.info(resp.json())
    ra_vpn_enabled_devices = json.loads(resp.json()["data"]["responseBody"])

    available_devices = []  # List of all the available devices
    ra_vpn_devices = []  # List of only the devices with RA-VPN enabled
    device_details = get(
        get_endpoints().DEVICES_DETAILS_URL + "&limit=200", print_body=False
    )
    for device in device_details:
        device_obj = Device(
            device_name=device["name"],
            aegis_device_uid=device["uid"],
            device_record_uid=device["metadata"]["deviceRecordUuid"],
            container_type=device["metadata"]["containerType"],
        )
        ra_vpn_enabled = False
        if is_ra_vpn_enabled(
            ra_vpn_enabled_devices, device["metadata"]["deviceRecordUuid"]
        ):
            ra_vpn_enabled = True
            ra_vpn_devices.append(device_obj)
        device_obj.ra_vpn_enabled = ra_vpn_enabled
        available_devices.append(device_obj)
    context.devices = available_devices

    logging.info(
        f"There are {len(available_devices)} devices available with {len(ra_vpn_devices)} devices having RA-VPN enabled"
    )
    logging.info(
        f"Devices with RA-VPN enabled: {[device.device_name for device in ra_vpn_devices]}"
    )

    if not any(device.ra_vpn_enabled for device in available_devices):
        raise Exception("RA-VPN gateway not found")


def is_ra_vpn_enabled(ra_vpn_enabled_devices, device_record_uid):
    for item in ra_vpn_enabled_devices:
        if "device" not in item:
            return False
        device_id = item["device"]["id"]

        if device_record_uid == device_id:
            return True
    return False


def before_feature(context, feature):
    if feature.name == "Testing RA-VPN forecasting":
        logging.info("Updating RA-VPN forecasting module settings")
        module_settings = {
            "moduleName": "RAVPN_MAX_SESSIONS_BREACH_FORECAST",
            "enable": True,
            "severity": "AUTO",
            "forecastDurationInDays": 90,
            "maxSessionsThreshold": 100.0,
            "accuracyLevel": "MEDIUM",
            "minimumTrainingPeriodInDays": 7,
            "historyDurationInDays": 14,
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
    if context.stop_execution:
        scenario.skip("Skipping scenario due to a previous failure.")

    try:
        context.scenario = ScenarioEnum(scenario.name)
    except:
        context.scenario = ScenarioEnum.UNKNOWN_SCENARIO


def after_scenario(context, scenario):
    if scenario.status == Status.failed:
        context.stop_execution = True


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
