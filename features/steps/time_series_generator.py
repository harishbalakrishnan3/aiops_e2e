from datetime import timedelta , datetime
import pandas as pd 

from mockseries.noise import RedNoise
from mockseries.trend import  Switch
from mockseries.transition.lambda_transition import LambdaTransition
from mockseries.seasonality.seasonality import Seasonality
from mockseries.seasonality.sinusoidal_seasonality import SinusoidalSeasonality
from mockseries.utils import datetime_range
from mockseries.noise.noise import Noise
from typing import Optional

from pydantic import BaseModel

class NoiseConfig(BaseModel,arbitrary_types_allowed=True):
    enable: bool
    noise: Optional[Noise] = None

class SeasonalityConfig(BaseModel, arbitrary_types_allowed=True):
    enable: bool
    seasonality:Optional[Seasonality] = None

default_noise = NoiseConfig(enable=True, noise=RedNoise(mean=0, std=2, correlation=0.5 , random_seed=42))
default_seasonality = SeasonalityConfig(enable=True, seasonality=SinusoidalSeasonality(amplitude=3, period=timedelta(hours=6)))


def convert_to_dataframe(ts_values ,current_time:datetime , step:timedelta )-> pd.DataFrame:
    current_time = current_time.timestamp() * 1000
    metrics = pd.DataFrame(columns=["ds", "y"])
    for i, value in enumerate(ts_values):
        timestamp = int(current_time - len(ts_values) * step.total_seconds() * 1e9 + i * step.total_seconds() * 1e9)
        metrics.loc[i] = [timestamp, value]

    return metrics

def generate_timeseries(start_value: float, end_value: float, transition_start: timedelta, duration: timedelta ,noise_config:NoiseConfig=default_noise ,step:timedelta=timedelta(minutes=1),transition:LambdaTransition=None ,  seasonality_config:SeasonalityConfig=default_seasonality ):
    now = datetime.now()
    switch = None    
    if transition is None:
        switch = Switch(
                    start_time=now + transition_start,
                    base_value=start_value, 
                    switch_value=end_value,
                )
    else:
        switch = Switch(
            start_time=now + transition_start,
            base_value=start_value,
            switch_value=end_value,
            transition=transition
        )
    time_series = switch

    if seasonality_config.enable:
        time_series = time_series + seasonality_config.seasonality

    if noise_config.enable:
        time_series = time_series + noise_config.noise

    time_points = datetime_range(
        granularity=timedelta(minutes=1),
        start_time=now ,
        end_time=now + duration)
        
    ts_values = time_series.generate(time_points=time_points)

    return convert_to_dataframe(ts_values, now, step)