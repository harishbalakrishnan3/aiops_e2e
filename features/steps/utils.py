import copy
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

import yaml

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pydantic import BaseModel

from features.model import Device, ScenarioEnum
from features.steps.cdo_apis import get, update_device_data
from features.steps.env import Path, get_endpoints
from shared.label_utils import format_labels
from shared.step_utils import parse_step_to_seconds
from features.steps.time_series_generator import (
    NoiseConfig,
    SeasonalityConfig,
    SeriesConfig,
    TimeConfig,
    TransitionConfig,
    default_noise,
    generate_timeseries,
)

# Load scenario prerequisites from JSON config
_SCENARIO_PREREQUISITES = None


def _load_scenario_prerequisites() -> dict:
    global _SCENARIO_PREREQUISITES
    if _SCENARIO_PREREQUISITES is None:
        config_path = os.path.join(Path.RESOURCES_DIR, "scenario_prerequisites.json")
        with open(config_path, "r") as f:
            _SCENARIO_PREREQUISITES = json.load(f)
    return _SCENARIO_PREREQUISITES


def _filter_devices_by_type(devices: list, device_filter: str) -> list:
    """Filter devices based on the device_filter from prerequisites config."""
    if device_filter == "standalone":
        return [d for d in devices if d.container_type is None]
    elif device_filter == "HA_PAIR":
        return [d for d in devices if d.container_type == "HA_PAIR"]
    elif device_filter == "CLUSTER":
        return [d for d in devices if d.container_type == "CLUSTER"]
    elif device_filter == "ravpn":
        return [d for d in devices if d.ra_vpn_enabled]
    else:
        logging.warning(
            f"Unknown device_filter '{device_filter}', returning all devices"
        )
        return devices


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


def store_ts_in_context(context, labels, key, metric_name):
    ts = copy.deepcopy(labels)
    if metric_name not in context.timeseries.keys():
        context.timeseries[metric_name] = {}
    context.timeseries[metric_name][key] = ts
    logging.info(f"Timeseries in context: {context.timeseries}")


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
        logging.info(
            "Selected device: %s (aegis_uid: %s, record_uid: %s)",
            device.device_name,
            device.aegis_device_uid,
            device.device_record_uid,
        )
        if context.scenario == ScenarioEnum.RAVPN_FORECAST:
            update_device_data(device.aegis_device_uid)
        context.scenario_to_device_map[context.scenario] = device
        # Track device as used globally to minimize overlap across scenarios
        if hasattr(context, "used_devices"):
            context.used_devices.add(device.device_record_uid)

    return {"tenant_uuid": context.tenant_id, "uuid": device.device_record_uid}


def convert_str_list_to_dict(s):
    if not s:
        return {}
    return dict(
        map(lambda x: (x.split("=")[0].strip(), x.split("=")[1].strip()), s.split(","))
    )


def get_appropriate_device(context, duration) -> Device:
    """
    Pickup a device for by scenario . Find a device where the to be ingested data is not present in the duration specified . This will avoid data ingestion failures due to existing data in the prometheus

    Devices already used within the same feature file are excluded to ensure
    each scenario in a feature gets a distinct device.

    :param context: behave context
    :param duration: duration for which data will be ingested
    """
    prerequisites = _load_scenario_prerequisites()
    scenario_key = context.scenario.name

    if scenario_key not in prerequisites:
        logging.warning(
            f"No prerequisites found for scenario '{scenario_key}', picking up the last available device"
        )
        return context.devices[-1]

    config = prerequisites[scenario_key]
    available_devices = _filter_devices_by_type(
        context.devices, config["device_filter"]
    )
    query = config["query"]

    # Prefer devices not yet used by any scenario to maximize diversity
    used = getattr(context, "used_devices", set())
    if used:
        unused_devices = [
            d for d in available_devices if d.device_record_uid not in used
        ]
        if unused_devices:
            logging.info(
                f"{len(unused_devices)} unused device(s) available out of "
                f"{len(available_devices)} candidate(s), preferring unused"
            )
            available_devices = unused_devices
        else:
            logging.warning(
                f"All {len(available_devices)} candidate device(s) already used "
                f"by other scenarios, allowing overlap"
            )

    return find_device_available_for_data_ingestion(available_devices, query, duration)


def find_device_available_for_data_ingestion(
    available_devices: list, query: str, duration: timedelta
):
    for device in available_devices:
        if not is_data_present(query.format(uuid=device.device_record_uid), duration):
            return device
    logging.error("No device available for ingestion , Failing test")
    raise Exception("No device available for ingestion")


def is_data_present(query: str, duration: timedelta, step="5m"):
    MAX_PROMETHEUS_DATAPOINTS = 11000

    start_time = datetime.now(timezone.utc) - duration
    end_time = datetime.now(timezone.utc)

    total_duration_seconds = int(duration.total_seconds())
    step_seconds = parse_step_to_seconds(step)

    expected_datapoints = total_duration_seconds // step_seconds

    if expected_datapoints > MAX_PROMETHEUS_DATAPOINTS:
        step_seconds = total_duration_seconds // MAX_PROMETHEUS_DATAPOINTS
        step_minutes = round(step_seconds / 60 / 10) * 10
        step = f"{step_minutes}m"
        logging.info(
            f"Query would return {expected_datapoints} datapoints, increasing step to {step}"
        )

    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())
    endpoint = f"{get_endpoints().PROMETHEUS_RANGE_QUERY_URL}?{query}&start={start_time_epoch}&end={end_time_epoch}&step={step}"
    logging.info(endpoint)
    response = get(endpoint, print_body=False)
    return len(response["data"]["result"]) > 0


# Helper function that can be used to dump the graph of genertaed timeseries when debugging
def _save_timeseries_graph(
    generated_data: pd.DataFrame, metric_name: str, labels: dict
):
    """Save a graph of the timeseries data to a local file."""
    import os

    # Create directory if it doesn't exist
    os.makedirs("./generated_graphs", exist_ok=True)

    # Create a filename from metric name and labels
    label_str = "_".join([f"{k}_{v}" for k, v in labels.items()])
    filename = f"./generated_graphs/{metric_name}_{label_str}.png"

    # Plot the data
    plt.figure(figsize=(12, 6))
    plt.plot(generated_data["ds"], generated_data["y"])
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.title(f"{metric_name} - {label_str}")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

    logging.info(f"Saved graph to {filename}")


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
    noise: bool = None,
) -> GeneratedData:
    now = datetime.now(timezone.utc)
    offsetted_start_time = now - timedelta(minutes=duration) + time_offset

    # Configure noise based on the noise parameter
    if noise is None:
        noise_config = default_noise
    else:
        noise_config = NoiseConfig(enable=noise) if noise else NoiseConfig(enable=False)

    generated_data = generate_timeseries(
        time_config=TimeConfig(
            series_config=SeriesConfig(
                start_time=offsetted_start_time,
                duration=timedelta(minutes=duration),
                start_value=start_value,
                end_value=end_value,
                step=timedelta(minutes=1),
            ),
            transition_config=TransitionConfig(
                transition_window=timedelta(minutes=spike_duration_minutes),
                start_time=offsetted_start_time + timedelta(minutes=start_spike_minute),
            ),
        ),
        noise_config=noise_config,
        seasonality_config=SeasonalityConfig(enable=False),
    )

    if metric_type == "counter":
        # For counter metrics, apply cumulative sum to convert gauge values to counter
        generated_data["y"] = generated_data["y"].cumsum()
    elif metric_type == "exponential":
        # For exponential metrics, implement quartic growth pattern to achieve steep upward slope
        # that will be visible even after rate() calculation in Prometheus
        # This type ignores end_value parameter
        spike_start_idx = start_spike_minute
        spike_end_idx = start_spike_minute + spike_duration_minutes

        # Get the values array
        y_values = generated_data["y"].values

        # Generate time points for the spike window (0 to spike_duration_minutes)
        t = np.arange(spike_duration_minutes)

        # Apply quartic growth: y = start_value + coefficient * t^4
        coefficient = 10000000000.0
        y_values[spike_start_idx:spike_end_idx] = start_value + coefficient * (t**4)

        # Update the dataframe
        generated_data["y"] = y_values

    label_map = get_label_map(context, label_string, timedelta(minutes=duration))

    write_timeseries_yaml(
        context=context,
        metric_name=metric_name,
        labels=label_map,
        generated_data=generated_data,
        ts_features={
            "seasonality": False,
            "trend": f"{start_value} -> {end_value} over {spike_duration_minutes}m (start at {start_spike_minute}m)",
            "noise": noise_config.enable,
        },
    )

    return GeneratedData(
        metric_name=metric_name,
        values=generated_data,
        labels=label_map,
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


def check_if_data_present(
    metric_name: str, duration_delta: timedelta, labels: dict = {}
) -> bool:
    start_time = datetime.now(timezone.utc) - duration_delta
    end_time = datetime.now(timezone.utc)

    # Convert to epoch seconds
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    query = f"?query={metric_name}{{{format_device_labels(labels)}}}&start={start_time_epoch}&end={end_time_epoch}&step=5m"
    return start_polling(query=query, retry_count=60, retry_frequency_seconds=60)


def start_polling(query: str, retry_count: int, retry_frequency_seconds: int) -> bool:
    endpoint = get_endpoints().PROMETHEUS_RANGE_QUERY_URL + query

    count = 0
    success = False
    logging.info(f"Polling data store with PromQL: {query}")
    while True:
        # Exit after 60 minutes
        if count > retry_count:
            logging.error("Data not ingested in Prometheus. Exiting.")
            break

        count += 1
        logging.info(f"Attempt {count}/{retry_count}: Checking for data in Prometheus")

        # Check for data in Prometheus
        response = get(endpoint, print_body=False)
        if len(response["data"]["result"]) > 0:
            num_data_points = len(response["data"]["result"][0]["values"])
            logging.debug(f"Active data points: {num_data_points}.")
            if num_data_points > 3900:
                success = True
                logging.info(
                    f"Total time taken to ingest data: {count * retry_frequency_seconds/60} minutes"
                )
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


# Re-export for backward compatibility
format_device_labels = format_labels


def _sanitize_dirname(name: str) -> str:
    """Convert a display name to a safe directory name."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name).strip("_")


def write_timeseries_yaml(
    context,
    metric_name: str,
    labels: dict,
    generated_data,
    ts_features: dict,
):
    """Write generated timeseries to a YAML file under outputs/<feature>/<scenario>/."""
    feature_name = getattr(context, "feature_name", "unknown_feature")
    scenario_enum = getattr(context, "scenario", ScenarioEnum.UNKNOWN_SCENARIO)

    feature_dir = _sanitize_dirname(feature_name)
    scenario_dir = _sanitize_dirname(scenario_enum.name)

    output_dir = os.path.join(Path.OUTPUTS_DIR, feature_dir, scenario_dir)
    os.makedirs(output_dir, exist_ok=True)

    short_hash = uuid.uuid4().hex[:8]
    filename = f"{scenario_enum.name}_{metric_name}_{short_hash}.yaml"
    filepath = os.path.join(output_dir, filename)

    timestamps = generated_data["ds"].tolist()
    values = generated_data["y"].tolist()

    doc = {
        "metric": metric_name,
        "labels": [{k: str(v)} for k, v in labels.items()],
        "start_time": datetime.fromtimestamp(timestamps[0]).isoformat()
        if timestamps
        else "",
        "end_time": datetime.fromtimestamp(timestamps[-1]).isoformat()
        if timestamps
        else "",
        "ts_features": ts_features,
        "timeseries": [{int(ts): round(val, 4)} for ts, val in zip(timestamps, values)],
    }

    with open(filepath, "w") as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False)

    logging.info(f"Wrote timeseries YAML to {filepath}")


def convert_to_backfill_data(
    generated_data_list: List[GeneratedData],
) -> List[BackfillData]:
    backfill_data_list: List[BackfillData] = []
    for generated_data in generated_data_list:
        update_index = get_index_of_metric_object(backfill_data_list, generated_data)

        series = Series(
            labels=format_device_labels(generated_data.labels),
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


def compute_onboard_status_ignoring_fmc_export(response):
    """
    Computes the effective onboard status by ignoring FMC_METRIC_EXPORT and METRIC_BACKFILL tasks.

    Returns the computed overall status based on:
    - timeSeriesStore status
    - dataSources status (excluding FMC_METRIC_EXPORT and METRIC_BACKFILL tasks)
    - applications status

    Valid statuses:
    - SUCCESS: ONBOARD_SUCCESS, OFFBOARD_SUCCESS
    - FAILURE: ONBOARD_FAILURE, OFFBOARD_FAILURE, ONBOARD_PARTIAL, OFFBOARD_PARTIAL
    - IN_PROGRESS: ONBOARD_IN_PROGRESS, OFFBOARD_IN_PROGRESS
    - IN_QUEUE: ONBOARD_IN_QUEUE, OFFBOARD_IN_QUEUE

    Status priority: FAILURE/PARTIAL > IN_PROGRESS/IN_QUEUE > SUCCESS
    """
    statuses = []

    # Check timeSeriesStore
    if "timeSeriesStore" in response:
        statuses.append(response["timeSeriesStore"]["status"])

    # Check dataSources (excluding FMC_METRIC_EXPORT and METRIC_BACKFILL)
    if "dataSources" in response:
        for data_source in response["dataSources"]:
            # Check tasks, excluding FMC_METRIC_EXPORT and METRIC_BACKFILL
            if "tasks" in data_source:
                filtered_tasks = [
                    task
                    for task in data_source["tasks"]
                    if task["name"] not in ["FMC_METRIC_EXPORT", "METRIC_BACKFILL"]
                ]
                if filtered_tasks:
                    # Collect statuses from filtered tasks
                    for task in filtered_tasks:
                        statuses.append(task["status"])
                # If all tasks were FMC_METRIC_EXPORT, don't add any status
            elif "status" in data_source:
                statuses.append(data_source["status"])

    # Check applications
    if "applications" in response:
        for app in response["applications"]:
            if "status" in app:
                statuses.append(app["status"])

    # Determine overall status based on priority
    # Priority: FAILURE/PARTIAL > IN_PROGRESS/IN_QUEUE > SUCCESS
    has_failure = any("FAILURE" in status or "PARTIAL" in status for status in statuses)
    has_in_progress = any(
        "IN_PROGRESS" in status or "IN_QUEUE" in status for status in statuses
    )
    has_success = any("SUCCESS" in status for status in statuses)

    if has_failure:
        # Return appropriate failure status based on what's in the response
        if any("ONBOARD_FAILURE" in status for status in statuses):
            return "ONBOARD_FAILURE"
        elif any("ONBOARD_PARTIAL" in status for status in statuses):
            return "ONBOARD_PARTIAL"
        elif any("OFFBOARD_FAILURE" in status for status in statuses):
            return "OFFBOARD_FAILURE"
        elif any("OFFBOARD_PARTIAL" in status for status in statuses):
            return "OFFBOARD_PARTIAL"
    elif has_in_progress:
        # Return appropriate in-progress status
        if any("ONBOARD_IN_PROGRESS" in status for status in statuses):
            return "ONBOARD_IN_PROGRESS"
        elif any("ONBOARD_IN_QUEUE" in status for status in statuses):
            return "ONBOARD_IN_QUEUE"
        elif any("OFFBOARD_IN_PROGRESS" in status for status in statuses):
            return "OFFBOARD_IN_PROGRESS"
        elif any("OFFBOARD_IN_QUEUE" in status for status in statuses):
            return "OFFBOARD_IN_QUEUE"
    elif has_success and all("SUCCESS" in status for status in statuses):
        # All statuses contain SUCCESS
        if any("ONBOARD_SUCCESS" in status for status in statuses):
            return "ONBOARD_SUCCESS"
        elif any("OFFBOARD_SUCCESS" in status for status in statuses):
            return "OFFBOARD_SUCCESS"

    return "UNKNOWN"
