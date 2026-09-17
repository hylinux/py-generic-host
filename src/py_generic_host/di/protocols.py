from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dependency_injector.providers import BaseResource


@runtime_checkable
class ResourceContainer(Protocol):
    """DI 容器生命周期锲约

    只描述"资源合适初始化/释放", 不描述"对象如何创建"
    singleton / factory / resource 的语义属于 dependency_injector
    Host 不应该也不需要知道。

    返回类型严格对齐 dependency_injector 的真实签名
    容器内全是同步资源时返回 None,存在异步资源时返回 Awaitable。
    调用方 **必须** 判定后再 await,不可无条件 await。
    """

    def init_resources(
            self,
            resource_type: type[BaseResource[Any]] = ...,
    ) -> Awaitable[None] | None: ...

    def shutdown_resources(
            self,
            resource_type: type[BaseResource[Any]] = ...,
    ) -> Awaitable[None] | None: ...

    def wire(
            self,
            modules: list[Any] | None = ...,
            packages: list[Any] | None = ...,
    ) -> None: ...

    def unwire(self) -> None: ...





@runtime_checkable
class HealthServiceProvider(Protocol):
    """Anything exposing a callable `health_service` provider."""

    def health_service(self) -> Any: ...



@runtime_checkable
class AppContainerProtocol(HealthServiceProvider, ResourceContainer, Protocol):
    """Full container contract used across the framework."""
