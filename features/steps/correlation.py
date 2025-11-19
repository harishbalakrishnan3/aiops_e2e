import logging
from behave import *


@step("confirm correlated metrics")
def step_impl(context):
    insight = context.matched_insight
    correlationMetrics = insight["data"]["correlationMetrics"]

    for row in context.table:
        metric_name = row["metric_name"]
        confidence = row["confidence"]

        found = False
        for correlationMetric in correlationMetrics:
            if (
                correlationMetric["metricName"] == metric_name
                and correlationMetric["correlationRank"] == confidence
            ):
                found = True
                break

        if not found:
            logging.error(
                f"Expected correlation metric {metric_name} with confidence {confidence} not found"
            )
            assert (
                False
            ), f"Expected correlation metric {metric_name} with confidence {confidence} not found"

    assert True
