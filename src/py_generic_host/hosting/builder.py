from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

from fastapi import FastAPI

from ..di.protocols import ResourceContainer
from ..health.endpoints import build_health_router
from ..web.scope_middleware import RequestScopeMiddleware
from ..web.uvicorn_service import UvicornHostedService
from .host import Host, HostOptions
from .hosted_service import IHostedService
from .lifetime import ApplicationLifetime

TSettings = TypeVar("TSettings")


@dataclass
class HostContext[TSettings]:
    """
    Host 构建的上下文

    该对象只用于 Builder 构建阶段, 用于在配置函数之间共享:
    - settings
    - container
    - services
    - lifetime

    注意:
    HostContext 不是运行时生命周期对象。
    运行时生命周期由 ApplicationLifetime 管理
    """

    settings: TSettings | None = None
    container: ResourceContainer | None = None
    services: list[IHostedService] = field(default_factory=list)
    lifetime: ApplicationLifetime | None = None



class WebHostBuilder[TSettings]:
    """
    WebHostBuilder.

    .Net Generic Host + ASP.Net Core WebHost 的 Python实现

    Host 本身不依赖 FastAPI / Uvicron.
    Web Service的能力
    """

    def __init__(self) -> None:

        self._settings: TSettings | None = None
        self._container: ResourceContainer | None = None
        self._lifetime: ApplicationLifetime | None = None

        self._host_options: HostOptions | None = None

        self._hosted_services : list[IHostedService] = []

        self._service_configurators: list[
            Callable[[HostContext[TSettings]], None]
         ] = []

        self._middleware_configurators: list[
            Callable[[HostContext[TSettings], FastAPI], None]
        ] = []

        self._endpoint_configurators: list[
            Callable[[HostContext[TSettings], FastAPI], None]
        ] = []

        self._host = "0.0.0.0"  # noqa: S104
        self._port = 8080

        self._app_title = "py_generic_host"

        self._enable_health_checks = True
        self._enable_request_scope = True


    # ----------------------------------------------------------------
    # Fluent API
    # ----------------------------------------------------------------

    def use_settings(
            self,
            settings: TSettings,
    ) -> WebHostBuilder:
        """
        注入应用配置对象

        Builder 不负责配置读取
        """

        self._settings = settings

        service_name = getattr(
            settings,
            "service_name",
            None,
        )

        if isinstance(service_name, str) and service_name:
            self._app_title = service_name

        return self

    def use_container(
            self,
            container: ResourceContainer,
    ) -> WebHostBuilder:
        """
        注入 DI Contianer
        """

        self._container = container
        return self

    def use_lifetime(
            self,
            lifetime: ApplicationLifetime,
    ) -> WebHostBuilder:
        """"
        注入Application LifeTime

        主要用于:
        - 测试
        - 外部控制生命周期
        - 与其他运行时集成
        """

        self._lifetime = lifetime

        return self

    def use_host_options(
            self,
            options: HostOptions,
    ) -> WebHostBuilder:
        """
        注入 HostOptions

        用于:
        - 配置文件
        - 环境变量
        - 命令行参数
        - 单元测试

        但是读取的逻辑不应放到builder.py
        """

        self._host_options = options
        return self


    def use_urls(
            self,
            host: str,
            port: int,
    ) -> WebHostBuilder:
        """
        设置Web Server的监听地址和端口
        """

        self._host = host
        self._port = port

        return self

    def use_app_title(
            self,
            title: str,
    ) -> WebHostBuilder:

        self._app_title = title
        return self

    def enable_health_checks(
            self,
            enabled: bool = True,
    ) -> WebHostBuilder:

        self._enable_health_checks = enabled
        return self

    def enable_request_scope(
            self,
            enabled: bool = True,
    ) -> WebHostBuilder:

        self._enable_request_scope = enabled
        return self

    def add_hosted_service(
            self,
            svc: IHostedService,
    ) -> WebHostBuilder:
        """
        添加HostedService.

        例如:
        - BackgroundService
        - QueueConsumer
        - TimerService
        - 自定义的 IHostedService
        """

        self._hosted_services.append(svc)
        return self


    def configure_services(
            self,
            fn: Callable[[HostContext[TSettings]], None],
    ) -> WebHostBuilder:
        """
        配置服务

        和.Net Host的ConfigureServices 类似的实现,用法如下:
        builder.configure_services(
            lambda ctx: ctx.services.append(MyWorker())
        )
        """

        self._service_configurators.append(fn)

        return self


    def configure_middleware(
            self,
            fn: Callable[[HostContext[TSettings], FastAPI], None],
    ) -> WebHostBuilder:
        """
        配置 Middleware

        Middleware 配置u会在 endpoint 配置之前执行
        """
        self._middleware_configurators.append(fn)
        return self


    def configure_endpoint(
            self,
            fn: Callable[[HostContext[TSettings], FastAPI], None],
    ) -> WebHostBuilder:
        """
        配置 API endpoints / routers

        示例:

        builder.configure_endpoint(
            lambda ctx, app: app.include_router(api_router)
        )
        """

        self._endpoint_configurators.append(fn)

        return self


    def configure_web_app(
            self,
            fn: Callable[[HostContext[TSettings], FastAPI], None],
    ) -> WebHostBuilder:
        """
        完全不需要的方法,可以不用调用
        """
        return self.configure_endpoint(fn)


    # -------------------------------------------------------------------------
    # Build
    # -------------------------------------------------------------------------

    def build_app(self) -> FastAPI:
        """
        只构建FastAPI App, 不构建Host.

        适合:
        - 路由单元测试
        - OpenAPI 测试
        - 不启动 Uvicorn的Web 测试
        """

        ctx = self._create_build_context()
        self._run_service_configurators(ctx)

        return self._build_fastapi_app(ctx)


    def build(self) -> Host:
        """
        构建完整的Host。

        build() 不修改builder的内部状态
        可以多次调用build(), 不用担心重复添加服务.
        """

        ctx = self._create_build_context()

        self._run_service_configurators(ctx)

        app = self._build_fastapi_app(ctx)

        services = list(ctx.services)

        services.append(
            UvicornHostedService(
                app=app,
                host=self._host,
                port=self._port,
            )
        )

        lifetime = (
            ctx.lifetime
            if ctx.lifetime is not None
            else ApplicationLifetime()
        )

        container = self._require_container()


        return Host(
            container=container,
            services=services,
            lifetime=lifetime,
            options=self._host_options,
        )


    # --------------------------------------------------------------------------
    # 私有方法定义区域
    # --------------------------------------------------------------------------

    def _create_build_context(self) -> HostContext:
        """
        创建build 专用的上下文

        注意这里会复制services, 避免build() 修改内部状态
        """

        return HostContext(
            settings=self._settings,
            container=self._require_container(),
            services=list(self._hosted_services),
            lifetime=self._lifetime,
        )


    def _run_service_configurators(
            self,
            ctx: HostContext[TSettings],
    ) -> None:
        for fn in self._service_configurators:
            fn(ctx)

    def _build_fastapi_app(
            self,
            ctx: HostContext[TSettings],
    ) -> FastAPI:

        container = self._require_container()

        app = FastAPI(
            title=self._app_title,
        )

        if self._enable_request_scope:
            app.add_middleware(
                RequestScopeMiddleware,
                container,
            )

        for fn in self._middleware_configurators:
            fn(ctx, app)

        if self._enable_health_checks:
            app.include_router(
                build_health_router(container),
            )

        for fn in self._endpoint_configurators:
            fn(ctx, app)

        return app


    def _require_container(self) -> ResourceContainer:
        """
        获取必要的容器
        """

        if self._container is None:
            raise ValueError(
                "Container is required."
                "Please call use_container(container) before build()."
            )

        return self._container
