from typing import TypeVar

from fastapi import Request

T = TypeVar("T")


def from_container(provider_name: str):
    async def _resolver(request: Request):
        container = request.scope["state"]["container"]
        provider = getattr(container, provider_name)
        result = provider()

        if hasattr(result, "__await__"):
            return await result
        return result
    return _resolver

