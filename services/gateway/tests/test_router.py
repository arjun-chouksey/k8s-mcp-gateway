from __future__ import annotations

from mcp.types import CallToolResult, TextContent
import pytest
from sqlalchemy import select

from app.database import make_engine, make_session_factory
from app.mcp_gateway.catalog import CatalogService
from app.mcp_gateway.router import GatewayRouter
from app.models import Upstream, UpstreamTool, User
from app.security.api_keys import ApiKeyActor
from app.security.upstream_crypto import CredentialCipher
from app.security.web_sessions import hash_password
from _catalog_support import catalog_database_url, clean_catalog


KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


class FakeAdapter:
    calls = []

    def __init__(self, config, credential):
        self.config, self.credential = config, credential

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments, self.credential))
        return CallToolResult(content=[TextContent(type="text", text="called")])


async def setup_router(url: str):
    engine = make_engine(url)
    sessions = make_session_factory(engine)
    cipher = CredentialCipher(KEY)
    async with sessions() as db:
        user = User(
            email="router@example.test", password_hash=hash_password("password long enough"),
            role="member", active=True,
        )
        upstream = Upstream(
            slug="currency", display_name="Currency", url="https://currency.example.test/mcp",
            auth_type="bearer", credential_ciphertext=cipher.encrypt("upstream-only"),
            enabled=True, status="connected", connect_timeout_ms=100, call_timeout_ms=100,
        )
        db.add_all([user, upstream])
        await db.flush()
        db.add(UpstreamTool(
            upstream_id=upstream.id, original_name="convert_currency",
            public_alias="currency__convert_currency", description="Convert amount",
            input_schema={
                "type": "object", "properties": {"amount": {"type": "number"}},
                "required": ["amount"], "additionalProperties": False,
            }, output_schema=None, annotations=None, definition_hash="a" * 64,
        ))
        await db.commit()
        actor = ApiKeyActor(user.id, user.email, user.role, None, "mcp")
        upstream_id = upstream.id
    catalog = CatalogService(sessions, cipher)
    router = GatewayRouter(sessions, catalog, cipher, adapter_factory=FakeAdapter)
    return engine, sessions, router, actor, upstream_id


@pytest.mark.asyncio
async def test_list_is_cached_and_call_uses_exact_original_name(catalog_database_url: str):
    FakeAdapter.calls.clear()
    engine, _sessions, router, actor, _ = await setup_router(catalog_database_url)
    tools = await router.list_tools(actor)
    assert [tool.name for tool in tools] == ["currency__convert_currency"]
    result = await router.call_tool(actor, tools[0].name, {"amount": 10})
    assert result.is_error is False
    assert FakeAdapter.calls == [("convert_currency", {"amount": 10}, "upstream-only")]
    await engine.dispose()


@pytest.mark.asyncio
async def test_bad_schema_unknown_alias_and_disabled_stale_call_are_rejected(catalog_database_url: str):
    from mcp.shared.exceptions import MCPError

    FakeAdapter.calls.clear()
    engine, sessions, router, actor, upstream_id = await setup_router(catalog_database_url)
    with pytest.raises(MCPError, match="Arguments do not match"):
        await router.call_tool(actor, "currency__convert_currency", {"amount": "ten"})
    with pytest.raises(MCPError, match="Unknown tool"):
        await router.call_tool(actor, "currency__missing", {})
    async with sessions() as db:
        upstream = await db.get(Upstream, upstream_id)
        upstream.enabled = False
        upstream.status = "disabled"
        await db.commit()
    with pytest.raises(MCPError, match="disabled"):
        await router.call_tool(actor, "currency__convert_currency", {"amount": 10})
    assert FakeAdapter.calls == []
    await engine.dispose()
