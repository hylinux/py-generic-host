import pytest


@pytest.mark.asyncio
async def test_items_endpoint(http_client):
    resp = await http_client.get("/items/")
    assert resp.status_code == 200
    assert resp.json() == [{"id": 1, "name": "demo"}]