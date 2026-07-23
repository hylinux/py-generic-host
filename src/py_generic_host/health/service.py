from __future__ import annotations

import asyncio
import time

from .abstractions import HealthResult, HealthStatus, IHealthCheck


class HealthCheckService:

    def __init__(self, checks: list[IHealthCheck]) -> None:
        self._checks = checks

    async def run(self, tag: str | None = None ) -> dict:

        targets = [ c for c in self._checks if not tag or tag in (c.tags or set() ) ]

        async def one(c: IHealthCheck) -> tuple[str, HealthResult]:
            t0 = time.perf_counter()

            try:

                r = await asyncio.wait_for(c.check(), timeout=5)
            except asyncio.TimeoutError:  # noqa: UP041
                r = HealthResult(HealthStatus.UNHEALTHY, "timeout")
            except Exception as e:
                r = HealthResult(HealthStatus.UNHEALTHY, f"exception: {e}")

            r.duration_ms = round((time.perf_counter() - t0) * 1000, 2)

            return c.name, r

        results = dict(await asyncio.gather( * (one(c) for c in targets ))) if targets else {}

        if any(r.status == HealthStatus.UNHEALTHY for r in results.values() ):
            overall = HealthStatus.UNHEALTHY
        elif any( r.status == HealthStatus.DEGRADED for r in results.values() ):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY


        return {
            "status": overall,
            "checks": {
                k: {
                    "status": v.status,
                    "description": v.description,
                    "duration_ms": v.duration_ms,
                    "data": v.data } for k, v in results.items()
            },
        }
