# Backfill Script Usage

## Overview
The `backfill.py` script allows you to backfill metrics to Prometheus with synthetically generated timeseries data. It uses the same timeseries generation pattern from the test features with configurable trend coefficients.

## Prerequisites
- `.env` file must be configured with `ENV` and `CDO_TOKEN`
- Poetry dependencies installed: `poetry install` or `make install`
- `backfill.sh` script must exist in the `utils/` directory

## Quick Start with Makefile

The easiest way to run the backfill script is using the provided Makefile:

```bash
# Install dependencies first
make install

# Backfill 21 days of data (default for RAVPN)
make backfill-21d METRIC_NAME=vpn LABELS='instance=127.0.0.2:9273,uuid=device-123,vpn=active_ravpn_tunnels'

# Backfill 7 days of data
make backfill-7d METRIC_NAME=cpu LABELS='cpu=lina_cp_avg,uuid=device-456'

# Backfill 1 day of data
make backfill-1d

# Custom date range (requires epoch timestamps)
make backfill START_EPOCH=1702800000 END_EPOCH=1704614400 METRIC_NAME=memory

# Clean up generated files
make clean

# View all available commands
make help
```

## Manual Usage

```bash
python3 scripts/backfill.py \
  --metric-name <metric_name> \
  --labels "<key1>=<value1>,<key2>=<value2>" \
  --start-epoch <unix_timestamp> \
  --end-epoch <unix_timestamp> \
  --trend-coefficient <float> \
  [--flat-base <float>] \
  [--description "<description>"] \
  [--step-size <size>] \
  [--output-dir <directory>]
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--metric-name` | Yes | - | Name of the metric (e.g., 'vpn', 'cpu', 'memory') |
| `--labels` | Yes | - | Label key-value pairs in format 'key1=value1,key2=value2' |
| `--start-epoch` | Yes | - | Backfill start time as Unix epoch timestamp |
| `--end-epoch` | Yes | - | Backfill end time as Unix epoch timestamp |
| `--trend-coefficient` | No | 0.1 | Trend coefficient for timeseries generation |
| `--flat-base` | No | 5.0 | Flat base value for trend generation |
| `--description` | No | "Backfilled metric data" | Metric description |
| `--step-size` | No | 5m | Time granularity (e.g., '5m', '15m', '1h') |
| `--output-dir` | No | `<project>/utils` | Output directory for generated files |

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

### Example 1: Backfill VPN metrics for 21 days
```bash
# Calculate epoch times for 21 days ago to now
START_EPOCH=$(date -v-21d +%s)
END_EPOCH=$(date +%s)

python3 scripts/backfill.py \
  --metric-name vpn \
  --labels "instance=127.0.0.2:9273,job=metrics_generator:8123,tenant_uuid=abc123,uuid=device-uuid-123,vpn=active_ravpn_tunnels" \
  --start-epoch $START_EPOCH \
  --end-epoch $END_EPOCH \
  --trend-coefficient 0.1 \
  --flat-base 5.0 \
  --description "Active RAVPN tunnels"
```

### Example 2: Backfill CPU metrics with higher trend
```bash
START_EPOCH=1702800000
END_EPOCH=1704614400

python3 scripts/backfill.py \
  --metric-name cpu \
  --labels "cpu=lina_cp_avg,tenant_uuid=xyz789,uuid=device-xyz" \
  --start-epoch $START_EPOCH \
  --end-epoch $END_EPOCH \
  --trend-coefficient 0.5 \
  --flat-base 10.0 \
  --description "CPU utilization"
```

## Default Timeseries Pattern

The script generates timeseries with:
- **Trend**: Linear trend with configurable parameters
  - `coefficient` (default: 0.1, configurable via `--trend-coefficient`)
  - `time_unit=timedelta(hours=1)`
  - `flat_base` (default: 5.0, configurable via `--flat-base`)
- **Seasonality**: Daily seasonality pattern matching the test features
- **Noise**: Gaussian noise with `mean=0`, `std=3`, `random_seed=42`
- **Granularity**: Configurable via `--step-size` (default: 5m, can use 5m, 15m, 1h, etc.)

## Output

The script will:
1. Generate timeseries data based on your parameters
2. Write data to OpenMetrics format file in the utils directory
3. Fetch remote write configuration from GCM
4. Execute `backfill.sh` to upload data blocks to Prometheus
5. Clean up generated block files

## Notes

- The script automatically fetches remote write credentials from the CDO platform
- Generated files follow the naming pattern: `<metric_name>_backfill_<start_epoch>.txt`
- Data blocks are temporarily stored in `/<metric_name>_backfill_data/` and cleaned up after upload
- The script uses the same seasonality pattern as defined in `generate_timeseries()` in `ra_vpn.py`
