from __future__ import annotations

import asyncio

from .stop_reason import StopReason


class ApplicationLifetime:
    """Application Lifetime
    """

    def __init__(self) -> None:
        """
        定义应用程序的声明周期
        """
        self.started = asyncio.Event()
        self.stopping = asyncio.Event()
        self.stopped = asyncio.Event()

        # 停机原因(可选), 由 stop_application(reason=...) 写入。
        # 采用与 Host 一致的"首次写入优先"。
        #
        # 注意: 这里只承载"外部调用方主动声明的原因"。
        # Host 自身的失败路径有自己的 _stop_reason, 两者在
        # Host.stop_async() 中合流。
        self.stop_reason: StopReason | None = None
        self.stop_detail: str | None = None

    def stop_application(
            self,
            reason: StopReason | None = None,
            detail: str | None = None,
    ) -> None:
        """请求应用停止。

        :param reason:
            有界的停机原因枚举。会作为 host.stopped 的 reason 字段输出,
            适合直接用作指标维度(基数可控)。

        :param detail:
            自由文本补充说明。只进日志, 不作为指标维度,
            用于承载应用自定义的停机语境, 例如 "config_reload"、
            "cli_interrupt"、"integration_test_teardown"。

        两个参数都是可选的, 保持对既有调用点的完全向后兼容:
        stop_application() 的行为与改动前一致。
        """

        # 首次写入优先: 只有当还没有任何原因信息时才记录。
        # 不携带任何信息的裸调用不会占位, 因此后续携带原因的调用仍然有效。
        if (reason is not None or detail is not None) and (
            self.stop_reason is None and self.stop_detail is None
        ):
            self.stop_reason = reason
            self.stop_detail = detail

        self.stopping.set()
