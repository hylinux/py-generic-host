import asyncio

import structlog
import uvicorn

from ..hosting.hosted_service import IHostedService


class UvicornHostedService(IHostedService):

    def __init__(
            self,
            app,
            host: str = "0.0.0.0",  # noqa: S104
            port : int = 8000,
            **kwargs
    ) -> None:
        cfg = uvicorn.Config(
            app, host=host, port=port, lifespan="on",
            log_config=None, access_log=False, **kwargs,
        )  # 这个部分也需要重构一下，因为日志配置和access 日志配置都没有指定。  # noqa: RUF003

        self._server = uvicorn.Server(cfg)
        self._server.install_signal_handlers = lambda: None # type: ignore # 为什么要忽略这里, 后面要仔细看一下这个部分

        self._task : asyncio.Task | None = None
        self._log = structlog.get_logger("Uvicorn")

    async def start(self, stopping: asyncio.Event ) -> None:
        self._task = asyncio.create_task(self._server.serve(), name="UvicornServer")
        self._log.info("uvicorn.started")


    async def stop(self, stopping: asyncio.Event) -> None:
        self._server.should_exit = True

        if self._task :
            try:
                await asyncio.wait_for(self._task, timeout=30)
            except asyncio.TimeoutError:    # noqa: UP041
                self._log.warning("uvicorn.force_exit")
                self._server.force_exit = True
                await self._task

        self._log.info("uvicorn.stopped")
