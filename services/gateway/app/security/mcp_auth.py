from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.responses import JSONResponse

from app.security.api_keys import authenticate_api_key
from app.security.internal_jwt import authenticate_internal_jwt


logger = logging.getLogger(__name__)


class MCPApiKeyMiddleware:
    def __init__(
        self, app: Callable[..., Awaitable[None]],
        session_factory: async_sessionmaker[AsyncSession], pepper: bytes,
        internal_jwt_secret: str,
    ) -> None:
        self.app = app
        self.session_factory = session_factory
        self.pepper = pepper
        self.internal_jwt_secret = internal_jwt_secret

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
                if plaintext.startswith("mcpgw_"):
                    actor = await authenticate_api_key(db, plaintext, self.pepper)
                else:
                    actor = await authenticate_internal_jwt(
                        db, plaintext, self.internal_jwt_secret,
                    )
        if actor is None:
            logger.warning("Rejected unauthenticated MCP request")
            response = JSONResponse(
                {"detail": "Invalid API key"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return
        scope.setdefault("state", {})["mcp_actor"] = actor
        await self.app(scope, receive, send)
