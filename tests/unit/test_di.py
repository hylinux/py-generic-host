import pytest
from samples.web_api.container import AppContainer


def test_container_resolves_user_service():
    c = AppContainer()
    # Resource Provider 需要 init
    import asyncio
    asyncio.run(c.init_resources())
    try:
        svc = c.user_service()
        assert svc is not None
    finally:
        asyncio.run(c.shutdown_resources())