from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, update

from app.bootstrap_admin import bootstrap_admin
from app.database import make_engine, make_session_factory
from app.main import create_app
from app.models import User, WebSession
from app.settings import AppSettings


ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "correct horse battery staple"


@pytest.fixture(scope="module")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for session tests")
    root = Path(__file__).parents[1]
    config = Config(root / "alembic.ini")
    config.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = url
    command.upgrade(config, "head")
    return url


@pytest_asyncio.fixture(autouse=True)
async def clean_identity_tables(database_url: str):
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        await db.execute(delete(WebSession))
        await db.execute(delete(User))
        await db.commit()
    await engine.dispose()


def settings(database_url: str, **overrides) -> AppSettings:
    values = dict(
        database_url=database_url, allowed_origin="http://app.test",
        cookie_secure=False, session_ttl_seconds=3600,
        login_max_failures=2, login_window_seconds=300,
    )
    values.update(overrides)
    return AppSettings(**values)


@pytest.mark.asyncio
async def test_bootstrap_once_login_me_origin_guard_and_logout(database_url: str):
    assert await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url) == "admin-created"
    assert await bootstrap_admin("other@example.test", "different long password", database_url) == "existing-admin-preserved"

    app = create_app(settings(database_url))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://app.test") as client:
        login = await client.post("/api/auth/login", json={"email": ADMIN_EMAIL.upper(), "password": ADMIN_PASSWORD})
        assert login.status_code == 200
        assert login.json()["role"] == "admin"
        assert "password" not in login.text and "session" not in login.json()
        cookie = login.headers["set-cookie"]
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie

        me = await client.get("/api/me")
        assert me.status_code == 200 and me.json()["email"] == ADMIN_EMAIL

        blocked = await client.post("/api/auth/logout", headers={"Origin": "https://evil.example"})
        assert blocked.status_code == 403
        assert (await client.get("/api/me")).status_code == 200

        logout = await client.post("/api/auth/logout", headers={"Origin": "http://app.test"})
        assert logout.status_code == 204
        assert (await client.get("/api/me")).status_code == 401
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_invalid_credentials_throttle_inactive_users_and_secure_cookie(database_url: str):
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)
    app = create_app(settings(database_url, cookie_secure=True))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://app.test") as client:
        for _ in range(2):
            denied = await client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong password"})
            assert denied.status_code == 401
        throttled = await client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert throttled.status_code == 429
    await app.state.engine.dispose()

    active_app = create_app(settings(database_url))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=active_app), base_url="http://app.test") as client:
        login = await client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert login.status_code == 200
        engine = make_engine(database_url)
        sessions = make_session_factory(engine)
        async with sessions() as db:
            await db.execute(update(User).values(active=False))
            await db.commit()
        await engine.dispose()
        assert (await client.get("/api/me")).status_code == 401
    await active_app.state.engine.dispose()

    secure_app = create_app(settings(database_url, cookie_secure=True, login_max_failures=5))
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        await db.execute(update(User).values(active=True))
        await db.commit()
    await engine.dispose()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=secure_app), base_url="https://app.test") as client:
        response = await client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert response.status_code == 200 and "Secure" in response.headers["set-cookie"]
    await secure_app.state.engine.dispose()
