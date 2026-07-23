from __future__ import annotations

import asyncio
import contextlib
from abc import ABC, abstractmethod

import structlog


class IHostedService(ABC):

    @abstractmethod
    async def start(self, stopping: asyncio.Event) -> None: ...

    @abstractmethod
    async def stop(self, stopping: asyncio.Event) -> None: ...


class BackgroundService(IHostedService):

    def __init__(self) -> None:
        self._task : asyncio.Task[None] | None = None
        self._log = structlog.get_logger(self.__class__.__name__)

    async def start(self, stopping: asyncio.Event) -> None:
        self._task = asyncio.create_task(self._safe_run(stopping),
                                         name=self.__class__.__name__
                                         )

    async def _safe_run(self, stopping: asyncio.Event) -> None:

        try:
            await self.execute_async(stopping)

        except asyncio.CancelledError:
            raise
        except Exception:
            self._log.exception("background.crashed")

    async def stop(self, stopping: asyncio.Event) -> None:

        if not self._task:
            return

        try:
            await asyncio.wait_for(self._task, timeout=30)
        except TimeoutError:
            self._task.cancel()

            # 思考为什么要使用如下的结构替换try - except
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task

    @abstractmethod
    async def execute_async(self, stopping: asyncio.Event) -> None: ...



