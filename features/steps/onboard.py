import time

from behave import *
from hamcrest import assert_that

from features.steps.cdo_apis import post_onboard_action, get_onboard_status


@step('perform a tenant {action}')
def step_impl(context, action):
    if action.upper() == "ONBOARD":
        post_onboard_action("ONBOARD")
    else:
        post_onboard_action("OFFBOARD")


@step('the tenant onboard state is {state}')
def step_impl(context, state):
    response = get_onboard_status()
    assert_that(response["onboardState"] == state)


@step('verify if the onboard status changes to {state} with a timeout of {timeout} minute(s)')
def step_impl(context, state, timeout):
    for i in range(int(timeout) * 6):
        try:
            context.execute_steps(
                f"\nThen the tenant onboard state is {state}")
        except:
            time.sleep(10)
            continue
        else:
            return
