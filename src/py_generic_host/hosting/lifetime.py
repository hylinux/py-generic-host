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


