import json
import os
import subprocess
import time
from typing import List
import logging

from behave import *
from hamcrest import assert_that
from jinja2 import Template

from features.steps.utils import (
    check_if_data_present,
    convert_to_backfill_data,
)
from model import ScenarioEnum
from features.steps.env import Path, get_endpoints
from features.steps.metrics import batch_remote_write
from features.steps.cdo_apis import (
    delete_all_insights,
    delete_insight_by_uid,
    post,
    verify_insight_type_and_state,
    get_insights,
)
from datetime import timedelta, datetime, timezone
from features.steps.metrics import instant_remote_write
from features.steps.utils import (
    generate_synthesized_ts_obj,
    split_data_for_batch_and_live_ingestion,
    GeneratedData,
    get_label_map,
    write_timeseries_yaml,
)
from time_series_generator import (
    generate_timeseries,
    NoiseConfig,
    TimeConfig,
    SeasonalityConfig,
    SeriesConfig,
    TransitionConfig,
)


@step("the insights are cleared")
def step_impl(context):
    delete_all_insights()


@step("the insights created in this scenario are cleared")
def step_impl(context):
    """Delete only the insights that were created during the current scenario"""
    if hasattr(context, "scenario_insights") and context.scenario_insights:
        logging.info(
            f"Cleaning up {len(context.scenario_insights)} insight(s) created during this scenario"
        )
        for insight_uid in context.scenario_insights:
            try:
                delete_insight_by_uid(insight_uid)
                logging.info(f"Successfully deleted insight: {insight_uid}")
            except Exception as e:
                logging.warning(f"Failed to delete insight {insight_uid}: {e}")
        # Clear the list after cleanup
        context.scenario_insights = []
    else:
        logging.info("No insights to clean up in this scenario")


@step("verify if an {insight_type} insight with state {insight_state} is created")
def step_impl(context, insight_type, insight_state):
    verification_status = verify_insight_type_and_state(
        context, insight_type, insight_state
    )
    if not verification_status:
        logging.error(
            f"Failed to verify insight of type {insight_type} and state {insight_state}"
        )
    assert_that(verification_status)


@step(
    "verify if an {insight_type} insight with state {insight_state} is created with a timeout of {timeout} minute(s)"
)
def step_impl(context, insight_type, insight_state, timeout):
    for i in range(int(timeout)):
        if verify_insight_type_and_state(context, insight_type, insight_state):
            assert_that(True)
            return
        time.sleep(60)
    logging.error(
        f"Failed to verify insight of type {insight_type} and state {insight_state}"
    )
    assert_that(False)


@step(
    "verify if an {insight_type} insight with state {insight_state} is not created with a timeout of {timeout} minute(s)"
)
def step_impl(context, insight_type, insight_state, timeout):
    for i in range(int(timeout)):
        if verify_insight_type_and_state(context, insight_type, insight_state):
            logging.error(
                f"Found insight of type {insight_type} and state {insight_state} , when none was expected"
            )
            assert_that(False)
            return
        time.sleep(60)
    assert_that(True)


@step("verify no insight is present with a timeout of {timeout} minute(s)")
def step_impl(context, timeout):
    for i in range(int(timeout)):
        insights = get_insights(fields="insightType,impactedResources,insightState")
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
        end_value = float(row.get("end_value", 0))
        start_spike_minute = int(row["start_spike_minute"])
        spike_duration_minutes = int(row["spike_duration_minutes"])
        label_string = row["label_values"]
        metric_name = row["metric_name"]
        metric_type = (
            row["metric_type"] if "metric_type" in context.table.headings else "gauge"
        )
        noise = (
            row["noise"].lower() == "true"
            if "noise" in context.table.headings
            else None
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
            noise=noise,
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
    logging.info(
        f"Pushing {live_ingest_datapoints_count} datapoints through live ingestion "
    )
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


module_name_to_subscriber = {
    "RAVPN": {
        "subscriber": "RAVPN_MAX_SESSIONS_BREACH_FORECAST",
        "destination": "ai-ops-forecast",
    },
    "CONNECTIONS": {
        "subscriber": "CONNECTIONS_ANOMALY",
        "destination": "ai-ops-anomaly-detection",
    },
    "THROUGHPUT": {
        "subscriber": "THROUGHPUT_ANOMALY",
        "destination": "ai-ops-anomaly-detection",
    },
}


@step("trigger the {module_name} forecasting workflow through {method}")
def step_impl(context, module_name, method):
    if method == "SNS":
        payload = {
            "subscriber": module_name_to_subscriber[module_name]["subscriber"],
            "trigger-type": "SCHEDULE_TICKS",
            "config": {"periodicity": "INTERVAL_24_HOURS"},
            "pipeline": {
                "output": [
                    {
                        "plugin": "SNS",
                        "config": {
                            "destination": module_name_to_subscriber[module_name][
                                "destination"
                            ]
                        },
                    }
                ],
                "processor": [],
            },
            "deviceIds": ["886db434-b93a-11ef-be41-f1b0f896e566"],
            "timestamp": "2024-08-21T05:55:00.000",
            "attributes": {},
        }
        post(get_endpoints().TRIGGER_MANAGER_URL, json.dumps(payload))
    else:
        payload = {
            "moduleName": module_name_to_subscriber[module_name]["subscriber"],
        }
        post(
            get_endpoints().AI_OPS_ANOMALY_DETECTION_FORECAST_TRIGGER_URL,
            json.dumps(payload),
            expected_return_code=201,
        )


@step(
    "prepare backfill metrics for {scenario} for a suitable device over {duration} hour(s)"
)
def step_impl(context, scenario, duration):
    context.scenario = ScenarioEnum[scenario]
    generated_data_list = generate_data_for_input(
        context, timedelta(hours=int(duration))
    )
    context.generated_data_list.extend(generated_data_list)


# TODO: Check if this step is required
@step("start backfill")
def step_impl(context):
    backfill_generated_data(context, context.generated_data_list)
    assert check_if_backfilled_data_present(context.generated_data_list)


@step("backfill metrics for a suitable device over {duration} hour(s)")
def step_impl(context, duration):
    duration_delta = timedelta(hours=int(duration))
    generated_data_list = generate_data_for_input(context, duration_delta)
    backfill_generated_data(context, generated_data_list)
    assert check_if_backfilled_data_present(generated_data_list)


def check_if_backfilled_data_present(generated_data_list: List[GeneratedData]):
    for generated_data in generated_data_list:
        start = generated_data.values["ds"].iloc[0]
        end = generated_data.values["ds"].iloc[-1]
        duration_hours = (end - start) / 3600

        if not check_if_data_present(
            generated_data.metric_name,
            timedelta(hours=duration_hours),
            generated_data.labels,
        ):
            return False
    return True


def backfill_generated_data(context, generated_data_list: List[GeneratedData]):
    historical_data_file = "{}_historical_data.txt".format(context.scenario)
    data_block_directory = "/{}_data/".format(context.scenario)

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


def generate_data_for_input(context, duration_delta: timedelta) -> List[GeneratedData]:
    if context.remote_write_config is None:
        logging.info("Remote write config not found. Skipping backfill.")
        assert False

    generated_data_list: List[GeneratedData] = []
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
        amplitude = (
            int(row["amplitude"]) if "amplitude" in context.table.headings else 20
        )

        start_time = datetime.now(timezone.utc) - duration_delta
        generated_data = generate_timeseries(
            time_config=TimeConfig(
                series_config=SeriesConfig(
                    start_value=start_value,
                    end_value=end_value,
                    start_time=start_time,
                    duration=duration_delta,
                ),
                transition_config=TransitionConfig(
                    start_time=start_time + timedelta(minutes=start_spike_minute),
                    transition_window=timedelta(minutes=spike_duration_minutes),
                ),
            ),
            seasonality_config=SeasonalityConfig(
                enable=True,
                amplitude=amplitude,
                period=timedelta(hours=seasonality_period_hours),
            ),
            noise_config=NoiseConfig(enable=False),
        )

        if metric_type == "counter":
            generated_data["y"] = generated_data["y"].cumsum()

        label_map = get_label_map(context, label_string, duration_delta)

        write_timeseries_yaml(
            context=context,
            metric_name=metric_name,
            labels=label_map,
            generated_data=generated_data,
            ts_features={
                "seasonality": {
                    "enabled": True,
                    "amplitude": amplitude,
                    "period_hours": seasonality_period_hours,
                },
                "trend": f"{start_value} -> {end_value} over {spike_duration_minutes}m (start at {start_spike_minute}m)",
                "noise": False,
            },
        )

        generated_data_list.append(
            GeneratedData(
                metric_name=metric_name,
                values=generated_data,
                labels=label_map,
            )
        )
    return generated_data_list
