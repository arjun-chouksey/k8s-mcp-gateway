from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.bootstrap_admin import bootstrap_admin
from app.database import make_engine, make_session_factory
from app.main import create_app
from app.models import AuditEvent, User, WebSession
from app.security.web_sessions import hash_password
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
        pytest.skip("TEST_DATABASE_URL is required for audit access tests")
    root = Path(__file__).parents[1]
    config = Config(root / "alembic.ini")
    config.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = url
    command.upgrade(config, "head")
    return url


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(database_url: str):
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        await db.execute(delete(AuditEvent))
        await db.execute(delete(WebSession))
        await db.execute(delete(User))
        await db.commit()
    await engine.dispose()


def settings(database_url: str) -> AppSettings:
    return AppSettings(
        database_url=database_url, allowed_origin=ORIGIN, cookie_secure=False,
        api_key_pepper="test-pepper-that-is-at-least-32-characters",
        upstream_credential_key="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        internal_jwt_secret="test-internal-jwt-secret-at-least-32-characters",
        session_ttl_seconds=3600, login_max_failures=5, login_window_seconds=300,
    )


async def seed(database_url: str) -> None:
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        member = User(
            email=MEMBER_EMAIL, password_hash=hash_password(MEMBER_PASSWORD),
            role="member", active=True,
        )
        other = User(
            email="other@example.test", password_hash=hash_password("other password long enough"),
            role="member", active=True,
        )
        db.add_all([member, other])
        await db.flush()
        now = datetime.now(timezone.utc)
        db.add_all([
            AuditEvent(
                request_id=uuid4(), user_id=member.id, api_key_id=None, channel="chat",
                server_slug="currency", public_tool="currency__rates",
                original_tool="rates", started_at=now, duration_ms=4,
                outcome="ok", error_summary=None,
            ),
            AuditEvent(
                request_id=uuid4(), user_id=other.id, api_key_id=None, channel="mcp",
                server_slug="weather", public_tool="weather__forecast",
                original_tool="forecast", started_at=now - timedelta(minutes=1),
                duration_ms=8, outcome="upstream_error", error_summary="Upstream unavailable",
            ),
        ])
        await db.commit()
    await engine.dispose()


async def login(client: httpx.AsyncClient, email: str, password: str) -> None:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_member_sees_only_own_audit_and_filters_are_validated(database_url: str):
    await seed(database_url)
    app = create_app(settings(database_url))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=ORIGIN,
    ) as member:
        await login(member, MEMBER_EMAIL, MEMBER_PASSWORD)
        page = await member.get("/api/audit", params={"server": "currency", "outcome": "ok"})
        assert page.status_code == 200
        assert page.json()["total"] == 1
        assert [item["server_slug"] for item in page.json()["items"]] == ["currency"]
        assert (await member.get("/api/audit", params={"outcome": "invalid"})).status_code == 422
        assert (await member.get("/api/audit", params={
            "started_after": "2026-10-19T00:00:00Z",
            "started_before": "2026-10-18T00:00:00Z",
        })).status_code == 422
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_admin_sees_all_rows_with_pagination(database_url: str):
    await seed(database_url)
    app = create_app(settings(database_url))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=ORIGIN,
    ) as admin:
        await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
        first = await admin.get("/api/audit", params={"limit": 1, "offset": 0})
        second = await admin.get("/api/audit", params={"limit": 1, "offset": 1})
        assert first.status_code == second.status_code == 200
        assert first.json()["total"] == second.json()["total"] == 2
        assert len(first.json()["items"]) == len(second.json()["items"]) == 1
        assert first.json()["items"][0]["id"] != second.json()["items"][0]["id"]
    await app.state.engine.dispose()
