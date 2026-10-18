from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from mcp.shared.exceptions import MCPError
from mcp.types import CallToolResult, TextContent
import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.database import make_engine, make_session_factory
from app.mcp_gateway.adapter import UpstreamTimeoutError
from app.mcp_gateway.catalog import CatalogService
from app.mcp_gateway.router import GatewayRouter
from app.models import ApiKey, AuditEvent, Upstream, UpstreamTool, User
from app.security.api_keys import ApiKeyActor
from app.security.upstream_crypto import CredentialCipher
from app.security.web_sessions import hash_password


KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


@pytest.fixture(scope="module")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for audit tests")
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
        await db.execute(delete(ApiKey))
        await db.execute(delete(Upstream))
        await db.execute(delete(User))
        await db.commit()
    await engine.dispose()


class ResultAdapter:
    result = CallToolResult(content=[TextContent(type="text", text="ok")])

    def __init__(self, _config, _credential):
        pass

    async def call_tool(self, _name, _arguments):
        return self.result


class TimeoutAdapter(ResultAdapter):
    async def call_tool(self, _name, _arguments):
        raise UpstreamTimeoutError("secret raw timeout details")


async def setup_router(database_url: str, adapter=ResultAdapter):
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    cipher = CredentialCipher(KEY)
    async with sessions() as db:
        user = User(
            email="audited@example.test", password_hash=hash_password("password long enough"),
            role="member", active=True,
        )
        upstream = Upstream(
            slug="currency", display_name="Currency", url="https://currency.example.test/mcp",
            auth_type="none", enabled=True, status="connected",
            connect_timeout_ms=100, call_timeout_ms=100,
        )
        db.add_all([user, upstream])
        await db.flush()
        api_key = ApiKey(
            user_id=user.id, prefix="123456789abc", key_digest="d" * 64, name="audit key",
        )
        db.add(api_key)
        db.add(UpstreamTool(
            upstream_id=upstream.id, original_name="convert_currency",
            public_alias="currency__convert_currency", description=None,
            input_schema={
                "type": "object", "properties": {"amount": {"type": "number"}},
                "required": ["amount"], "additionalProperties": False,
            }, output_schema=None, annotations=None, definition_hash="a" * 64,
        ))
        await db.commit()
        actor = ApiKeyActor(user.id, user.email, user.role, api_key.id, "mcp")
        upstream_id = upstream.id
    router = GatewayRouter(
        sessions, CatalogService(sessions, cipher), cipher, adapter_factory=adapter,
    )
    return engine, sessions, router, actor, upstream_id


@pytest.mark.asyncio
async def test_success_tool_error_and_timeout_are_attributed_without_arguments(database_url: str):
    engine, sessions, router, actor, _ = await setup_router(database_url)
    secret_argument = "customer-secret-value"
    await router.call_tool(actor, "currency__convert_currency", {"amount": 10})
    ResultAdapter.result = CallToolResult(
        isError=True, content=[TextContent(type="text", text=secret_argument)],
    )
    await router.call_tool(actor, "currency__convert_currency", {"amount": 20})
    router._adapter_factory = TimeoutAdapter
    await router.call_tool(actor, "currency__convert_currency", {"amount": 30})

    async with sessions() as db:
        events = (await db.scalars(select(AuditEvent).order_by(AuditEvent.started_at))).all()
    assert [event.outcome for event in events] == ["ok", "tool_error", "timeout"]
    assert all(event.user_id == actor.id and event.api_key_id == actor.key_id for event in events)
    assert all(event.channel == "mcp" and event.server_slug == "currency" for event in events)
    assert all(event.duration_ms >= 0 for event in events)
    assert secret_argument not in " ".join(event.error_summary or "" for event in events)
    assert events[-1].error_summary == "Upstream timed out"
    ResultAdapter.result = CallToolResult(content=[TextContent(type="text", text="ok")])
    await engine.dispose()


@pytest.mark.asyncio
async def test_denied_disabled_and_unknown_calls_are_audited(database_url: str):
    engine, sessions, router, actor, upstream_id = await setup_router(database_url)
    with pytest.raises(MCPError, match="Arguments do not match"):
        await router.call_tool(
            actor, "currency__convert_currency", {"amount": "private-value"},
        )
    async with sessions() as db:
        upstream = await db.get(Upstream, upstream_id)
        upstream.enabled = False
        upstream.status = "disabled"
        await db.commit()
    with pytest.raises(MCPError, match="disabled"):
        await router.call_tool(actor, "currency__convert_currency", {"amount": 1})
    with pytest.raises(MCPError, match="Unknown tool"):
        await router.call_tool(actor, "private-unknown-alias", {})

    async with sessions() as db:
        events = (await db.scalars(select(AuditEvent).order_by(AuditEvent.started_at))).all()
    assert [event.outcome for event in events] == ["denied", "denied", "denied"]
    assert events[0].error_summary == "Arguments do not match tool schema"
    assert events[1].error_summary == "Tool upstream is disabled"
    assert events[2].server_slug == "unknown"
    assert "private-value" not in " ".join(event.error_summary or "" for event in events)
    await engine.dispose()
