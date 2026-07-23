import httpx
from dependency_injector import containers, providers

from py_generic_host.config.monitor import OptionsMonitor
from py_generic_host.health.builtin import LivenessCheck
from py_generic_host.health.service import HealthCheckService

from .services.external_api import ExternalApiClient
from .services.health_checks import ExternalApiHealthCheck
from .services.user_service import UserService
from .settings import AppSettings, ExternalApiSettings


async def _http_client_resource(timeout: float):  # noqa: ASYNC109
    async with httpx.AsyncClient(timeout=timeout) as client:
        yield client


class AppContainer(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(
        modules=["app.api.users",
                 "app.api.items",
                 ]
    )

    settings = providers.Singleton(AppSettings)

    external_options = providers.Singleton(
        OptionsMonitor[ExternalApiSettings],
        factory = lambda: AppSettings().external,
    )

    # Resource = 请求级作用域 + 自动 dispose
    http_client = providers.Resource(_http_client_resource, timeout=5.0)

    external_api = providers.Factory(
        ExternalApiClient,
        client = http_client,
        options = external_options,
    )

    user_service = providers.Factory(UserService, api=external_api)

    # Health check
    liveness_check = providers.Singleton(LivenessCheck)
    external_check = providers.Singleton(ExternalApiHealthCheck, api=external_api)

    health_service = providers.Singleton(
        HealthCheckService,
        checks = providers.List(liveness_check, external_check),
    )


