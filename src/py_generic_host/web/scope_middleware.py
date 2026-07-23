import uuid

import structlog
from starlette.types import (
    ASGIApp,
    Receive,
    Scope,
    Send,
)


class RequestScopeMiddleware:

    def __init__(
            self,
            app: ASGIApp,
            container,
    ) -> None:
        self.app = app
        self.container = container

    async def __call__(
            self,
            scope: Scope,
            receive: Receive,
            send: Send,
    ) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [] )
        req_id = (headers.get(b"x-request-id", b"") or b"").decode() or uuid.uuid4().hex

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id = req_id,
            method=scope.get("method"),
            path=scope.get("path"),
        )

        scope.setdefault("state", {})
        scope["state"]["request_id"] = req_id
        scope["state"]["container"] = self.container

        # 把 Resource Provider 的生命周期绑到一次请求
        await self.container.init_resources()

        try:
            await self.app(scope, receive, send)
        finally:
            await self.container.shutdown_resources()
