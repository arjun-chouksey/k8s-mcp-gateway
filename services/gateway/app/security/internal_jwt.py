from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.security.api_keys import ApiKeyActor
from app.security.web_sessions import SessionActor


def mint_internal_jwt(actor: SessionActor, secret: str, ttl_seconds: int = 300) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": str(actor.id), "aud": "gateway-mcp", "iss": "platform-chat",
        "iat": now, "exp": now + timedelta(seconds=ttl_seconds), "channel": "chat",
    }, secret, algorithm="HS256")


async def authenticate_internal_jwt(
    db: AsyncSession, token: str, secret: str,
) -> ApiKeyActor | None:
    try:
        claims = jwt.decode(
            token, secret, algorithms=["HS256"], audience="gateway-mcp",
            issuer="platform-chat", options={"require": ["sub", "aud", "iss", "iat", "exp"]},
        )
        if claims.get("channel") != "chat":
            return None
        user_id = UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
    user = await db.scalar(select(User).where(User.id == user_id, User.active.is_(True)))
    if user is None:
        return None
    return ApiKeyActor(
        id=user.id, email=user.email, role=user.role, key_id=None, channel="chat",
    )
