import asyncio
import contextlib

import pytest

from py_generic_host.hosting.hosted_service import BackgroundService
from py_generic_host.hosting.lifetime import ApplicationLifetime


class Counter(BackgroundService):
    def __init__(self):
        super().__init__()
        self.ticks = 0
    async def execute_async(self, stopping):
        while not stopping.is_set():
            self.ticks += 1
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(stopping.wait(), timeout=0.05)


@pytest.mark.asyncio
async def test_background_service_starts_and_stops():
    lifetime = ApplicationLifetime()
    svc = Counter()
    await svc.start(lifetime.stopping)
    await asyncio.sleep(0.2)
    lifetime.stopping.set()
    await svc.stop(lifetime.stopping)
    assert svc.ticks >= 1
