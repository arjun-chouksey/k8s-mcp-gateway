from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from mcp.types import Tool
import pytest
from sqlalchemy import select

from app.database import make_engine, make_session_factory
from app.mcp_gateway.adapter import UpstreamTimeoutError
from app.mcp_gateway.catalog import CatalogService
from app.models import Upstream
from app.security.upstream_crypto import CredentialCipher
from _catalog_support import catalog_database_url, clean_catalog


KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
TOOL = Tool(name="echo", inputSchema={"type": "object"})


class StatefulAdapter:
    def __init__(self, state):
        self.state = state

    async def list_tools(self):
        if self.state.get("wait"):
            await self.state["wait"].wait()
        if self.state.get("fail"):
            raise UpstreamTimeoutError("upstream request timed out")
        return [TOOL]


async def setup(catalog_database_url: str, state):
    engine = make_engine(catalog_database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        upstream = Upstream(
            slug="slow", display_name="Slow", url="https://slow.example.test/mcp",
            auth_type="none", enabled=True, status="checking",
            connect_timeout_ms=100, call_timeout_ms=100,
        )
        db.add(upstream)
        await db.commit()
        await db.refresh(upstream)
    catalog = CatalogService(
        sessions, CredentialCipher(KEY),
        adapter_factory=lambda _config, _credential: StatefulAdapter(state),
    )
    return engine, sessions, upstream, catalog


@pytest.mark.asyncio
async def test_unreachable_retains_cache_and_disabled_is_immediately_absent(catalog_database_url: str):
    state = {}
    engine, sessions, upstream, catalog = await setup(catalog_database_url, state)
    await catalog.refresh_upstream(upstream.id)
    state["fail"] = True
    await catalog.refresh_upstream(upstream.id)
    async with sessions() as db:
        current = await db.get(Upstream, upstream.id)
        assert current.status == "unreachable" and current.last_checked_at is not None
        assert len(await catalog.list_tools(db)) == 1
        current.enabled = False
        current.status = "disabled"
        current.updated_at = datetime.now(timezone.utc)
        await db.commit()
        assert await catalog.list_tools(db) == []
    await engine.dispose()


@pytest.mark.asyncio
async def test_slow_probe_does_not_block_cached_list_or_overwrite_disable(catalog_database_url: str):
    gate = asyncio.Event()
    state = {"wait": gate}
    engine, sessions, upstream, catalog = await setup(catalog_database_url, state)
    refresh = asyncio.create_task(catalog.refresh_upstream(upstream.id))
    await asyncio.sleep(0.05)
    async with sessions() as db:
        assert await asyncio.wait_for(catalog.list_tools(db), timeout=0.2) == []
        current = await db.scalar(select(Upstream).where(Upstream.id == upstream.id).with_for_update())
        current.enabled = False
        current.status = "disabled"
        current.updated_at = datetime.now(timezone.utc)
        await db.commit()
    gate.set()
    await refresh
    async with sessions() as db:
        current = await db.get(Upstream, upstream.id)
        assert current.enabled is False and current.status == "disabled"
    await engine.dispose()
