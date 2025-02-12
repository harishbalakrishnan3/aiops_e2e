import os
import subprocess
import time
from typing import List

from behave import *
from hamcrest import assert_that
from jinja2 import Template
from features.steps.utils import (
    BackfillData,
    check_if_data_present,
    convert_to_backfill_data,
)
from features.steps.env import Path
from features.steps.metrics import batch_remote_write
from features.steps.cdo_apis import (
    delete_insights,
    verify_insight_type_and_state,
    get_insights,
)
from datetime import timedelta
from features.steps.metrics import instant_remote_write
from features.steps.utils import (
    generate_synthesized_ts_obj,
    split_data_for_batch_and_live_ingestion,
    GeneratedData,
    get_label_map,
)
from time_series_generator import generate_timeseries, TimeConfig, SeasonalityConfig
from mockseries.transition import LinearTransition
from mockseries.seasonality.sinusoidal_seasonality import SinusoidalSeasonality


@step("the insights are cleared")
def step_impl(context):
    delete_insights()


@step("verify if an {insight_type} insight with state {insight_state} is created")
def step_impl(context, insight_type, insight_state):
    assert_that(verify_insight_type_and_state(context, insight_type, insight_state))


@step(
    "verify if an {insight_type} insight with state {insight_state} is created with a timeout of {timeout} minute(s)"
)
def step_impl(context, insight_type, insight_state, timeout):
    for i in range(int(timeout)):
        if verify_insight_type_and_state(context, insight_type, insight_state):
            assert_that(True)
            return
        time.sleep(60)
    assert_that(False)


@step("verify no insight is present with a timeout of {timeout} minute(s)")
def step_impl(context, timeout):
    for i in range(int(timeout)):
        insights = get_insights()
        if insights["count"] == 0:
            assert_that(True)
            return
        time.sleep(60)
    assert_that(False)


@step("wait for {duration} {unit}")
def step_impl(context, duration, unit):
    if unit == "seconds" or unit == "second":
        time.sleep(int(duration))
    elif unit == "minutes" or unit == "minute":
        time.sleep(int(duration) * 60)
    else:
        raise Exception(f"Unsupported unit: {unit}")


@then(
    "push timeseries for {duration} minute(s) of which send last {live_duration} minute(s) of timeseries in live mode"
)
def step_impl(context, duration, live_duration):
    synthesized_ts_list = []
    duration = int(duration)
    live_duration = int(live_duration)
    for row in context.table:
        start_value = float(row["start_value"])
        end_value = float(row["end_value"])
        start_spike_minute = int(row["start_spike_minute"])
        spike_duration_minutes = int(row["spike_duration_minutes"])
        label_string = row["label_values"]
        metric_name = row["metric_name"]
        metric_type = (
            row["metric_type"] if "metric_type" in context.table.headings else "gauge"
        )
        synthesized_ts_obj = generate_synthesized_ts_obj(
            context=context,
            metric_name=metric_name,
            label_string=label_string,
            start_value=start_value,
            end_value=end_value,
            start_spike_minute=start_spike_minute,
            spike_duration_minutes=spike_duration_minutes,
            time_offset=timedelta(minutes=live_duration),
            duration=duration,
            metric_type=metric_type,
        )
        synthesized_ts_list.append(synthesized_ts_obj)

    [
        synthesized_ts_list_for_batch_fill,
        synthesized_ts_list_for_live_fill,
    ] = split_data_for_batch_and_live_ingestion(synthesized_ts_list, live_duration)
    # batch data fill
    for synthesized_data in synthesized_ts_list_for_batch_fill:
        batch_remote_write(synthesized_data, timedelta(minutes=1))

    # Live data generation
    live_ingest_datapoints_count = len(synthesized_ts_list_for_live_fill[0].values)
    print(f"Pushing {live_ingest_datapoints_count} datapoints through live ingestion ")
    for i in range(live_ingest_datapoints_count):
        data_for_current_instant = []
        for value_dict in synthesized_ts_list_for_live_fill:
            data_for_current_instant.append(
                {
                    "metric_name": value_dict.metric_name,
                    "value": value_dict.values.iloc[i]["y"],
                    "labels": value_dict.labels,
                }
            )

        for data in data_for_current_instant:
            instant_remote_write(data["metric_name"], data["labels"], data["value"])
        time.sleep(60)


t = Template(
    """{%- for backfill_data in backfill_data_list %}
# HELP {{backfill_data.metric_name}} {{backfill_data.description}}
# TYPE {{backfill_data.metric_name}} gauge
{% for series in backfill_data.series %}
{{backfill_data.metric_name}}{{ "{" }}{{  series.labels }}{{ "}" }} {{ series.value[index] }} {{ series.timestamp[index] }}
{%- endfor -%}
{% endfor %}
"""
)


@step("backfill metrics for a suitable device over {duration} hour(s)")
def step_impl(context, duration):
    if context.remote_write_config is None:
        print("Remote write config not found. Skipping backfill.")
        assert False

    historical_data_file = "{}_historical_data.txt".format(context.scenario)
    data_block_directory = "/{}_data/".format(context.scenario)

    duration_delta = timedelta(hours=int(duration))
    generated_data_list: List[BackfillData] = []
    for row in context.table:
        start_value = float(row["start_value"])
        end_value = float(row["end_value"])
        start_spike_minute = int(row["start_spike_minute"])
        spike_duration_minutes = int(row["spike_duration_minutes"])
        label_string = row["label_values"]
        seasonality_period_hours = int(row["seasonality_period_hours"])
        metric_name = row["metric_name"]
        metric_type = (
            row["metric_type"] if "metric_type" in context.table.headings else "gauge"
        )

        generated_data = generate_timeseries(
            TimeConfig(
                start_value=start_value,
                end_value=end_value,
                transition_start=timedelta(minutes=start_spike_minute),
                transition=LinearTransition(
                    transition_window=timedelta(minutes=spike_duration_minutes)
                ),
                duration=duration_delta,
            ),
            seasonality_config=SeasonalityConfig(
                enable=True,
                seasonality_list=[
                    SinusoidalSeasonality(
                        amplitude=8000, period=timedelta(hours=seasonality_period_hours)
                    )
                ],
            ),
        )

        if metric_type == "counter":
            generated_data["y"] = generated_data["y"].cumsum()

        generated_data_list.append(
            GeneratedData(
                metric_name=metric_name,
                values=generated_data,
                labels=get_label_map(context, label_string, duration_delta),
            )
        )

    # At this point we can have same metrics as multiple objects
    # we need to combine same metric name to a single object (single block)
    # each unique label tuple should have seprate entry in block
    backfill_data_list = convert_to_backfill_data(generated_data_list)
    file_text = ""
    with open(os.path.join(Path.PYTHON_UTILS_ROOT, historical_data_file), "w") as file:
        for i in range(len(backfill_data_list[0].series[0].value)):
            multiline_text = t.render(backfill_data_list=backfill_data_list, index=i)
            file_text += multiline_text

        # remove all empty lines
        output_lines = [line for line in file_text.splitlines() if line.strip()]
        file_text = "\n".join(output_lines)

        file.write(file_text)
        file.write("\n# EOF")

    remote_write_config = context.remote_write_config
    subprocess.run(
        [
            os.path.join(Path.PYTHON_UTILS_ROOT, "backfill.sh"),
            remote_write_config["url"].removesuffix("/api/prom/push"),
            remote_write_config["username"],
            remote_write_config["password"],
            Path.PYTHON_UTILS_ROOT,
            data_block_directory,
            historical_data_file,
        ],
    )

    assert check_if_data_present(
        context, generated_data_list[0].metric_name, duration_delta
    )
