import time
from behave import *
from hamcrest import assert_that
from features.model import Device
from datetime import timedelta
from features.steps.utils import is_data_present


def is_anomaly_upper_lower_bounds_present(
    metric_name: str, device: Device, range: timedelta
) -> bool:
    query = 'query={metric_name}{{type="lower" , uuid="{uuid}"}} and on (uuid) {metric_name}{{type="lower" , uuid="{uuid}"}}'.format(
        uuid=device.device_record_uid, metric_name=metric_name
    )
    return is_data_present(query, range)


@step(
    "keep checking if {metric_name} upper and lower bounds are ingested for {duration} minute(s)"
)
def step_impl(context, metric_name, duration):
    for i in range(int(duration)):
        device: Device = context.scenario_to_device_map[context.scenario]
        if is_anomaly_upper_lower_bounds_present(
            metric_name, device, timedelta(minutes=10)
        ):
            assert_that(True)
            return
        time.sleep(60)
    assert_that(False)
