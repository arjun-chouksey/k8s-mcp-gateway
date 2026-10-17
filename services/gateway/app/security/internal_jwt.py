from __future__ import annotations

from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.security.api_keys import ApiKeyActor


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
