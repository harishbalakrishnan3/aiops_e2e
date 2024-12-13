import json
import os
from datetime import datetime, timedelta

import jwt
from behave.model_core import Status

from dotenv import load_dotenv

from features.steps.cdo_apis import get, post
from features.steps.env import get_endpoints

timeseries = {}


def before_all(context):
    # Initialize logging
    context.config.setup_logging()

    # Creating an empty timeseries dictionary - this will be populated in the due course of test execution
    context.timeseries = timeseries

    # Loading the CDO token from the .env file and adding it to the environment variables
    load_dotenv()
    cdo_token = os.getenv('CDO_TOKEN')
    os.environ['CDO_TOKEN'] = cdo_token

    # Adding the tenant_id to the context
    if cdo_token != "" and cdo_token is not None:
        decoded = jwt.decode(cdo_token, options={"verify_signature": False})
        context.tenant_id = decoded['parentId']

    # Update the device details such as its name, id and aegis record id in context
    update_device_details(context)

    # Initialize a flag to track failures
    context.stop_execution = False

    # Get the remote write config for GCM
    context.remote_write_config = get_gcm_remote_write_config()


def update_device_details(context):
    # Get cdFMC UID
    resp = get(get_endpoints().FMC_DETAILS_URL, print_body=False)
    uid = ""
    for d in resp:
        uid = d['uid']

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
                    "body": ""
                }
            ]
        }
    }

    resp = post(get_endpoints().DEVICE_GATEWAY_COMMAND_URL, json.dumps(req))
    print(resp.json())
    resp_body = json.loads(resp.json()['data']['responseBody'])

    for item in resp_body:
        device_id = item['device']['id']
        device_name = item['device']['name']

        # Check if there is data in the last 15 days
        if can_run_ravpn_feature(device_id):
            context.device_id = device_id
            context.device_name = device_name
            query = f"?q=metadata.deviceRecordUuid:{device_id}"
            device_details = get(get_endpoints().DEVICES_DETAILS_URL + query, print_body=False)
            context.aegis_device_record_id = device_details[0]['uid']
            print(
                f"Found a suitable FTD device {device_name} with UUID {device_id} and record ID {context.aegis_device_record_id}")
            return

    raise Exception("RA-VPN gateway not found")


def before_scenario(context, scenario):
    if context.stop_execution:
        scenario.skip("Skipping scenario due to a previous failure.")


def after_scenario(context, scenario):
    if scenario.status == Status.failed:
        context.stop_execution = True


def can_run_ravpn_feature(device_id):
    # Calculate the start and end times
    start_time = datetime.now() - timedelta(days=7)
    end_time = datetime.now() - timedelta(days=1)

    # Convert to epoch seconds
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    query = f"?query=vpn{{uuid=\"{device_id}\"}}&start={start_time_epoch}&end={end_time_epoch}&step=5m"
    endpoint = get_endpoints().PROMETHEUS_RANGE_QUERY_URL + query

    # If there is some data in the last 7 days, then the RAVPN feature should be skipped
    response = get(endpoint, print_body=False)
    if len(response["data"]["result"]) > 0:
        return False

    return True


def get_gcm_remote_write_config():
    gcm_stack_config = get(get_endpoints().TENANT_GCM_STACK_CONFIG_URL)
    return {
        "url": '/'.join([gcm_stack_config['hmInstancePromUrl'], 'api/prom/push']),
        "username": gcm_stack_config['hmInstancePromId'],
        "password": gcm_stack_config['prometheusToken']
    }
