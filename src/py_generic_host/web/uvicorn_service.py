from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI

from ..hosting.hosted_service import BackgroundService


class HostedUvicornServer(uvicorn.Server):

    def install_signal_handlers(self) -> None:
        """
        Host统一处理SIGINT/SIGTERM。

        禁用Uvicorn自己的Signal处理。
        """
        return


class UvicornHostedService(BackgroundService):
    """
    Uvicorn hosted service.

    主要的职责:
    - 将 Uvicorn 作为一个普通的 HostedService 接入Host
    - 通过 BackgroundService 接入 CrashInfo / CrashHandler 机制
    - 避免 Uvicorn 自己注册 signal handler
    - 由 Host 统一处理 SIGINT / SIGTERM
    - 支持优雅停止和强制退出
    """

    def __init__(
            self,
            app: FastAPI,
            host: str = "0.0.0.0",  #noqa : S104
            port: int = 8000,
            graceful_shutdown_timeout: float = 30.0,
            force_exit_timeout: float = 5.0,
            **uvicorn_kwargs: Any,
    ) -> None:
        super().__init__()

        self._host = host
        self._port = port
        self._graceful_shutdown_timeout = graceful_shutdown_timeout
        self._force_exit_timeout = force_exit_timeout


        config = uvicorn.Config(
            app = app,
            host = host,
            port = port,
            lifespan = "on",
            log_config = None,
            access_log = False,
            **uvicorn_kwargs,
        )

        self._server = HostedUvicornServer(config)

        self._log = structlog.get_logger(
            "UvicornHostedService",
        )


    async def start(
            self,
            stopping: asyncio.Event,
    ) -> None:
        """
        启动 Uvicorn.

        需要注意:
        create_task 成功不代表 uvicorn 启动成功
        因此要等待 self._server.started 变为True
        """

        await super().start(stopping)

        try:
            await self._wait_until_started(stopping)

        except BaseException:

            self._server.should_exit = True

            if self._task is not None:
                self._task.cancel()

                with contextlib.suppress(asyncio.CancelledError, Exception,):
                    await self._task

                self._task = None

            # 重新抛出
            raise

        self._log.info(
            "uvicorn.started",
            host = self._host,
            port = self._port,
        )


    async def execute_async(
            self,
            stopping: asyncio.Event,
    ) -> None:
        """
        Background service 启动入口
        """

        await self._server.serve()



    async def stop(self, stopping: asyncio.Event) -> None:
        """
        停止 Uvicorn

        停止的策略:
        1. 设置 should_exit = True, 请求uvicron 自己退出
        2. 等待 graceful_shutdown_timeout
        3. 如果没有能退出,设置 force_exit=true
        4. 再等待 force_exit_timeout
        5. 仍未退出,取消后台task
        """

        if self._task is None:
            return

        self._server.should_exit = True

        try:

            await asyncio.wait_for(
                self._task,
                timeout = self._graceful_shutdown_timeout,
            )

            self._log.info(
                "uvicorn.stopped",
                mode="gracefual",
            )

            return

        except asyncio.TimeoutError:  # noqa: UP041
            self._log.warning(
                "uvicorn.graceful_shutdown.timeout",
                timeout=self._graceful_shutdown_timeout,
            )

        self._server.force_exit = True

        try:
            await asyncio.wait_for(
                self._task,
                timeout=self._force_exit_timeout,
            )

            self._log.warning(
                "uvicorn.stopped",
                mode="force_exit",
            )

            return

        except asyncio.TimeoutError:  # noqa: UP041
            self._log.error(
                "uvicorn.force_exit.timeout",
                timeout=self._force_exit_timeout,
            )


        self._task.cancel()

        with contextlib.suppress(asyncio.CancelledError, Exception,):
            await self._task


        self._log.error(
            "uvicorn.stopped",
            mode="cancelled",
        )

        self._task = None


    async def _wait_until_started(
            self,
            stopping: asyncio.Event,
    ) -> None:

        while not self._server.started:

            if stopping.is_set():
                raise RuntimeError(
                    "Uvicorn startup was cancelled because host is stopping."
                )

            if self._task is not None and self._task.done():

                if self._task.cancelled():
                    raise RuntimeError(
                        "Uvicorn startup task was cancelled."
                    )

                exception = self._task.exception()

                if exception is not None:
                    raise RuntimeError(
                        "Uvicorn startup failed."
                    ) from exception

                raise RuntimeError(
                    "Uvicorn exited before startup completed."
                )

            await asyncio.sleep(0.05)
