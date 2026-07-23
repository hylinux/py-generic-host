from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .abstractions import HealthStatus
from .service import HealthCheckService


def build_health_router(container) -> APIRouter:
    r = APIRouter(tags=["health"])

    async def _run(tag: str) -> JSONResponse:
        svc: HealthCheckService = container.health_service()
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
