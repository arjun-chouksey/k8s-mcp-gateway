from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.responses import JSONResponse

from app.security.api_keys import authenticate_api_key


class MCPApiKeyMiddleware:
    def __init__(
        self, app: Callable[..., Awaitable[None]],
        session_factory: async_sessionmaker[AsyncSession], pepper: bytes,
    ) -> None:
        self.app = app
        self.session_factory = session_factory
        self.pepper = pepper

    async def __call__(
        self, scope: dict[str, Any], receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        path = scope.get("path", "")
        if scope.get("type") != "http" or not (path == "/mcp" or path.startswith("/mcp/")):
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        scheme, separator, plaintext = authorization.partition(" ")
        actor = None
        if separator and scheme.lower() == "bearer" and plaintext and " " not in plaintext:
            async with self.session_factory() as db:
                actor = await authenticate_api_key(db, plaintext, self.pepper)
        if actor is None:
            response = JSONResponse(
                {"detail": "Invalid API key"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return
        scope.setdefault("state", {})["mcp_actor"] = actor
        await self.app(scope, receive, send)
