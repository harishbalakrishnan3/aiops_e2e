from features.steps.cdo_apis import get_insights
from behave import *


@step('check elephant flow enhanced insight data')
def step_impl(context):
    insight = context.matched_insight
    if(len(insight["data"]["flows"])!=1):
        print(f"Expected 1 flow but got {len(insight['data']['flows'])}")
        assert False
    flow = insight["data"]["flows"][0]
    
    expected_flow_data = {
        "sourceIp": "10.10.0.98",
        "destinationIp": "20.20.0.98",
        "sourcePort": 43000,
        "destinationPort": 98,
        "protocol": 6,  
        "application": {
                        "id": 929,
                        "name": "YouTube",
                        "description": "A video-sharing website on which users can upload, share, and view videos.",
                        "riskIndex": 4
                    }
    }

    del flow["stats"]
    if(flow != expected_flow_data):
        print(f"Expected flow data {expected_flow_data} but got {flow}")
        assert False
    


@step('check elephant flow basic insight data')
def step_impl(context):
    insight = context.matched_insight
    if(len(insight["data"]["flows"])!=1):
        print(f"Expected 1 flow but got {len(insight['data']['flows'])}")
        assert False
    flow = insight["data"]["flows"][0]
    
    expected_flow_data = {
        "sourceIp": "10.10.0.98",
        "destinationIp": "20.20.1.98",
        "sourcePort": 43000,
        "destinationPort": 99,
        "protocol": 6,  
        "application": {
                    "id": 0,
                    "name": None,
                    "description": None,
                    "riskIndex": 0
                }
    }

    del flow["stats"]
    if(flow != expected_flow_data):
        print(f"Expected flow data {expected_flow_data} but got {flow}")
        assert False
    

