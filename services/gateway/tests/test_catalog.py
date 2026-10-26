from __future__ import annotations

import asyncio

from mcp.types import Tool, ToolAnnotations
import pytest
from sqlalchemy import select

from app.database import make_engine, make_session_factory
from app.mcp_gateway.catalog import CatalogService
from app.models import Upstream, UpstreamTool
from app.security.upstream_crypto import CredentialCipher
from _catalog_support import catalog_database_url, clean_catalog


KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


class StaticAdapter:
    def __init__(self, tools):
        self.tools = tools

    async def list_tools(self):
        return self.tools


def tool(name: str) -> Tool:
    return Tool(
        name=name, description=f"Description for {name}",
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object"},
        annotations=ToolAnnotations(readOnlyHint=True),
    )


async def add_upstream(sessions, slug: str) -> Upstream:
    async with sessions() as db:
        upstream = Upstream(
            slug=slug, display_name=slug.title(), url=f"https://{slug}.example.test/mcp",
            auth_type="none", enabled=True, status="checking",
            connect_timeout_ms=500, call_timeout_ms=500,
        )
        db.add(upstream)
        await db.commit()
        await db.refresh(upstream)
        return upstream


@pytest.mark.asyncio
async def test_three_catalogs_persist_exact_aliases_hashes_and_cache_only_listing(
    catalog_database_url: str,
):
    engine = make_engine(catalog_database_url)
    sessions = make_session_factory(engine)
    created = [await add_upstream(sessions, slug) for slug in ("woo", "currency", "policy")]
    calls = 0

    def factory(_config, _credential):
        nonlocal calls
        calls += 1
        return StaticAdapter([tool("list_products")])

    catalog = CatalogService(sessions, CredentialCipher(KEY), adapter_factory=factory)
    for upstream in created:
        await catalog.refresh_upstream(upstream.id)
    assert calls == 3
    async with sessions() as db:
        cached = await catalog.list_tools(db, actor=object())
        stored = list(await db.scalars(select(UpstreamTool)))
    assert calls == 3
    assert [entry.public_alias for entry in cached] == [
        "currency__list_products", "policy__list_products", "woo__list_products",
    ]
    assert len(stored) == 3
    assert all(len(row.definition_hash) == 64 and row.annotations == {"readOnlyHint": True} for row in stored)
    await engine.dispose()


@pytest.mark.asyncio
async def test_invalid_schema_does_not_replace_last_known_catalog(catalog_database_url: str):
    engine = make_engine(catalog_database_url)
    sessions = make_session_factory(engine)
    upstream = await add_upstream(sessions, "woo")
    state = {"tools": [tool("list_products")]}
    catalog = CatalogService(
        sessions, CredentialCipher(KEY),
        adapter_factory=lambda _config, _credential: StaticAdapter(state["tools"]),
    )
    await catalog.refresh_upstream(upstream.id)
    state["tools"] = [Tool(name="bad", inputSchema={"type": "not-a-json-schema-type"})]
    await catalog.refresh_upstream(upstream.id)
    async with sessions() as db:
        current = await db.get(Upstream, upstream.id)
        cached = await catalog.list_tools(db)
    assert current.status == "unreachable"
    assert current.last_error == "Upstream tool catalog is invalid"
    assert [entry.public_alias for entry in cached] == ["woo__list_products"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_background_refresher_survives_unexpected_error(catalog_database_url: str):
    engine = make_engine(catalog_database_url)
    sessions = make_session_factory(engine)
    catalog = CatalogService(sessions, CredentialCipher(KEY), refresh_seconds=0.01)
    recovered = asyncio.Event()
    calls = 0

    async def flaky_refresh():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database temporarily unavailable")
        recovered.set()

    catalog.refresh_all = flaky_refresh
    catalog.start()
    await asyncio.wait_for(recovered.wait(), timeout=2)
    await catalog.stop()
    assert calls >= 2
    await engine.dispose()
