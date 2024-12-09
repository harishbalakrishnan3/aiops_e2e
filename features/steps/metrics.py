import os
import time
from datetime import datetime

from behave import *
from opentelemetry import metrics
from opentelemetry.exporter.prometheus_remote_write import PrometheusRemoteWriteMetricsExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import InMemoryMetricReader, MetricExportResult
from opentelemetry.sdk.resources import Resource

from features.steps.env import get_endpoints

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


def remote_write(context, metric_name: str, labels: dict[str, str], value: float):
    if metric_name not in active_metrics:
        create_gauge(metric_name, "Gauge metric")

    if "tenant_uuid" not in labels:
        labels["tenant_uuid"] = context.tenant_id

    if "uuid" not in labels:
        labels["uuid"] = context.device_id

    active_metrics[metric_name].set(float(value), labels)

    exporter = PrometheusRemoteWriteMetricsExporter(
        endpoint=get_endpoints().DATA_INGEST_URL,
        headers={"Authorization": "Bearer " + os.getenv('CDO_TOKEN')},
    )

    metrics_data = memory_reader.get_metrics_data()
    result = exporter.export(metrics_data)
    if result == MetricExportResult.FAILURE:
        print(f"Failed to export metric {metric_name} with labels {labels} and value {value}")
    else:
        print(
            f"Exported metric {metric_name} with labels {labels} and value {value} at {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")


@step('ingest the following metrics for {duration} minutes')
def step_impl(context, duration):
    for i in range(int(duration)):
        for row in context.table:
            labels = {}
            increment_params = {}
            if row['labels'] != '':
                labels = convert_str_list_to_dict(row['labels'])
            if row['increment_params'] != '':
                increment_params = convert_str_list_to_dict(row['increment_params'])
            current_value = calculate_current_value(float(row['start_value']), row['increment_type'],
                                                    increment_params, i)
            remote_write(context, row['metric_name'], labels, current_value)
        time.sleep(60)


def convert_str_list_to_dict(s):
    return dict(map(lambda x: (x.split('=')[0].strip(), x.split('=')[1].strip()), s.split(',')))


def calculate_current_value(start_value: float, increment_type: str, increment_params: dict[str, str],
                            current_time: int):
    if increment_type == 'linear':
        return start_value + float(increment_params['slope']) * float(current_time)
    if increment_type == 'none':
        return start_value

    raise Exception(f"Unknown increment type {increment_type}")
