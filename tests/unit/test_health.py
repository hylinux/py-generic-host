import pytest

from py_generic_host.health.abstractions import HealthResult, HealthStatus, IHealthCheck
from py_generic_host.health.service import HealthCheckService


class Ok(IHealthCheck):
    name = "ok"
    tags = {"ready"}  # noqa: RUF012
    async def check(self): return HealthResult(HealthStatus.HEALTHY)


class Bad(IHealthCheck):
    name = "bad"
    tags = {"ready"}  # noqa: RUF012
    async def check(self): return HealthResult(HealthStatus.UNHEALTHY, "boom")


@pytest.mark.asyncio
async def test_health_unhealthy_when_any_bad():
    svc = HealthCheckService([Ok(), Bad()])
    result = await svc.run(tag="ready")
    assert result["status"] == HealthStatus.UNHEALTHY
    assert "bad" in result["checks"]


@pytest.mark.asyncio
async def test_health_tag_filter():
    svc = HealthCheckService([Ok()])
    result = await svc.run(tag="live")
    assert result["checks"] == {}