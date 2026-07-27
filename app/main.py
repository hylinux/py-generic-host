from __future__ import annotations

import asyncio

import structlog
from fastapi import FastAPI

from app.api import register_routes
from app.container import AppContainer
from py_generic_host.hosting.builder import HostContext, WebHostBuilder
from py_generic_host.logging_.setup import configure_logging
from py_generic_host.telemetry.instrumentation import auto_instrument
from py_generic_host.telemetry.metrics import configure_metrics
from py_generic_host.telemetry.tracing import configure_tracking


def _configure_app(ctx: HostContext, app: FastAPI) -> None:
    auto_instrument(app)
    register_routes(app)


async def amain() -> None:

    container = AppContainer()
    settings = container.settings()

    # 可观测性必须最早初始化
    configure_logging(
        settings.otel.service_name,
        settings.env,
        settings.otel.otlp_endpoint,
        settings.log_level,
    )

    configure_tracking(
        settings.otel.service_name,
        settings.env,
        settings.otel.otlp_endpoint,
        settings.otel.sample_ratio,
    )

    configure_metrics(
        settings.otel.service_name,
        settings.env,
        settings.otel.otlp_endpoint,
        prom_port=9464,
    )


    log = structlog.get_logger("Bootstrap")
    log.info("bootstrap.start", env=settings.env)

    host = (
        WebHostBuilder()
        .use_settings(settings)
        .use_container(container)
        .use_urls(settings.http_host, settings.http_port)
        .configure_web_app(_configure_app)
        .build()
    )

    container.wire(modules=["app.api.users", "app.api.items"])
    await host.run_async()


def run() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    run()
