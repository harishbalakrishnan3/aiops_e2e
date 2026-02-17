#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from darts.utils.timeseries_generation import (
    linear_timeseries,
    sine_timeseries,
)
from dotenv import load_dotenv
from opentelemetry import metrics
from opentelemetry.exporter.prometheus_remote_write import (
    PrometheusRemoteWriteMetricsExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.export import MetricExportResult
from opentelemetry.sdk.resources import Resource

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from features.steps.env import get_base_url
from shared.label_utils import parse_labels, sanitize_label_name

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
)

# Initialize OpenTelemetry metrics
memory_reader = InMemoryMetricReader()
meter_provider = MeterProvider(
    metric_readers=[memory_reader], resource=Resource.get_empty()
)
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Global registry of active metrics
active_metrics = {}


def create_gauge(name: str, description: str):
    """Create a gauge metric."""
    gauge = meter.create_gauge(
        name=name,
        description=description,
    )
    logging.info(f"Created gauge '{name}' with description '{description}'")
    active_metrics[name] = gauge
    return gauge


def generate_timeseries(start_time, end_time, trend_coefficient, flat_base=5):
    """Generate timeseries with specified trend coefficient and default seasonality/noise."""
    start_ts = pd.Timestamp(start_time)
    total_minutes = int((end_time - start_time).total_seconds() / 60)
    freq = "60s"

    # Trend component
    total_hours = total_minutes / 60
    end_trend_value = flat_base + trend_coefficient * (total_hours / 0.95)
    trend = linear_timeseries(
        start_value=flat_base,
        end_value=end_trend_value,
        start=start_ts,
        length=total_minutes,
        freq=freq,
    )

    # Seasonality component (daily sinusoidal approximation)
    seasonality = sine_timeseries(
        value_frequency=1.0 / 1440.0,
        value_amplitude=9.25,
        value_y_offset=10.25,
        value_phase=np.pi,
        start=start_ts,
        length=total_minutes,
        freq=freq,
    )

    combined = trend + seasonality
    pdf = combined.pd_dataframe()
    ts_values = pdf.iloc[:, 0].values
    time_points = list(pdf.index.to_pydatetime())
    return ts_values, time_points


def get_remote_write_config(env):
    """Get remote write configuration."""
    load_dotenv()

    cdo_token = os.getenv("CDO_TOKEN")
    if not cdo_token:
        raise ValueError("CDO_TOKEN environment variable not set in .env file")

    base_url = get_base_url(env)
    data_ingest_url = f"{base_url}/api/platform/ai-ops-data-ingest/v2/healthmetrics"

    return {
        "endpoint": data_ingest_url,
        "token": cdo_token,
    }


def instant_remote_write(
    metric_name: str, labels: dict[str, str], value: float, exporter
):
    """Push a single metric value to Prometheus."""
    if metric_name not in active_metrics:
        create_gauge(metric_name, "Live gauge metric")

    active_metrics[metric_name].set(float(value), labels)

    metrics_data = memory_reader.get_metrics_data()
    try:
        result = exporter.export(metrics_data)
        if result == MetricExportResult.FAILURE:
            logging.error(f"Failed to export metric {metric_name}")
            return False
        logging.info(f"✓ Pushed {metric_name} = {value:.2f} (labels: {labels})")
        return True
    except Exception as e:
        logging.error(f"Exception exporting metric {metric_name}: {e}")
        return False


def push_live_metrics(
    metric_name,
    labels,
    duration_minutes,
    trend_coefficient,
    description,
    env,
    flat_base=5,
):
    """Generate and push live metrics to Prometheus."""
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=duration_minutes)

    logging.info(f"Generating timeseries from {start_time} to {end_time}")
    logging.info(f"Duration: {duration_minutes} minutes")
    logging.info(f"Metric: {metric_name}")
    logging.info(f"Labels: {labels}")
    logging.info(f"Trend coefficient: {trend_coefficient}")
    logging.info(f"Flat base: {flat_base}")
    logging.info(f"Environment: {env}")

    # Generate timeseries data
    ts_values, time_points = generate_timeseries(
        start_time, end_time, trend_coefficient, flat_base
    )

    logging.info(f"Generated {len(ts_values)} datapoints")
    logging.info("=" * 80)

    # Get remote write config
    config = get_remote_write_config(env)
    exporter = PrometheusRemoteWriteMetricsExporter(
        endpoint=config["endpoint"],
        headers={"Authorization": f"Bearer {config['token']}"},
    )

    logging.info(f"Starting live metric push (1 datapoint per minute)")
    logging.info(f"Press Ctrl+C to stop")
    logging.info("=" * 80)

    try:
        for i, value in enumerate(ts_values):
            timestamp = time_points[i]
            logging.info(
                f"[{i+1}/{len(ts_values)}] Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            success = instant_remote_write(metric_name, labels, value, exporter)

            if not success:
                logging.warning("Failed to push metric, continuing...")

            # Sleep for 1 minute unless it's the last datapoint
            if i < len(ts_values) - 1:
                logging.info("Sleeping for 60 seconds...")
                time.sleep(60)
            else:
                logging.info("=" * 80)
                logging.info("✓ All datapoints pushed successfully!")

    except KeyboardInterrupt:
        logging.info("\n" + "=" * 80)
        logging.info(f"Interrupted! Pushed {i+1}/{len(ts_values)} datapoints")
        logging.info("=" * 80)
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Push live metrics to Prometheus with generated timeseries data"
    )
    parser.add_argument(
        "--metric-name",
        required=True,
        help="Name of the metric (e.g., 'vpn', 'cpu', 'memory')",
    )
    parser.add_argument(
        "--labels",
        required=True,
        help="Label key-value pairs in format 'key1=value1,key2=value2'",
    )
    parser.add_argument(
        "--duration",
        type=int,
        required=True,
        help="Duration in minutes to push metrics",
    )
    parser.add_argument(
        "--trend-coefficient",
        type=float,
        default=0.1,
        help="Trend coefficient for timeseries generation (default: 0.1)",
    )
    parser.add_argument(
        "--description",
        default="Live metric data",
        help="Metric description (default: 'Live metric data')",
    )
    parser.add_argument(
        "--flat-base",
        type=float,
        default=5.0,
        help="Flat base value for trend generation (default: 5.0)",
    )
    parser.add_argument(
        "--env",
        default="staging",
        help="Environment (e.g., 'scale', 'staging', 'ci' for edge URLs, others for prod URLs). Default: staging",
    )

    args = parser.parse_args()

    if args.duration <= 0:
        logging.error("Duration must be greater than 0")
        sys.exit(1)

    labels_dict = parse_labels(args.labels)

    push_live_metrics(
        args.metric_name,
        labels_dict,
        args.duration,
        args.trend_coefficient,
        args.description,
        args.env,
        args.flat_base,
    )


if __name__ == "__main__":
    main()
