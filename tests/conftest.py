import pytest
from samples.web_api.container import AppContainer


@pytest.fixture
def container() -> AppContainer:
    c = AppContainer()

    return c


@pytest.fixture
async def http_client():
    from samples.web_api.api import register_routes
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    app = FastAPI()

    register_routes(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

