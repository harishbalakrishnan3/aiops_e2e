import json
import logging
from datetime import datetime

from behave import *


@step("check elephant flow insight data")
def step_impl(context):
    insight = context.matched_insight
    expected_flow_data = json.loads(context.text)["flows"]
    expected_length = len(expected_flow_data)
    if len(insight["data"]["flows"]) != expected_length:
        logging.info(
            f"Expected {expected_length} flow but got {len(insight['data']['flows'])}"
        )
        assert False
    flows = insight["data"]["flows"]

    # remove timeseries data before assertion
    for flow in flows:
        del flow["stats"]

    if flows != expected_flow_data:
        logging.error(f"Expected flow data {expected_flow_data} but got {flows}")
        assert False


@step("capture the current insight timestamp")
def step_impl(context):
    """Capture both createdTime and updatedTime from the current matched insight"""
    insight = context.matched_insight

    # Log the insight structure to help debug
    logging.info(f"Insight keys: {list(insight.keys())}")

    # Verify both createdTime and updatedTime exist
    if "createdTime" not in insight or "updatedTime" not in insight:
        logging.error(
            f"Missing timestamp fields. Available fields: {list(insight.keys())}"
        )
        logging.error(f"Full insight: {insight}")
        assert False, "Insight must have both 'createdTime' and 'updatedTime' fields"

    context.captured_created_time = insight["createdTime"]
    context.captured_updated_time = insight["updatedTime"]
    context.captured_time = datetime.now()

    logging.info(f"Captured insight createdTime: {context.captured_created_time}")
    logging.info(f"Captured insight updatedTime: {context.captured_updated_time}")

    # Capture the insight UID - required for tracking the same insight
    if "uid" not in insight:
        logging.error(
            f"Missing 'uid' field in insight. Available fields: {list(insight.keys())}"
        )
        assert False, "Insight must have 'uid' field to track updates"

    context.captured_insight_uid = insight["uid"]
    logging.info(f"Captured insight UID: {context.captured_insight_uid}")


@step("verify the insight timestamp has been updated")
def step_impl(context):
    """Verify that updatedTime changed while createdTime stayed the same (proving update, not recreation)"""
    import time as time_module

    from features.steps.cdo_apis import get_insights

    previous_created_time = context.captured_created_time
    previous_updated_time = context.captured_updated_time

    # Check that at least 1.5 minutes have elapsed since capture
    time_elapsed = (datetime.now() - context.captured_time).total_seconds()
    if time_elapsed < 90:  # 1.5 minutes = 90 seconds
        logging.warning(
            f"Only {time_elapsed:.0f} seconds elapsed since timestamp capture. Elephant flow updates require at least 90 seconds (1.5 minutes) between updates."
        )

    logging.info(f"Previous createdTime: {previous_created_time}")
    logging.info(f"Previous updatedTime: {previous_updated_time}")
    logging.info(f"Polling for timestamp update (max 3 minutes)...")

    # Poll for up to 3 minutes (180 seconds) for timestamp to update
    max_attempts = 18  # 18 attempts * 10 seconds = 180 seconds
    attempt = 0

    while attempt < max_attempts:
        # Fetch fresh insight using the ORIGINAL captured UID
        if not hasattr(context, "captured_insight_uid"):
            logging.error(
                "No captured insight UID found. Make sure 'capture the current insight timestamp' step was executed first."
            )
            assert False

        insight_uid = context.captured_insight_uid
        complete_insight_response = get_insights(query_params=f"uid:{insight_uid}")
        if complete_insight_response["count"] == 0:
            logging.error(f"Failed to fetch insight with uid: {insight_uid}")
            assert False

        insight = complete_insight_response["items"][0]

        # Verify both timestamp fields exist
        if "createdTime" not in insight or "updatedTime" not in insight:
            logging.error(
                f"Missing timestamp fields in refreshed insight. Available fields: {list(insight.keys())}"
            )
            assert False

        current_created_time = insight["createdTime"]
        current_updated_time = insight["updatedTime"]

        # Parse timestamps
        try:
            prev_created_dt = datetime.fromisoformat(
                previous_created_time.replace("Z", "+00:00")
            )
            curr_created_dt = datetime.fromisoformat(
                current_created_time.replace("Z", "+00:00")
            )
            prev_updated_dt = datetime.fromisoformat(
                previous_updated_time.replace("Z", "+00:00")
            )
            curr_updated_dt = datetime.fromisoformat(
                current_updated_time.replace("Z", "+00:00")
            )

            # CRITICAL VERIFICATION: createdTime must NOT change (same insight)
            if curr_created_dt != prev_created_dt:
                logging.error(
                    f"createdTime changed! This means the insight with UID {insight_uid} was modified incorrectly."
                )
                logging.error(f"Previous createdTime: {prev_created_dt}")
                logging.error(f"Current createdTime: {curr_created_dt}")
                logging.error(
                    f"This indicates a backend issue - createdTime should never change for an existing insight."
                )
                assert (
                    False
                ), "Insight createdTime changed (backend bug or insight recreation)"

            time_diff = (curr_updated_dt - prev_updated_dt).total_seconds()

            # Check if updatedTime increased (insight was updated)
            if curr_updated_dt > prev_updated_dt:
                logging.info(
                    f"✓ createdTime unchanged: {current_created_time} (same insight)"
                )
                logging.info(
                    f"✓ updatedTime changed: {previous_updated_time} → {current_updated_time}"
                )
                logging.info(
                    f"✓ Insight successfully UPDATED (not recreated) after {attempt * 10} seconds"
                )
                logging.info(f"✓ Update delta: {time_diff} seconds")

                # Verify the update happened after at least 1.5 minutes from initial detection
                if time_diff < 90:
                    logging.warning(
                        f"updatedTime delta ({time_diff}s) is less than the expected 1.5 minute (90s) minimum update interval"
                    )

                # Update context with fresh insight
                context.matched_insight = insight
                assert True
                return
            else:
                logging.debug(
                    f"Attempt {attempt + 1}/{max_attempts}: updatedTime not yet changed."
                )
                logging.debug(f"  createdTime: {curr_created_dt} (unchanged ✓)")
                logging.debug(
                    f"  updatedTime: {curr_updated_dt} (waiting for change...)"
                )
        except Exception as e:
            logging.error(f"Failed to parse timestamps: {e}")
            logging.error(
                f"Previous createdTime: {previous_created_time}, Current: {current_created_time}"
            )
            logging.error(
                f"Previous updatedTime: {previous_updated_time}, Current: {current_updated_time}"
            )
            assert False

        attempt += 1
        if attempt < max_attempts:
            time_module.sleep(10)

    # If we exhausted all attempts
    logging.error(
        f"updatedTime was not updated after {max_attempts * 10} seconds (max polling time)."
    )
    logging.error(f"createdTime: {previous_created_time} → {current_created_time}")
    logging.error(f"updatedTime: {previous_updated_time} → {current_updated_time}")
    assert False, "Insight timestamp was not updated within the polling period"
