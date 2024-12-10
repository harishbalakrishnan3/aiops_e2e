import json
import os
from datetime import datetime
import requests
from opentelemetry.exporter.prometheus_remote_write import (
    PrometheusRemoteWriteMetricsExporter,
)
from opentelemetry.sdk.metrics.export import MetricsData, MetricExportResult
from features.steps.env import get_endpoints

endpoints = get_endpoints()


def get_insights():
    return get(endpoints.INSIGHTS_URL)


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
    return get(endpoints.TENANT_ONBOARD_URL)


def get(endpoint, print_body=True):
    print(f"Sending GET request to {endpoint}")
    response = requests.get(endpoint, headers={"Content-Type": "application/json",
                                               "Authorization": "Bearer " + os.getenv('CDO_TOKEN')})
    response_payload = response.json()
    if print_body:
        print("Response: ", response_payload)
    assert response.status_code == 200, f"GET request to {endpoint} failed with status code {response.status_code}"
    return response_payload


def post(endpoint, payload=None, expected_return_code=200):
    print(f"Sending POST request to {endpoint} with payload {payload}")
    response = requests.post(endpoint, data=payload, headers={"Content-Type": "application/json",
                                                              "Authorization": "Bearer " + os.getenv('CDO_TOKEN')})
    print("Response: ", response)
    assert response.status_code == expected_return_code, f"POST request to {endpoint} failed with status code {response.status_code}"
    return response


def delete(endpoint, expected_return_code=200):
    print(f"Sending DELETE request to {endpoint}")
    response = requests.delete(endpoint, headers={"Authorization": "Bearer " + os.getenv('CDO_TOKEN')})
    print("Response: ", response)
    assert response.status_code == expected_return_code, f"DELETE request to {endpoint} failed with status code {response.status_code}"
