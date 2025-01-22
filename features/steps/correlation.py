from behave import *

@step('confirm correlated metrics')
def step_impl(context):
    for row in context.table:
        metric_name = row["metric_name"]
        confidence  = row["confidence"]

        insight = context.matched_insight
        correlationMetrics = insight["data"]["correlationMetrics"]

        for correlationMetric in correlationMetrics:
            if correlationMetric["metricName"] == metric_name:
                if correlationMetric["correlationRank"] == confidence: 
                    return True
        
        print(f"Expected correlation metric {metric_name} with confidence {confidence} not found")
        assert False
                
