import logging
from behave import *


@step("confirm correlated metrics")
def step_impl(context):
    insight = context.matched_insight
    correlationMetrics = insight["data"]["correlationMetrics"]

    for row in context.table:
        metric_name = row["metric_name"]
        confidence = row.get("confidence", None)

        found = False
        for correlationMetric in correlationMetrics:
            if correlationMetric["metricName"] == metric_name:
                # If confidence is provided, also check confidence match
                if confidence is not None:
                    if correlationMetric["correlationRank"] == confidence:
                        found = True
                        break
                else:
                    # If no confidence column, just metric name match is enough
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
