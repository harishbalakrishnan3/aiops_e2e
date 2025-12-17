# Push Live Metrics Script Usage

## Overview
The `push_live_metrics.py` script allows you to push live metrics to Prometheus with synthetically generated timeseries data. It pushes one datapoint per minute for the specified duration, making it ideal for testing real-time metric ingestion and monitoring.

## Prerequisites
- `.env` file must be configured with `ENV` and `CDO_TOKEN`
- Poetry dependencies installed: `poetry install` or `make install`

## Quick Start with Makefile

The easiest way to run the push live metrics script is using the provided Makefile:

```bash
# Install dependencies first
make install

# Push live metrics for 30 minutes (default)
make push-live-30m METRIC_NAME=cpu LABELS='cpu=lina_cp_avg,tenant_uuid=abc123,uuid=device-456'

# Push live metrics for 1 hour
make push-live-1h METRIC_NAME=vpn LABELS='vpn=active_ravpn_tunnels,uuid=device-123'

# Push live metrics for 2 hours
make push-live-2h METRIC_NAME=memory LABELS='mem=used_percentage_lina,uuid=device-789'

# Custom duration (in minutes)
make push-live METRIC_NAME=cpu LABELS='cpu=snort_avg,uuid=device-xyz' DURATION=45

# View all available commands
make help
```

## Manual Usage

```bash
python3 scripts/push_live_metrics.py \
  --metric-name <metric_name> \
  --labels "<key1>=<value1>,<key2>=<value2>" \
  --duration <minutes> \
  --trend-coefficient <float> \
  [--description "<description>"]
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--metric-name` | Yes | - | Name of the metric (e.g., 'vpn', 'cpu', 'memory') |
| `--labels` | Yes | - | Label key-value pairs in format 'key1=value1,key2=value2' |
| `--duration` | Yes | - | Duration in minutes to push metrics (1 datapoint per minute) |
| `--trend-coefficient` | No | 0.1 | Trend coefficient for timeseries generation |
| `--description` | No | "Live metric data" | Metric description |

### Label Naming Rules

Label names must follow Prometheus naming conventions:
- Can only contain letters (a-z, A-Z), numbers (0-9), and underscores (_)
- Must match the pattern: `[a-zA-Z_][a-zA-Z0-9_]*`
- Cannot start with a number
- **Invalid characters (like hyphens) are automatically converted to underscores**

Examples:
- ❌ `test-label` → ✅ Auto-converted to `test_label`
- ❌ `123metric` → ✅ Auto-converted to `_123metric`
- ✅ `tenant_uuid` → No conversion needed
- ✅ `vpn_type` → No conversion needed

## Examples

### Example 1: Push CPU metrics for 30 minutes
```bash
make push-live-30m METRIC_NAME=cpu LABELS='cpu=lina_cp_avg,tenant_uuid=abc123,uuid=device-456'
```

### Example 2: Push VPN metrics for 1 hour with higher trend
```bash
make push-live-1h METRIC_NAME=vpn \
  LABELS='vpn=active_ravpn_tunnels,tenant_uuid=xyz789,uuid=device-123' \
  TREND_COEFFICIENT=0.5
```

### Example 3: Custom duration of 45 minutes
```bash
make push-live METRIC_NAME=memory \
  LABELS='mem=used_percentage_snort,tenant_uuid=def456,uuid=device-789' \
  DURATION=45
```

### Example 4: Manual command with all parameters
```bash
poetry run python scripts/push_live_metrics.py \
  --metric-name conn_stats \
  --labels "conn_stats=connection,description=in_use,tenant_uuid=abc123,uuid=device-xyz" \
  --duration 60 \
  --trend-coefficient 0.3 \
  --description "Connection statistics"
```

## Default Timeseries Pattern

The script generates timeseries with:
- **Trend**: Linear trend with configurable coefficient (default 0.1)
  - `time_unit=timedelta(hours=0.95)`
  - `flat_base=5`
- **Seasonality**: Daily seasonality pattern matching the test features
- **Noise**: Gaussian noise with `mean=0`, `std=3`, `random_seed=42`
- **Granularity**: 1-minute intervals (1 datapoint per minute)

## How It Works

1. **Generate Timeseries**: Creates synthetic data for the specified duration with 1-minute granularity
2. **Initialize Metrics**: Sets up OpenTelemetry metrics and remote write exporter
3. **Push Loop**: For each minute:
   - Push the current datapoint to Prometheus
   - Log the timestamp and value
   - Sleep for 60 seconds
   - Repeat until all datapoints are pushed
4. **Graceful Exit**: Handles Ctrl+C to stop early with summary

## Output Example

```
[2025-12-17 11:00:00,000] [INFO] Generating timeseries from 2025-12-17 11:00:00 to 2025-12-17 11:30:00
[2025-12-17 11:00:00,000] [INFO] Duration: 30 minutes
[2025-12-17 11:00:00,000] [INFO] Metric: cpu
[2025-12-17 11:00:00,000] [INFO] Labels: {'cpu': 'lina_cp_avg', 'tenant_uuid': 'abc123', 'uuid': 'device-456'}
[2025-12-17 11:00:00,000] [INFO] Generated 30 datapoints
[2025-12-17 11:00:00,000] [INFO] ================================================================================
[2025-12-17 11:00:00,000] [INFO] Starting live metric push (1 datapoint per minute)
[2025-12-17 11:00:00,000] [INFO] Press Ctrl+C to stop
[2025-12-17 11:00:00,000] [INFO] ================================================================================
[2025-12-17 11:00:00,000] [INFO] [1/30] Timestamp: 2025-12-17 11:00:00
[2025-12-17 11:00:00,500] [INFO] ✓ Pushed cpu = 12.45 (labels: {'cpu': 'lina_cp_avg', ...})
[2025-12-17 11:00:00,500] [INFO] Sleeping for 60 seconds...
[2025-12-17 11:01:00,500] [INFO] [2/30] Timestamp: 2025-12-17 11:01:00
[2025-12-17 11:01:01,000] [INFO] ✓ Pushed cpu = 13.21 (labels: {'cpu': 'lina_cp_avg', ...})
...
```

## Stopping Early

Press `Ctrl+C` at any time to gracefully stop the script. It will display how many datapoints were successfully pushed:

```
^C
================================================================================
Interrupted! Pushed 15/30 datapoints
================================================================================
```

## Notes

- The script pushes data in real-time (1 datapoint per minute)
- Total execution time = duration in minutes (e.g., 30 minutes for 30 datapoints)
- Each datapoint is pushed immediately to Prometheus using the OpenTelemetry remote write exporter
- Uses the same seasonality pattern as defined in `generate_timeseries()` in `ra_vpn.py`
- Can be interrupted with Ctrl+C without data loss (already pushed data remains in Prometheus)

## Comparison with Backfill

| Feature | backfill.py | push_live_metrics.py |
|---------|-------------|----------------------|
| **Use Case** | Historical data | Real-time/Live data |
| **Speed** | Fast (uploads entire dataset at once) | Slow (1 datapoint per minute) |
| **Time Range** | Past data (start/end epochs) | Current time forward (duration) |
| **Granularity** | 15-minute intervals | 1-minute intervals |
| **Method** | Prometheus backfill via promtool/mimirtool | Direct API push via OpenTelemetry |
| **Interruptible** | No (all-or-nothing) | Yes (Ctrl+C) |
