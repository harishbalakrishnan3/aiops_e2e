import json
import os
import logging
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


def get_insights(query_params=None, fields=None):
    url = endpoints.INSIGHTS_URL

    # Build query parameters
    params = []

    # Add query parameter if specified (e.g., q=uid:xxxx-xxxxxx)
    if query_params:
        params.append(f"q={query_params}")

    # Add fields parameter if specified (e.g., fields=insightType,impactedResources,insightState)
    if fields:
        params.append(f"fields={fields}")

    # Note: If no fields specified, fetch entire insights without field restrictions

    # Construct final URL with parameters
    if params:
        url += "?" + "&".join(params)

    return get(url, print_body=False)


def delete_insights(limit=200, offset=0):
    url = endpoints.INSIGHTS_URL
    params = [f"limit={limit}", f"offset={offset}"]
    url += "?" + "&".join(params)
    delete(url)


def delete_all_insights():
    # First get the total count of insights
    insights_response = get_insights()
    total_count = insights_response.get("count", 0)
    batch_size = 200

    if total_count == 0:
        logging.info("No insights found to delete.")
        return

    logging.info(f"Found {total_count} insights. Deleting in batches of {batch_size}.")

    # Delete in batches
    offset = 0
    while offset < total_count:
        logging.info(f"Deleting insights batch: offset={offset}, limit={batch_size}")
        delete_insights(limit=batch_size, offset=offset)
        offset += batch_size

    logging.info(f"Successfully deleted all {total_count} insights.")


def remote_write(metrics_data: MetricsData):
    exporter = PrometheusRemoteWriteMetricsExporter(
        endpoint=get_endpoints().DATA_INGEST_URL,
        headers={"Authorization": "Bearer " + os.getenv("CDO_TOKEN")},
    )

    result = exporter.export(metrics_data)
    if result == MetricExportResult.FAILURE:
        logging.error("Failed to export metric data")
        raise Exception("Failed to export metric data")
    else:
        logging.info(
            f"Exported metrics at {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        )


def verify_insight_type_and_state(context, insight_type, state):
    # Use field projections to get only the fields we need for initial filtering (including uid for later query)
    insights = get_insights(fields="insightType,impactedResources,insightState,uid")
    if insights["count"] == 0:
        return False
    for insight in insights["items"]:
        if insight["type"] == insight_type:
            # first find the insight object that has correct type and verify state and content of insight , This way we only log error when the state or content fails
            if (
                insight["state"] == state
                and insight["impactedResources"][0]["uid"]
                == context.scenario_to_device_map[context.scenario].aegis_device_uid
                and insight["impactedResources"][0]["name"]
                == context.scenario_to_device_map[context.scenario].device_name
                and True
                if context.scenario_to_device_map[context.scenario].container_type
                is None
                else "member" in insight["impactedResources"][0]
            ):
                # Fetch the complete insight object using its uid
                insight_uid = insight["uid"]
                complete_insight_response = get_insights(
                    query_params=f"uid:{insight_uid}"
                )
                if complete_insight_response["count"] > 0:
                    context.matched_insight = complete_insight_response["items"][0]
                else:
                    logging.error(
                        f"Failed to fetch complete insight for uid: {insight_uid}"
                    )
                    context.matched_insight = insight  # fallback to partial insight
                return True
            else:
                logging.debug(
                    f"Expected insight type: {insight_type} - state: {state} - device name: {context.scenario_to_device_map[context.scenario].device_name} - device id: {context.scenario_to_device_map[context.scenario].aegis_device_uid}"
                )
                logging.debug(f"Actual Insight: {insight}")
    logging.info(
        f"Failed to find an insight with type: {insight_type} and state: {state} for device name: {context.scenario_to_device_map[context.scenario].device_name} and device id: {context.scenario_to_device_map[context.scenario].aegis_device_uid}"
    )
    return False


def post_onboard_action():
    return post(endpoints.TENANT_ONBOARD_V2_URL, expected_return_code=202)


def post_offboard_action():
    payload = {"cleanupType": "SHALLOW"}
    return post(endpoints.TENANT_OFFBOARD_V2_URL, json.dumps(payload), 202)


def get_onboard_status():
    return get(endpoints.TENANT_STATUS_V2_URL, print_body=True)


def update_device_data(device_uid):
    logging.info(f"Updating device data for {device_uid} to have 250 max sessions")
    payload = {"device_uid": device_uid, "max_vpn_sessions": 250}
    return post(endpoints.CAPACITY_ANALYTICS_DEVICE_DATA_URL, json.dumps(payload), 201)


def get(endpoint, print_body=True):
    try:
        logging.debug(f"Sending GET request to {endpoint}")
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[i for i in range(400, 600)],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        response = session.get(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + os.getenv("CDO_TOKEN"),
            },
            timeout=180,
        )
        response_payload = response.json()
        if print_body:
            logging.info(
                f"Response status: {response.status_code}, Response: {response_payload}"
            )
        assert (
            response.status_code == 200
        ), f"GET request to {endpoint} failed with status code {response.status_code}"
        return response_payload
    except Exception as e:
        logging.error(f"Failed to send GET request to {endpoint}: {str(e)}")
        raise e


def post(endpoint, payload=None, expected_return_code=200):
    try:
        logging.info(f"Sending POST request to {endpoint} with payload {payload}")
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[i for i in range(400, 600)],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        response = session.post(
            endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + os.getenv("CDO_TOKEN"),
            },
            timeout=180,
        )
        logging.info(
            f"Response status: {response.status_code}, Response: {response.text}"
        )
        assert (
            response.status_code == expected_return_code
        ), f"POST request to {endpoint} failed with status code {response.status_code}"
        return response
    except Exception as e:
        logging.error(
            f"Failed to send POST request to {endpoint} with payload {payload}: {str(e)}"
        )
        raise e


def delete(endpoint, expected_return_code=200):
    try:
        logging.info(f"Sending DELETE request to {endpoint}")
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[i for i in range(400, 600)],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        response = session.delete(
            endpoint,
            headers={"Authorization": "Bearer " + os.getenv("CDO_TOKEN")},
            timeout=180,
        )
        logging.info(
            f"Response status: {response.status_code}, Response: {response.text}"
        )
        assert (
            response.status_code == expected_return_code
        ), f"DELETE request to {endpoint} failed with status code {response.status_code}"
    except Exception as e:
        logging.error(f"Failed to send DELETE request to {endpoint}: {str(e)}")
        raise e
