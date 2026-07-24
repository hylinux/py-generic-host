import asyncio

from .hosted_service import BackgroundService


# 一个工作类的实现demo
# 如果用户有自己的workservice需要实现，那么可以按照这个参考类来实现
class WorkerService(BackgroundService):

    async def execute_async(
        self,
        stopping: asyncio.Event,
    ) -> None:
        while not stopping.is_set():
            await self.run_once()

            try:
                await asyncio.wait_for(
                    stopping.wait(),
                    timeout=5.0,
                )

            except asyncio.TimeoutError:  # noqa: UP041
                continue

    async def run_once(self) -> None:
        raise RuntimeError("simulated background failure")