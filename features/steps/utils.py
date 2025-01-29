import copy
from datetime import timedelta , datetime
from typing import Any

from mockseries.noise import GaussianNoise ,RedNoise
from mockseries.seasonality import DailySeasonality
from mockseries.trend import LinearTrend , Switch
from mockseries.transition import LinearTransition
from mockseries.utils import datetime_range
from features.model import ScenarioEnum , Device
from features.steps.env import get_endpoints
from features.steps.cdo_apis import get


def store_ts_in_context(context, labels, key, metric_name):
    ts = copy.deepcopy(labels)
    if metric_name not in context.timeseries.keys():
        context.timeseries[metric_name] = {}
    context.timeseries[metric_name][key] = ts
    print(f"Timeseries in context: {context.timeseries}")

def get_label_map(context, label_string: str , duration:timedelta):
    common_labels = get_common_labels(context, duration)

    label_map = convert_str_list_to_dict(label_string)
    if "tenant_uuid" not in label_map and context.tenant_id is None:
        raise Exception("Tenant ID not found in context")
    if "uuid" not in label_map and "uuid" not in common_labels:
        raise Exception("Device ID not found in context")
    
    return label_map | common_labels

def get_common_labels(context, duration:timedelta):
    if context.scenario in  context.scenario_to_device_map:
        device = context.scenario_to_device_map[context.scenario]
    else:
        device = get_appropriate_device(context , duration)
        print("Selected device: ", device)
        context.scenario_to_device_map[context.scenario] = device

    return {
        "tenant_uuid": context.tenant_id,
        "uuid": device.device_record_uid
    }

def convert_str_list_to_dict(s):
    if not s:
        return {}
    return dict(map(lambda x: (x.split('=')[0].strip(), x.split('=')[1].strip()), s.split(',')))


def get_appropriate_device(context , duration) -> Device:
    """
    Pickup a device for by scenario . Find a devuce where the to be ingested data is not present in the duration specified . This will avoid data ingwstion failures due to existing data in the prometheus

    :param context: behave context
    :param duration: duration for which data will be ingested
    """

    query=""
    available_devices = context.devices
    match context.scenario:
        case ScenarioEnum.ELEPHANTFLOW_ENHANCED|  ScenarioEnum.ELEPHANTFLOW_LEGACY:
            query = "query=efd_cpu_usage{{uuid=\"{uuid}\"}}"
        case ScenarioEnum.CORRELATION_CPU_LINA:
            query = "query=cpu{{cpu=~\"lina_cp_avg|lina_dp_avg\" , uuid=\"{uuid}\"}} or rate(interface{{description=~\"input_bytes|input_packets\" ,interface=\"all\" , uuid=\"{uuid}\"}}[4m]) or conn_stats{{conn_stats=\"connection\", description=\"in_use\",  uuid=\"{uuid}\"}} or deployed_configuration{{deployed_configuration=\"number_of_ACEs\"  , uuid=\"{uuid}\"}} or sum(rate(interface{{description=\"drop_packets\", uuid=\"{uuid}\"}}[4m])) by (uuid , description)"
        case ScenarioEnum.CORRELATION_CPU_SNORT:
            query = "query=cpu{{cpu=~\"snort_avg|lina_cp_avg\" , uuid=\"{uuid}\"}} or rate(interface{{description=~\"input_bytes|input_packets|input_avg_packet_size\" ,interface=\"all\" , uuid=\"{uuid}\"}}[4m]) or conn_stats{{conn_stats=\"connection\", description=\"in_use\",  uuid=\"{uuid}\"}} or snort{{description=\"denied_flow_events\",snort=\"stats\" , uuid=\"{uuid}\"}} or snort3_perfstats{{snort3_perfstats=\"concurrent_elephant_flows\", uuid=\"{uuid}\"}} or rate(asp_drops{{asp_drops=\"snort-busy-not-fp\", uuid=\"{uuid}\"}}[4m])"
        case ScenarioEnum.CORRELATION_MEM_LINA:
            query = "query=mem{{mem=\"used_percentage_lina\", uuid=\"{uuid}\"}} or rate(interface{{description=~\"input_bytes|input_packets\" ,interface=\"all\" , uuid=\"{uuid}\"}}[4m]) or conn_stats{{conn_stats=\"connection\", description=\"in_use\",  uuid=\"{uuid}\"}} or deployed_configuration{{deployed_configuration=\"number_of_ACEs\"  , uuid=\"{uuid}\"}}"
        case ScenarioEnum.CORRELATION_MEM_SNORT:
            query = "query=mem{{mem=\"used_percentage_snort\", uuid=\"{uuid}\"}} or rate(interface{{description=~\"input_bytes|input_packets\" ,interface=\"all\" , uuid=\"{uuid}\"}}[4m]) or conn_stats{{conn_stats=\"connection\", description=\"in_use\",  uuid=\"{uuid}\"}}"
        case ScenarioEnum.CORRELATION_MEM_SNORT:
            query = "query=mem{{mem=\"used_percentage_snort\", uuid=\"{uuid}\"}} or rate(interface{{description=~\"input_bytes|input_packets\" ,interface=\"all\" , uuid=\"{uuid}\"}}[4m]) or conn_stats{{conn_stats=\"connection\", description=\"in_use\",  uuid=\"{uuid}\"}}"
        case ScenarioEnum.RAVPN_FORECAST:
            available_devices = [device for device in  context.devices if device.ra_vpn_enabled == True]
            query = "query=vpn{{uuid=\"{uuid}\"}}"
        case _:
            print("No matching scenarios found , picking up the last available device")
            return context.devices[-1]
    return find_device_available_for_data_ingestion(available_devices ,  query , duration)

def find_device_available_for_data_ingestion(available_devices:list ,  query:str ,  duration:timedelta):
    for device in available_devices:
        if is_data_not_present(query.format(uuid=device.device_record_uid) , duration):
            return device
    print("No device available for ingestion , Failing test")
    raise("No device available for ingestion")


def is_data_not_present(query:str , duration:timedelta , step="5m"):
    # Calculate the start and end times
    start_time = datetime.now() - duration
    end_time = datetime.now() 

    # Convert to epoch seconds
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    endpoint = f"{get_endpoints().PROMETHEUS_RANGE_QUERY_URL}?{query}&start={start_time_epoch}&end={end_time_epoch}&step={step}"
    print(endpoint)
    response = get(endpoint, print_body=False)
    if len(response["data"]["result"]) > 0:
        return False

    return True


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

    noise = RedNoise(mean=0, std=2, correlation=0.5 , random_seed=42)

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
        "labels": get_label_map(context, label_string , timedelta(minutes=duration))
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