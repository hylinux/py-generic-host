from __future__ import annotations

import uuid
from typing import Any

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send

from ..di.protocols import ResourceContainer


class RequestScopeMiddleware:
    """
    Rquest Scope 中间件

    用处:
    - 为每个 Http/WebSocket 请求生成或者传递 requst_id
    - 将 Request_id, method, path 绑定到 structlog contextvars
    - 将 request_id 和 container 放入 ASGI scope["state"]
    - 请求结束后 清理 structlog contextvars

    注意:
    本类不负责 container.init_resources() 以及  shutdown_resources()。

    ResourceContainer的生命周期由 Host 管理,而不是由每个请求来管理
    """

    def __init__(
            self,
            app: ASGIApp,
            containr: ResourceContainer,
    ) -> None:
        self.app = app
        self.container = self.container


    async def __call__(
            self,
            scope: Scope,
            receive: Receive,
            send: Send,
    ) -> None:

        scope_type = scope['type']

        if scope_type not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request_id = self._get_or_create_request_id(scope)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id = request_id,
            method = scope.get("method"),
            path = scope.get("path"),
        )

        state = self._ensure_state(scope)
        state["request_id"] = request_id
        state["container"] = self.container

        try:

            await self.app(scope, receive, send)
        finally:
            structlog.contextvars.clear_contextvars()


    def _get_or_create_request_id(
            self,
            scope: Scope,
    ) -> str:

        headers = dict(scope.get("headers") or [])

        raw_request_id = headers.get(b"x-request-id", b"")

        if raw_request_id:
            request_id = raw_request_id.decode(
                encoding="utf-8",
                errors = "ignore",
            ).strip()

            if request_id:
                return request_id

        return uuid.uuid4().hex


    def _ensure_state(
            self,
            scope: Scope,
    ) -> dict[str, Any]:

        state = scope.setdefault("state", {})

        if not isinstance(state, dict):
            raise TypeError(
                "ASGI scope['state'] must be a dictionary."
            )

        return state
