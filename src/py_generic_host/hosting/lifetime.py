from __future__ import annotations

import asyncio


class ApplicationLifetime:
    """Application Lifetime
    """

    def __init(self) -> None:
        """
        定义应用程序的声明周期
        """
        self.started = asyncio.Event()
        self.stopping = asyncio.Event()
        self.stopped = asyncio.Event()

    def stop_application(self) -> None:
        self.stopping.set()
