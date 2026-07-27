from py_generic_host.health.abstractions import (
    HealthResult,
    HealthStatus,
    IHealthCheck,
)

from .external_api import ExternalApiClient


class ExternalApiHealthCheck(IHealthCheck):

    name = "external_api"

    def __init__(
            self,
            api: ExternalApiClient,
    ) -> None:
        self._api = api
        self.tags: set[str] = {"ready"}


    async def check(self) -> HealthResult:
        ok = await self._api.ping()

        return HealthResult(
            HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
            "external api reachable" if ok else "external api unreachable",
        )
