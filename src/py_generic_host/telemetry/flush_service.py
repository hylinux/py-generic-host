from __future__ import annotations

import asyncio

import structlog
from opentelemetry import _logs, metrics, trace

from ..hosting.hosted_service import IHostedService


class TelemetryFlushService(IHostedService):
    """在停机最后阶段刷出遥测数据。

    必须是第一个 add_hosted_service 的服务:
    stop_async() 按 reversed(_started_services) 停止, 最先注册者最后停止,
    这样其他服务停机期间产生的 span / 日志才能被这一步刷出去。
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout
        self._log = structlog.get_logger("TelemetryFlushService")

    async def start(self, stopping: asyncio.Event) -> None:
        return

    async def stop(self, stopping: asyncio.Event) -> None:
        for name, provider in (
            ("trace", trace.get_tracer_provider()),
            ("metrics", metrics.get_meter_provider()),
            ("logs", _logs.get_logger_provider()),
        ):
            shutdown = getattr(provider, "shutdown", None)
            if shutdown is None:
                continue

            try:
                # OTel 的 shutdown() 是同步阻塞调用(内部等待导出完成),
                # 直接在事件循环里调会卡死整个停机流程, 连超时都触发不了。
                await asyncio.wait_for(
                    asyncio.to_thread(shutdown),
                    timeout=self._timeout,
                )
                self._log.info("telemetry.flushed", provider=name)

            except asyncio.TimeoutError:  # noqa: UP041
                self._log.error(
                    "telemetry.flush.timeout",
                    provider=name,
                    timeout=self._timeout,
                )
            except Exception:
                self._log.exception("telemetry.flush.failed", provider=name)
