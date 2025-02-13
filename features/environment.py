import json
import os

import jwt
from behave.model_core import Status

from dotenv import load_dotenv

from features.steps.cdo_apis import get, post
from features.steps.env import get_endpoints
from features.model import Device, ScenarioEnum

timeseries = {}


def before_all(context):
    # Initialize logging
    context.config.setup_logging()

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

    # Initialize map between a scenartio and a device (each scenario can have an associated device)
    context.scenario_to_device_map = {}

    # Get the remote write config for GCM
    context.remote_write_config = get_gcm_remote_write_config()


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
    print(resp.json())
    ra_vpn_enabled_devices = json.loads(resp.json()["data"]["responseBody"])

    available_devices = []
    device_details = get(get_endpoints().DEVICES_DETAILS_URL, print_body=False)
    for device in device_details:
        device_obj = Device(
            device_name=device["name"],
            aegis_device_uid=device["uid"],
            device_record_uid=device["metadata"]["deviceRecordUuid"],
            ra_vpn_enabled=is_ra_vpn_enabled(
                ra_vpn_enabled_devices, device["metadata"]["deviceRecordUuid"]
            ),
        )
        available_devices.append(device_obj)

    context.devices = available_devices

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


def get_gcm_remote_write_config():
    gcm_stack_config = get(get_endpoints().TENANT_GCM_STACK_CONFIG_URL)
    return {
        "url": "/".join([gcm_stack_config["hmInstancePromUrl"], "api/prom/push"]),
        "username": gcm_stack_config["hmInstancePromId"],
        "password": gcm_stack_config["prometheusToken"],
    }
