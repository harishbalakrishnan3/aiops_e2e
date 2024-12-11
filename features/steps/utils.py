import copy
from datetime import timedelta , datetime
from typing import Any

from mockseries.noise import GaussianNoise ,RedNoise
from mockseries.seasonality import DailySeasonality
from mockseries.trend import LinearTrend , Switch
from mockseries.transition import LinearTransition
from mockseries.utils import datetime_range


def store_ts_in_context(context, labels, key, metric_name):
    ts = copy.deepcopy(labels)
    if metric_name not in context.timeseries.keys():
        context.timeseries[metric_name] = {}
    context.timeseries[metric_name][key] = ts
    print(f"Timeseries in context: {context.timeseries}")

def get_label_map(context, label_string: str):
    label_map = convert_str_list_to_dict(label_string)
    if "tenant_uuid" not in label_map and context.tenant_id is None:
        raise Exception("Tenant ID not found in context")
    if "uuid" not in label_map and context.device_id is None:
        raise Exception("Device ID not found in context")
    return label_map | {
        "tenant_uuid": context.tenant_id,
        "uuid": context.device_id
    }

def convert_str_list_to_dict(s):
    return dict(map(lambda x: (x.split('=')[0].strip(), x.split('=')[1].strip()), s.split(',')))


def generate_ts(trend_config, seasonality_config, noise_config, time_points):
    trend = LinearTrend(coefficient=trend_config['coefficient'], time_unit=timedelta(hours=trend_config['time_unit']),
                        flat_base=trend_config['flat_base'])
    seasonality = DailySeasonality(seasonality_config)
    noise = GaussianNoise(mean=noise_config['mean'], std=noise_config['std'])
    timeseries = trend + seasonality + noise
    ts_values = timeseries.generate(time_points=time_points)
    return ts_values

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
        "labels": get_label_map(context, label_string)
    }

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