import os
from datetime import datetime, timedelta

import jwt

from dotenv import load_dotenv

from features.steps.cdo_apis import get
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

    # Add the device id to the context
    context.device_id = get_device_id(context)

    # Decide if the RAVPN feature should run
    context.run_ravpn_feature = should_ravpn_feature_run()


def get_device_id(context):
    devices_details = get(get_endpoints().DEVICES_DETAILS_URL)
    for device in devices_details:
        if 'metadata' in device.keys() and 'deviceRecordUuid' in device['metadata'].keys():
            print(f"Found FTD device with UUID {device['metadata']['deviceRecordUuid']}")
            return device['metadata']['deviceRecordUuid']
    print("No FTD device found for the tenant. Returning a random UUID.")
    return "f5b1b3b0-0b3b-4b3b-8b3b-0b3b3b3b3b3b"


def before_feature(context, feature):
    if "RA-VPN" in feature.name and context.run_ravpn_feature is False:
        print("Skipping the RAVPN feature as there is some data in Grafana the last 14 days.")
        feature.skip()


def should_ravpn_feature_run():
    # Calculate the start and end times
    start_time = datetime.now() - timedelta(days=14)
    end_time = datetime.now() - timedelta(days=1)

    # Convert to epoch seconds
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    query = "?query=vpn&start=" + str(start_time_epoch) + "&end=" + str(
        end_time_epoch) + "&step=5m"
    endpoint = get_endpoints().PROMETHEUS_RANGE_QUERY_URL + query

    # If there is some data in the last 14 days, then the RAVPN feature should be skipped
    response = get(endpoint, print_body=False)
    if len(response["data"]["result"]) > 0:
        return False

    return True
