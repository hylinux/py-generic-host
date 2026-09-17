from __future__ import annotations

from enum import StrEnum


class StopReason(StrEnum):
    """Host 停止原因

    用于结构化日志, 退出码以及停机后的可观测性分析。

    继承StrEnum, 因此枚举成员本身就是字符串,
    可以直接作为 structlog的字段值输出, 无需 .value
    """

    # 正常停止, 外部代码主动调用了lifetime.stop_application()
    GRACEFUL = "graceful"

    # 收到 SIGINT / SIGTERM (K8s 滚动更新的正常路径)
    SIGNAL = "signal"

    # 后台服务崩溃, 且 stop_on_background_crash = True
    BACKGROUND_CRASH = "background_crash"

    # DI 容器资源初始化失败 (配置错误 / 外部依赖不可达)
    RESOURCE_INIT_FAILED = "resource_init_failed"

    # Hosted service 启动失败或启动超时
    STARTUP_FAILED = "startup_failed"

    @property
    def is_failure(self) -> bool:
        """该原因是否代表异常停机.

        决定 host.stopped 的日志级别与进程退出码.

        注意: SIGNAL 不算失败 SIGTERM 是k8s 滚动更新的标准动作.
        """
        return self in _FAILURE_REASONS

    @property
    def exit_code(self) -> int:
        """建议的进程退出码"""
        return 1 if self.is_failure else 0

_FAILURE_REASONS = frozenset(
    {
        StopReason.BACKGROUND_CRASH,
        StopReason.RESOURCE_INIT_FAILED,
        StopReason.STARTUP_FAILED
    }
)


