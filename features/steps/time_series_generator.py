from datetime import timedelta, datetime

import numpy as np
import pandas as pd

from mockseries.noise import RedNoise
from mockseries.transition.transition import Transition
from mockseries.trend import Switch
from mockseries.seasonality.seasonality import Seasonality
from mockseries.seasonality.sinusoidal_seasonality import SinusoidalSeasonality
from mockseries.utils import datetime_range
from mockseries.noise.noise import Noise
from typing import List, Optional

from pydantic import BaseModel


class SeriesConfig(BaseModel, arbitrary_types_allowed=True):
    start_value: float
    end_value: float
    start_time: datetime = datetime.now()
    duration: timedelta
    step: timedelta = timedelta(minutes=1)


class TransitionConfig(BaseModel, arbitrary_types_allowed=True):
    start_time: datetime
    transition: Optional[Transition] = None


class TimeConfig(BaseModel, arbitrary_types_allowed=True):
    series_config: SeriesConfig
    transition_config: Optional[TransitionConfig] = None


class NoiseConfig(BaseModel, arbitrary_types_allowed=True):
    enable: bool
    noise_list: List[Noise] = []


class SeasonalityConfig(BaseModel, arbitrary_types_allowed=True):
    enable: bool
    seasonality_list: List[Seasonality] = []


class MissingDataConfig(BaseModel, arbitrary_types_allowed=True):
    start_time: datetime
    duration: timedelta
    miss_probability: float  # Probability of a value being missing (0)


default_noise = NoiseConfig(
    enable=True, noise_list=[RedNoise(mean=0, std=2, correlation=0.5, random_seed=42)]
)
default_seasonality = SeasonalityConfig(
    enable=True,
    seasonality_list=[SinusoidalSeasonality(amplitude=200, period=timedelta(hours=6))],
)


def convert_to_dataframe(ts_values, time_points: List[datetime]) -> pd.DataFrame:
    metrics = pd.DataFrame(columns=["ds", "y"])
    for i, value in enumerate(time_points):
        metrics.loc[i] = [value.timestamp(), ts_values[i]]

    metrics = metrics.dropna()
    return metrics


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
    switch = None
    if time_config.transition_config is None:
        switch = Switch(
            start_time=time_config.series_config.start_time,
            base_value=time_config.series_config.start_value,
            switch_value=time_config.series_config.end_value,
        )
    else:
        switch = Switch(
            start_time=time_config.transition_config.start_time,
            base_value=time_config.series_config.start_value,
            switch_value=time_config.series_config.end_value,
            transition=time_config.transition_config.transition,
        )
    time_series = switch

    if seasonality_config.enable:
        for seasonality in seasonality_config.seasonality_list:
            time_series = time_series + seasonality

    if noise_config.enable:
        for noise in noise_config.noise_list:
            time_series = time_series + noise

    time_points = datetime_range(
        granularity=time_config.series_config.step,
        start_time=time_config.series_config.start_time,
        end_time=time_config.series_config.start_time
        + time_config.series_config.duration,
    )

    ts_values = time_series.generate(time_points=time_points)

    if missing_data_configs is not None:
        for missing_data_config in missing_data_configs:
            missing_data = generate_missing_data(
                missing_data_config, time_config.series_config.step
            )

            # Find the first index in timepoints corresponding to the start time of the missing data
            start_index = find_closest_index(
                time_points, missing_data_config.start_time
            )

            # Replace the values with missing data
            for i in range(len(missing_data)):
                if missing_data[i] == 0:
                    ts_values[start_index + i] = None

    return convert_to_dataframe(ts_values, time_points)


def generate_spikes(spike_pattern, spike_multiplier, ts_values):
    # Cycle through the spike pattern
    for i in range(len(ts_values)):
        if spike_pattern[i % len(spike_pattern)]:
            ts_values[i] *= spike_multiplier

    return ts_values
