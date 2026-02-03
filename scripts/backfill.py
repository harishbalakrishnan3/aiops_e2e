#!/usr/bin/env python3

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from jinja2 import Template
from mockseries.noise import GaussianNoise
from mockseries.seasonality import DailySeasonality
from mockseries.trend import LinearTrend
from mockseries.utils import datetime_range
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
)

TEMPLATE = Template(
    """# HELP {{ metric_name }} {{ description }}
# TYPE {{ metric_name }} gauge
{% for i in range(values|length) -%}
{{ metric_name }}{{ "{" }}{{ labels }}{{ "}" }} {{ values[i] }} {{ timestamps[i] }}
{% endfor -%}
"""
)


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


def format_labels(labels_dict):
    """Format labels dict into Prometheus label string."""
    return ",".join([f'{k}="{v}"' for k, v in labels_dict.items()])


def parse_step_size(step_size_str):
    """
    Parse step size string (e.g., '5m', '15m', '1h') to minutes.
    If input is already an integer, return it as-is.

    Args:
        step_size_str: Step size string like '5m', '15m', '1h', '30s' or integer

    Returns:
        int: Step size in minutes

    Raises:
        ValueError: If format is invalid
    """
    import re

    # If it's already an integer, return it
    if isinstance(step_size_str, int):
        return step_size_str

    # Try to parse as integer directly
    try:
        return int(step_size_str)
    except ValueError:
        pass

    # Parse string format like '5m', '1h'
    match = re.match(r"^(\d+)([smhd])$", str(step_size_str).lower())
    if not match:
        raise ValueError(
            f"Invalid step size format: '{step_size_str}'. "
            "Expected format: <number><unit> where unit is s(econds), m(inutes), h(ours), or d(ays), "
            "or just a number in minutes. Examples: 5m, 15m, 1h, 30s, or 5"
        )

    value = int(match.group(1))
    unit = match.group(2)

    # Convert to minutes
    if unit == "s":
        minutes = value / 60.0
    elif unit == "m":
        minutes = value
    elif unit == "h":
        minutes = value * 60
    elif unit == "d":
        minutes = value * 1440
    else:
        raise ValueError(f"Unsupported time unit: {unit}")

    if minutes < 1:
        raise ValueError(
            f"Step size must be at least 1 minute, got {minutes} minutes from '{step_size_str}'"
        )

    return int(minutes)


def generate_timeseries(
    start_time, end_time, trend_coefficient, granularity_minutes=15, flat_base=5
):
    """Generate timeseries with specified trend coefficient and default seasonality/noise."""
    trend = LinearTrend(
        coefficient=trend_coefficient, time_unit=timedelta(hours=1), flat_base=flat_base
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

    noise = GaussianNoise(mean=0, std=3, random_seed=42)

    timeseries = trend + seasonality + noise

    time_points = datetime_range(
        granularity=timedelta(minutes=granularity_minutes),
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
    else:
        return f"https://www.{env_lower}.cdo.cisco.com"


def get_remote_write_config(env):
    """Fetch remote write configuration from GCM."""
    load_dotenv()

    cdo_token = os.getenv("CDO_TOKEN")
    if not cdo_token:
        raise ValueError("CDO_TOKEN environment variable not set in .env file")

    base_url = get_base_url(env)
    gcm_stack_url = (
        f"{base_url}/api/platform/ai-ops-tenant-services/v2/timeseries-stack"
    )

    logging.info(f"Fetching GCM stack configuration from {gcm_stack_url}")

    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[i for i in range(400, 600)],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)

    response = session.get(
        gcm_stack_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cdo_token}",
        },
        timeout=180,
    )

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch GCM config: {response.status_code} - {response.text}"
        )

    gcm_stack_config = response.json()

    return {
        "url": gcm_stack_config["hmInstancePromUrl"].removesuffix("/api/prom/push"),
        "username": gcm_stack_config["hmInstancePromId"],
        "password": gcm_stack_config["prometheusToken"],
    }


def write_openmetrics_file(
    metric_name, labels_str, values, timestamps, output_file, description
):
    """Write timeseries data to OpenMetrics format file."""
    content = TEMPLATE.render(
        metric_name=metric_name,
        labels=labels_str,
        values=values,
        timestamps=timestamps,
        description=description,
    )

    with open(output_file, "w") as f:
        f.write(content)
        f.write("# EOF\n")

    logging.info(f"Wrote {len(values)} datapoints to {output_file}")


def run_backfill(remote_write_config, utils_dir, data_block_dir, historical_data_file):
    """Execute backfill.sh script to upload data to Prometheus."""
    backfill_script = os.path.join(utils_dir, "backfill.sh")

    if not os.path.exists(backfill_script):
        raise FileNotFoundError(f"backfill.sh not found at {backfill_script}")

    cmd = [
        backfill_script,
        remote_write_config["url"],
        remote_write_config["username"],
        remote_write_config["password"],
        utils_dir,
        data_block_dir,
        historical_data_file,
    ]

    logging.info(f"Running backfill command: {' '.join(cmd)}")
    logging.info("=" * 80)

    # Run without capturing output so logs stream in real-time
    result = subprocess.run(cmd)

    logging.info("=" * 80)

    if result.returncode != 0:
        logging.error(f"Backfill failed with return code {result.returncode}")
        sys.exit(1)

    logging.info("Backfill completed successfully")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill metrics to Prometheus with generated timeseries data"
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
        "--start-epoch",
        type=int,
        required=True,
        help="Backfill start time as Unix epoch timestamp",
    )
    parser.add_argument(
        "--end-epoch",
        type=int,
        required=True,
        help="Backfill end time as Unix epoch timestamp",
    )
    parser.add_argument(
        "--trend-coefficient",
        type=float,
        default=0.1,
        help="Trend coefficient for timeseries generation (default: 0.1)",
    )
    parser.add_argument(
        "--description",
        default="Backfilled metric data",
        help="Metric description (default: 'Backfilled metric data')",
    )
    parser.add_argument(
        "--step-size",
        default="5m",
        help="Time granularity for data points (default: 5m). Examples: 5m, 15m, 1h, or just 5 for 5 minutes",
    )
    parser.add_argument(
        "--flat-base",
        type=float,
        default=5.0,
        help="Flat base value for trend generation (default: 5.0)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for generated files (default: project utils directory)",
    )
    parser.add_argument(
        "--env",
        default="staging",
        help="Environment (e.g., 'scale', 'staging', 'ci' for edge URLs, others for prod URLs). Default: staging",
    )

    args = parser.parse_args()

    # Parse step size
    try:
        step_size_minutes = parse_step_size(args.step_size)
    except ValueError as e:
        logging.error(f"Invalid step-size: {e}")
        sys.exit(1)

    start_time = datetime.fromtimestamp(args.start_epoch)
    end_time = datetime.fromtimestamp(args.end_epoch)

    if start_time >= end_time:
        logging.error("Start time must be before end time")
        sys.exit(1)

    logging.info(f"Generating timeseries from {start_time} to {end_time}")
    logging.info(f"Metric: {args.metric_name}")
    logging.info(f"Labels: {args.labels}")
    logging.info(f"Trend coefficient: {args.trend_coefficient}")
    logging.info(f"Flat base: {args.flat_base}")
    logging.info(f"Step size: {step_size_minutes} minutes")

    labels_dict = parse_labels(args.labels)
    labels_str = format_labels(labels_dict)

    ts_values, time_points = generate_timeseries(
        start_time, end_time, args.trend_coefficient, step_size_minutes, args.flat_base
    )

    timestamps = [int(tp.timestamp()) for tp in time_points]

    utils_dir = (
        args.output_dir if args.output_dir else os.path.join(project_root, "utils")
    )
    historical_data_file = f"{args.metric_name}_backfill_{args.start_epoch}.txt"
    data_block_dir = f"/{args.metric_name}_backfill_data/"

    output_file = os.path.join(utils_dir, historical_data_file)

    write_openmetrics_file(
        args.metric_name,
        labels_str,
        ts_values,
        timestamps,
        output_file,
        args.description,
    )

    logging.info(f"Environment: {args.env}")
    logging.info("Fetching remote write configuration...")
    remote_write_config = get_remote_write_config(args.env)

    run_backfill(remote_write_config, utils_dir, data_block_dir, historical_data_file)

    logging.info("Backfill process completed successfully!")


if __name__ == "__main__":
    main()
