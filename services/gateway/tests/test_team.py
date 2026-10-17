from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from alembic import command
from alembic.config import Config
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update

from app.bootstrap_admin import bootstrap_admin
from app.database import make_engine, make_session_factory
from app.main import create_app
from app.models import ApiKey, Invite, User, WebSession
from app.security.web_sessions import session_digest
from app.settings import AppSettings


ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "correct horse battery staple"
MEMBER_EMAIL = "member@example.test"
MEMBER_PASSWORD = "another correct horse battery staple"
ORIGIN = "http://app.test"


@pytest.fixture(scope="module")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for team tests")
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
        await db.execute(delete(Invite))
        await db.execute(delete(WebSession))
        await db.execute(delete(User))
        await db.commit()
    await engine.dispose()


def settings(database_url: str) -> AppSettings:
    return AppSettings(
        database_url=database_url, allowed_origin=ORIGIN, cookie_secure=False,
        api_key_pepper="test-pepper-that-is-at-least-32-characters",
        upstream_credential_key="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        session_ttl_seconds=3600, invite_ttl_seconds=3600,
        login_max_failures=5, login_window_seconds=300,
    )


async def login(client: httpx.AsyncClient, email: str, password: str) -> None:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


async def issue_invite(client: httpx.AsyncClient, email: str = MEMBER_EMAIL) -> httpx.Response:
    return await client.post(
        "/api/invites", json={"email": email, "role": "member"}, headers={"Origin": ORIGIN},
    )


def token_from(response: httpx.Response) -> str:
    return parse_qs(urlparse(response.json()["invite_url"]).query)["token"][0]


@pytest.mark.asyncio
async def test_admin_invite_accept_member_login_and_digest_only(database_url: str):
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)
    app = create_app(settings(database_url))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as admin:
        await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
        invitation = await issue_invite(admin)
        assert invitation.status_code == 201
        token = token_from(invitation)

        engine = make_engine(database_url)
        sessions = make_session_factory(engine)
        async with sessions() as db:
            stored = await db.scalar(select(Invite))
            assert stored is not None
            assert stored.token_digest == session_digest(token)
            assert token not in stored.token_digest
        await engine.dispose()

        accepted = await admin.post(
            "/api/invites/accept", json={"token": token, "password": MEMBER_PASSWORD},
        )
        assert accepted.status_code == 201
        assert accepted.json()["email"] == MEMBER_EMAIL
        assert accepted.json()["role"] == "member"
        assert (await admin.post(
            "/api/invites/accept", json={"token": token, "password": MEMBER_PASSWORD},
        )).status_code == 409

        members = await admin.get("/api/members")
        assert members.status_code == 200
        assert {entry["email"] for entry in members.json()} == {ADMIN_EMAIL, MEMBER_EMAIL}

    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as member:
        await login(member, MEMBER_EMAIL, MEMBER_PASSWORD)
        assert (await member.get("/api/me")).json()["role"] == "member"
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_expired_invite_and_invalid_role_are_denied(database_url: str):
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)
    app = create_app(settings(database_url))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as admin:
        await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert (await admin.post(
            "/api/invites", json={"email": MEMBER_EMAIL, "role": "owner"},
            headers={"Origin": ORIGIN},
        )).status_code == 422
        invitation = await issue_invite(admin)
        token = token_from(invitation)
        engine = make_engine(database_url)
        sessions = make_session_factory(engine)
        async with sessions() as db:
            await db.execute(update(Invite).values(
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
            ))
            await db.commit()
        await engine.dispose()
        expired = await admin.post(
            "/api/invites/accept", json={"token": token, "password": MEMBER_PASSWORD},
        )
        assert expired.status_code == 410
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_member_denied_and_deactivation_revokes_access(database_url: str):
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)
    app = create_app(settings(database_url))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as admin:
        await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
        invitation = await issue_invite(admin)
        accepted = await admin.post(
            "/api/invites/accept",
            json={"token": token_from(invitation), "password": MEMBER_PASSWORD},
        )
        member_id = accepted.json()["id"]
        admin_id = (await admin.get("/api/me")).json()["id"]

        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as member:
            await login(member, MEMBER_EMAIL, MEMBER_PASSWORD)
            assert (await member.get("/api/members")).status_code == 403
            assert (await member.post(
                "/api/invites", json={"email": "other@example.test"},
                headers={"Origin": ORIGIN},
            )).status_code == 403
            assert (await member.patch(
                f"/api/members/{admin_id}", json={"active": False},
                headers={"Origin": ORIGIN},
            )).status_code == 403

            engine = make_engine(database_url)
            sessions = make_session_factory(engine)
            async with sessions() as db:
                db.add(ApiKey(
                    user_id=member_id, prefix="test-member", key_digest="digest-only",
                    name="test key",
                ))
                await db.commit()
            await engine.dispose()

            deactivated = await admin.patch(
                f"/api/members/{member_id}", json={"active": False},
                headers={"Origin": ORIGIN},
            )
            assert deactivated.status_code == 200
            assert deactivated.json()["active"] is False
            assert (await member.get("/api/me")).status_code == 401
            assert (await member.post(
                "/api/auth/login", json={"email": MEMBER_EMAIL, "password": MEMBER_PASSWORD},
            )).status_code == 401

        final_admin = await admin.patch(
            f"/api/members/{admin_id}", json={"active": False}, headers={"Origin": ORIGIN},
        )
        assert final_admin.status_code == 409

        engine = make_engine(database_url)
        sessions = make_session_factory(engine)
        async with sessions() as db:
            key = await db.scalar(select(ApiKey).where(ApiKey.user_id == member_id))
            assert key is not None and key.revoked_at is not None
        await engine.dispose()
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_admin_mutations_require_exact_origin(database_url: str):
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)
    app = create_app(settings(database_url))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as admin:
        await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
        denied = await admin.post(
            "/api/invites", json={"email": MEMBER_EMAIL},
            headers={"Origin": "https://evil.example"},
        )
        assert denied.status_code == 403
    await app.state.engine.dispose()
