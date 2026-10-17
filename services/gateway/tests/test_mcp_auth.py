from __future__ import annotations

import pytest
import httpx
from sqlalchemy import select, update

from app.database import make_engine, make_session_factory
from app.main import create_app
from app.models import ApiKey, User
from test_api_keys import (
    ADMIN_EMAIL, ADMIN_PASSWORD, MEMBER_EMAIL, MEMBER_PASSWORD, ORIGIN,
    create_users, database_url, clean_identity_tables, login, settings,
)


@pytest.mark.asyncio
async def test_every_mcp_request_rechecks_key_and_revocation_is_immediate(database_url: str):
    _, member_id = await create_users(database_url)
    app = create_app(settings(database_url))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as admin:
            await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
            admin_key = (await admin.post(
                "/api/keys", json={"name": "Admin MCP"}, headers={"Origin": ORIGIN},
            )).json()
            member_key = (await admin.post(
                f"/api/members/{member_id}/keys", json={"name": "Member MCP"},
                headers={"Origin": ORIGIN},
            )).json()

            assert (await admin.post("/mcp")).status_code == 401
            assert (await admin.post(
                "/mcp", headers={"Authorization": "Bearer malformed"},
            )).status_code == 401
            valid_member = await admin.post(
                "/mcp", headers={"Authorization": f"Bearer {member_key['key']}"},
            )
            assert valid_member.status_code != 401

            engine = make_engine(database_url)
            sessions = make_session_factory(engine)
            async with sessions() as db:
                used = await db.scalar(select(ApiKey).where(ApiKey.id == member_key["id"]))
                assert used is not None and used.last_used_at is not None
            await engine.dispose()

            revoked = await admin.delete(
                f"/api/members/{member_id}/keys/{member_key['id']}", headers={"Origin": ORIGIN},
            )
            assert revoked.status_code == 204
            assert (await admin.post(
                "/mcp", headers={"Authorization": f"Bearer {member_key['key']}"},
            )).status_code == 401
            assert (await admin.post(
                "/mcp", headers={"Authorization": f"Bearer {admin_key['key']}"},
            )).status_code != 401

            inactive_key = (await admin.post(
                f"/api/members/{member_id}/keys", json={"name": "Inactive member"},
                headers={"Origin": ORIGIN},
            )).json()
            engine = make_engine(database_url)
            sessions = make_session_factory(engine)
            async with sessions() as db:
                await db.execute(update(User).where(User.id == member_id).values(active=False))
                await db.commit()
            await engine.dispose()
            assert (await admin.post(
                "/mcp", headers={"Authorization": f"Bearer {inactive_key['key']}"},
            )).status_code == 401
