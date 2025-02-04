from datetime import datetime, timedelta
import os
import subprocess
import time

from pydantic import BaseModel
from features.steps.cdo_apis import get
from features.steps.env import get_endpoints, Path
from behave import *
from time_series_generator import generate_timeseries , TimeConfig , SeasonalityConfig
from mockseries.transition import LinearTransition
from features.steps.utils import GeneratedData, get_label_map 
from mockseries.seasonality.sinusoidal_seasonality import SinusoidalSeasonality
from typing import List
from jinja2 import Template

class Series(BaseModel ,arbitrary_types_allowed=True):
    labels: str
    value: List[float]
    timestamp: List[int]

class BackfillData(BaseModel ,arbitrary_types_allowed=True):
    metric_name: str
    series:List[Series]
    description : str = "Test Backfill Data"

t = Template(
"""{%- for backfill_data in backfill_data_list %}
# HELP {{backfill_data.metric_name}} {{backfill_data.description}}
# TYPE {{backfill_data.metric_name}} gauge
{% for series in backfill_data.series -%}
{{backfill_data.metric_name}}{{ "{" }}{{  series.labels }}{{ "}" }} {{ series.value[index] }} {{ series.timestamp[index] }}
{%- endfor -%}
{% endfor %}
""")

def get_index_of_metric_object(backfill_data_list:List[BackfillData] ,generated_data:GeneratedData):
    for i , backfill_data in enumerate(backfill_data_list):
        if backfill_data.metric_name == generated_data.metric_name:
            return i
    # No exisiting object found
    return -1

def convert_to_backfill_data(generated_data_list:List[GeneratedData])-> List[BackfillData]:
    backfill_data_list:List[BackfillData] = []
    for generated_data in generated_data_list:
        update_index = get_index_of_metric_object(backfill_data_list , generated_data)

        series = Series(
                labels= ",".join([f"{k}=\"{v}\"" for k, v in generated_data.labels.items()]) , 
                value=generated_data.values["y"].tolist() , 
                timestamp=generated_data.values["ds"].astype(int).tolist()
            )

        if update_index != -1:
            # update existing block
            backfill_data_list[update_index].series.append(series)
        else:
            # add a new block
            backfill_data_list.append(BackfillData(
                metric_name = generated_data.metric_name,
                series = [series],
                description = "Test Backfill Data"
            ))
    
    return backfill_data_list

def check_if_data_present(context , metric_name:str ,  duration_delta:timedelta) -> bool:
    start_time = datetime.now() - duration_delta
    end_time = datetime.now() 

    # Convert to epoch seconds
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())

    query = f"?query={metric_name}{{uuid=\"{context.scenario_to_device_map[context.scenario].device_record_uid}\"}}&start={start_time_epoch}&end={end_time_epoch}&step=5m"

    return start_polling(query=query , retry_count=60 , retry_frequency_seconds=60)

def start_polling(query:str , retry_count:int , retry_frequency_seconds:int)-> bool:
    endpoint = get_endpoints().PROMETHEUS_RANGE_QUERY_URL + query

    count = 0
    success = False
    while True:
        # Exit after 60 minutes
        if count > retry_count:
            print("Data not ingested in Prometheus. Exiting.")
            break

        count += 1

        # Check for data in Prometheus
        response = get(endpoint, print_body=False)
        if len(response["data"]["result"]) > 0:
            num_data_points_active_ravpn = len(response["data"]["result"][0]["values"])
            # num_data_points_inactive_ravpn = len(response["data"]["result"][1]["values"])
            print(
                f"Active data points: {num_data_points_active_ravpn}.")
            if num_data_points_active_ravpn > 3700 :
                success = True
                break

        time.sleep(retry_frequency_seconds)
        # TODO: Ingest live data till backfill data is available
    return success



@step('backfill metrics for a suitable device over {duration} hour(s)')
def step_impl(context , duration):
    if context.remote_write_config is None:
        print("Remote write config not found. Skipping backfill.")
        assert False
    
    duration_delta = timedelta(hours=int(duration))
    generated_data_list:List[BackfillData] = []
    for row in context.table:
        start_value = float(row["start_value"])
        end_value = float(row["end_value"])
        start_spike_minute = int(row["start_spike_minute"])
        spike_duration_minutes = int(row["spike_duration_minutes"])
        label_string = row["label_values"]
        seasonality_period_hours = int(row["seasonality_period_hours"])
        metric_name = row["metric_name"]

        generated_data = generate_timeseries(TimeConfig(start_value=start_value ,
                                                     end_value=end_value , 
                                                     transition_start=timedelta(minutes=start_spike_minute) , 
                                                     transition=LinearTransition(transition_window=timedelta(minutes=spike_duration_minutes)),
                                                     duration=duration_delta,  
                                                    ), seasonality_config=SeasonalityConfig(enable=True ,seasonality_list=[SinusoidalSeasonality(amplitude=3, period=timedelta(hours=seasonality_period_hours ))]))
        
        generated_data_list.append(GeneratedData(
            metric_name =metric_name,
            values = generated_data,
            labels = get_label_map(context, label_string , duration_delta)
        ))

    # At this point we can have same metrics as multiple objects 
    # we need to combine same metric name to a single object (single block)
    # each unique label tuple should have seprate entry in block
    backfill_data_list = convert_to_backfill_data(generated_data_list)
    file_text =""
    with open(os.path.join(Path.PYTHON_UTILS_ROOT, "historical_data.txt"), 'w') as file:
        for i in range(len(backfill_data_list[0].series[0].value)):
            multiline_text = t.render(backfill_data_list=backfill_data_list , index=i)
            file_text += multiline_text
        
        # remove first line
        output_lines = file_text.splitlines()
        output_lines.pop(0)   
        file_text = "\n".join(output_lines) 

        file.write(file_text)
        file.write("\n# EOF")
    

    remote_write_config = context.remote_write_config
    subprocess.run([os.path.join(Path.PYTHON_UTILS_ROOT, "backfill.sh"),
                    remote_write_config["url"].removesuffix("/api/prom/push"),
                    remote_write_config["username"], remote_write_config["password"], Path.PYTHON_UTILS_ROOT])
    
    assert check_if_data_present(context , generated_data_list[0].metric_name , duration_delta)

    
    

    