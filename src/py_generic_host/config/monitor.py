from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from typing import TypeVar

import structlog
from watchfiles import awatch

from py_generic_host.hosting.hosted_service import IHostedService

log = structlog.get_logger("OptionsMonitor")
T = TypeVar("T")


class OptionsMonitor[T]:
    def __init__(
            self,
            factory: Callable[ [],  T],
    ) -> None:
        self._factory = factory
        self._current: T = factory()
        self._listeners: list[Callable[[T], None]] = []
        self._lock = asyncio.Lock()

    @property
    def current_value(self) -> T:
        return self._current

    def on_change(self, listener: Callable[[T], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    async def reload(self) -> None:
        async with self._lock:
            try:
                new_value = self._factory()
            except Exception:
                log.exception("Options.reload.failed")
                return

            if new_value == self._current :
                return

            self._current = new_value
            log.info("options.changed", type=type(new_value).__name__)

            for ln in list(self._listeners):
                try:
                    ln(new_value)
                except Exception:
                    log.exception("options.listener.error")

class ConfigWatcher(IHostedService):
    """HostedService 包装的文件监听器"""

    def __init__(self, paths: list[str], monitors: list[OptionsMonitor]) -> None:
        self._paths = paths
        self._monitors = monitors
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self, stopping: asyncio.Event) -> None:
        self._task = asyncio.create_task(self._run(), name="ConfigWatcher")

    async def stop(self, stopping: asyncio.Event) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        async for _ in awatch(*self._paths, stop_event=self._stop):
            log.info("config.files.change")
            for m in self._monitors:
                await m.reload()

