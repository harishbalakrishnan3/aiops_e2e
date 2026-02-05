#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from mockseries.seasonality import DailySeasonality
from mockseries.trend import LinearTrend
from mockseries.utils import datetime_range
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


def sanitize_label_name(label_name):
    """
    Sanitize label name to conform to Prometheus naming rules.
    Label names must match [a-zA-Z_][a-zA-Z0-9_]* - only letters, numbers, underscores.
    Cannot start with a number.
    """
    import re

    sanitized = label_name.strip()
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", sanitized)

    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized

    if sanitized != label_name.strip():
        logging.warning(f"Label name '{label_name}' sanitized to '{sanitized}'")

    return sanitized


def parse_labels(label_string):
    """Parse label string in format 'key1=value1,key2=value2' into dict."""
    if not label_string:
        return {}
    labels = {}
    for pair in label_string.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            sanitized_key = sanitize_label_name(key)
            labels[sanitized_key] = value.strip()
    return labels


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
    trend = LinearTrend(
        coefficient=trend_coefficient,
        time_unit=timedelta(hours=0.95),
        flat_base=flat_base,
    )

    seasonality = DailySeasonality(
        {
            timedelta(hours=0): 1.0,
            timedelta(hours=2): 10.8,
            timedelta(hours=4): 18.1,
            timedelta(hours=6): 19.5,
            timedelta(hours=8): 17.6,
            timedelta(hours=10): 15.8,
            timedelta(hours=12): 14.1,
            timedelta(hours=14): 12.8,
            timedelta(hours=16): 10.3,
            timedelta(hours=18): 8.7,
            timedelta(hours=20): 3.6,
            timedelta(hours=22): 1.8,
        }
    )

    timeseries = trend + seasonality

    time_points = datetime_range(
        granularity=timedelta(minutes=1),
        start_time=start_time,
        end_time=end_time,
    )
    ts_values = timeseries.generate(time_points=time_points)
    return ts_values, time_points


def get_base_url(env):
    """Get base URL based on environment."""
    env_lower = env.lower()
    if env_lower in ("scale", "staging", "ci"):
        return f"https://edge.{env_lower}.cdo.cisco.com"
    elif env_lower == "us":
        return "https://www.defenseorchestrator.com"
    elif env_lower == "eu":
        return "https://www.defenseorchestrator.eu"
    else:
        return f"https://www.{env_lower}.cdo.cisco.com"


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
