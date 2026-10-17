from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.database import make_engine, make_session_factory
from app.models import User
from app.security.internal_jwt import authenticate_internal_jwt
from app.security.web_sessions import hash_password
from _catalog_support import catalog_database_url, clean_catalog


SECRET = "test-internal-jwt-secret-at-least-32-characters"


@pytest.mark.asyncio
async def test_internal_jwt_requires_issuer_audience_expiry_channel_and_active_user(
    catalog_database_url: str,
):
    engine = make_engine(catalog_database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        user = User(
            email="chat@example.test", password_hash=hash_password("password long enough"),
            role="member", active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        now = datetime.now(timezone.utc)
        claims = {
            "sub": str(user.id), "aud": "gateway-mcp", "iss": "platform-chat",
            "iat": now, "exp": now + timedelta(minutes=3), "channel": "chat",
        }
        token = jwt.encode(claims, SECRET, algorithm="HS256")
        actor = await authenticate_internal_jwt(db, token, SECRET)
        assert actor is not None and actor.id == user.id and actor.channel == "chat"
        assert await authenticate_internal_jwt(
            db, jwt.encode({**claims, "aud": "wrong"}, SECRET, algorithm="HS256"), SECRET,
        ) is None
        assert await authenticate_internal_jwt(
            db, jwt.encode({**claims, "channel": "mcp"}, SECRET, algorithm="HS256"), SECRET,
        ) is None
        user.active = False
        await db.commit()
        assert await authenticate_internal_jwt(db, token, SECRET) is None
    await engine.dispose()
