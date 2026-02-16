import json
import logging
import os.path
import subprocess
import time
from datetime import datetime, timezone
from datetime import timedelta
from string import Template

import numpy as np
import pandas as pd
from behave import *
from darts.utils.timeseries_generation import (
    gaussian_timeseries,
    linear_timeseries,
    sine_timeseries,
)
from features.steps.cdo_apis import get, post
from features.steps.env import get_endpoints, Path
from features.steps.utils import get_common_labels
from shared.step_utils import parse_step_to_seconds

t = Template(
    """# HELP $metric_name $description
# TYPE $metric_name gauge
$metric_name{$labels_1} $value $timestamp
$metric_name{$labels_2} $value $timestamp
"""
)

HISTORICAL_DATA_FILE = "ravpn_historical_data.txt"


@step("backfill RAVPN metrics for a suitable device")
def step_impl(context):
    if context.remote_write_config is None:
        logging.info("Remote write config not found. Skipping backfill.")
        assert False

    ts_values, time_points = generate_timeseries()

    metric_name = "vpn"
    common_labels = {
        "instance": "127.0.0.2:9273",
        "job": "metrics_generator:8123",
    } | get_common_labels(context, timedelta(days=21))

    labels_1 = {**common_labels, "vpn": "active_ravpn_tunnels"}
    labels_2 = {**common_labels, "vpn": "inactive_ravpn_tunnels"}
    description = "Currently active and inactive RAVPN tunnels"
    labels_1 = ",".join([f'{k}="{v}"' for k, v in labels_1.items()])
    labels_2 = ",".join([f'{k}="{v}"' for k, v in labels_2.items()])
    with open(os.path.join(Path.PYTHON_UTILS_ROOT, HISTORICAL_DATA_FILE), "w") as file:
        for i in range(len(time_points)):
            multiline_text = t.substitute(
                value=ts_values[i],
                timestamp=int(time_points[i].timestamp()),
                metric_name=metric_name,
                labels_1=labels_1,
                labels_2=labels_2,
                description=description,
            )
            file.write(multiline_text)
        file.write("# EOF")

    remote_write_config = context.remote_write_config

    start_time = time.time()
    subprocess.run(
        [
            os.path.join(Path.PYTHON_UTILS_ROOT, "backfill.sh"),
            remote_write_config["url"].removesuffix("/api/prom/push"),
            remote_write_config["username"],
            remote_write_config["password"],
            Path.PYTHON_UTILS_ROOT,
            "/ravpn_data/",
            HISTORICAL_DATA_FILE,
        ],
    )
    end_time = time.time()
    logging.info(f"Backfill took {(end_time - start_time)/60:.2f} minutes")

    # Calculate the start and end times
    start_time = datetime.now(timezone.utc) - timedelta(days=21)
    end_time = datetime.now(timezone.utc) - timedelta(days=1)

    # Convert to epoch seconds
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    query_string = f'vpn{{uuid="{context.scenario_to_device_map[context.scenario].device_record_uid}"}}'

    ingestion_start_time = time.time()
    count = 0
    success = False
    while True:
        # Exit after 180 minutes
        if count > 180:
            logging.error("Data not ingested in Prometheus. Exiting.")
            break

        count += 1

        # Check for data in Prometheus using pagination-aware function
        logging.info(f"Attempt {count}: Checking for data in Prometheus")
        series_data_points = _get_total_data_points(
            start_time_epoch, end_time_epoch, query_string, step_size="1m"
        )

        if series_data_points:
            total_data_points = sum(series_data_points.values())
            logging.info(
                f"Total RAVPN data points across all series: {total_data_points}"
            )

            if total_data_points > 55000:
                ingestion_end_time = time.time()
                logging.info(
                    f"Data ingestion took {(ingestion_end_time - ingestion_start_time)/60:.2f} minutes"
                )
                success = True
                break
        else:
            logging.info("No data points found")

        time.sleep(60)
        # TODO: Ingest live data till backfill data is available
    assert success


@step("trigger the RAVPN forecasting workflow")
def step_impl(context):
    payload = {
        "subscriber": "RAVPN_MAX_SESSIONS_BREACH_FORECAST",
        "trigger-type": "SCHEDULE_TICKS",
        "config": {"periodicity": "INTERVAL_24_HOURS"},
        "pipeline": {
            "output": [
                {
                    "plugin": "SNS",
                    "config": {"destination": "ai-ops-capacity-analytics"},
                }
            ],
            "processor": [],
        },
        "deviceIds": [
            context.scenario_to_device_map[context.scenario].device_record_uid
        ],
        "timestamp": "2024-08-21T05:55:00.000",
        "attributes": {},
    }
    post(get_endpoints().TRIGGER_MANAGER_URL, json.dumps(payload))


def _get_total_data_points(start_epoch, end_epoch, query_string, step_size="1m"):
    """
    Get total data points from Prometheus, handling the 11000 data point limit per query.

    Args:
        start_epoch: Start time in epoch seconds
        end_epoch: End time in epoch seconds
        query_string: The Prometheus query string (e.g., 'vpn{uuid="..."}')
        step_size: Query step size (default: "1m"). Supports format like "1m", "5m", "1h"

    Returns:
        Dictionary with series names as keys and their total data point counts as values.
        Returns empty dict if no data found.
    """
    step_seconds = parse_step_to_seconds(step_size)

    # Calculate total duration and expected data points
    total_duration = end_epoch - start_epoch
    expected_points = (total_duration // step_seconds) + 1

    # Maximum data points per query (use 10000 to be safe, limit is 11000)
    max_points_per_query = 10000

    # Calculate chunk size if we need to split
    if expected_points <= max_points_per_query:
        # Single query is sufficient
        chunks = [(start_epoch, end_epoch)]
    else:
        # Split into multiple chunks
        chunk_duration = max_points_per_query * step_seconds
        chunks = []
        current_start = start_epoch
        while current_start < end_epoch:
            current_end = min(current_start + chunk_duration, end_epoch)
            chunks.append((current_start, current_end))
            current_start = current_end

    logging.info(
        f"Query will be split into {len(chunks)} chunk(s) to handle {expected_points} expected data points"
    )

    # Execute queries for each chunk and aggregate results
    series_data_points = {}

    for idx, (chunk_start, chunk_end) in enumerate(chunks):
        query = f"?query={query_string}&start={chunk_start}&end={chunk_end}&step={step_size}"
        endpoint = get_endpoints().PROMETHEUS_RANGE_QUERY_URL + query

        response = get(endpoint, print_body=False)

        if len(response["data"]["result"]) > 0:
            for series in response["data"]["result"]:
                metric_labels = series.get("metric", {})
                series_key = metric_labels.get("vpn", "unknown")

                num_points = len(series["values"])
                series_data_points[series_key] = (
                    series_data_points.get(series_key, 0) + num_points
                )

            logging.info(
                f"Chunk {idx + 1}/{len(chunks)}: Retrieved data points for {len(response['data']['result'])} series"
            )
        else:
            logging.info(f"Chunk {idx + 1}/{len(chunks)}: No data points found")

    return series_data_points


def generate_timeseries():
    start_time = pd.Timestamp(datetime.now(timezone.utc) - timedelta(days=21))
    end_time = pd.Timestamp(datetime.now(timezone.utc))
    total_minutes = int((end_time - start_time).total_seconds() / 60)
    freq = "60s"

    # Trend component: linear from flat_base=5, increasing by 0.1 per 0.95 hours
    # Over 21 days: end_value = 5 + 0.1 * (21*24/0.95) = 5 + 53.05 ≈ 58
    total_hours = 21 * 24
    end_trend_value = 5 + 0.1 * (total_hours / 0.95)
    trend = linear_timeseries(
        start_value=5,
        end_value=end_trend_value,
        start=start_time,
        length=total_minutes,
        freq=freq,
    )

    # Seasonality component: daily pattern approximated with sinusoidal
    # Original DailySeasonality peaks around hour 6 (19.5) and troughs around hour 0 (1.0)
    # Amplitude ≈ (19.5 - 1.0) / 2 ≈ 9.25, y_offset ≈ (19.5 + 1.0) / 2 ≈ 10.25
    # Period = 1 day = 1440 minutes, so value_frequency = 1/1440
    seasonality = sine_timeseries(
        value_frequency=1.0 / 1440.0,
        value_amplitude=9.25,
        value_y_offset=10.25,
        value_phase=np.pi,  # Phase shift to approximate original daily pattern
        start=start_time,
        length=total_minutes,
        freq=freq,
    )

    # Noise component
    noise = gaussian_timeseries(
        mean=0,
        std=3,
        start=start_time,
        length=total_minutes,
        freq=freq,
    )

    # Combine components
    combined = trend + seasonality + noise

    # Convert to the format expected by callers: (ts_values, time_points)
    pdf = combined.pd_dataframe()
    ts_values = pdf.iloc[:, 0].values
    time_points = list(pdf.index.to_pydatetime())
    return ts_values, time_points
