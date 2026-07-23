from .abstractions import HealthResult, HealthStatus, IHealthCheck


class LivenessCheck(IHealthCheck):
    name = "liveness"
    tags = {"live"}  # noqa: RUF012

    async def check(self) -> HealthResult: # type: ignore
        return HealthResult(HealthStatus.HEALTHY, "alive")
