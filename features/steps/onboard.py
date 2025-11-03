import time
import logging

from behave import *
from hamcrest import assert_that

from features.steps.cdo_apis import (
    post_onboard_action,
    post_offboard_action,
    get_onboard_status,
)
from features.steps.utils import compute_onboard_status_ignoring_fmc_export


@step("perform a tenant {action}")
def step_impl(context, action):
    if action.upper() == "ONBOARD":
        post_onboard_action()
    else:
        post_offboard_action()


@step("the tenant onboard state is {state}")
def step_impl(context, state):
    response = get_onboard_status()
    # Compute status ignoring FMC_METRIC_EXPORT which can take hours
    computed_status = compute_onboard_status_ignoring_fmc_export(response)
    logging.info(
        f"Computed onboard status (ignoring FMC_METRIC_EXPORT): {computed_status}"
    )
    assert_that(computed_status == state)


@step(
    "verify if the onboard status changes to {state} with a timeout of {timeout} minute(s)"
)
def step_impl(context, state, timeout):
    timeout_minutes = int(timeout)
    max_attempts = timeout_minutes * 6  # 6 attempts per minute (every 10 seconds)

    for attempt in range(max_attempts):
        try:
            context.execute_steps(f"\nThen the tenant onboard state is {state}")
            logging.info(
                f"Onboard status reached {state} after {(attempt + 1) * 10} seconds"
            )
            return  # Success - exit the step
        except AssertionError as e:
            if attempt < max_attempts - 1:
                # Not the last attempt, wait and retry
                logging.debug(
                    f"Attempt {attempt + 1}/{max_attempts}: Status not yet {state}, retrying in 10 seconds..."
                )
                time.sleep(10)
            else:
                # Last attempt failed, raise the error
                logging.error(
                    f"Timeout after {timeout_minutes} minute(s): Onboard status did not reach {state}"
                )
                raise AssertionError(
                    f"Onboard status did not reach {state} within {timeout_minutes} minute(s). Last error: {str(e)}"
                )


@step("verify status action is not in {action_state} state")
def step_impl(context, action_state):
    response = get_onboard_status()
    if "status" in response:
        assert_that(response["status"]["action"] != action_state)
