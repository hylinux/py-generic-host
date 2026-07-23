from __future__ import annotations

import logging
import sys

import structlog
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource


def _add_trace_context(_, __, event_dict):
    span = trace.get_current_span()
    ctx = span.get_span_context() if span else None
    if ctx and ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict

def _redact_secrets(_, __, event_dict):
    for k in list(event_dict.keys()):
        if any(s in k.lower() for s in ("password", "secret", "token", "apikey", "api_key") ):
            event_dict[k] = "***REDACTED***"
    return event_dict

def configure_logging(
        service_name: str,
        env: str,
        otlp_endpoint: str | None = None,
        level: str = "INFO",
) -> None:
    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _add_trace_context,
        _redact_secrets,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=pre_chain,
        processor=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ], # type: ignore
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(stream_handler)

    if otlp_endpoint:
        resource = Resource.create(
            {"service.name": service_name, "deployment.environment": env}
        )

        provider = LoggerProvider(resource=resource)
        provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=otlp_endpoint, insecure=True))
        )

        set_logger_provider(provider)
        otel_handler = LoggingHandler(level=getattr(logging, level), logger_provider=provider)
        root.addHandler(otel_handler)

    root.setLevel(level=level)

    structlog.configure(
        processors=[*pre_chain, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )