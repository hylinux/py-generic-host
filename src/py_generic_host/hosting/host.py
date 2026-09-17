from __future__ import annotations

import asyncio
import contextlib
import inspect
import signal
import time
from dataclasses import dataclass
from typing import Any

import structlog

from ..di.protocols import ResourceContainer
from .crash_models import CrashInfo
from .hosted_service import IHostedService, SupportsCrashHandler
from .lifetime import ApplicationLifetime
from .stop_reason import StopReason


@dataclass(slots=True)
class HostOptions:
    shutdown_timeout: float = 60   # 一分钟停止
    startup_timeout: float = 60    # 一分钟启动
    stop_on_background_crash: bool = True   # 设置是否背景任务失败直接停止。


class Host:

    def __init__(
            self,
            container: ResourceContainer,
            services: list[IHostedService],
            lifetime: ApplicationLifetime,
            options: HostOptions | None = None,
    ) -> None:

        if options is None:
            options = HostOptions()

        self.container = container
        self.services = services
        self.lifetime = lifetime
        self.options = options

        self._log = structlog.get_logger("Host")

        self._started = False
        self._stopping = False
        self._resource_shutdown = False

        # 已经启动的服务
        self._started_services: list[IHostedService] = []

        # 停机原因追踪
        # _stop_reason 用 None 而不是默认的GRACEFUL,
        # 这样没有人明确说明原因和原因确实是graceful 可以区分出来
        self._stop_reason: StopReason | None = None
        self._stop_error: BaseException | None = None
        self._stop_detail: str | None = None

        # 用于计算uptime, 排查启动即崩溃问题
        self._started_at: float | None = None


    # ---------------------------------------------
    # 公开属性
    # ---------------------------------------------

    @property
    def stop_reason(self) -> StopReason | None:
        """Host 的停机原因。

        stop_async() 执行完成之后才有确定值。
        """
        return self._stop_reason


    @property
    def exit_code(self) -> int:
        """建议的进程退出码。

        用于"没有异常抛出但属于异常停机"的场景,
        典型就是后台服务崩溃触发的停机: run_async() 正常返回,
        但进程应当以非 0 退出。
        """
        if self._stop_reason is None:
            return 0

        return self._stop_reason.exit_code


    async def run_async(self) -> None:
        """Main Host Loop

            主要的Host 启动步骤
        """

        # 注册信号处理器
        self._register_signal_handlers()

        try:
            await self.start_async()
            await self.lifetime.stopping.wait()
        finally:
            await self.stop_async()




    async def start_async(self) -> None:
        """
        正式启动Host
        """

        # 如果已经启动了
        if self._started:
            return

        self._log.info(
            "host.starting",
            services = len(self.services)
        )

        # 先初始化DI 资源 资源没有就绪 服务启动没有意义

        try:
            await asyncio.wait_for(
                _maybe_await(self.container.init_resources()),
                timeout=self.options.startup_timeout,
            )

            self._log.info("host.container.started")

            # wiring 与  unwire 成对 统一由Host 管理
            self.container.wire()
            self._log.info("host.container.wired")

        except asyncio.TimeoutError as exc: #noqa: UP041
            self._log.error(
                "host.container.start.timeout",
                timeout=self.options.startup_timeout,
            )

            self._set_stop_reason(StopReason.RESOURCE_INIT_FAILED, exc)

            # 可能已经初始化成功了一部分资源 必须回收。
            await self._shutdown_resources(phase="startup_rollback")
            raise

        except Exception as exc:
            self._log.exception("host.container.start.failed")
            self._set_stop_reason(StopReason.RESOURCE_INIT_FAILED, exc)
            await self._shutdown_resources(phase="startup_rollback")
            raise



        # 启动服务的逻辑
        try:

            for svc in self.services:

                # 配置可能的crash 启动器
                # 这里使用Protocl, SupportsCrashHandler 解耦 BackgroundService,
                # 即只需要有set_crash_handler 即可以完成解耦。
                self._configure_crash_handler(svc)

                self._log.info(
                    "host.service.starting",
                    service = type(svc).__name__,
                )

                # 设置服务启动的超时时间
                await asyncio.wait_for(
                    svc.start(self.lifetime.stopping),
                    timeout=self.options.startup_timeout,
                )

                self._started_services.append(svc)

                self._log.info(
                    "host.service.started",
                    service=type(svc).__name__,
                )

        except asyncio.TimeoutError as exc:  # noqa: UP041
            # 处理启动超时
            self._log.error(
                "host.start.timeout",
                timeout=self.options.startup_timeout,
            )

            self._set_stop_reason(StopReason.STARTUP_FAILED, exc)
            await self._rollback_started_services()

            # 重新抛出异常
            raise

        except Exception as exc:
            self._log.exception(
                "host.start.failed",
            )

            self._set_stop_reason(StopReason.STARTUP_FAILED, exc)

            # 发现失败时候,要将其他的服务rollback 回来
            await self._rollback_started_services()

            # 重新抛出异常
            raise

        self._started = True
        self._started_at = time.monotonic()

        self.lifetime.started.set()

        self._log.info("host.started")



    async def stop_async(self) -> None:
        """
        停止Host
        """

        # 预防多次调用stop
        if self._stopping:
            return

        self._stopping = True

        # 走到了这里还没有原因,说明是外部代码主动调用stop_application() 停机
        # 首次写入优先, 所以真正的原因不会被覆盖
        self._adopt_external_stop_reason()
        self._set_stop_reason(StopReason.GRACEFUL)

        reason = self._stop_reason
        assert reason is not None

        self._log.info("host.stopping", reason=reason)

        # 确保停止的信号被发布出去
        if not self.lifetime.stopping.is_set():
            self.lifetime.stop_application(reason)

        # 停止Host的所有服务
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.options.shutdown_timeout

        for svc in reversed(self._started_services):

            remaining = max(0.0, deadline - loop.time())

            if remaining <= 0:
                self._log.error(
                    "host.stop.budget_exhausted",
                    service=type(svc).__name__,
                )

                break

            try:
                await asyncio.wait_for(
                    svc.stop(self.lifetime.stopping),
                    timeout=remaining,
                )

                self._log.info(
                    "host.service.stopped",
                    service=type(svc).__name__,
                )
            except asyncio.TimeoutError:  # noqa: UP041
                self._log.error(
                    "host.service.stop.timeout",
                    service=type(svc).__name__,
                    timeout=remaining,
                )
            except Exception:
                self._log.exception(
                    "host.service.stop.failed",
                    service=type(svc).__name__,
                )

        self._started_services.clear()

        with contextlib.suppress(Exception):
            self.container.unwire()
            self._log.info("host.container.unwired.")

        # 关闭DI 资源
        await self._shutdown_resources(phase="shutdown")

        self.lifetime.stopped.set()
        self._log_stopped(reason)


    # 将私有方法往后面放, 从这里开始放私有方法
    # ---------------------------------------------


    def _set_stop_reason(
            self,
            reason: StopReason,
            error: BaseException | None = None,
    ) -> None:
        """记录停机原因。

        采用"首次写入优先"(first writer wins):
        真正的根因总是最先发生的那一个。

        典型场景:
        后台服务崩溃 -> stop_application() -> 进入停机流程,
        此时运维人员如果按下 Ctrl+C, SIGNAL 不应该覆盖掉
        BACKGROUND_CRASH 这个真正的根因。
        """

        if self._stop_reason is not None:

            if self._stop_reason is not reason:
                self._log.debug(
                    "host.stop_reason.ignored",
                    existing=self._stop_reason,
                    ignored=reason,
                )
            return

        self._stop_reason = reason
        self._stop_error = error


    def _adopt_external_stop_reason(self) -> None:
        """采纳外部调用方通过 lifetime.stop_application(reason=...) 声明的原因。

        为什么 Host 仍然要保有自己的 _stop_reason:
        Host 的部分失败路径根本不会经过 lifetime.stop_application(),
        最典型的就是 RESOURCE_INIT_FAILED —— DI 资源初始化失败时直接
        回滚并 raise, 一次都不会碰 lifetime。
        所以 lifetime 上的原因只是"外部调用方的补充信息", 不是唯一来源。
        """

        if self.lifetime.stop_reason is not None:
            self._set_stop_reason(self.lifetime.stop_reason)

        if self.lifetime.stop_detail is not None and self._stop_detail is None:
            self._stop_detail = self.lifetime.stop_detail


    def _log_stopped(
            self,
            reason: StopReason,
    ) -> None:
        """输出停机的最终结论。

        事件名固定为 host.stopped, 用字段承载上下文;
        日志级别随 is_failure 浮动, 作为告警的第二层保险。
        """

        uptime = (
            round(time.monotonic() - self._started_at, 3)
            if self._started_at is not None
            else None
        )

        fields: dict[str, Any] = {
            "reason": reason,
            "exit_code": reason.exit_code,
            "uptime_seconds": uptime,
        }

        if self._stop_detail is not None:
            fields["detail"] = self._stop_detail

        if self._stop_error is not None:
            # 只输出异常类型名。
            # 异常消息里可能带连接串 / token 等敏感信息,
            # 完整堆栈由抛出点的 log.exception 负责。
            fields["error"] = type(self._stop_error).__name__

        if reason.is_failure:
            self._log.error("host.stopped", **fields)
        else:
            self._log.info("host.stopped", **fields)


    def _register_signal_handlers(self) -> None:
        """
        注册信号处理器
        """
        # 获取默认的运行loop
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM ):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, self._on_signal, sig)


    def _on_signal(self, sig: signal.Signals) -> None:
        """
        接收到信号处理
        """
        self._log.info("host.signal.received", signal=sig.name)

        self._set_stop_reason(StopReason.SIGNAL)

        if not self.lifetime.stopping.is_set():
            self.lifetime.stop_application(StopReason.SIGNAL)



    async def _rollback_started_services(self) -> None:
        """启动失败时回滚已经启动成功的服务。

        直接使用 self._started_services 并在结束后清空,
        避免 run_async() 的 finally -> stop_async() 再停一次。
        """

        self.lifetime.stop_application(StopReason.STARTUP_FAILED)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.options.shutdown_timeout


        for svc in reversed(self._started_services):

            remaining = max(0.0, deadline - loop.time())

            if remaining <= 0:
                self._log.error(
                    "host.stop.budget_exhausted",
                    service=type(svc).__name__,
                )

                break


            try:

                await asyncio.wait_for(
                    svc.stop(self.lifetime.stopping),
                    timeout=remaining,
                )

            except asyncio.TimeoutError:  # noqa: UP041
                self._log.error(
                    "host.rollback.stop.timeout",
                    service=type(svc).__name__,
                    timeout=remaining,
                )

            except Exception:

                self._log.exception(
                    "host.rollback.stop.failed",
                    service=type(svc).__name__,
                )
        # 已经回滚过了 不用再跑一边
        self._started_services.clear()

        await self._shutdown_resources(phase="startup_rollback")



    # 增加处理如果Background Service 启动失败的处理
    def _on_background_crash(
        self,
        info: CrashInfo,
    ) -> None:

        self._log.error(
            "host.background_service.crashed",
            service = info.source,
            exception=type(info.exception).__name__,
        )

        if not self.options.stop_on_background_crash:
            self._log.warning(
                "host.background_service.crash_ignored",
                service=info.source,
            )

            return

        self._log.error(
            "host.background_service.requesting_stop",
            service=info.source,
        )

        # 必须放在下面的early return 之前
        # 即使stopping 已经被set, 崩溃这个根因也要记录下来
        self._set_stop_reason(
            StopReason.BACKGROUND_CRASH,
            error=info.exception,
        )

        if self.lifetime.stopping.is_set():
            return

        self.lifetime.stop_application(StopReason.BACKGROUND_CRASH)

    # 配置crash 处理器
    def _configure_crash_handler(
            self,
            svc: IHostedService,
    ) -> None:
        if isinstance(svc, SupportsCrashHandler):
            svc.set_crash_handler(
                self._on_background_crash,
            )


    # 关闭资源的resource
    async def _shutdown_resources(self, phase: str = "shutdown") -> None:

        # 如果已经关闭了, 直接返回
        if self._resource_shutdown:
            self._log.debug("host.container.stop.skipped", phase=phase)
            return

        self._resource_shutdown = True

        try:
            await asyncio.wait_for(
                _maybe_await(
                    self.container.shutdown_resources()
                ),
                timeout=self.options.shutdown_timeout,
            )

            self._log.info(
                "host.container.stopped",phase=phase
            )

        except asyncio.TimeoutError:  # noqa: UP041
            self._log.error(
                "host.container.stop.timeout", phase=phase,
                timeout=self.options.shutdown_timeout,
            )
        except Exception:

            self._log.exception(
                "host.container.stop.failed",
                phase=phase
            )


async def _maybe_await(result: Any) -> None:
    """dependency_injector 的 init/shutdown_resources 返回 Awaitable | None。

    - 容器内全是同步资源 -> None
    - 存在异步资源(且已点亮 async mode) -> 协程
    绝不能无条件 await。
    """
    if inspect.isawaitable(result):
        await result
