from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from prometheus_client import start_http_server


def configure_metrics(
        service_name: str,
        env: str,
        otlp_endpoint: str,
        prom_port: int | None = 9464,
) -> None:

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": env
        }
    )

    readers = [
        PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True),
            export_interval_millis=15000,
        )
    ]

    if prom_port:
        readers.append(PrometheusMetricReader()) # type: ignore
        start_http_server(prom_port)

    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))

