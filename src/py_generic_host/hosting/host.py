from __future__ import annotations

import asyncio
import contextlib
import signal

import structlog

from .hosted_service import IHostedService
from .lifetime import ApplicationLifetime


class Host:

    def __init__(
            self,
            container,
            services: list[IHostedService],
            lifetime: ApplicationLifetime
    ) -> None:
        self.container = container
        self.services = services
        self.lifetime = lifetime
        self._log = structlog.get_logger("Host")

    async def run_async(self) -> None:
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, self._on_signal)

        await self._start()
        await self.lifetime.stopping.wait()
        await self._stop()

    def _on_signal(self) -> None:
        self._log.info("host.signal.received")
        self.lifetime.stopping.set()

    async def _start(self) -> None:
        self._log.info("host.starting", services = len(self.services))

        for svc in self.services:
            await svc.start(self.lifetime.stopping)

        self.lifetime.started.set()
        self._log.info("host.started")

    async def _stop(self) -> None:
        self._log.info("host.stopping")

        for svc in reversed(self.services):
            try:
                await svc.stop(self.lifetime.stopping)
            except Exception:
                self._log.exception("host.stop.error", service=type(svc).__name__)

        try:
            await self.container.shutdown_resources()
        except Exception:
            self._log.exception("host.container.shutdown.error")

        self.lifetime.stopped.set()
        self._log.info("host.stopped")
