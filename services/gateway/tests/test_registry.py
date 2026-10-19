from __future__ import annotations

import os
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
from app.models import Upstream, UpstreamTool, User, WebSession
from app.security.upstream_crypto import CredentialCipher
from app.security.web_sessions import hash_password
from app.settings import AppSettings


ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "correct horse battery staple"
MEMBER_EMAIL = "member@example.test"
MEMBER_PASSWORD = "another correct horse battery staple"
ORIGIN = "http://app.test"
FERNET_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


@pytest.fixture(scope="module")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for registry tests")
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
        await db.execute(delete(Upstream))
        await db.execute(delete(WebSession))
        await db.execute(delete(User))
        await db.commit()
    await engine.dispose()


def settings(database_url: str) -> AppSettings:
    return AppSettings(
        database_url=database_url, allowed_origin=ORIGIN, cookie_secure=False,
        api_key_pepper="test-pepper-that-is-at-least-32-characters",
        upstream_credential_key=FERNET_KEY,
        internal_jwt_secret="test-internal-jwt-secret-at-least-32-characters",
        session_ttl_seconds=3600, invite_ttl_seconds=3600,
        login_max_failures=5, login_window_seconds=300,
    )


async def create_users(database_url: str) -> None:
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        db.add(User(
            email=MEMBER_EMAIL, password_hash=hash_password(MEMBER_PASSWORD),
            role="member", active=True,
        ))
        await db.commit()
    await engine.dispose()


async def login(client: httpx.AsyncClient, email: str, password: str) -> None:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def server_payload(**overrides):
    payload = {
        "slug": "currency", "display_name": "Currency MCP",
        "url": "http://currency-mcp.mcp.svc.cluster.local:8000/mcp",
        "auth_type": "bearer", "credential": "first-upstream-secret",
        "enabled": True, "connect_timeout_ms": 3000, "call_timeout_ms": 20000,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_admin_crud_encrypts_and_redacts_credentials(database_url: str):
    await create_users(database_url)
    app = create_app(settings(database_url))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as admin:
        await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
        created = await admin.post(
            "/api/servers", json=server_payload(), headers={"Origin": ORIGIN},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["slug"] == "currency" and body["status"] == "checking"
        assert body["has_credential"] is True
        assert "credential" not in body and "credential_ciphertext" not in body
        assert "first-upstream-secret" not in created.text
        server_id = body["id"]

        engine = make_engine(database_url)
        sessions = make_session_factory(engine)
        async with sessions() as db:
            stored = await db.scalar(select(Upstream).where(Upstream.id == server_id))
            assert stored is not None and stored.credential_ciphertext is not None
            assert b"first-upstream-secret" not in stored.credential_ciphertext
            assert CredentialCipher(FERNET_KEY).decrypt(stored.credential_ciphertext) == "first-upstream-secret"
            db.add(UpstreamTool(
                upstream_id=stored.id, original_name="convert_currency",
                public_alias="currency__convert_currency", description="Convert an amount",
                input_schema={"type": "object"}, output_schema=None,
                annotations={"readOnlyHint": True}, definition_hash="a" * 64,
            ))
            await db.commit()
        await engine.dispose()

        tools = await admin.get(f"/api/servers/{server_id}/tools")
        assert tools.status_code == 200
        assert tools.json() == [{
            "public_alias": "currency__convert_currency",
            "original_name": "convert_currency", "description": "Convert an amount",
            "input_schema": {"type": "object"}, "output_schema": None,
            "annotations": {"readOnlyHint": True},
        }]
        assert "credential" not in tools.text
        assert (await admin.get(f"/api/servers/00000000-0000-0000-0000-000000000000/tools")).status_code == 404

        replaced = await admin.patch(
            f"/api/servers/{server_id}",
            json={"credential_action": "set", "credential": "replacement-secret"},
            headers={"Origin": ORIGIN},
        )
        assert replaced.status_code == 200 and replaced.json()["has_credential"] is True
        disabled = await admin.patch(
            f"/api/servers/{server_id}", json={"enabled": False}, headers={"Origin": ORIGIN},
        )
        assert disabled.status_code == 200 and disabled.json()["status"] == "disabled"
        enabled = await admin.patch(
            f"/api/servers/{server_id}", json={"enabled": True}, headers={"Origin": ORIGIN},
        )
        assert enabled.status_code == 200 and enabled.json()["status"] == "checking"
        cleared = await admin.patch(
            f"/api/servers/{server_id}",
            json={"auth_type": "none", "credential_action": "clear"},
            headers={"Origin": ORIGIN},
        )
        assert cleared.status_code == 200 and cleared.json()["has_credential"] is False
        assert (await admin.patch(
            f"/api/servers/{server_id}", json={"slug": "changed"}, headers={"Origin": ORIGIN},
        )).status_code == 422
        assert (await admin.delete(
            f"/api/servers/{server_id}", headers={"Origin": ORIGIN},
        )).status_code == 204
        assert (await admin.get("/api/servers")).json() == []
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_member_read_only_duplicate_slug_and_ssrf_denied(database_url: str):
    await create_users(database_url)
    app = create_app(settings(database_url))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as admin:
        await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert (await admin.post(
            "/api/servers", json=server_payload(), headers={"Origin": ORIGIN},
        )).status_code == 201
        assert (await admin.post(
            "/api/servers", json=server_payload(), headers={"Origin": ORIGIN},
        )).status_code == 409
        metadata = await admin.post(
            "/api/servers", json=server_payload(
                slug="metadata", display_name="Metadata",
                url="https://169.254.169.254/latest/meta-data",
            ), headers={"Origin": ORIGIN},
        )
        assert metadata.status_code == 422

    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as member:
        await login(member, MEMBER_EMAIL, MEMBER_PASSWORD)
        listed = await member.get("/api/servers")
        assert listed.status_code == 200 and listed.json()[0]["has_credential"] is True
        assert "credential" not in listed.json()[0]
        assert "credential_ciphertext" not in listed.json()[0]
        assert "first-upstream-secret" not in listed.text
        denied = await member.post(
            "/api/servers", json=server_payload(slug="policy"), headers={"Origin": ORIGIN},
        )
        assert denied.status_code == 403
    await app.state.engine.dispose()
