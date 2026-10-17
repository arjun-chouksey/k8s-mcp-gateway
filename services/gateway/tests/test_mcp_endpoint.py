from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import socket

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server import MCPServer
from mcp.shared.exceptions import MCPError
import pytest
from sqlalchemy import select
import uvicorn

from app.database import make_engine, make_session_factory
from app.main import create_app
from app.models import ApiKey, Upstream, UpstreamTool, User
from app.security.api_keys import api_key_digest, parse_public_prefix
from app.security.web_sessions import hash_password
from app.settings import AppSettings
from _catalog_support import catalog_database_url, clean_catalog


PEPPER = b"test-pepper-that-is-at-least-32-characters"
FERNET_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
API_KEY = "mcpgw_abcdef123456_" + "a" * 43


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
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await task


def upstream_app():
    server = MCPServer("endpoint-upstream", version="0.1.0")

    @server.tool()
    async def echo(value: str) -> str:
        """Return a value through the gateway."""
        return value

    return server.streamable_http_app(stateless_http=True)


def settings(database_url: str) -> AppSettings:
    return AppSettings(
        database_url=database_url, allowed_origin="http://app.test", cookie_secure=False,
        api_key_pepper=PEPPER.decode(), upstream_credential_key=FERNET_KEY,
        internal_jwt_secret="test-internal-jwt-secret-at-least-32-characters",
        upstream_refresh_seconds=3600,
    )


@pytest.mark.asyncio
async def test_external_client_lists_calls_and_stale_disabled_alias_is_rejected(
    catalog_database_url: str,
):
    async with serve(upstream_app()) as upstream_base:
        engine = make_engine(catalog_database_url)
        sessions = make_session_factory(engine)
        async with sessions() as db:
            user = User(
                email="external@example.test", password_hash=hash_password("password long enough"),
                role="member", active=True,
            )
            upstream = Upstream(
                slug="probe", display_name="Probe", url=f"{upstream_base}/mcp",
                auth_type="none", enabled=True, status="connected",
                connect_timeout_ms=500, call_timeout_ms=500,
            )
            db.add_all([user, upstream])
            await db.flush()
            prefix = parse_public_prefix(API_KEY)
            assert prefix is not None
            key = ApiKey(
                user_id=user.id, prefix=prefix, key_digest=api_key_digest(API_KEY, PEPPER),
                name="External client",
            )
            db.add_all([key, UpstreamTool(
                upstream_id=upstream.id, original_name="echo", public_alias="probe__echo",
                description="Echo", input_schema={
                    "type": "object", "properties": {"value": {"type": "string"}},
                    "required": ["value"], "additionalProperties": False,
                }, output_schema=None, annotations=None, definition_hash="b" * 64,
            )])
            await db.commit()
            upstream_id, key_id = upstream.id, key.id
        await engine.dispose()

        gateway = create_app(settings(catalog_database_url))
        async with serve(gateway) as gateway_base:
            async with httpx2.AsyncClient(
                headers={"Authorization": f"Bearer {API_KEY}"}, trust_env=False,
            ) as http:
                async with Client(
                    streamable_http_client(f"{gateway_base}/mcp", http_client=http),
                    read_timeout_seconds=2,
                ) as client:
                    listed = await client.list_tools(cache_mode="reload")
                    assert [tool.name for tool in listed.tools] == ["probe__echo"]
                    called = await client.call_tool("probe__echo", {"value": "through-gateway"})
                    assert called.is_error is False
                    assert called.content[0].text == "through-gateway"

                    engine = make_engine(catalog_database_url)
                    sessions = make_session_factory(engine)
                    async with sessions() as db:
                        current = await db.get(Upstream, upstream_id)
                        current.enabled = False
                        current.status = "disabled"
                        await db.commit()
                    await engine.dispose()
                    assert (await client.list_tools(cache_mode="reload")).tools == []
                    with pytest.raises(MCPError, match="disabled"):
                        await client.call_tool("probe__echo", {"value": "stale"})

            async with httpx2.AsyncClient(trust_env=False) as raw:
                denied = await raw.post(
                    f"{gateway_base}/mcp", headers={"Authorization": "Bearer invalid"},
                )
                assert denied.status_code == 401
                wrong_host = await raw.post(
                    f"{gateway_base}/mcp",
                    headers={"Authorization": f"Bearer {API_KEY}", "Host": "evil.example"},
                )
                assert wrong_host.status_code in {400, 421}

                engine = make_engine(catalog_database_url)
                sessions = make_session_factory(engine)
                async with sessions() as db:
                    record = await db.get(ApiKey, key_id)
                    from datetime import datetime, timezone
                    record.revoked_at = datetime.now(timezone.utc)
                    await db.commit()
                await engine.dispose()
                revoked = await raw.post(
                    f"{gateway_base}/mcp", headers={"Authorization": f"Bearer {API_KEY}"},
                )
                assert revoked.status_code == 401
