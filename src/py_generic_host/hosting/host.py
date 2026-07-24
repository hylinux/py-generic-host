from __future__ import annotations

import asyncio
import contextlib
import signal
from dataclasses import dataclass

import structlog

from ..di.protocols import ResourceContainer
from .crash_models import CrashInfo
from .hosted_service import IHostedService, SupportsCrashHandler
from .lifetime import ApplicationLifetime


@dataclass(slots=True)
class HostOptions:
    shutdown_timeout: float = 60   # 一分钟停止
    startup_timeout: float = 60    # 一分钟启动
    stop_on_background_crash: bool = True   # 设置是否背景任务失败直接停止。


class Host:

    def __init__(
            self,
            container: ResourceContainer,
            services: list[IHostedService],
            lifetime: ApplicationLifetime,
            options: HostOptions | None = None,
    ) -> None:

        if options is None:
            options = HostOptions()

        self.container = container
        self.services = services
        self.lifetime = lifetime
        self.options = options

        self._log = structlog.get_logger("Host")

        self._started = False
        self._stopping = False
        self._resource_shutdown = False


    async def run_async(self) -> None:
        """Main Host Loop

            主要的Host 启动步骤
        """

        # 注册信号处理器
        self._register_signal_handlers()

        try:
            await self.start_async()
            await self.lifetime.stopping.wait()
        finally:
            await self.stop_async()




    async def start_async(self) -> None:
        """
        正式启动Host
        """

        # 如果已经启动了
        if self._started:
            return

        self._log.info(
            "host.starting",
            services = len(self.services)
        )

        started_services: list[IHostedService] = []

        try:

            for svc in self.services:

                # 配置可能的crash 启动器
                # 这里使用Protocl, SupportsCrashHandler 解耦 BackgroundService,
                # 即只需要有set_crash_handler 即可以完成解耦。
                self._configure_crash_handler(svc)

                self._log.info(
                    "host.service.starting",
                    service = type(svc).__name__,
                )

                # 设置服务启动的超时时间
                await asyncio.wait_for(
                    svc.start(self.lifetime.stopping),
                    timeout=self.options.startup_timeout,
                )

                started_services.append(svc)

                self._log.info(
                    "host.service.started",
                    service=type(svc).__name__,
                )

        except asyncio.TimeoutError:  # noqa: UP041
            # 处理启动超时
            self._log.error(
                "host.start.timeout",
                timeout=self.options.startup_timeout,
            )

            await self._rollback_started_services(started_services)

            # 重新抛出异常
            raise

        except Exception:
            self._log.exception(
                "host.start.failed",
            )

            # 发现失败时候,要将其他的服务rollback 回来
            await self._rollback_started_services(started_services)

            # 重新抛出异常
            raise

        self._started = True

        self.lifetime.started.set()

        self._log.info("host.started")



    async def stop_async(self) -> None:
        """
        停止Host
        """

        # 预防多次调用stop
        if self._stopping:
            return

        self._stopping = True

        self._log.info("host.stopping")

        # 确保停止的信号被发布出去
        if not self.lifetime.stopping.is_set():
            self.lifetime.stop_application()

        # 停止Host的所有服务
        for svc in reversed(self.services):
            try:
                await asyncio.wait_for(
                    svc.stop(self.lifetime.stopping),
                    timeout=self.options.shutdown_timeout,
                )

                self._log.info(
                    "host.service.stopped",
                    service=type(svc).__name__,
                )
            except asyncio.TimeoutError:  # noqa: UP041
                self._log.error(
                    "host.service.stop.timeout",
                    service=type(svc).__name__,
                    timeout=self.options.shutdown_timeout,
                )
            except Exception:
                self._log.exception(
                    "host.service.stop.failed",
                    service=type(svc).__name__,
                )

        # 关闭DI 资源
        await self._shutdown_resources()

        self.lifetime.stopped.set()
        self._log.info("host.stopped")


    # 将私有方法往后面放, 从这里开始放私有方法
    # ---------------------------------------------


    def _register_signal_handlers(self) -> None:
        """
        注册信号处理器
        """
        # 获取默认的运行loop
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM ):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, self._on_signal)


    def _on_signal(self) -> None:
        """
        接收到信号处理
        """
        self._log.info("host.signal.received")

        if not self.lifetime.stopping.is_set():
            self.lifetime.stop_application()



    async def _rollback_started_services(
        self,
        started_services: list[IHostedService],
    ) -> None:

        self.lifetime.stop_application()

        for svc in reversed(started_services):

            try:

                await asyncio.wait_for(
                    svc.stop(self.lifetime.stopping),
                    timeout=self.options.shutdown_timeout,
                )

            except asyncio.TimeoutError:  # noqa: UP041
                self._log.error(
                    "host.rollback.stop.timeout",
                    service=type(svc).__name__,
                    timeout=self.options.shutdown_timeout,
                )

            except Exception:

                self._log.exception(
                    "host.rollback.stop.failed",
                    service=type(svc).__name__,
                )

        await self._shutdown_resources()



    # 增加处理如果Background Service 启动失败的处理
    def _on_background_crash(
        self,
        info: CrashInfo,
    ) -> None:

        self._log.error(
            "host.background_service.crashed",
            service = info.source,
            exception=type(info.exception).__name__,
        )

        if not self.options.stop_on_background_crash:
            self._log.warning(
                "host.background_service.crash_ignored",
                service=info.source,
            )

            return

        self._log.error(
            "host.background_service.requesting_stop",
            service=info.source,
        )

        if self.lifetime.stopping.is_set():
            return

        self.lifetime.stop_application()

    # 配置crash 处理器
    def _configure_crash_handler(
            self,
            svc: IHostedService,
    ) -> None:
        if isinstance(svc, SupportsCrashHandler):
            svc.set_crash_handler(
                self._on_background_crash,
            )


    # 关闭资源的resource
    async def _shutdown_resources(self) -> None:

        # 如果已经关闭了, 直接返回
        if self._resource_shutdown:
            return

        self._resource_shutdown = True

        try:

            await self.container.shutdown_resources()

            self._log.info(
                "host.containr.stopped",
            )

        except Exception:

            self._log.exception(
                "host.rollback.container.failed"
            )
