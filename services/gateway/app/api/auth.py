from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.permissions import current_actor, database, require_same_origin
from app.security.web_sessions import (
    SESSION_COOKIE, LoginThrottle, SessionActor, create_session, revoke_session,
)
from app.settings import AppSettings


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class ActorResponse(BaseModel):
    id: str
    email: str
    role: str


def create_auth_router(
    settings: AppSettings,
    throttle: LoginThrottle | None = None,
) -> APIRouter:
    router = APIRouter()
    email_limiter = throttle or LoginThrottle(
        settings.login_max_failures, settings.login_window_seconds
    )
    ip_limiter = LoginThrottle(
        settings.login_max_failures * 5, settings.login_window_seconds
    )

    @router.post("/api/auth/login", response_model=ActorResponse)
    async def login(
        payload: LoginRequest, request: Request, response: Response,
        db: AsyncSession = Depends(database),
    ):
        client = request.client.host if request.client else "unknown"
        email_key = f"email:{payload.email.lower()}"
        ip_key = f"ip:{client}"
        if email_limiter.blocked(email_key) or ip_limiter.blocked(ip_key):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts")
        created = await create_session(db, payload.email, payload.password, settings.session_ttl_seconds)
        if created is None:
            email_limiter.failure(email_key)
            ip_limiter.failure(ip_key)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
        email_limiter.success(email_key)
        response.set_cookie(
            SESSION_COOKIE, created.token, max_age=settings.session_ttl_seconds,
            httponly=True, secure=settings.cookie_secure, samesite="lax", path="/",
        )
        return ActorResponse(id=str(created.actor.id), email=created.actor.email, role=created.actor.role)

    @router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    async def logout(
        request: Request, response: Response, db: AsyncSession = Depends(database),
        token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
        _current: SessionActor = Depends(current_actor),
    ) -> None:
        require_same_origin(request)
        assert token is not None
        await revoke_session(db, token)
        response.delete_cookie(SESSION_COOKIE, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax")

    @router.get("/api/me", response_model=ActorResponse)
    async def me(current: SessionActor = Depends(current_actor)) -> ActorResponse:
        return ActorResponse(id=str(current.id), email=current.email, role=current.role)

    return router
