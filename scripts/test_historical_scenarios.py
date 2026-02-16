#!/usr/bin/env python3
"""
Test script for generating and validating different historical data scenarios.
Supports dry-run mode for visualization before actual backfill.

Test Scenarios:
1. One month historical data with upward trend and seasonality
2. One month historical data with no trend / seasonality
3. One week historical data with trend and seasonality
4. One week historical data with no trend and seasonality
5. One day historical data
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import requests
from darts.utils.timeseries_generation import (
    gaussian_timeseries,
    linear_timeseries,
    sine_timeseries,
)
from dotenv import load_dotenv
from jinja2 import Template
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.label_utils import format_labels, parse_labels, sanitize_label_name
from shared.step_utils import parse_step_to_minutes, parse_step_to_seconds

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


class ScenarioConfig:
    """Configuration for a test scenario."""

    def __init__(
        self,
        name,
        days_back,
        trend_coefficient,
        flat_base,
        has_seasonality,
        description,
        granularity_minutes=15,
    ):
        self.name = name
        self.days_back = days_back
        self.trend_coefficient = trend_coefficient
        self.flat_base = flat_base
        self.has_seasonality = has_seasonality
        self.description = description
        self.granularity_minutes = granularity_minutes

    def __repr__(self):
        return (
            f"ScenarioConfig(name='{self.name}', days_back={self.days_back}, "
            f"trend_coefficient={self.trend_coefficient}, flat_base={self.flat_base}, "
            f"has_seasonality={self.has_seasonality})"
        )


SCENARIOS = {
    "1": ScenarioConfig(
        name="1_month_trend_seasonality",
        days_back=30,
        trend_coefficient=0.05,  # Moderate upward trend: ~36 unit increase over 30 days
        flat_base=10,
        has_seasonality=True,
        description="One month data with upward trend and daily seasonality",
    ),
    "2": ScenarioConfig(
        name="1_month_flat",
        days_back=30,
        trend_coefficient=0.0,
        flat_base=20,
        has_seasonality=False,
        description="One month data with no trend or seasonality (flat line with noise)",
    ),
    "3": ScenarioConfig(
        name="1_week_trend_seasonality",
        days_back=7,
        trend_coefficient=0.2,  # Stronger upward trend: ~33.6 unit increase over 7 days
        flat_base=15,
        has_seasonality=True,
        description="One week data with upward trend and daily seasonality",
    ),
    "4": ScenarioConfig(
        name="1_week_flat",
        days_back=7,
        trend_coefficient=0.0,
        flat_base=25,
        has_seasonality=False,
        description="One week data with no trend or seasonality (flat line with noise)",
    ),
    "5": ScenarioConfig(
        name="1_day",
        days_back=1,
        trend_coefficient=0.5,  # Visible trend even over 1 day: ~12 unit increase
        flat_base=30,
        has_seasonality=True,
        description="One day historical data",
        granularity_minutes=5,
    ),
    "6": ScenarioConfig(
        name="2_weeks_trend_seasonality",
        days_back=14,
        trend_coefficient=0.1,  # Moderate upward trend: ~33.6 unit increase over 14 days
        flat_base=12,
        has_seasonality=True,
        description="Two weeks data with upward trend and daily seasonality",
    ),
}


def generate_timeseries(
    start_time,
    end_time,
    trend_coefficient,
    flat_base,
    has_seasonality,
    granularity_minutes=15,
):
    """
    Generate timeseries with specified parameters using Darts.

    Args:
        start_time: Start datetime
        end_time: End datetime
        trend_coefficient: Linear trend slope (0 for flat line)
        flat_base: Base value for trend
        has_seasonality: Whether to include daily seasonality pattern
        granularity_minutes: Time granularity in minutes

    Returns:
        tuple: (ts_values, time_points)
    """
    start_ts = pd.Timestamp(start_time)
    total_minutes = int((end_time - start_time).total_seconds() / 60)
    total_points = total_minutes // granularity_minutes
    freq = f"{granularity_minutes * 60}s"

    # Trend component (coefficient per hour)
    total_hours = total_minutes / 60
    end_trend_value = flat_base + trend_coefficient * total_hours
    trend = linear_timeseries(
        start_value=flat_base,
        end_value=end_trend_value,
        start=start_ts,
        length=total_points,
        freq=freq,
    )

    combined = trend

    if has_seasonality:
        steps_per_day = int(24 * 60 / granularity_minutes)
        seasonality = sine_timeseries(
            value_frequency=1.0 / steps_per_day,
            value_amplitude=9.25,
            value_y_offset=10.25,
            value_phase=np.pi,
            start=start_ts,
            length=total_points,
            freq=freq,
        )
        combined = combined + seasonality

    # Noise component
    noise = gaussian_timeseries(
        mean=0,
        std=3,
        start=start_ts,
        length=total_points,
        freq=freq,
    )
    combined = combined + noise

    pdf = combined.pd_dataframe()
    ts_values = pdf.iloc[:, 0].values
    time_points = list(pdf.index.to_pydatetime())

    return ts_values, time_points


def plot_timeseries(
    ts_values,
    time_points,
    scenario_config,
    output_dir,
    actual_trend_coef=None,
    actual_flat_base=None,
):
    """Plot and save timeseries visualization."""
    # Use actual values if provided, otherwise use scenario defaults
    trend_coef_display = (
        actual_trend_coef
        if actual_trend_coef is not None
        else scenario_config.trend_coefficient
    )
    flat_base_display = (
        actual_flat_base if actual_flat_base is not None else scenario_config.flat_base
    )

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(time_points, ts_values, linewidth=0.8, alpha=0.8, color="#1f77b4")
    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Value", fontsize=12)
    ax.set_title(
        f"Scenario: {scenario_config.description}",
        fontsize=14,
        fontweight="bold",
    )
    ax.grid(True, alpha=0.3)

    if scenario_config.days_back > 7:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    elif scenario_config.days_back > 1:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    else:
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    plt.xticks(rotation=45)

    stats_text = (
        f"Data Points: {len(ts_values)}\n"
        f"Min: {min(ts_values):.2f}\n"
        f"Max: {max(ts_values):.2f}\n"
        f"Mean: {sum(ts_values) / len(ts_values):.2f}\n"
        f"Trend Coef: {trend_coef_display}\n"
        f"Flat Base: {flat_base_display}"
    )
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        fontsize=9,
    )

    plt.tight_layout()
    plot_filename = f"{scenario_config.name}.png"
    plot_path = os.path.join(output_dir, plot_filename)
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close()

    logging.info(f"Saved plot to {plot_path}")


def get_devices():
    """Fetch all available devices from CDO."""
    load_dotenv()
    env = os.getenv("ENV")
    cdo_token = os.getenv("CDO_TOKEN")

    if not env or not cdo_token:
        raise ValueError("ENV and CDO_TOKEN must be set in .env file")

    base_url = f"https://edge.{env.lower()}.cdo.cisco.com"
    devices_url = f"{base_url}/aegis/rest/v1/services/targets/devices?q=deviceType:FTDC"

    logging.info(f"Fetching devices from {devices_url}")

    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[i for i in range(400, 600)],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)

    response = session.get(
        devices_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cdo_token}",
        },
        timeout=180,
    )

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch devices: {response.status_code} - {response.text}"
        )

    devices = response.json()
    logging.info(f"Found {len(devices)} devices")
    return devices


def is_data_present(
    device_uid, metric_name, label_filters, duration: timedelta, step="5m"
):
    """Check if data exists for a device in Prometheus for the specified duration."""
    load_dotenv()
    env = os.getenv("ENV")
    cdo_token = os.getenv("CDO_TOKEN")

    if not env or not cdo_token:
        raise ValueError("ENV and CDO_TOKEN must be set in .env file")

    base_url = f"https://edge.{env.lower()}.cdo.cisco.com"
    prometheus_url = (
        f"{base_url}/api/platform/ai-ops-data-query/v2/healthmetrics/queryRange"
    )

    MAX_PROMETHEUS_DATAPOINTS = 11000

    start_time = datetime.now() - duration
    end_time = datetime.now()

    total_duration_seconds = int(duration.total_seconds())
    step_seconds = parse_step_to_seconds(step)

    expected_datapoints = total_duration_seconds // step_seconds

    if expected_datapoints > MAX_PROMETHEUS_DATAPOINTS:
        step_seconds = total_duration_seconds // MAX_PROMETHEUS_DATAPOINTS
        step_minutes = round(step_seconds / 60 / 10) * 10
        step = f"{step_minutes}m"
        logging.debug(
            f"Query would return {expected_datapoints} datapoints, increasing step to {step}"
        )

    # Construct PromQL query based on metric and label filters
    if label_filters:
        query = f'{metric_name}{{{label_filters},uuid="{device_uid}"}}'
    else:
        query = f'{metric_name}{{uuid="{device_uid}"}}'

    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    endpoint = f"{prometheus_url}?query={query}&start={start_time_epoch}&end={end_time_epoch}&step={step}"

    logging.debug(f"Checking data for device {device_uid}: {endpoint}")

    retry = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[i for i in range(500, 600)],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)

    try:
        response = session.get(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cdo_token}",
            },
            timeout=60,
        )

        if response.status_code != 200:
            logging.warning(
                f"Query failed for device {device_uid}: {response.status_code}"
            )
            return False

        result = response.json()
        has_data = len(result.get("data", {}).get("result", [])) > 0

        if has_data:
            logging.debug(f"Device {device_uid} has existing data")
        else:
            logging.debug(f"Device {device_uid} has NO data for the specified period")

        return has_data
    except Exception as e:
        logging.warning(f"Error checking data for device {device_uid}: {e}")
        return False


def find_device_without_data(
    metric_name, label_filters, duration: timedelta, max_devices=10
):
    """Find a device that doesn't have data for the specified historical duration."""
    logging.info("=" * 80)
    logging.info(f"Searching for device without data for metric: {metric_name}")
    logging.info(f"Duration: {duration.days} days")
    logging.info(f"Label filters: {label_filters}")
    logging.info("=" * 80)

    try:
        devices = get_devices()

        # Filter standalone devices (no container type)
        standalone_devices = [d for d in devices if d.get("containerType") is None]

        if not standalone_devices:
            logging.warning("No standalone devices found, using all devices")
            standalone_devices = devices

        logging.info(
            f"Checking {min(len(standalone_devices), max_devices)} devices for existing data..."
        )

        checked_count = 0
        for device in standalone_devices[:max_devices]:
            device_uid = device.get("uid")
            device_name = device.get("name", "Unknown")

            if not device_uid:
                continue

            checked_count += 1
            logging.info(
                f"[{checked_count}/{min(len(standalone_devices), max_devices)}] Checking device: {device_name} (uuid: {device_uid})"
            )

            if not is_data_present(device_uid, metric_name, label_filters, duration):
                logging.info("")
                logging.info("✓ Found suitable device!")
                logging.info(f"  Device Name: {device_name}")
                logging.info(f"  Device UUID: {device_uid}")
                logging.info(f"  No data present for the last {duration.days} days")
                logging.info("")
                return device_uid, device_name

        logging.warning(f"All checked devices ({checked_count}) have existing data")
        logging.warning("Returning first device - backfill may fail if data overlaps")

        if standalone_devices:
            first_device = standalone_devices[0]
            return first_device.get("uid"), first_device.get("name", "Unknown")

        return None, None

    except Exception as e:
        logging.error(f"Failed to find device without data: {e}")
        logging.warning("Continuing without device auto-selection")
        return None, None


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


def run_backfill_script(
    metric_name,
    labels,
    start_epoch,
    end_epoch,
    trend_coefficient,
    flat_base,
    description,
    step_size_minutes,
):
    """Execute backfill.py script."""
    backfill_script = os.path.join(project_root, "scripts", "backfill.py")

    if not os.path.exists(backfill_script):
        raise FileNotFoundError(f"backfill.py not found at {backfill_script}")

    cmd = [
        "poetry",
        "run",
        "python",
        backfill_script,
        "--metric-name",
        metric_name,
        "--labels",
        labels,
        "--start-epoch",
        str(start_epoch),
        "--end-epoch",
        str(end_epoch),
        "--trend-coefficient",
        str(trend_coefficient),
        "--step-size",
        str(step_size_minutes),
        "--description",
        description,
    ]

    logging.info(f"Running backfill command: {' '.join(cmd)}")
    logging.info("=" * 80)

    result = subprocess.run(cmd)

    logging.info("=" * 80)

    if result.returncode != 0:
        logging.error(f"Backfill failed with return code {result.returncode}")
        return False

    logging.info("Backfill completed successfully")
    return True


def process_scenario(
    scenario_id,
    metric_name,
    labels,
    description_override,
    trend_coef_override,
    flat_base_override,
    dry_run,
    output_dir,
    auto_select_device,
    step_size_minutes,
):
    """Process a single test scenario."""
    if scenario_id not in SCENARIOS:
        logging.error(f"Invalid scenario ID: {scenario_id}")
        return False

    scenario = SCENARIOS[scenario_id]

    trend_coefficient = (
        trend_coef_override
        if trend_coef_override is not None
        else scenario.trend_coefficient
    )
    flat_base = (
        flat_base_override if flat_base_override is not None else scenario.flat_base
    )
    description = description_override if description_override else scenario.description
    granularity_minutes = (
        step_size_minutes
        if step_size_minutes is not None
        else scenario.granularity_minutes
    )

    logging.info("=" * 80)
    logging.info(f"Processing Scenario {scenario_id}: {scenario.name}")
    logging.info("=" * 80)
    logging.info(f"Description: {description}")
    logging.info(f"Days back: {scenario.days_back}")
    logging.info(f"Trend coefficient: {trend_coefficient}")
    logging.info(f"Flat base: {flat_base}")
    logging.info(f"Has seasonality: {scenario.has_seasonality}")
    logging.info(f"Step size (granularity): {granularity_minutes} minutes")
    logging.info(f"Dry run: {dry_run}")
    logging.info(f"Auto-select device: {auto_select_device}")
    logging.info("")

    # Auto-select device if enabled
    selected_device_uid = None
    selected_device_name = None

    if auto_select_device:
        # Parse existing labels to extract filters (excluding uuid if present)
        labels_dict = parse_labels(labels)

        # Remove uuid from labels if present (we'll auto-select it)
        if "uuid" in labels_dict:
            logging.info(f"Removing existing uuid from labels: {labels_dict['uuid']}")
            del labels_dict["uuid"]

        # Reconstruct label filters for PromQL query
        label_filters = (
            ",".join([f'{k}="{v}"' for k, v in labels_dict.items()])
            if labels_dict
            else None
        )

        # Find device without data
        duration = timedelta(days=scenario.days_back)
        selected_device_uid, selected_device_name = find_device_without_data(
            metric_name, label_filters, duration
        )

        if selected_device_uid:
            # Add uuid to labels
            labels_dict["uuid"] = selected_device_uid
            labels = ",".join([f"{k}={v}" for k, v in labels_dict.items()])
            logging.info(f"Updated labels with auto-selected device: {labels}")
        else:
            logging.warning("Could not auto-select device, using provided labels")
    else:
        logging.info("Device auto-selection disabled, using provided labels")

    logging.info("")

    end_time = datetime.now()
    start_time = end_time - timedelta(days=scenario.days_back)

    ts_values, time_points = generate_timeseries(
        start_time,
        end_time,
        trend_coefficient,
        flat_base,
        scenario.has_seasonality,
        granularity_minutes,
    )

    logging.info(f"Generated {len(ts_values)} data points")
    logging.info(f"Time range: {time_points[0]} to {time_points[-1]}")
    logging.info(f"Value range: {min(ts_values):.2f} to {max(ts_values):.2f}")
    logging.info(f"Mean: {sum(ts_values) / len(ts_values):.2f}")

    if selected_device_name:
        logging.info(f"Target device: {selected_device_name} ({selected_device_uid})")

    logging.info("")

    plot_timeseries(
        ts_values, time_points, scenario, output_dir, trend_coefficient, flat_base
    )

    if dry_run:
        logging.info("DRY RUN: Skipping actual backfill")
        logging.info(
            f"To execute backfill, run with --dry-run false or use the generated make command below"
        )
        logging.info("")

        start_epoch = int(start_time.timestamp())
        end_epoch = int(end_time.timestamp())

        make_cmd = (
            f"make backfill "
            f"METRIC_NAME={metric_name} "
            f"LABELS='{labels}' "
            f"START_EPOCH={start_epoch} "
            f"END_EPOCH={end_epoch} "
            f"TREND_COEFFICIENT={trend_coefficient} "
            f"DESCRIPTION='{description}'"
        )
        logging.info(f"Make command:\n{make_cmd}")

        if selected_device_name:
            logging.info("")
            logging.info(f"Selected Device: {selected_device_name}")
            logging.info(f"Device UUID: {selected_device_uid}")

        logging.info("")
        return True
    else:
        logging.info("Executing backfill...")
        labels_dict = parse_labels(labels)
        labels_str = format_labels(labels_dict)
        start_epoch = int(start_time.timestamp())
        end_epoch = int(end_time.timestamp())

        success = run_backfill_script(
            metric_name,
            labels,
            start_epoch,
            end_epoch,
            trend_coefficient,
            flat_base,
            description,
            granularity_minutes,
        )
        return success


def main():
    """Main function to execute test scenarios."""
    parser = argparse.ArgumentParser(
        description="Test historical data scenarios with visualization and backfill support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Scenarios:
  1 - One month historical data with upward trend and seasonality
  2 - One month historical data with no trend / seasonality (flat)
  3 - One week historical data with trend and seasonality
  4 - One week historical data with no trend and seasonality (flat)
  5 - One day historical data

Examples:
  # Dry run all scenarios (generate graphs only)
  poetry run python scripts/test_historical_scenarios.py --dry-run true

  # Dry run single scenario with auto-device selection
  poetry run python scripts/test_historical_scenarios.py --scenario 1 --dry-run true \\
    --metric-name mem --labels "mem=used_percentage_lina" --auto-select-device true

  # Execute backfill for scenario 1 (requires uncommenting code)
  poetry run python scripts/test_historical_scenarios.py --scenario 1 --dry-run false \\
    --metric-name vpn --labels "instance=127.0.0.2:9273,uuid=device-123,vpn=active_ravpn_tunnels"

  # Override trend coefficient and flat base with auto-device selection
  poetry run python scripts/test_historical_scenarios.py --scenario 3 --dry-run true \\
    --metric-name mem --labels "mem=used_percentage_lina" \\
    --trend-coefficient 0.5 --flat-base 50 --auto-select-device true
  
  # Custom step size for higher granularity
  poetry run python scripts/test_historical_scenarios.py --scenario 1 --dry-run true \\
    --metric-name mem --labels "mem=used_percentage_lina" --step-size 15m
        """,
    )

    parser.add_argument(
        "--scenario",
        choices=["1", "2", "3", "4", "5", "6", "all"],
        default="all",
        help="Scenario to execute (default: all)",
    )
    parser.add_argument(
        "--metric-name",
        default="test_metric",
        help="Name of the metric (default: test_metric)",
    )
    parser.add_argument(
        "--labels",
        default="instance=127.0.0.1:9090,job=test",
        help="Label key-value pairs in format 'key1=value1,key2=value2'",
    )
    parser.add_argument(
        "--description",
        default=None,
        help="Override metric description (default: use scenario description)",
    )
    parser.add_argument(
        "--trend-coefficient",
        type=float,
        default=None,
        help="Override trend coefficient (default: use scenario default)",
    )
    parser.add_argument(
        "--flat-base",
        type=float,
        default=None,
        help="Override flat base value (default: use scenario default)",
    )
    parser.add_argument(
        "--dry-run",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Dry run mode: true = generate graphs only, false = execute backfill (default: true)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for plots (default: project_root/analysis/test_scenarios)",
    )
    parser.add_argument(
        "--auto-select-device",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Auto-select device without historical data: true = auto-select, false = use provided uuid (default: true)",
    )
    parser.add_argument(
        "--step-size",
        default="5m",
        help="Time granularity for data points (default: 5m). Examples: 5m, 15m, 1h, 30s",
    )

    args = parser.parse_args()

    # Parse step size
    try:
        step_size_minutes = parse_step_to_minutes(args.step_size)
    except ValueError as e:
        logging.error(f"Invalid step-size: {e}")
        sys.exit(1)

    load_dotenv()
    cdo_token = os.getenv("CDO_TOKEN")

    # CDO_TOKEN required for backfill or device auto-selection
    if not cdo_token:
        if not args.dry_run:
            logging.error("CDO_TOKEN not found in .env file (required for backfill)")
            sys.exit(1)
        elif args.auto_select_device:
            logging.error(
                "CDO_TOKEN not found in .env file (required for device auto-selection)"
            )
            sys.exit(1)

    output_dir = (
        args.output_dir
        if args.output_dir
        else os.path.join(project_root, "analysis", "test_scenarios")
    )
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Output directory: {output_dir}")
    logging.info("")

    scenarios_to_run = (
        ["1", "2", "3", "4", "5", "6"] if args.scenario == "all" else [args.scenario]
    )

    success_count = 0
    failure_count = 0

    for scenario_id in scenarios_to_run:
        try:
            success = process_scenario(
                scenario_id,
                args.metric_name,
                args.labels,
                args.description,
                args.trend_coefficient,
                args.flat_base,
                args.dry_run,
                output_dir,
                args.auto_select_device,
                step_size_minutes,
            )
            if success:
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            logging.error(
                f"Error processing scenario {scenario_id}: {e}", exc_info=True
            )
            failure_count += 1

    logging.info("=" * 80)
    logging.info("EXECUTION SUMMARY")
    logging.info("=" * 80)
    logging.info(f"Total scenarios: {len(scenarios_to_run)}")
    logging.info(f"Successful: {success_count}")
    logging.info(f"Failed: {failure_count}")
    logging.info(f"Plots saved to: {output_dir}")

    if args.dry_run:
        logging.info("")
        logging.info(
            "DRY RUN MODE - Review the generated plots before executing backfill"
        )
        logging.info("To execute backfill:")
        logging.info("  1. Uncomment the backfill code in process_scenario() function")
        logging.info("  2. Run with --dry-run false")
        logging.info("  3. Or use the generated make commands shown above")

    sys.exit(0 if failure_count == 0 else 1)


if __name__ == "__main__":
    main()
