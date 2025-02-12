import copy
from datetime import timedelta, datetime
import time
from typing import List
import pandas as pd
from mockseries.transition import LinearTransition
from pydantic import BaseModel
from features.model import ScenarioEnum, Device
from features.steps.env import get_endpoints
from features.steps.cdo_apis import get
from time_series_generator import (
    NoiseConfig,
    generate_timeseries,
    TimeConfig,
    SeasonalityConfig,
)
from mockseries.seasonality.sinusoidal_seasonality import SinusoidalSeasonality


class GeneratedData(BaseModel, arbitrary_types_allowed=True):
    metric_name: str
    values: pd.DataFrame
    labels: dict


class Series(BaseModel, arbitrary_types_allowed=True):
    labels: str
    value: List[float]
    timestamp: List[int]


class BackfillData(BaseModel, arbitrary_types_allowed=True):
    metric_name: str
    series: List[Series]
    description: str = "Test Backfill Data"


# TODO : make this dynamic
HISTORICAL_DATA_FILE = "anomaly_historical_data.txt"


def store_ts_in_context(context, labels, key, metric_name):
    ts = copy.deepcopy(labels)
    if metric_name not in context.timeseries.keys():
        context.timeseries[metric_name] = {}
    context.timeseries[metric_name][key] = ts
    print(f"Timeseries in context: {context.timeseries}")


def get_label_map(context, label_string: str, duration: timedelta):
    common_labels = get_common_labels(context, duration)

    label_map = convert_str_list_to_dict(label_string)
    if "tenant_uuid" not in label_map and context.tenant_id is None:
        raise Exception("Tenant ID not found in context")
    if "uuid" not in label_map and "uuid" not in common_labels:
        raise Exception("Device ID not found in context")

    return label_map | common_labels


def get_common_labels(context, duration: timedelta):
    if context.scenario in context.scenario_to_device_map:
        device = context.scenario_to_device_map[context.scenario]
    else:
        device = get_appropriate_device(context, duration)
        print("Selected device: ", device)
        context.scenario_to_device_map[context.scenario] = device

    return {"tenant_uuid": context.tenant_id, "uuid": device.device_record_uid}


def convert_str_list_to_dict(s):
    if not s:
        return {}
    return dict(
        map(lambda x: (x.split("=")[0].strip(), x.split("=")[1].strip()), s.split(","))
    )


def get_appropriate_device(context, duration) -> Device:
    """
    Pickup a device for by scenario . Find a devuce where the to be ingested data is not present in the duration specified . This will avoid data ingwstion failures due to existing data in the prometheus

    :param context: behave context
    :param duration: duration for which data will be ingested
    """

    query = ""
    available_devices = context.devices

    scenario = context.scenario
    match scenario:
        case ScenarioEnum.ELEPHANTFLOW_ENHANCED | ScenarioEnum.ELEPHANTFLOW_LEGACY:
            query = 'query=efd_cpu_usage{{uuid="{uuid}"}}'
        case ScenarioEnum.CORRELATION_CPU_LINA:
            query = 'query=cpu{{cpu=~"lina_cp_avg|lina_dp_avg" , uuid="{uuid}"}} or rate(interface{{description=~"input_bytes|input_packets" ,interface="all" , uuid="{uuid}"}}[4m]) or conn_stats{{conn_stats="connection", description="in_use",  uuid="{uuid}"}} or deployed_configuration{{deployed_configuration="number_of_ACEs"  , uuid="{uuid}"}} or sum(rate(interface{{description="drop_packets", uuid="{uuid}"}}[4m])) by (uuid , description)'
        case ScenarioEnum.CORRELATION_CPU_SNORT:
            query = 'query=cpu{{cpu=~"snort_avg|lina_cp_avg" , uuid="{uuid}"}} or rate(interface{{description=~"input_bytes|input_packets|input_avg_packet_size" ,interface="all" , uuid="{uuid}"}}[4m]) or conn_stats{{conn_stats="connection", description="in_use",  uuid="{uuid}"}} or snort{{description="denied_flow_events",snort="stats" , uuid="{uuid}"}} or snort3_perfstats{{snort3_perfstats="concurrent_elephant_flows", uuid="{uuid}"}} or rate(asp_drops{{asp_drops="snort-busy-not-fp", uuid="{uuid}"}}[4m])'
        case ScenarioEnum.CORRELATION_MEM_LINA:
            query = 'query=mem{{mem="used_percentage_lina", uuid="{uuid}"}} or rate(interface{{description=~"input_bytes|input_packets" ,interface="all" , uuid="{uuid}"}}[4m]) or conn_stats{{conn_stats="connection", description="in_use",  uuid="{uuid}"}} or deployed_configuration{{deployed_configuration="number_of_ACEs"  , uuid="{uuid}"}}'
        case ScenarioEnum.CORRELATION_MEM_SNORT:
            query = 'query=mem{{mem="used_percentage_snort", uuid="{uuid}"}} or rate(interface{{description=~"input_bytes|input_packets" ,interface="all" , uuid="{uuid}"}}[4m]) or conn_stats{{conn_stats="connection", description="in_use",  uuid="{uuid}"}}'
        case ScenarioEnum.CORRELATION_MEM_SNORT:
            query = 'query=mem{{mem="used_percentage_snort", uuid="{uuid}"}} or rate(interface{{description=~"input_bytes|input_packets" ,interface="all" , uuid="{uuid}"}}[4m]) or conn_stats{{conn_stats="connection", description="in_use",  uuid="{uuid}"}}'
        case ScenarioEnum.RAVPN_FORECAST:
            available_devices = [
                device for device in context.devices if device.ra_vpn_enabled == True
            ]
            query = 'query=vpn{{uuid="{uuid}"}}'
        case ScenarioEnum.ANOMALY_CONNECTION:
            query = 'query=conn_stats{{uuid="{uuid}"}}'
        case ScenarioEnum.ANOMALY_THROUGHPUT:
            query = 'query=interface{{interface="all", description="input_bytes", uuid="{uuid}"}} or interface{{interface="all", description="output_bytes", uuid="{uuid}"}}'
        case _:
            print("No matching scenarios found , picking up the last available device")
            return context.devices[-1]
    return find_device_available_for_data_ingestion(available_devices, query, duration)


def find_device_available_for_data_ingestion(
    available_devices: list, query: str, duration: timedelta
):
    for device in available_devices:
        if not is_data_present(query.format(uuid=device.device_record_uid), duration):
            return device
    print("No device available for ingestion , Failing test")
    raise ("No device available for ingestion")


def is_data_present(query: str, duration: timedelta, step="5m"):
    # Calculate the start and end times
    start_time = datetime.now() - duration
    end_time = datetime.now()

    # Convert to epoch seconds
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    endpoint = f"{get_endpoints().PROMETHEUS_RANGE_QUERY_URL}?{query}&start={start_time_epoch}&end={end_time_epoch}&step={step}"
    print(endpoint)
    response = get(endpoint, print_body=False)
    return len(response["data"]["result"]) > 0


def generate_synthesized_ts_obj(
    context,
    metric_name: str,
    label_string: str,
    start_value: float,
    end_value: float,
    spike_duration_minutes: int,
    start_spike_minute: int,
    duration: int,
    time_offset: timedelta,
    metric_type: str = "gauge",
) -> GeneratedData:
    generated_data = generate_timeseries(
        TimeConfig(
            start_value=start_value,
            end_value=end_value,
            transition_start=timedelta(minutes=start_spike_minute),
            transition=LinearTransition(
                transition_window=timedelta(minutes=spike_duration_minutes)
            ),
            duration=timedelta(minutes=duration),
            time_offset=time_offset,
        ),
        seasonality_config=SeasonalityConfig(enable=False),
    )

    if metric_type == "counter":
        generated_data["y"] = generated_data["y"].cumsum()
    return GeneratedData(
        metric_name=metric_name,
        values=generated_data,
        labels=get_label_map(context, label_string, timedelta(minutes=duration)),
    )


def split_data_for_batch_and_live_ingestion(
    synthesized_ts_list: List[GeneratedData], live_duration: int
) -> List[List[GeneratedData]]:
    data_split_index = len(synthesized_ts_list[0].values) - live_duration

    synthesized_ts_list_for_batch_fill: List[GeneratedData] = []
    synthesized_ts_list_for_live_fill: List[GeneratedData] = []
    for synthesized_ts in synthesized_ts_list:
        if data_split_index != 0:
            synthesized_ts_list_for_batch_fill.append(
                GeneratedData(
                    metric_name=synthesized_ts.metric_name,
                    values=synthesized_ts.values[:data_split_index],
                    labels=synthesized_ts.labels,
                )
            )
        synthesized_ts_list_for_live_fill.append(
            GeneratedData(
                metric_name=synthesized_ts.metric_name,
                values=synthesized_ts.values[data_split_index:],
                labels=synthesized_ts.labels,
            )
        )
    return [synthesized_ts_list_for_batch_fill, synthesized_ts_list_for_live_fill]


def check_if_data_present(context, metric_name: str, duration_delta: timedelta) -> bool:
    start_time = datetime.now() - duration_delta
    end_time = datetime.now()

    # Convert to epoch seconds
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    query = f'?query={metric_name}{{uuid="{context.scenario_to_device_map[context.scenario].device_record_uid}"}}&start={start_time_epoch}&end={end_time_epoch}&step=5m'

    return start_polling(query=query, retry_count=60, retry_frequency_seconds=60)


def start_polling(query: str, retry_count: int, retry_frequency_seconds: int) -> bool:
    endpoint = get_endpoints().PROMETHEUS_RANGE_QUERY_URL + query

    count = 0
    success = False
    while True:
        # Exit after 60 minutes
        if count > retry_count:
            print("Data not ingested in Prometheus. Exiting.")
            break

        count += 1

        # Check for data in Prometheus
        response = get(endpoint, print_body=False)
        if len(response["data"]["result"]) > 0:
            num_data_points = len(response["data"]["result"][0]["values"])
            print(f"Active data points: {num_data_points}.")
            if num_data_points > 3700:
                success = True
                break

        time.sleep(retry_frequency_seconds)
        # TODO: Ingest live data till backfill data is available
    return success


def get_index_of_metric_object(
    backfill_data_list: List[BackfillData], generated_data: GeneratedData
):
    for i, backfill_data in enumerate(backfill_data_list):
        if backfill_data.metric_name == generated_data.metric_name:
            return i
    # No exisiting object found
    return -1


def convert_to_backfill_data(
    generated_data_list: List[GeneratedData],
) -> List[BackfillData]:
    backfill_data_list: List[BackfillData] = []
    for generated_data in generated_data_list:
        update_index = get_index_of_metric_object(backfill_data_list, generated_data)

        series = Series(
            labels=",".join([f'{k}="{v}"' for k, v in generated_data.labels.items()]),
            value=generated_data.values["y"].tolist(),
            timestamp=generated_data.values["ds"].astype(int).tolist(),
        )

        if update_index != -1:
            # update existing block
            backfill_data_list[update_index].series.append(series)
        else:
            # add a new block
            backfill_data_list.append(
                BackfillData(
                    metric_name=generated_data.metric_name,
                    series=[series],
                    description="Test Backfill Data",
                )
            )

    return backfill_data_list
