import json
import os.path
import subprocess
import time
from datetime import datetime
from datetime import timedelta
from string import Template

from behave import *
from mockseries.noise import GaussianNoise
from mockseries.seasonality import DailySeasonality
from mockseries.trend import LinearTrend
from mockseries.utils import datetime_range
from features.steps.cdo_apis import get, post
from features.steps.env import get_endpoints, Path
from features.steps.utils import get_common_labels , is_data_not_present

t = Template("""# HELP $metric_name $description
# TYPE $metric_name gauge
$metric_name{$labels_1} $value $timestamp
$metric_name{$labels_2} $value $timestamp
""")

# TODO : Make this dynamic
HISTORICAL_DATA_FILE = "ravpn_historical_data.txt"

@step('backfill RAVPN metrics for a suitable device')
def step_impl(context):
    if context.remote_write_config is None:
        print("Remote write config not found. Skipping backfill.")
        assert False

    # TODO : Remove post checking backfill behaviour for RA-VPN
    # if is_device_present_with_ra_vpn_data(context):
    #     assert True 
    #     return
        
    ts_values, time_points = generate_timeseries()

    metric_name = "vpn"
    common_labels = {
                        "instance": "127.0.0.2:9273",
                        "job": "metrics_generator:8123",
                    } | get_common_labels(context, timedelta(days=7))

    labels_1 = {**common_labels, "vpn": "active_ravpn_tunnels"}
    labels_2 = {**common_labels, "vpn": "inactive_ravpn_tunnels"}
    description = "Currently active and inactive RAVPN tunnels"
    labels_1 = ",".join([f"{k}=\"{v}\"" for k, v in labels_1.items()])
    labels_2 = ",".join([f"{k}=\"{v}\"" for k, v in labels_2.items()])
    with open(os.path.join(Path.PYTHON_UTILS_ROOT, HISTORICAL_DATA_FILE), 'w') as file:
        for i in range(len(time_points)):
            multiline_text = t.substitute(value=ts_values[i], timestamp=int(time_points[i].timestamp()),
                                          metric_name=metric_name, labels_1=labels_1, labels_2=labels_2,
                                          description=description)
            file.write(multiline_text)
        file.write("# EOF")

    remote_write_config = context.remote_write_config

    subprocess.run([os.path.join(Path.PYTHON_UTILS_ROOT, "backfill.sh"),
                    remote_write_config["url"].removesuffix("/api/prom/push"),
                    remote_write_config["username"], remote_write_config["password"], Path.PYTHON_UTILS_ROOT , "/ravpn_data/" , HISTORICAL_DATA_FILE] ,)

    # Calculate the start and end times
    start_time = datetime.now() - timedelta(days=14)
    end_time = datetime.now() - timedelta(days=1)

    # Convert to epoch seconds
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    query = f"?query=vpn{{uuid=\"{context.scenario_to_device_map[context.scenario].device_record_uid}\"}}&start={start_time_epoch}&end={end_time_epoch}&step=5m"

    endpoint = get_endpoints().PROMETHEUS_RANGE_QUERY_URL + query

    count = 0
    success = False
    while True:
        # Exit after 60 minutes
        if count > 60:
            print("Data not ingested in Prometheus. Exiting.")
            break

        count += 1

        # Check for data in Prometheus
        response = get(endpoint, print_body=False)
        if len(response["data"]["result"]) > 0:
            num_data_points_active_ravpn = len(response["data"]["result"][0]["values"])
            num_data_points_inactive_ravpn = len(response["data"]["result"][1]["values"])
            print(
                f"Active RAVPN data points: {num_data_points_active_ravpn}. Inactive RAVPN data points: {num_data_points_inactive_ravpn}")
            if num_data_points_active_ravpn > 3700 and num_data_points_inactive_ravpn > 3700:
                success = True
                break

        time.sleep(60)
        # TODO: Ingest live data till backfill data is available
    assert success


@step('trigger the RAVPN forecasting workflow')
def step_impl(context):
    payload = {
        "subscriber": "RAVPN_MAX_SESSIONS_BREACH_FORECAST",
        "trigger-type": "SCHEDULE_TICKS",
        "config": {
            "periodicity": "INTERVAL_24_HOURS"
        },
        "pipeline": {
            "output": [
                {
                    "plugin": "SNS",
                    "config": {
                        "destination": "ai-ops-forecast"
                    }
                }
            ],
            "processor": []
        },
        "deviceIds": [
            context.scenario_to_device_map[context.scenario].device_record_uid
        ],
        "timestamp": "2024-08-21T05:55:00.000",
        "attributes": {}
    }
    post(get_endpoints().TRIGGER_MANAGER_URL, json.dumps(payload))

def is_device_present_with_ra_vpn_data(context):
    available_devices = [device for device in  context.devices if device.ra_vpn_enabled == True]
    query = "query=vpn{{uuid=\"{uuid}\"}}"
    for device in available_devices:
        if not is_data_not_present(query.format(uuid=device.device_record_uid) , timedelta(days=365) , "60m"):
            context.scenario_to_device_map[context.scenario] = device
            print("Device with RA-VPN data already present , Selected device: ", device)
            return True
    return False


def generate_timeseries():
    # Trend component
    trend = LinearTrend(coefficient=0.2, time_unit=timedelta(hours=0.95), flat_base=5)

    # Seasonality component
    seasonality = DailySeasonality(
        {timedelta(hours=0): 1., timedelta(hours=2): 10.8, timedelta(hours=4): 18.1, timedelta(hours=6): 19.5,
         timedelta(hours=8): 17.6, timedelta(hours=10): 15.8, timedelta(hours=12): 14.1, timedelta(hours=14): 12.8,
         timedelta(hours=16): 10.3, timedelta(hours=18): 8.7, timedelta(hours=20): 3.6, timedelta(hours=22): 1.8,
         })

    # Noise component
    noise = GaussianNoise(mean=0, std=3 , random_seed=42)

    # Combine components
    timeseries = trend + seasonality + noise

    # Generate timeseries
    time_points = datetime_range(
        granularity=timedelta(minutes=5),
        start_time=datetime.now() - timedelta(days=14),
        end_time=datetime.now()
    )
    ts_values = timeseries.generate(time_points=time_points)
    return ts_values, time_points
