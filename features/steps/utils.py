import copy
from datetime import timedelta

from mockseries.noise import GaussianNoise
from mockseries.seasonality import DailySeasonality
from mockseries.trend import LinearTrend


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