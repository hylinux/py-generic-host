from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import FastAPI

from ..health.endpoints import build_health_router
from ..web.scope_middleware import RequestScopeMiddleware
from ..web.uvicorn_service import UvicornHostedService
from .host import Host
from .hosted_service import IHostedService
from .lifetime import ApplicationLifetime


@dataclass
class HostContext:
    settings: object | None = None
    container: object | None = None
    services: list[IHostedService] = field(default_factory = list )


class WebHostBuilder:
    def __init__(self) -> None:
        self._ctx = HostContext()
        self._app_factories: list[Callable[[HostContext, FastAPI], None]] = []
        self._host = "0.0.0.0"  # noqa: S104
        self._port = 8080

    # -- fluent API ---
    def use_settings(self, settings) -> WebHostBuilder:
        self._ctx.settings = settings
        return self

    def use_container(self, container) -> WebHostBuilder:
        self._ctx.container = container
        return self

    def add_hosted_service(self, svc: IHostedService) -> WebHostBuilder:
        self._ctx.services.append(svc)
        return self

    def use_urls(self, host: str, port: int) -> WebHostBuilder:
        self._host, self._port = host, port
        return self

    def configure_web_app(self, fn: Callable[ [HostContext, FastAPI], None]) -> WebHostBuilder:
        self._app_factories.append(fn)
        return self


    # build
    def build(self) -> Host:
        assert self._ctx.container is not None, "Container is required"

        app = FastAPI(title=getattr(self._ctx.settings, "service_name", "py_generic_host"))
        app.add_middleware(RequestScopeMiddleware, container = self._ctx.container)
        app.include_router(build_health_router(self._ctx.container))

        for fn in self._app_factories:
            fn(self._ctx, app)


        self._ctx.services.append(UvicornHostedService(app, host=self._host, port=self._port))
        lifetime = ApplicationLifetime()

        return Host(self._ctx.container, self._ctx.services, lifetime)
