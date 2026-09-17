from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar


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
    tags: ClassVar[set[str]] = set()

    @abstractmethod
    async def check(self) -> HealthResult: ... # type: ignore
