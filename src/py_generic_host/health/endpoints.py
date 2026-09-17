from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..di.protocols import AppContainerProtocol
from .abstractions import HealthStatus
from .service import HealthCheckService


def build_health_router(container: AppContainerProtocol) -> APIRouter:
    r = APIRouter(tags=["health"])

    async def _run(tag: str) -> JSONResponse:
        svc: HealthCheckService = await container.health_service()
        result = await svc.run(tag=tag)
        code = 200 if result["status"] != HealthStatus.UNHEALTHY else 503
        return JSONResponse(result, status_code=code)

    @r.get("/healthz/live")
    async def live():
        return await _run("live")

    @r.get("/healthz/ready")
    async def ready():
        return await _run("ready")

    @r.get("/healthz/startup")
    async def startup():
        return await _run("startup")

    return r
