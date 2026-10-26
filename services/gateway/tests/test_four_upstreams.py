from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
import httpx
from mcp.types import CallToolResult, TextContent, Tool
from mcp.shared.exceptions import MCPError
import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.bootstrap_admin import bootstrap_admin
from app.bootstrap_upstream import UpstreamSeed, seed_upstream
from app.database import make_engine, make_session_factory
from app.main import create_app
from app.mcp_gateway.catalog import CatalogService
from app.mcp_gateway.adapter import UpstreamError
from app.mcp_gateway.router import GatewayRouter
from app.models import ApiKey, AuditEvent, Upstream, User, WebSession
from app.security.api_keys import ApiKeyActor
from app.security.upstream_crypto import CredentialCipher
from app.settings import AppSettings


ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "correct horse battery staple"
ORIGIN = "http://app.test"
KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
URLS = {
    "woo": "http://woocommerce-mcp.mcp.svc.cluster.local:8000/mcp",
    "currency": "http://currency-mcp.mcp.svc.cluster.local:8000/mcp",
    "policy": "http://policy-mcp.mcp.svc.cluster.local:8000/mcp",
    "analytics": "http://analytics-mcp.mcp.svc.cluster.local:8000/mcp",
}
TOOLS = {
    "woo": ["list_products", "create_product", "list_orders", "get_order", "update_order_status"],
    "currency": ["convert_currency", "get_demo_rates"],
    "policy": ["list_store_policies", "get_store_policy", "list_products"],
    "analytics": [
        "summarize_sales", "get_top_products", "get_order_status_breakdown",
        "calculate_sales_trend",
    ],
}


@pytest.fixture(scope="module")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for four-upstream tests")
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
        await db.execute(delete(WebSession))
        await db.execute(delete(User))
        await db.commit()
    await engine.dispose()


def settings(database_url: str) -> AppSettings:
    return AppSettings(
        database_url=database_url, allowed_origin=ORIGIN, cookie_secure=False,
        api_key_pepper="test-pepper-that-is-at-least-32-characters",
        upstream_credential_key=KEY,
        internal_jwt_secret="test-internal-jwt-secret-at-least-32-characters",
        session_ttl_seconds=3600, login_max_failures=5, login_window_seconds=300,
    )


class FourServerAdapter:
    unavailable: set[str] = set()

    def __init__(self, config, credential):
        self.slug = next(slug for slug, url in URLS.items() if url == config.url)
        assert credential == f"{self.slug}-secret"

    async def list_tools(self):
        if self.slug in self.unavailable:
            raise UpstreamError(f"{self.slug} unavailable")
        return [Tool(
            name=name, description=f"{self.slug} {name}",
            inputSchema={"type": "object", "additionalProperties": True},
        ) for name in TOOLS[self.slug]]

    async def call_tool(self, name, _arguments):
        if self.slug in self.unavailable:
            raise UpstreamError(f"{self.slug} unavailable")
        assert name in TOOLS[self.slug]
        return CallToolResult(content=[TextContent(
            type="text", text=f"{self.slug}:{name}",
        )])


@pytest.mark.asyncio
async def test_seed_runtime_registration_alias_calls_and_restart_persistence(database_url: str):
    seed = UpstreamSeed("woo", "WooCommerce", URLS["woo"], "woo-secret")
    assert await seed_upstream(database_url, KEY, seed) == "upstream-created"
    assert await seed_upstream(database_url, KEY, seed) == "existing-upstream-preserved"
    await bootstrap_admin(ADMIN_EMAIL, ADMIN_PASSWORD, database_url)

    app = create_app(settings(database_url))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=ORIGIN,
    ) as admin:
        login = await admin.post(
            "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert login.status_code == 200
        for slug in ("currency", "policy", "analytics"):
            created = await admin.post(
                "/api/servers",
                headers={"Origin": ORIGIN},
                json={
                    "slug": slug, "display_name": slug.title(), "url": URLS[slug],
                    "auth_type": "bearer", "credential": f"{slug}-secret",
                },
            )
            assert created.status_code == 201
        listed = await admin.get("/api/servers")
        assert listed.status_code == 200
        assert [server["slug"] for server in listed.json()] == [
            "woo", "currency", "policy", "analytics",
        ]
    await app.state.engine.dispose()

    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    cipher = CredentialCipher(KEY)
    catalog = CatalogService(sessions, cipher, adapter_factory=FourServerAdapter)
    await catalog.refresh_all()
    async with sessions() as db:
        admin_user = await db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    assert admin_user is not None
    actor = ApiKeyActor(admin_user.id, admin_user.email, admin_user.role, None, "chat")
    router = GatewayRouter(sessions, catalog, cipher, adapter_factory=FourServerAdapter)
    aliases = [tool.name for tool in await router.list_tools(actor)]
    assert len(aliases) == 14
    assert "woo__list_products" in aliases and "policy__list_products" in aliases
    for alias in (
        "woo__list_products", "currency__get_demo_rates", "policy__list_products",
        "analytics__summarize_sales", "analytics__get_top_products",
    ):
        result = await router.call_tool(actor, alias, {})
        assert result.is_error is False
        assert result.content[0].text == alias.replace("__", ":")
    async with sessions() as db:
        analytics_audits = list(await db.scalars(
            select(AuditEvent).where(AuditEvent.server_slug == "analytics")
        ))
        analytics = await db.scalar(select(Upstream).where(Upstream.slug == "analytics"))
        assert analytics is not None
        analytics.enabled = False
        analytics.status = "disabled"
        await db.commit()
    assert {event.public_tool for event in analytics_audits} == {
        "analytics__summarize_sales", "analytics__get_top_products",
    }
    assert all(event.outcome == "ok" for event in analytics_audits)
    assert all(not tool.name.startswith("analytics__") for tool in await router.list_tools(actor))
    with pytest.raises(MCPError, match="disabled"):
        await router.call_tool(actor, "analytics__summarize_sales", {})
    async with sessions() as db:
        analytics = await db.scalar(select(Upstream).where(Upstream.slug == "analytics"))
        analytics.enabled = True
        analytics.status = "connected"
        await db.commit()
        analytics_id = analytics.id
    FourServerAdapter.unavailable.add("analytics")
    await catalog.refresh_all()
    async with sessions() as db:
        analytics = await db.get(Upstream, analytics_id)
        assert analytics.status == "unreachable"
    assert "woo__list_products" in [tool.name for tool in await router.list_tools(actor)]
    woo_result = await router.call_tool(actor, "woo__list_products", {})
    analytics_result = await router.call_tool(actor, "analytics__summarize_sales", {})
    assert woo_result.is_error is False
    assert analytics_result.is_error is True
    FourServerAdapter.unavailable.clear()
    await engine.dispose()

    restarted_engine = make_engine(database_url)
    restarted_sessions = make_session_factory(restarted_engine)
    restarted_catalog = CatalogService(restarted_sessions, cipher, adapter_factory=FourServerAdapter)
    restarted_router = GatewayRouter(
        restarted_sessions, restarted_catalog, cipher, adapter_factory=FourServerAdapter,
    )
    assert [tool.name for tool in await restarted_router.list_tools(actor)] == aliases
    async with restarted_sessions() as db:
        assert len(list(await db.scalars(select(Upstream)))) == 4
    await restarted_engine.dispose()


@pytest.mark.asyncio
async def test_seed_preserves_existing_admin_configuration(database_url: str):
    seed = UpstreamSeed("woo", "WooCommerce", URLS["woo"], "woo-secret")
    assert await seed_upstream(database_url, KEY, seed) == "upstream-created"
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        woo = await db.scalar(select(Upstream).where(Upstream.slug == "woo"))
        woo.display_name = "Admin-owned Woo"
        await db.commit()
    assert await seed_upstream(database_url, KEY, seed) == "existing-upstream-preserved"
    async with sessions() as db:
        woo = await db.scalar(select(Upstream).where(Upstream.slug == "woo"))
        assert woo.display_name == "Admin-owned Woo"
        assert CredentialCipher(KEY).decrypt(woo.credential_ciphertext) == "woo-secret"
    await engine.dispose()
