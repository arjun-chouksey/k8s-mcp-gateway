from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.web_sessions import SESSION_COOKIE, SessionActor, resolve_session


async def database(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessions() as session:
        yield session


async def current_actor(
    db: AsyncSession = Depends(database),
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> SessionActor:
    actor = await resolve_session(db, token)
    if actor is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return actor


async def require_admin(actor: SessionActor = Depends(current_actor)) -> SessionActor:
    if actor.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required")
    return actor


def require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin", "").rstrip("/")
    if origin != request.app.state.settings.allowed_origin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-origin request denied")
