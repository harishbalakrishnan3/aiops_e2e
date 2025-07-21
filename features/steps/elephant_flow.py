from behave import *
import json
import logging


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
