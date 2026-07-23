from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased


def configure_tracking(
        service_name: str,
        env: str,
        otlp_endpoint: str,
        ratio: float = 1.0,
) -> None:
    resource = Resource.create(
        {
            "service.name": service_name,
            "service_namespace": "py_generic_host",
            "deployment.environment": env
        }
    )

    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(ratio))
    )

    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True
            )
        )
    )

    trace.set_tracer_provider(provider)
