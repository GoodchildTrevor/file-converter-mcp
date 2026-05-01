"""Bearer token authentication middleware."""
from __future__ import annotations

from __future__ import annotations
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse


class BearerAuthMiddleware:
    """Pure ASGI Bearer token middleware — не использует BaseHTTPMiddleware."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self._token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {self._token}":
                response = JSONResponse({"detail": "Unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
