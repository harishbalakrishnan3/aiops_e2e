import time
from typing import Any, Dict
from datetime import timedelta
from behave import *
from opentelemetry import metrics
from cdo_apis import remote_write
from features.steps.utils import get_label_map , convert_str_list_to_dict
from opentelemetry.sdk.metrics._internal.point import ResourceMetrics , ScopeMetrics,Metric,Gauge, NumberDataPoint
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.sdk.metrics.export import MetricsData
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource

memory_reader = InMemoryMetricReader()
meter_provider = MeterProvider(
    metric_readers=[memory_reader], resource=Resource.get_empty()
)
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)


def create_gauge(name: str, description: str):
    gauge = meter.create_gauge(
        name=name,
        description=description,
    )
    print(f"Created gauge {name} with description {description}")
    active_metrics[name] = gauge


# Global registry of active metrics
active_metrics = {}


def batch_remote_write(synthesized_ts: Dict[str, Any], step: timedelta):
    values = synthesized_ts["values"]
    labels = synthesized_ts["labels"]

    data_points = []
    for i, value in enumerate(values):
        timestamp = int(time.time_ns() - len(values) * step.total_seconds() * 1e9 + i * step.total_seconds() * 1e9)
        data_points.append(NumberDataPoint(
            time_unix_nano=timestamp,
            start_time_unix_nano=timestamp,
            value=value,
            attributes=labels,
        ))

    resource_metric = ResourceMetrics(
        resource=Resource.get_empty(),
        schema_url="",
        scope_metrics=[
            ScopeMetrics(
                scope=InstrumentationScope(name="sample_scope"),
                metrics=[
                    Metric(
                        name=synthesized_ts["metric_name"],
                        description="",
                        data=Gauge(data_points=data_points),
                        unit="",
                    ),
                ],
                schema_url="",
            )
        ]
    )

    metrics_data_now = MetricsData(
        resource_metrics=[resource_metric]
    )

    remote_write(metrics_data=metrics_data_now)

def instant_remote_write(metric_name: str, labels: dict[str, str], value: float):
    if metric_name not in active_metrics:
        create_gauge(metric_name, "Gauge metric")

    active_metrics[metric_name].set(float(value), labels)

    metrics_data = memory_reader.get_metrics_data()
    try:
        remote_write(metrics_data=metrics_data)
    except Exception as e:
        print(f"Failed to export metric {metric_name} with labels {labels} and value {value}")
    print(f"Exported metric {metric_name} with labels {labels} and value {value} succesfully")


@step('ingest the following metrics for {duration} minutes')
def step_impl(context, duration):
    for i in range(int(duration)):
        for row in context.table:
            labels = {}
            increment_params = {}
            if row['labels'] != '':
                labels = get_label_map(context , row['labels'])
            if row['increment_params'] != '':
                increment_params = convert_str_list_to_dict(row['increment_params'])
            current_value = calculate_current_value(float(row['start_value']), row['increment_type'],
                                                    increment_params, i)
            instant_remote_write(row['metric_name'], labels, current_value)
        time.sleep(60)

def calculate_current_value(start_value: float, increment_type: str, increment_params: dict[str, str],
                            current_time: int):
    if increment_type == 'linear':
        return start_value + float(increment_params['slope']) * float(current_time)
    if increment_type == 'none':
        return start_value

    raise Exception(f"Unknown increment type {increment_type}")
