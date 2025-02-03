from datetime import timedelta , datetime
import pandas as pd 

from mockseries.noise import RedNoise
from mockseries.trend import  Switch
from mockseries.transition.lambda_transition import LambdaTransition
from mockseries.seasonality.seasonality import Seasonality
from mockseries.seasonality.sinusoidal_seasonality import SinusoidalSeasonality
from mockseries.utils import datetime_range
from mockseries.noise.noise import Noise
from typing import List , Optional

from pydantic import BaseModel

class TimeConfig(BaseModel,arbitrary_types_allowed=True):
    start_value : float
    end_value : float
    transition_start : timedelta
    transition:Optional[LambdaTransition]=None
    duration : timedelta
    step:timedelta = timedelta(minutes=1)

class NoiseConfig(BaseModel,arbitrary_types_allowed=True):
    enable: bool
    noise_list: List[Noise] = []

class SeasonalityConfig(BaseModel, arbitrary_types_allowed=True):
    enable: bool
    seasonality_list: List[Seasonality] = []

default_noise = NoiseConfig(enable=True, noise_list=[RedNoise(mean=0, std=2, correlation=0.5 , random_seed=42)])
default_seasonality = SeasonalityConfig(enable=True, seasonality_list=[SinusoidalSeasonality(amplitude=3, period=timedelta(hours=6))])


def convert_to_dataframe(ts_values , time_points:List[datetime] )-> pd.DataFrame:
    metrics = pd.DataFrame(columns=["ds", "y"])
    for i, value in enumerate(time_points):
        metrics.loc[i] = [value.timestamp() , ts_values[i]]

    return metrics

def generate_timeseries(time_config : TimeConfig ,noise_config:NoiseConfig=default_noise ,  seasonality_config:SeasonalityConfig=default_seasonality ):
    now = datetime.now()
    switch = None    
    if time_config.transition is None:
        switch = Switch(
                    start_time=now - time_config.duration + time_config.transition_start,
                    base_value=time_config.start_value, 
                    switch_value=time_config.end_value,
                )
    else:
        switch = Switch(
            start_time=now - time_config.duration + time_config.transition_start,
            base_value=time_config.start_value,
            switch_value=time_config.end_value,
            transition=time_config.transition
        )
    time_series = switch

    if seasonality_config.enable:
        for seasonality in seasonality_config.seasonality_list:
            time_series = time_series + seasonality

    if noise_config.enable:
        for noise in noise_config.noise_list:
            time_series = time_series + noise

    time_points = datetime_range(
        granularity=time_config.step,
        start_time= now - time_config.duration ,
        end_time=now)
        
    ts_values = time_series.generate(time_points=time_points)
    return convert_to_dataframe(ts_values, time_points)