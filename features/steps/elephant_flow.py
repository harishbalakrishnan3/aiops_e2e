import json
import logging
import os
import time as time_module
from datetime import datetime
from behave import *
from features.steps.cdo_apis import get_insights
from features.steps.env import Path


@step("check elephant flow insight data from {filename}")
def step_impl(context, filename):
    """Verify elephant flow insight data matches expected flows from JSON file"""
    if not hasattr(context, "matched_insight") or context.matched_insight is None:
        logging.error(
            "No matched insight found in context. Ensure verification step ran successfully."
        )
        assert False, "matched_insight is None or not set in context"

    insight = context.matched_insight

    # Load expected flow data from external JSON file
    flow_data_file = os.path.join(Path.RESOURCES_DIR, "elephant_flow", filename)

    if not os.path.exists(flow_data_file):
        logging.error(f"Flow data file not found: {flow_data_file}")
        assert False, f"Resource file {filename} not found"

    with open(flow_data_file, "r") as f:
        expected_flow_data = json.load(f)["flows"]

    expected_length = len(expected_flow_data)
    if len(insight["data"]["flows"]) != expected_length:
        logging.error(
            f"Expected {expected_length} flows but got {len(insight['data']['flows'])}"
        )
        assert (
            False
        ), f"Flow count mismatch: expected {expected_length}, got {len(insight['data']['flows'])}"

    flows = insight["data"]["flows"]

    # Remove timeseries data before assertion
    for flow in flows:
        del flow["stats"]

    def flow_sort_key(flow):
        return (
            flow["sourceIp"],
            flow["sourcePort"],
            flow["destinationIp"],
            flow["destinationPort"],
        )

    flows_sorted = sorted(flows, key=flow_sort_key)
    expected_sorted = sorted(expected_flow_data, key=flow_sort_key)

    if flows_sorted != expected_sorted:
        logging.error(f"Expected flow data {expected_sorted} but got {flows_sorted}")
        assert False, "Flow data mismatch"


@step(
    "verify the insight timestamp has been updated with a timeout of {timeout} minute(s)"
)
def step_impl(context, timeout):
    """Verify that updatedTime changed (proving update, not recreation)"""
    if not hasattr(context, "matched_insight") or context.matched_insight is None:
        logging.error("No matched insight found in context.")
        assert False, "matched_insight is None or not set in context"

    # Capture initial timestamps from current insight
    initial_insight = context.matched_insight
    if "updatedTime" not in initial_insight or "uid" not in initial_insight:
        logging.error(
            f"Missing required fields. Available: {list(initial_insight.keys())}"
        )
        assert False, "Insight must have 'updatedTime' and 'uid' fields"

    previous_updated_time = initial_insight["updatedTime"]
    insight_uid = initial_insight["uid"]

    logging.info(f"Initial updatedTime: {previous_updated_time}")
    logging.info(f"Insight UID: {insight_uid}")
    logging.info(f"Polling for timestamp update (max {timeout} minutes)...")

    # Calculate polling parameters
    timeout_seconds = int(timeout) * 60
    poll_interval = 10  # Poll every 10 seconds
    max_attempts = timeout_seconds // poll_interval
    attempt = 0

    while attempt < max_attempts:
        # Fetch fresh insight using the original UID
        complete_insight_response = get_insights(query_params=f"uid:{insight_uid}")
        if complete_insight_response["count"] == 0:
            logging.error(f"Failed to fetch insight with uid: {insight_uid}")
            assert False, f"Insight with UID {insight_uid} not found"

        insight = complete_insight_response["items"][0]

        if "updatedTime" not in insight:
            logging.error(
                f"Missing updatedTime in refreshed insight. Available: {list(insight.keys())}"
            )
            assert False, "Insight missing updatedTime field"

        current_updated_time = insight["updatedTime"]

        # Parse timestamps and compare
        try:
            prev_updated_dt = datetime.fromisoformat(
                previous_updated_time.replace("Z", "+00:00")
            )
            curr_updated_dt = datetime.fromisoformat(
                current_updated_time.replace("Z", "+00:00")
            )

            # Check if updatedTime increased (insight was updated)
            if curr_updated_dt > prev_updated_dt:
                time_diff = (curr_updated_dt - prev_updated_dt).total_seconds()
                logging.info(
                    f"updatedTime changed: {previous_updated_time} → {current_updated_time}"
                )
                logging.info(f"Insight successfully UPDATED after {time_diff} seconds")
                logging.info(f"Update delta: {time_diff} seconds")

                # Update context with fresh insight
                context.matched_insight = insight
                return
            else:
                logging.debug(
                    f"Attempt {attempt + 1}/{max_attempts}: updatedTime not yet changed."
                )
                logging.debug(
                    f"  Current updatedTime: {curr_updated_dt} (waiting for change...)"
                )
        except Exception as e:
            logging.error(f"Failed to parse timestamps: {e}")
            logging.error(
                f"Previous: {previous_updated_time}, Current: {current_updated_time}"
            )
            assert False, f"Timestamp parsing failed: {e}"

        attempt += 1
        if attempt < max_attempts:
            time_module.sleep(poll_interval)

    # If we exhausted all attempts
    logging.error(
        f"updatedTime was not updated after {timeout} minutes (max polling time)."
    )
    logging.error(f"updatedTime: {previous_updated_time} → {current_updated_time}")
    assert False, "Insight timestamp was not updated within the polling period"
