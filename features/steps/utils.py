import copy
from datetime import timedelta

from mockseries.noise import GaussianNoise
from mockseries.seasonality import DailySeasonality
from mockseries.trend import LinearTrend
import time

from features.steps.env import Path
from opentelemetry.exporter.prometheus_remote_write import (
    PrometheusRemoteWriteMetricsExporter,
)
from opentelemetry.sdk.metrics._internal.point import ResourceMetrics, ScopeMetrics, Metric, Gauge, \
    NumberDataPoint
from opentelemetry.sdk.metrics.export import MetricsData, MetricExportResult
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


def store_ts_in_context(context, labels, key, metric_name):
    ts = copy.deepcopy(labels)
    if metric_name not in context.timeseries.keys():
        context.timeseries[metric_name] = {}
    context.timeseries[metric_name][key] = ts
    print(f"Timeseries in context: {context.timeseries}")

def get_label_map(context, label_string: str):
    label_map = convert_str_list_to_dict(label_string)
    if "tenant_uuid" not in label_map and context.tenant_id is None:
        raise Exception("Tenant ID not found in context")
    if "uuid" not in label_map and context.device_id is None:
        raise Exception("Device ID not found in context")
    return label_map | {
        "tenant_uuid": context.tenant_id,
        "uuid": context.device_id
    }

def convert_str_list_to_dict(s):
    return dict(map(lambda x: (x.split('=')[0].strip(), x.split('=')[1].strip()), s.split(',')))


def generate_ts(trend_config, seasonality_config, noise_config, time_points):
    trend = LinearTrend(coefficient=trend_config['coefficient'], time_unit=timedelta(hours=trend_config['time_unit']),
                        flat_base=trend_config['flat_base'])
    seasonality = DailySeasonality(seasonality_config)
    noise = GaussianNoise(mean=noise_config['mean'], std=noise_config['std'])
    timeseries = trend + seasonality + noise
    ts_values = timeseries.generate(time_points=time_points)
    return ts_values


def batch_remote_write(synthesized_ts: Dict[str, Any], step: timedelta):
    url = "https://edge.staging.cdo.cisco.com/api/platform/ai-ops-data-ingest/v1/healthmetrics"
    exporter = PrometheusRemoteWriteMetricsExporter(
        endpoint=url,
        headers={"Authorization": "Bearer " + os.getenv('CDO_TOKEN')},
    )
    values = synthesized_ts["values"]
    labels = synthesized_ts["labels"]

    data_points = []
    current_time = time.time_ns()
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
        schema_url=url,
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
                schema_url=url,
            )
        ]
    )

    metrics_data_now = MetricsData(
        resource_metrics=[resource_metric]
    )

    if MetricExportResult.SUCCESS == exporter.export(metrics_data_now):
        print(f"Metric data remote written in batch succesfully upto time: {current_time}")
