import time
from behave import *
from hamcrest import assert_that
from features.model import Device
from datetime import timedelta
from features.steps.utils import is_data_present


def is_anomaly_upper_lower_bounds_present(device: Device, range: timedelta) -> bool:
    query = 'query=conn_stats_threshold{{type="lower" , uuid="{uuid}"}} and on (uuid) conn_stats_threshold{{type="lower" , uuid="{uuid}"}}'.format(
        uuid=device.device_record_uid
    )
    return is_data_present(query, range)


@step("keep checking if upper and lower bounds are ingested for {duration} minute(s)")
def step_impl(context, duration):
    for i in range(int(duration)):
        device: Device = context.scenario_to_device_map[context.scenario]
        if is_anomaly_upper_lower_bounds_present(device, timedelta(minutes=10)):
            assert_that(True)
            return
        time.sleep(60)
    assert_that(False)
