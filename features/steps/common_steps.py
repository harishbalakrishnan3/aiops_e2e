import time

from behave import *
from hamcrest import assert_that

from features.steps.cdo_apis import delete_insights, verify_insight_type_and_state

@step('the insights are cleared')
def step_impl(context):
    delete_insights()


@step('verify if an {insight_type} insight with state {insight_state} is created')
def step_impl(context, insight_type, insight_state):
    assert_that(verify_insight_type_and_state(insight_type, insight_state))


@step('verify if an {insight_type} insight with state {insight_state} is created with a timeout of {timeout} minutes')
def step_impl(context, insight_type, insight_state, timeout):
    for i in range(int(timeout) * 6):
        if verify_insight_type_and_state(insight_type, insight_state):
            assert_that(True)
            return
        time.sleep(10)
    assert_that(verify_insight_type_and_state(insight_type, insight_state))


@step('keep checking for {duration} minute(s) if an {insight_type} insight with state {insight_state} is created')
def step_impl(context, duration, insight_type, insight_state):
    for i in range(int(duration)):
        if verify_insight_type_and_state(insight_type, insight_state):
            assert_that(True)
            return
        time.sleep(60)
    assert_that(False)


@step('wait for {duration} {unit}')
def step_impl(context, duration, unit):
    if unit == "seconds" or unit == "second":
        time.sleep(int(duration))
    elif unit == "minutes" or unit == "minute":
        time.sleep(int(duration) * 60)
    else:
        raise Exception(f"Unsupported unit: {unit}")