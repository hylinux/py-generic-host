from __future__ import annotations

import httpx
from dependency_injector import containers, providers

from py_generic_host.health.builtin import (
    LivenessCheck,
)
from py_generic_host.health.service import (
    HealthCheckService,
)

from .services.external_api import (
    ExternalApiClient,
)
from .services.health_checks import (
    ExternalApiHealthCheck,
)
from .services.user_service import (
    UserService,
)
from .settings import (
    AppSettings,
)


async def _http_client_resource(
    timeout: float,  # noqa: ASYNC109
):
    async with httpx.AsyncClient(
        timeout=timeout,
    ) as client:
        yield client


class AppContainer(
    containers.DeclarativeContainer,
):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.api.users",
            "app.api.items",
        ],
    )

    # =====================================================
    # Settings
    # =====================================================

    settings = providers.Singleton(
        AppSettings,
    )

    external_settings = providers.Singleton(
        lambda settings: settings.external,
        settings,
    )

    otel_settings = providers.Singleton(
        lambda settings: settings.otel,
        settings,
    )

    # =====================================================
    # Resources
    # =====================================================

    http_client = providers.Resource(
        _http_client_resource,
        timeout=providers.Callable(
            lambda opts: opts.timeout,
            external_settings,
        ),
    )

    # =====================================================
    # External Services
    # =====================================================

    external_api = providers.Factory(
        ExternalApiClient,
        client=http_client,
        settings=external_settings,
    )

    # =====================================================
    # Business Services
    # =====================================================

    user_service = providers.Factory(
        UserService,
        api=external_api,
    )

    # =====================================================
    # Health Checks
    # =====================================================

    liveness_check = providers.Singleton(
        LivenessCheck,
    )

    external_check = providers.Singleton(
        ExternalApiHealthCheck,
        api=external_api,
    )

    health_service = providers.Singleton(
        HealthCheckService,
        checks=providers.List(
            liveness_check,
            external_check,
        ),
    )
