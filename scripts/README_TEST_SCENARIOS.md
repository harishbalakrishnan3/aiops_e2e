# Test Historical Scenarios

## Overview
The `test_historical_scenarios.py` script enables testing and validation of different historical data patterns before backfilling to Prometheus. It generates synthetic timeseries data with configurable characteristics and provides visualization to verify data quality.

## Features
- **5 predefined test scenarios** covering common data patterns
- **Automatic device selection** - finds devices without historical data to avoid conflicts
- **Dry-run mode** to generate and visualize data without backfilling
- **Parameterized configuration** for metric name, labels, trend coefficient, and flat base
- **Visual validation** with automatic graph generation
- **Make command generation** for easy backfill execution

## Prerequisites
- `.env` file configured with `ENV` and `CDO_TOKEN` (required for device auto-selection and backfill)
- Poetry dependencies installed: `make install`
- matplotlib for visualization: included in poetry dependencies

## Automatic Device Selection
The script can automatically find a device that **doesn't have data** for the specified historical duration. This prevents backfill conflicts with existing data.

**How it works:**
1. Fetches all available standalone devices from CDO
2. Queries Prometheus to check if each device has existing data for the time range
3. Selects the first device without any historical data
4. Automatically adds the device's `uuid` to the metric labels

**Example PromQL query used:**
```
mem{mem="used_percentage_lina", uuid="{device_uid}"}
```

**Enable/Disable:**
- `--auto-select-device true` (default): Automatically finds suitable device
- `--auto-select-device false`: Uses the uuid from provided labels

## Test Scenarios

| Scenario | Name | Duration | Trend | Seasonality | Description |
|----------|------|----------|-------|-------------|-------------|
| 1 | 1_month_trend_seasonality | 30 days | Yes (0.05) | Yes | One month data with upward trend and daily seasonality |
| 2 | 1_month_flat | 30 days | No (0.0) | No | One month data with no trend or seasonality (flat with noise) |
| 3 | 1_week_trend_seasonality | 7 days | Yes (0.2) | Yes | One week data with upward trend and daily seasonality |
| 4 | 1_week_flat | 7 days | No (0.0) | No | One week data with no trend or seasonality (flat with noise) |
| 5 | 1_day | 1 day | Yes (0.5) | Yes | One day historical data with 5-minute granularity |

## Quick Start with Makefile

### Run All Scenarios (Dry-run)
```bash
# Generate graphs for all scenarios with auto-device selection
make test-scenarios

# With custom metric and labels (auto-selects device)
make test-scenarios METRIC_NAME=mem LABELS='mem=used_percentage_lina'
```

### Run Single Scenario (Dry-run)
```bash
# Run scenario 1 with auto-device selection for memory metric
make test-scenarios-single SCENARIO=1 METRIC_NAME=mem LABELS='mem=used_percentage_lina'

# Run scenario 3 with custom parameters
make test-scenarios-single SCENARIO=3 TREND_COEFFICIENT=0.5 FLAT_BASE=50

# Run with custom step size (15 minute granularity)
make test-scenarios-single SCENARIO=1 METRIC_NAME=mem LABELS='mem=used_percentage_lina' STEP_SIZE=15m

# Run scenario 2 with manual device UUID (no auto-selection)
make test-scenarios-single SCENARIO=2 METRIC_NAME=memory LABELS='mem=used,uuid=device-456'
```

## Manual Usage

### Dry-run Mode (Default)
```bash
# Generate graphs for all scenarios with auto-device selection
poetry run python scripts/test_historical_scenarios.py --dry-run true

# Single scenario with memory metric (auto-selects device)
poetry run python scripts/test_historical_scenarios.py \
  --scenario 1 \
  --metric-name mem \
  --labels "mem=used_percentage_lina" \
  --dry-run true

# Override trend and base with auto-device selection
poetry run python scripts/test_historical_scenarios.py \
  --scenario 3 \
  --metric-name mem \
  --labels "mem=used_percentage_lina" \
  --trend-coefficient 0.5 \
  --flat-base 50 \
  --dry-run true

# Custom step size for higher/lower granularity
poetry run python scripts/test_historical_scenarios.py \
  --scenario 1 \
  --metric-name mem \
  --labels "mem=used_percentage_lina" \
  --step-size 15m \
  --dry-run true

# Disable auto-selection and use specific device
poetry run python scripts/test_historical_scenarios.py \
  --scenario 1 \
  --metric-name mem \
  --labels "mem=used_percentage_lina,uuid=specific-device-uuid" \
  --auto-select-device false \
  --dry-run true
```

### Execute Backfill Mode
**Note:** For the first iteration, the actual backfill invocation is commented out in the code. To enable:
1. Open `scripts/test_historical_scenarios.py`
2. Find the `process_scenario()` function
3. Uncomment the backfill execution block
4. Run with `--dry-run false`

```bash
poetry run python scripts/test_historical_scenarios.py \
  --scenario 1 \
  --metric-name vpn \
  --labels "instance=127.0.0.2:9273,uuid=device-123,vpn=active_ravpn_tunnels" \
  --dry-run false
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--scenario` | No | `all` | Scenario to execute (1-5 or "all") |
| `--metric-name` | No | `test_metric` | Name of the metric |
| `--labels` | No | `instance=127.0.0.1:9090,job=test` | Label key-value pairs (exclude uuid for auto-selection) |
| `--description` | No | Scenario description | Metric description |
| `--trend-coefficient` | No | Scenario default | Override trend coefficient |
| `--flat-base` | No | Scenario default | Override flat base value |
| `--step-size` | No | `5m` | Time granularity for data points (5m, 15m, 1h, 30s) |
| `--dry-run` | No | `true` | true = graphs only, false = execute backfill |
| `--auto-select-device` | No | `true` | true = auto-find device, false = use uuid from labels |
| `--output-dir` | No | `analysis/test_scenarios` | Output directory for plots |

## Output

### Dry-run Mode
The script generates:
1. **PNG graphs** for each scenario in `analysis/test_scenarios/`
   - File naming: `<scenario_name>.png`
   - Includes statistics overlay (data points, min/max, mean, trend coefficient, flat base)
2. **Make commands** to execute backfill later
3. **Summary statistics** in console output

### Backfill Mode
When dry-run is false and backfill code is uncommented:
1. Generates timeseries data
2. Creates OpenMetrics format file
3. Fetches remote write configuration from CDO
4. Executes backfill to Prometheus
5. Cleans up temporary files

## Scenario Details

### Understanding Trend Coefficient
The trend coefficient determines the rate of increase per hour:
- **Coefficient = 0.05**: Increases by 0.05 units/hour (~1.2 units/day, ~36 units/30 days)
- **Coefficient = 0.2**: Increases by 0.2 units/hour (~4.8 units/day, ~33.6 units/week)
- **Coefficient = 0.5**: Increases by 0.5 units/hour (~12 units/day)

### Scenario 1: One Month with Trend & Seasonality
- **Use case:** Baseline growth pattern
- **Trend coefficient:** 0.05 (moderate upward trend: ~36 unit increase over 30 days)
- **Flat base:** 10
- **Granularity:** 15 minutes
- **Data points:** ~2,880 points
- **Total increase:** ~36 units from start to end

### Scenario 2: One Month Flat
- **Use case:** Stable baseline with no patterns
- **Trend coefficient:** 0.0 (no trend)
- **Flat base:** 20
- **Seasonality:** None (only noise)
- **Granularity:** 15 minutes
- **Data points:** ~2,880 points

### Scenario 3: One Week with Trend & Seasonality
- **Use case:** Short-term growth pattern
- **Trend coefficient:** 0.2 (stronger upward trend: ~33.6 unit increase over 7 days)
- **Flat base:** 15
- **Granularity:** 15 minutes
- **Data points:** ~672 points
- **Total increase:** ~33.6 units from start to end

### Scenario 4: One Week Flat
- **Use case:** Short-term stable baseline
- **Trend coefficient:** 0.0 (no trend)
- **Flat base:** 25
- **Seasonality:** None (only noise)
- **Granularity:** 15 minutes
- **Data points:** ~672 points

### Scenario 5: One Day
- **Use case:** Detailed intraday pattern
- **Trend coefficient:** 0.5 (visible upward trend: ~12 unit increase over 1 day)
- **Flat base:** 30
- **Granularity:** 5 minutes (higher resolution)
- **Data points:** ~288 points
- **Total increase:** ~12 units from start to end

## Customization

### Modifying Scenario Defaults
Edit the `SCENARIOS` dictionary in `test_historical_scenarios.py`:
```python
SCENARIOS = {
    "1": ScenarioConfig(
        name="1_month_trend_seasonality",
        days_back=30,
        trend_coefficient=0.2,  # Modify this
        flat_base=10,           # Modify this
        has_seasonality=True,
        description="...",
    ),
}
```

### Adding New Scenarios
Add a new entry to the `SCENARIOS` dictionary:
```python
"6": ScenarioConfig(
    name="custom_scenario",
    days_back=14,
    trend_coefficient=0.15,
    flat_base=12,
    has_seasonality=True,
    description="Two weeks with custom parameters",
),
```

## Workflow

### 1. Dry-run and Validate
```bash
# Generate all scenarios
make test-scenarios

# Review generated plots in analysis/test_scenarios/
open analysis/test_scenarios/*.png
```

### 2. Adjust Parameters (if needed)
```bash
# Test with different trend coefficient
make test-scenarios-single SCENARIO=1 TREND_COEFFICIENT=0.5

# Test with different flat base
make test-scenarios-single SCENARIO=3 FLAT_BASE=100
```

### 3. Execute Backfill
```bash
# Option A: Uncomment backfill code in script and run
poetry run python scripts/test_historical_scenarios.py \
  --scenario 1 \
  --metric-name vpn \
  --labels "instance=127.0.0.2:9273,uuid=device-123" \
  --dry-run false

# Option B: Use generated make command from dry-run output
make backfill METRIC_NAME=vpn LABELS='...' START_EPOCH=... END_EPOCH=...
```

## Examples

### Example 1: Validate All Scenarios with Auto-Device Selection
```bash
# Generate graphs for all scenarios - auto-selects suitable device
make test-scenarios METRIC_NAME=mem LABELS='mem=used_percentage_lina'

# Output: 5 PNG files in analysis/test_scenarios/
# - 1_month_trend_seasonality.png
# - 1_month_flat.png
# - 1_week_trend_seasonality.png
# - 1_week_flat.png
# - 1_day.png
# Console output shows: "✓ Found suitable device! Device Name: ... Device UUID: ..."
```

### Example 2: Memory Metric with Auto-Device Selection
```bash
# Script automatically finds device without historical memory data
poetry run python scripts/test_historical_scenarios.py \
  --scenario 1 \
  --metric-name mem \
  --labels "mem=used_percentage_lina" \
  --dry-run true

# Console output shows:
# [1/10] Checking device: device-name-1 (uuid: xxx)
# [2/10] Checking device: device-name-2 (uuid: yyy)
# ✓ Found suitable device!
#   Device Name: device-name-2
#   Device UUID: yyy
#   No data present for the last 30 days
```

### Example 3: CPU Utilization Pattern with Manual Device
```bash
# Disable auto-selection to use specific device
poetry run python scripts/test_historical_scenarios.py \
  --scenario 3 \
  --metric-name cpu \
  --labels "cpu=lina_cp_avg,uuid=device-xyz" \
  --trend-coefficient 0.4 \
  --flat-base 20 \
  --description "CPU utilization with upward trend" \
  --auto-select-device false \
  --dry-run true
```

## Troubleshooting

### Issue: No graphs generated
**Solution:** Check that matplotlib is installed and output directory is writable
```bash
poetry install
ls -la analysis/test_scenarios/
```

### Issue: CDO_TOKEN error
**Solution:** Required for device auto-selection and backfill
```bash
# CDO_TOKEN is required for auto-device selection (default behavior)
cat .env | grep CDO_TOKEN

# To run without CDO_TOKEN, disable auto-selection
poetry run python scripts/test_historical_scenarios.py \
  --auto-select-device false \
  --labels "mem=used_percentage_lina,uuid=known-device-uuid" \
  --dry-run true
```

### Issue: "All checked devices have existing data"
**Solution:** All devices already have data for the time period
1. Try a different metric that might have less coverage
2. Manually specify a device uuid with `--auto-select-device false`
3. Use a shorter time duration scenario (e.g., scenario 5 for 1 day)

```bash
# Try 1-day scenario instead of 30-day
make test-scenarios-single SCENARIO=5 METRIC_NAME=mem LABELS='mem=used_percentage_lina'
```

### Issue: Device auto-selection taking too long
**Solution:** The script checks up to 10 devices by default
- First device check is slowest (fetches device list)
- Subsequent checks are faster
- Typically completes in 10-30 seconds
- Progress shown: `[1/10] Checking device: ...`

### Issue: Backfill not executing
**Solution:** The backfill code is commented out by default
1. Open `scripts/test_historical_scenarios.py`
2. Navigate to `process_scenario()` function (around line 380)
3. Uncomment the backfill execution block
4. Run with `--dry-run false`

## Integration with Existing Scripts

The test scenarios script complements existing backfill functionality:

- **test_historical_scenarios.py** → Visual validation and testing
- **backfill.py** → Direct backfill with custom parameters
- **test_timeseries_generator.py** → Timeseries parameter experimentation

Workflow:
1. Use `test_historical_scenarios.py` to validate data patterns
2. Use `test_timeseries_generator.py` to fine-tune parameters
3. Use `backfill.py` or enable backfill in scenarios for actual data push

## Clean Up

```bash
# Remove generated plots
rm -rf analysis/test_scenarios/

# Remove backfill data files (if any generated)
make clean
```

## Notes

- All scenarios use Gaussian noise with `mean=0`, `std=3`, `random_seed=42`
- Seasonality pattern matches the pattern in `features/steps/ra_vpn.py`
- Generated graphs include overlay statistics for quick validation
- Epoch timestamps are automatically calculated based on current time
- Label names are automatically sanitized to conform to Prometheus naming rules
