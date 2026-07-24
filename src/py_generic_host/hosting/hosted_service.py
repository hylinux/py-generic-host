from __future__ import annotations

import asyncio
import contextlib
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

import structlog

from .crash_models import CrashInfo
from .crash_protocols import CrashHandler


class IHostedService(ABC):

    @abstractmethod
    async def start(self, stopping: asyncio.Event) -> None: ...

    @abstractmethod
    async def stop(self, stopping: asyncio.Event) -> None: ...



@runtime_checkable
class SupportsCrashHandler(Protocol):

    def set_crash_handler(
            self,
            handler: CrashHandler,
    ) -> None:
        ...


class BackgroundService(IHostedService):

    def __init__(self) -> None:
        self._task : asyncio.Task[None] | None = None
        self._log = structlog.get_logger(self.__class__.__name__)

        self._crash_handler: CrashHandler | None = None


    # 设置crash处理Handler
    def set_crash_handler(
            self,
            handler: CrashHandler,
    ) -> None:
        self._crash_handler = handler


    async def start(self, stopping: asyncio.Event) -> None:
        self._task = asyncio.create_task(self._safe_run(stopping),
                                         name=self.__class__.__name__
                                         )


    async def stop(self, stopping: asyncio.Event) -> None:
        """
        停止服务
        """

        if self._task is None:
            return

        if not stopping.is_set():
            stopping.set()

        try:
            await asyncio.wait_for(self._task, timeout=60)
        except asyncio.TimeoutError:  # noqa: UP041
            self._task.cancel()

            # 思考为什么要使用如下的结构替换try - except
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
        except asyncio.CancelledError:
            raise

        except Exception:
            self._log.exception(
                "background.stop.observed_failed_task",
                service=self.__class__.__name__,
            )

        finally:
            if not self._task.done():
                self._task.cancel()

                with contextlib.suppress(asyncio.CancelledError, Exception,):
                    await self._task

            self._task = None



    # 如果要写BackgroundService, 主要就是要实现这个方法
    # 需要注意实现这个方法要合理的利用stopping 事件
    @abstractmethod
    async def execute_async(self, stopping: asyncio.Event) -> None: ...



    # 私有方法放置线
    # ---------------------------------

    async def _safe_run(self, stopping: asyncio.Event) -> None:

        try:
            await self.execute_async(stopping)

        except asyncio.CancelledError:
            raise
        except Exception as ex:
            self._log.exception(
                "background.crashed",
                service = self.__class__.__name__,
                exception = type(ex).__name__,
            )

            if self._crash_handler is not None:
                info = CrashInfo(
                    source=self.__class__.__name__,
                    exception=ex,
                )

                self._crash_handler(info)
