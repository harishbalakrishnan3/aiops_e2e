import time

from behave import *
from typing import Any
from features.steps.metrics import remote_write
from datetime import datetime
from mockseries.utils import datetime_range
from datetime import timedelta
from mockseries.noise import RedNoise
from mockseries.transition import LinearTransition
from mockseries.trend import Switch
from features.steps.utils import batch_remote_write
from utils import get_label_values


def generate_synthesized_ts_obj(context, metric_name: str, label_string: str, start_value: float, end_value: float,
                                spike_duration_minutes: int, start_spike_minute: int, duration: int):
    linear_transition = LinearTransition(
        transition_window=timedelta(minutes=spike_duration_minutes),
    )

    now = datetime.now()
    speed_switch = Switch(
        start_time=now + timedelta(minutes=start_spike_minute),
        base_value=start_value,
        switch_value=end_value,
        transition=linear_transition
    )

    noise = RedNoise(mean=0, std=2, correlation=0.5)

    time_series = speed_switch + noise

    time_points = datetime_range(
        granularity=timedelta(minutes=1),
        start_time=now,
        end_time=now + timedelta(minutes=duration),
    )
    ts_values = time_series.generate(time_points=time_points)

    return {
        "metric_name": metric_name,
        "values": ts_values,
        "labels": get_label_values(context, label_string)
    }


@then('push timeseries for next {duration} minutes of which send last {live_duration} minute(s) of timeseries in live mode')
def step_impl(context, duration , live_duration):
    synthesized_ts_list = []
    duration = int(duration)
    live_duration = int(live_duration)
    for row in context.table:
        start_value = float(row["start_value"])
        end_value = float(row["end_value"])
        start_spike_minute = int(row["start_spike_minute"])
        spike_duration_minutes = int(row["spike_duration_minutes"])
        label_string = row["label_values"]
        metric_name = row["metric_name"]

        synthesized_ts_obj = generate_synthesized_ts_obj(context=context,
                                                         metric_name=metric_name,
                                                         label_string=label_string,
                                                         start_value=start_value,
                                                         end_value=end_value,
                                                         start_spike_minute=start_spike_minute,
                                                         spike_duration_minutes=spike_duration_minutes,
                                                         duration=duration)
        synthesized_ts_list.append(synthesized_ts_obj)

    [synthesized_ts_list_for_batch_fill, synthesized_ts_list_for_live_fill] = split_data_for_batch_and_live_ingestion(
        synthesized_ts_list , live_duration)
    # batch data fill
    for synthesized_data in synthesized_ts_list_for_batch_fill:
        batch_remote_write(synthesized_data, timedelta(minutes=1))

    # Live data generation
    live_ingest_datapoints_count = len(synthesized_ts_list_for_live_fill[0]["values"])
    print(f"Pushing {live_ingest_datapoints_count} datapoints through live ingestion ")
    for i in range(live_ingest_datapoints_count):
        data_for_current_instant = []
        for value_dict in synthesized_ts_list_for_live_fill:
            data_for_current_instant.append({
                "metric_name": value_dict["metric_name"],
                "value": value_dict["values"][i],
                "labels": value_dict["labels"]
            })

        print("Pushing data for instant: ", data_for_current_instant)
        for data in data_for_current_instant:
            remote_write(context ,data["metric_name"] , data["labels"] , data["value"])
        time.sleep(60)


def split_data_for_batch_and_live_ingestion(synthesized_ts_list: [dict[str, Any]], live_duration: int):
    data_split_index = len(synthesized_ts_list[0]["values"]) - live_duration

    synthesized_ts_list_for_batch_fill = []
    synthesized_ts_list_for_live_fill = []
    for synthesized_ts in synthesized_ts_list:
        if data_split_index != 0:
            synthesized_ts_list_for_batch_fill.append({
                "metric_name": synthesized_ts["metric_name"],
                "values": synthesized_ts["values"][:data_split_index],
                "labels": synthesized_ts["labels"]
            })
        synthesized_ts_list_for_live_fill.append({
            "metric_name": synthesized_ts["metric_name"],
            "values": synthesized_ts["values"][data_split_index:],
            "labels": synthesized_ts["labels"]
        })
    return [synthesized_ts_list_for_batch_fill, synthesized_ts_list_for_live_fill]


def create_linear_ts(slope, intercept, points):
    ts = []
    for i in range(1, points + 1):
        ts.append(slope * i + intercept)
    return ts
