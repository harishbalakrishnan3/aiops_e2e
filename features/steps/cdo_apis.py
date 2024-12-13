import json
import os
from datetime import datetime
import requests
from opentelemetry.exporter.prometheus_remote_write import (
    PrometheusRemoteWriteMetricsExporter,
)
from opentelemetry.sdk.metrics.export import MetricsData, MetricExportResult
from features.steps.env import get_endpoints
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

endpoints = get_endpoints()


def get_insights():
    return get(endpoints.INSIGHTS_URL , print_body=False)


def delete_insights():
    delete(endpoints.INSIGHTS_URL)

def remote_write(metrics_data:MetricsData):
    exporter = PrometheusRemoteWriteMetricsExporter(
        endpoint=get_endpoints().DATA_INGEST_URL,
        headers={"Authorization": "Bearer " + os.getenv('CDO_TOKEN')},
    )

    result = exporter.export(metrics_data)
    if result == MetricExportResult.FAILURE:
        print(f"Failed to export metric data")
        raise Exception("Failed to export metric data")
    else:
        print(
            f"Exported metrics at {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

def verify_insight_type_and_state(insight_type, state):
    insights = get_insights()
    if insights['count'] == 0:
        return False
    for insights in insights['items']:
        if insights['type'] == insight_type and insights['state'] == state:
            return True
    return False


def post_onboard_action(action):
    payload = {
        "onboardState": action
    }
    return post(endpoints.TENANT_ONBOARD_URL, json.dumps(payload), 202)


def get_onboard_status():
    return get(endpoints.TENANT_ONBOARD_URL , print_body=False)


def get(endpoint, print_body=True):
    try:
        print(f"Sending GET request to {endpoint}")
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[i for i in range(400, 600)],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount('https://', adapter)
        response = session.get(endpoint, headers={"Content-Type": "application/json",
                                                   "Authorization": "Bearer " + os.getenv('CDO_TOKEN')}, timeout=180)
        response_payload = response.json()
        if print_body:
            print("Response: ", response_payload)
        assert response.status_code == 200, f"GET request to {endpoint} failed with status code {response.status_code}"
        return response_payload
    except Exception as e:
        print(f"Failed to send GET request to {endpoint}")
        raise e


def post(endpoint, payload=None, expected_return_code=200):
    try:
        print(f"Sending POST request to {endpoint} with payload {payload}")
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[i for i in range(400, 600)],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount('https://', adapter)
        response = session.post(endpoint, data=payload, headers={"Content-Type": "application/json",
                                                                  "Authorization": "Bearer " + os.getenv('CDO_TOKEN')}, timeout=180)
        print("Response: ", response)
        assert response.status_code == expected_return_code, f"POST request to {endpoint} failed with status code {response.status_code}"
        return response
    except Exception as e:
        print(f"Failed to send POST request to {endpoint} with payload {payload}")
        raise e



def delete(endpoint, expected_return_code=200):
    try:
        print(f"Sending DELETE request to {endpoint}")
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[i for i in range(400, 600)],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount('https://', adapter)
        response = session.delete(endpoint, headers={"Authorization": "Bearer " + os.getenv('CDO_TOKEN')}, timeout=180)
        print("Response: ", response)
        assert response.status_code == expected_return_code, f"DELETE request to {endpoint} failed with status code {response.status_code}"
    except Exception as e:
        print(f"Failed to send DELETE request to {endpoint}")
        raise e
