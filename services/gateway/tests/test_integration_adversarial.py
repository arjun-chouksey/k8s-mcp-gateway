from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import socket
from uuid import UUID

import httpx
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server import MCPServer
from mcp.shared.exceptions import MCPError
import pytest
from sqlalchemy import select
import uvicorn

from app.bootstrap_admin import bootstrap_admin
from app.database import make_engine, make_session_factory
from app.main import create_app
from app.models import ApiKey, AuditEvent, Upstream, User
from app.security.api_keys import issue_api_key
from app.security.web_sessions import hash_password
from app.settings import AppSettings
from _catalog_support import catalog_database_url, clean_catalog


ORIGIN = "http://app.test"
ADMIN_EMAIL = "integration-admin@example.test"
ADMIN_PASSWORD = "integration admin password"
PEPPER = "integration-pepper-that-is-at-least-32-characters"
FERNET_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


@asynccontextmanager
async def serve(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(
        app, log_level="critical", lifespan="on", timeout_graceful_shutdown=1,
    ))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    while not server.started:
        await asyncio.sleep(0.01)
    async def stop() -> None:
        if task.done():
            return
        server.should_exit = True
        await task
    try:
        yield f"http://127.0.0.1:{port}", port, stop
    finally:
        await stop()


def upstream_app(name: str, calls: dict[str, int], headers: list[str | None]):
    server = MCPServer(name, version="0.1.0")

    @server.tool()
    async def shared(value: str) -> str:
        """Return the upstream identity and supplied value."""
        calls["shared"] += 1
        return f"{name}:{value}"

    @server.tool()
    async def write_once(value: str) -> str:
        """Perform one deliberately slow write for timeout verification."""
        calls["write_once"] += 1
        await asyncio.sleep(0.35)
        return value

    mcp_app = server.streamable_http_app(stateless_http=True)

    async def capture(scope, receive, send):
        if scope["type"] == "http":
            raw = dict(scope.get("headers", []))
            authorization = raw.get(b"authorization")
            headers.append(authorization.decode() if authorization else None)
        await mcp_app(scope, receive, send)

    capture.router = mcp_app.router
    return capture


def settings(database_url: str, ports: tuple[int, ...]) -> AppSettings:
    return AppSettings(
        database_url=database_url, allowed_origin=ORIGIN, cookie_secure=False,
        api_key_pepper=PEPPER, upstream_credential_key=FERNET_KEY,
        internal_jwt_secret="integration-internal-jwt-secret-32-chars",
        upstream_refresh_seconds=3600,
        upstream_internal_allowlist=tuple(f"127.0.0.1:{port}" for port in ports),
    )


async def seed_identities(database_url: str) -> tuple[str, str]:
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        admin = await db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        member = User(
            email="integration-member@example.test",
            password_hash=hash_password("integration member password"),
            role="member", active=True,
        )
        db.add(member)
        await db.flush()
        admin_key = await issue_api_key(db, admin.id, "Admin integration", PEPPER.encode())
        member_key = await issue_api_key(db, member.id, "Member integration", PEPPER.encode())
        assert admin_key and member_key
    await engine.dispose()
    return admin_key.plaintext, member_key.plaintext


async def login(client: httpx.AsyncClient, email: str, password: str) -> None:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


async def wait_for_server(client: httpx.AsyncClient, slug: str, status: str) -> dict:
    for _ in range(100):
        response = await client.get("/api/servers")
        response.raise_for_status()
        match = next((item for item in response.json() if item["slug"] == slug), None)
        if match and match["status"] == status:
            return match
        await asyncio.sleep(0.03)
    raise AssertionError(f"{slug} did not reach {status}")


async def add_server(
    client: httpx.AsyncClient, slug: str, base_url: str, *, credential: str | None = None,
) -> dict:
    response = await client.post("/api/servers", headers={"Origin": ORIGIN}, json={
        "slug": slug, "display_name": slug.title(), "url": f"{base_url}/mcp",
        "auth_type": "bearer" if credential else "none", "credential": credential,
        "connect_timeout_ms": 300, "call_timeout_ms": 100,
    })
    assert response.status_code == 201, response.text
    return await wait_for_server(client, slug, "connected")


@asynccontextmanager
async def mcp_client(gateway_url: str, key: str):
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {key}"}, trust_env=False,
    ) as http:
        async with Client(
            streamable_http_client(f"{gateway_url}/mcp", http_client=http),
            read_timeout_seconds=2,
        ) as client:
            yield client


@pytest.mark.asyncio
async def test_real_mcp_lifecycle_adversarial_failures_and_audit(catalog_database_url: str):
    test_started_at = datetime.now(timezone.utc)
    alpha_calls = {"shared": 0, "write_once": 0}
    beta_calls = {"shared": 0, "write_once": 0}
    alpha_headers: list[str | None] = []
    beta_headers: list[str | None] = []
    async with serve(upstream_app("alpha", alpha_calls, alpha_headers)) as (alpha_url, alpha_port, _alpha_stop), \
            serve(upstream_app("beta", beta_calls, beta_headers)) as (beta_url, beta_port, beta_stop):
        admin_key, member_key = await seed_identities(catalog_database_url)
        gateway = create_app(settings(catalog_database_url, (alpha_port, beta_port)))
        async with serve(gateway) as (gateway_url, _gateway_port, _gateway_stop):
            async with httpx.AsyncClient(base_url=gateway_url) as admin, \
                    httpx.AsyncClient(base_url=gateway_url) as member:
                await login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
                await login(member, "integration-member@example.test", "integration member password")

                assert (await member.post("/api/servers", headers={"Origin": ORIGIN}, json={
                    "slug": "forbidden", "display_name": "Forbidden",
                    "url": f"{alpha_url}/mcp", "auth_type": "none",
                })).status_code == 403
                rejected = await admin.post("/api/servers", headers={"Origin": ORIGIN}, json={
                    "slug": "metadata", "display_name": "Metadata",
                    "url": "https://169.254.169.254/latest/meta-data", "auth_type": "none",
                })
                assert rejected.status_code == 422

                alpha = await add_server(admin, "alpha", alpha_url, credential="upstream-only")
                beta = await add_server(admin, "beta", beta_url)
                edited = await admin.patch(
                    f"/api/servers/{beta['id']}", headers={"Origin": ORIGIN},
                    json={"display_name": "Beta edited"},
                )
                assert edited.status_code == 200
                await wait_for_server(admin, "beta", "connected")

                async with mcp_client(gateway_url, member_key) as client:
                    listed = await client.list_tools(cache_mode="reload")
                    aliases = {tool.name for tool in listed.tools}
                    assert {"alpha__shared", "beta__shared", "alpha__write_once", "beta__write_once"} <= aliases
                    # Listing is served from PostgreSQL; no new upstream request is made.
                    header_count = len(alpha_headers) + len(beta_headers)
                    await client.list_tools(cache_mode="reload")
                    assert len(alpha_headers) + len(beta_headers) == header_count

                    first, second = await asyncio.gather(
                        client.call_tool("alpha__shared", {"value": "one"}),
                        client.call_tool("beta__shared", {"value": "two"}),
                    )
                    assert first.content[0].text == "alpha:one"
                    assert second.content[0].text == "beta:two"
                    assert any(value == "Bearer upstream-only" for value in alpha_headers)
                    assert all(value != f"Bearer {member_key}" for value in alpha_headers + beta_headers)

                    with pytest.raises(MCPError, match="Arguments do not match"):
                        await client.call_tool("alpha__shared", {"value": 7})
                    timed_out = await client.call_tool("alpha__write_once", {"value": "single"})
                    assert timed_out.is_error is True
                    assert "not retried" in timed_out.content[0].text
                    await asyncio.sleep(0.4)
                    assert alpha_calls["write_once"] == 1

                    await beta_stop()
                    await gateway.state.catalog.refresh_upstream(UUID(beta["id"]))
                    unreachable = await wait_for_server(admin, "beta", "unreachable")
                    assert unreachable["last_error"] in {
                        "upstream could not be reached",
                        "upstream returned an invalid MCP response",
                    }
                    loop = asyncio.get_running_loop()
                    started = loop.time()
                    cached = await client.list_tools(cache_mode="reload")
                    assert loop.time() - started < 1
                    assert "alpha__shared" in {tool.name for tool in cached.tools}
                    dead = await client.call_tool("beta__shared", {"value": "dead"})
                    assert dead.is_error is True and "currently unreachable" in dead.content[0].text
                    assert (await client.call_tool("alpha__shared", {"value": "still-up"})).is_error is False

                    disabled = await admin.patch(
                        f"/api/servers/{beta['id']}", headers={"Origin": ORIGIN},
                        json={"enabled": False},
                    )
                    assert disabled.status_code == 200
                    assert "beta__shared" not in {
                        tool.name for tool in (await client.list_tools(cache_mode="reload")).tools
                    }
                    with pytest.raises(MCPError, match="disabled"):
                        await client.call_tool("beta__shared", {"value": "stale"})

                engine = make_engine(catalog_database_url)
                sessions = make_session_factory(engine)
                async with sessions() as db:
                    key = await db.scalar(select(ApiKey).where(ApiKey.name == "Member integration"))
                    key.revoked_at = datetime.now(timezone.utc)
                    await db.commit()
                await engine.dispose()
                async with httpx.AsyncClient() as raw:
                    revoked = await raw.post(
                        f"{gateway_url}/mcp", headers={"Authorization": f"Bearer {member_key}"},
                    )
                    assert revoked.status_code == 401

                assert (await admin.delete(
                    f"/api/servers/{beta['id']}", headers={"Origin": ORIGIN},
                )).status_code == 204
                assert all(item["slug"] != "beta" for item in (await admin.get("/api/servers")).json())

        engine = make_engine(catalog_database_url)
        sessions = make_session_factory(engine)
        async with sessions() as db:
            events = list(await db.scalars(
                select(AuditEvent).where(
                    AuditEvent.started_at >= test_started_at,
                    AuditEvent.public_tool.in_((
                        "alpha__shared", "alpha__write_once", "beta__shared",
                    ))
                ).order_by(AuditEvent.started_at)
            ))
        await engine.dispose()
        assert {event.outcome for event in events} >= {"ok", "denied", "timeout", "upstream_error"}
        assert all(event.user_id is not None and event.duration_ms >= 0 for event in events)
        assert not any(member_key in (event.error_summary or "") for event in events)
