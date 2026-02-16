from datetime import timedelta, datetime, timezone

import numpy as np
import pandas as pd

from darts.utils.timeseries_generation import (
    constant_timeseries,
    gaussian_timeseries,
    linear_timeseries,
    sine_timeseries,
)
from typing import Any, List, Optional

from pydantic import BaseModel


class SeriesConfig(BaseModel, arbitrary_types_allowed=True):
    start_value: float
    end_value: float
    start_time: datetime = datetime.now(timezone.utc)
    duration: timedelta
    step: timedelta = timedelta(minutes=1)


class TransitionConfig(BaseModel, arbitrary_types_allowed=True):
    start_time: datetime
    transition_window: timedelta = timedelta(minutes=1)


class TimeConfig(BaseModel, arbitrary_types_allowed=True):
    series_config: SeriesConfig
    transition_config: Optional[TransitionConfig] = None


class NoiseConfig(BaseModel, arbitrary_types_allowed=True):
    enable: bool
    mean: float = 0.0
    std: float = 2.0


class SeasonalityConfig(BaseModel, arbitrary_types_allowed=True):
    enable: bool
    amplitude: float = 200.0
    period: timedelta = timedelta(hours=6)


class MissingDataConfig(BaseModel, arbitrary_types_allowed=True):
    start_time: datetime
    duration: timedelta
    miss_probability: float  # Probability of a value being missing (0)


default_noise = NoiseConfig(enable=True, mean=0, std=2)
default_seasonality = SeasonalityConfig(
    enable=True, amplitude=200, period=timedelta(hours=6)
)


_COMPONENT_NAME = "value"


def _darts_ts_to_dataframe(darts_ts) -> pd.DataFrame:
    """Convert a Darts TimeSeries to a pd.DataFrame with 'ds' (epoch) and 'y' columns."""
    pdf = darts_ts.pd_dataframe()
    timestamps = [t.timestamp() for t in pdf.index]
    values = pdf.iloc[:, 0].values
    return pd.DataFrame({"ds": timestamps, "y": values})


def _build_piecewise_signal(
    series_config: SeriesConfig,
    transition_config: Optional[TransitionConfig],
) -> Any:
    """Build a piecewise signal: flat(start_value) → linear transition → flat(end_value).

    Uses Darts linear_timeseries and constant_timeseries, then concatenates.
    """
    # Strip tz for darts (xarray doesn't support tz-aware timestamps)
    start_time = pd.Timestamp(series_config.start_time).tz_localize(None)
    end_time = start_time + series_config.duration
    freq_str = f"{int(series_config.step.total_seconds())}s"
    total_points = int(series_config.duration / series_config.step)

    if transition_config is None:
        # Instant switch at start_time
        return constant_timeseries(
            value=series_config.end_value,
            start=start_time,
            length=total_points,
            freq=freq_str,
            column_name=_COMPONENT_NAME,
        )

    transition_start = pd.Timestamp(transition_config.start_time).tz_localize(None)
    transition_end = transition_start + transition_config.transition_window

    # Calculate point counts for each segment
    pre_points = max(0, int((transition_start - start_time) / series_config.step))
    transition_points = max(
        1, int(transition_config.transition_window / series_config.step)
    )
    post_points = max(0, total_points - pre_points - transition_points)

    segments = []

    # Pre-transition flat segment
    if pre_points > 0:
        segments.append(
            constant_timeseries(
                value=series_config.start_value,
                start=start_time,
                length=pre_points,
                freq=freq_str,
                column_name=_COMPONENT_NAME,
            )
        )

    # Transition segment (linear ramp)
    trans_start_ts = start_time + pre_points * series_config.step
    if transition_points > 0:
        segments.append(
            linear_timeseries(
                start_value=series_config.start_value,
                end_value=series_config.end_value,
                start=trans_start_ts,
                length=transition_points,
                freq=freq_str,
                column_name=_COMPONENT_NAME,
            )
        )

    # Post-transition flat segment
    if post_points > 0:
        post_start_ts = trans_start_ts + transition_points * series_config.step
        segments.append(
            constant_timeseries(
                value=series_config.end_value,
                start=post_start_ts,
                length=post_points,
                freq=freq_str,
                column_name=_COMPONENT_NAME,
            )
        )

    # Concatenate all segments
    if len(segments) == 1:
        return segments[0]

    result = segments[0]
    for seg in segments[1:]:
        result = result.concatenate(seg, ignore_time_axis=True)
    return result


def generate_missing_data(config: MissingDataConfig, frequency: timedelta):
    """Generate a list of 0s (missing) and 1s (present) based on the miss_probability.

    Args:
        config (MissingDataConfig): Configuration containing start time, duration, and miss probability.
        frequency (timedelta): The interval at which to generate values (e.g., 1 second, 1 minute).

    Returns:
        list: A list of 0s (missing) and 1s (present).
    """
    num_samples = int(config.duration.total_seconds() / frequency.total_seconds())
    data = np.random.choice(
        [1, 0],
        size=num_samples,
        p=[1 - config.miss_probability, config.miss_probability],
    )
    return list(data)


def find_closest_index(time_points, target_time):
    time_array = np.array(
        time_points, dtype="datetime64[ns]"
    )  # Convert list to numpy datetime64
    return np.abs(time_array - np.datetime64(target_time)).argmin()


def generate_timeseries(
    time_config: TimeConfig,
    noise_config: NoiseConfig = default_noise,
    seasonality_config: SeasonalityConfig = default_seasonality,
    missing_data_configs: List[MissingDataConfig] | None = None,
) -> pd.DataFrame:
    # Strip tz for darts; re-localize to UTC after extraction for correct epoch conversion
    start_time = pd.Timestamp(time_config.series_config.start_time).tz_localize(None)
    freq_str = f"{int(time_config.series_config.step.total_seconds())}s"
    total_points = int(
        time_config.series_config.duration / time_config.series_config.step
    )

    # Build the base piecewise signal
    base_signal = _build_piecewise_signal(
        time_config.series_config, time_config.transition_config
    )

    # Extract time index and values as numpy arrays to avoid xarray
    # component-name alignment issues (FutureWarning + potential NaN)
    # Re-localize to UTC so .timestamp() produces correct epoch seconds
    time_index = base_signal.time_index.tz_localize("UTC")
    values = base_signal.values().flatten()

    # Add seasonality (numpy arithmetic)
    if seasonality_config.enable:
        period_in_steps = seasonality_config.period / time_config.series_config.step
        # value_frequency = number of full periods per time unit (1 step)
        value_frequency = 1.0 / period_in_steps
        seasonality_ts = sine_timeseries(
            value_frequency=value_frequency,
            value_amplitude=seasonality_config.amplitude,
            value_y_offset=0,
            start=start_time,
            length=total_points,
            freq=freq_str,
        )
        values = values + seasonality_ts.values().flatten()

    # Add noise (numpy arithmetic)
    if noise_config.enable:
        noise_ts = gaussian_timeseries(
            mean=noise_config.mean,
            std=noise_config.std,
            start=start_time,
            length=total_points,
            freq=freq_str,
        )
        values = values + noise_ts.values().flatten()

    # Build DataFrame directly from numpy arrays
    timestamps = [t.timestamp() for t in time_index]
    result_df = pd.DataFrame({"ds": timestamps, "y": values})

    # Apply missing data
    if missing_data_configs is not None:
        time_points = pd.to_datetime(result_df["ds"], unit="s")
        for missing_data_config in missing_data_configs:
            missing_data = generate_missing_data(
                missing_data_config, time_config.series_config.step
            )
            start_index = find_closest_index(
                time_points, missing_data_config.start_time
            )
            for i in range(len(missing_data)):
                if missing_data[i] == 0:
                    result_df.loc[start_index + i, "y"] = None
        result_df = result_df.dropna()

    return result_df


def generate_spikes(spike_pattern, spike_multiplier, ts_values):
    # Cycle through the spike pattern
    for i in range(len(ts_values)):
        if spike_pattern[i % len(spike_pattern)]:
            ts_values[i] *= spike_multiplier

    return ts_values
