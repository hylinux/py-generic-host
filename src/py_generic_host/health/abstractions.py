from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class HealthStatus(StrEnum):
    HEALTHY = "Healthy"
    DEGRADED = "Degraded"
    UNHEALTHY = "Unhealthy"


@dataclass
class HealthResult:
    status: HealthStatus
    description: str = ""
    data: dict | None = None
    duration_ms: float = 0.0


class IHealthCheck(ABC):
    name: str = "unname"
    tags: set[str] = field(default_factory=set )

    @abstractmethod
    async def check(self) -> HealthResult: ... # type: ignore
