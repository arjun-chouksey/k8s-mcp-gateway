from __future__ import annotations

import os
import re
from pathlib import Path

from alembic import command
from alembic.config import Config
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.bootstrap_admin import bootstrap_admin
from app.database import make_engine, make_session_factory
from app.main import create_app
from app.models import ApiKey, User, WebSession
from app.security.api_keys import api_key_digest
from app.security.web_sessions import hash_password
from app.settings import AppSettings


ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "correct horse battery staple"
MEMBER_EMAIL = "member@example.test"
MEMBER_PASSWORD = "another correct horse battery staple"
ORIGIN = "http://app.test"
PEPPER = "test-pepper-that-is-at-least-32-characters"


@pytest.fixture(scope="module")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for API-key tests")
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
        await db.execute(delete(ApiKey))
        await db.execute(delete(WebSession))
        await db.execute(delete(User))
        await db.commit()
    await engine.dispose()


def settings(database_url: str) -> AppSettings:
    return AppSettings(
        database_url=database_url, allowed_origin=ORIGIN, cookie_secure=False,
        api_key_pepper=PEPPER, session_ttl_seconds=3600, invite_ttl_seconds=3600,
        upstream_credential_key="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        login_max_failures=5, login_window_seconds=300,
    )


async def create_users(database_url: str) -> tuple[str, str]:
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        member = User(
            email=MEMBER_EMAIL, password_hash=hash_password(MEMBER_PASSWORD),
            role="member", active=True,
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        admin_id = await db.scalar(select(User.id).where(User.email == ADMIN_EMAIL))
    await engine.dispose()
    assert admin_id is not None
    return str(admin_id), str(member.id)


async def login(client: httpx.AsyncClient, email: str, password: str) -> None:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_personal_key_is_shown_once_and_stored_as_hmac(database_url: str):
    _, member_id = await create_users(database_url)
    app = create_app(settings(database_url))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as member:
        await login(member, MEMBER_EMAIL, MEMBER_PASSWORD)
        created = await member.post(
            "/api/keys", json={"name": "Cursor laptop"}, headers={"Origin": ORIGIN},
        )
        assert created.status_code == 201
        plaintext = created.json()["key"]
        assert re.fullmatch(r"mcpgw_[a-f0-9]{12}_[A-Za-z0-9_-]{43}", plaintext)
        assert created.json()["user_id"] == member_id

        listed = await member.get("/api/keys")
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert "key" not in listed.json()[0] and "key_digest" not in listed.text

        engine = make_engine(database_url)
        sessions = make_session_factory(engine)
        async with sessions() as db:
            stored = await db.scalar(select(ApiKey))
            assert stored is not None
            assert stored.key_digest == api_key_digest(plaintext, PEPPER.encode())
            assert plaintext not in stored.key_digest
        await engine.dispose()
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_ownership_admin_issuance_and_role_guards(database_url: str):
    admin_id, member_id = await create_users(database_url)
    app = create_app(settings(database_url))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as admin:
        await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
        admin_key = await admin.post(
            "/api/keys", json={"name": "Admin key"}, headers={"Origin": ORIGIN},
        )
        issued_for_member = await admin.post(
            f"/api/members/{member_id}/keys", json={"name": "Member key"},
            headers={"Origin": ORIGIN},
        )
        assert admin_key.status_code == 201 and issued_for_member.status_code == 201

    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as member:
        await login(member, MEMBER_EMAIL, MEMBER_PASSWORD)
        forbidden = await member.post(
            f"/api/members/{admin_id}/keys", json={"name": "Forbidden"},
            headers={"Origin": ORIGIN},
        )
        assert forbidden.status_code == 403
        other_key = admin_key.json()["id"]
        hidden = await member.delete(f"/api/keys/{other_key}", headers={"Origin": ORIGIN})
        assert hidden.status_code == 404
        own_keys = await member.get("/api/keys")
        assert [entry["id"] for entry in own_keys.json()] == [issued_for_member.json()["id"]]
    await app.state.engine.dispose()
