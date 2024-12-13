import time

from behave import *
from hamcrest import assert_that
from features.steps.metrics import batch_remote_write
from features.steps.cdo_apis import delete_insights, verify_insight_type_and_state
from datetime import timedelta
from features.steps.metrics import instant_remote_write
from features.steps.utils import generate_synthesized_ts_obj, split_data_for_batch_and_live_ingestion


@step('the insights are cleared')
def step_impl(context):
    delete_insights()


@step('verify if an {insight_type} insight with state {insight_state} is created')
def step_impl(context, insight_type, insight_state):
    assert_that(verify_insight_type_and_state(context, insight_type, insight_state))


@step('verify if an {insight_type} insight with state {insight_state} is created with a timeout of {timeout} minute(s)')
def step_impl(context, insight_type, insight_state, timeout):
    for i in range(int(timeout)):
        if verify_insight_type_and_state(context, insight_type, insight_state):
            assert_that(True)
            return
        time.sleep(60)
    assert_that(False)


@step('wait for {duration} {unit}')
def step_impl(context, duration, unit):
    if unit == "seconds" or unit == "second":
        time.sleep(int(duration))
    elif unit == "minutes" or unit == "minute":
        time.sleep(int(duration) * 60)
    else:
        raise Exception(f"Unsupported unit: {unit}")


@then(
    'push timeseries for {duration} minute(s) of which send last {live_duration} minute(s) of timeseries in live mode')
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

        synthesized_ts_obj = generate_synthesized_ts_obj(context=context,
                                                         metric_name=metric_name,
                                                         label_string=label_string,
                                                         start_value=start_value,
                                                         end_value=end_value,
                                                         start_spike_minute=start_spike_minute,
                                                         spike_duration_minutes=spike_duration_minutes,
                                                         duration=duration)
        synthesized_ts_list.append(synthesized_ts_obj)

    [synthesized_ts_list_for_batch_fill, synthesized_ts_list_for_live_fill] = split_data_for_batch_and_live_ingestion(
        synthesized_ts_list, live_duration)
    # batch data fill
    for synthesized_data in synthesized_ts_list_for_batch_fill:
        batch_remote_write(synthesized_data, timedelta(minutes=1))

    # Live data generation
    live_ingest_datapoints_count = len(synthesized_ts_list_for_live_fill[0]["values"])
    print(f"Pushing {live_ingest_datapoints_count} datapoints through live ingestion ")
    for i in range(live_ingest_datapoints_count):
        data_for_current_instant = []
        for value_dict in synthesized_ts_list_for_live_fill:
            data_for_current_instant.append({
                "metric_name": value_dict["metric_name"],
                "value": value_dict["values"][i],
                "labels": value_dict["labels"]
            })

        for data in data_for_current_instant:
            instant_remote_write(data["metric_name"], data["labels"], data["value"])
        time.sleep(60)
