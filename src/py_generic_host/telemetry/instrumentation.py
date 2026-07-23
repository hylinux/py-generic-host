from fastapi import FastAPI


def auto_instrument(app: FastAPI) -> None:

    from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="healthz/live,healthz/ready,healthz/startup,metrics"
    )

    HTTPXClientInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=False)
    AsyncioInstrumentor().instrument()
    SystemMetricsInstrumentor().instrument()
