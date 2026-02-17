import time
from behave import *
from hamcrest import assert_that

from features.model import Device
from datetime import timedelta, datetime, timezone

from features.steps.metrics import instant_remote_write
from features.steps.time_series_generator import (
    generate_timeseries,
    TimeConfig,
    SeriesConfig,
    TransitionConfig,
    generate_spikes,
)
from features.steps.utils import is_data_present, get_common_labels


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


@step("push data that is intermittently anomalous for {duration} minute(s)")
def step_impl(context, duration):
    labels = {"conn_stats": "connection", "description": "in_use"} | get_common_labels(
        context, timedelta(days=14)
    )
    now = datetime.now(timezone.utc)
    live_data = generate_timeseries(
        time_config=TimeConfig(
            series_config=SeriesConfig(
                start_time=now,
                duration=timedelta(minutes=int(duration)),
                start_value=200,
                end_value=200,
            ),
            transition_config=TransitionConfig(
                start_time=now,
                transition_window=timedelta(minutes=int(duration)),
            ),
        ),
    )

    live_data["y"] = generate_spikes(
        spike_pattern=[0, 1, 1, 0, 0], spike_multiplier=5, ts_values=live_data["y"]
    )

    live_data_list = live_data["y"].tolist()

    for i in range(int(duration)):
        instant_remote_write("conn_stats", labels, live_data_list[i])
        time.sleep(60)

    pass
