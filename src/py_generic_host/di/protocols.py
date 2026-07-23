from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HealthServiceProvider(Protocol):
    """Anything exposing a callable `health_service` provider."""

    def health_service(self) -> Any: ...


@runtime_checkable
class ResourceContainer(Protocol):
    """A dependency-injector container that supports async resource lifecycle.

    Declared as plain (non-async) methods returning Any so the protocol matches
    dependency-injector's real ``init_resources`` / ``shutdown_resources``
    signatures, which take an optional ``resource_type`` and return
    ``Awaitable[None] | None``. Callers are expected to ``await`` the result
    when running under an async container.
    """

    def init_resources(self) -> Any: ...
    def shutdown_resources(self) -> Any: ...


@runtime_checkable
class AppContainerProtocol(HealthServiceProvider, ResourceContainer, Protocol):
    """Full container contract used across the framework."""
