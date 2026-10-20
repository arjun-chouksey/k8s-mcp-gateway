from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


@asynccontextmanager
async def self_gateway_session(url: str, token: str) -> AsyncIterator[ClientSession]:
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=30.0, trust_env=False,
    ) as http:
        async with streamable_http_client(
            url, http_client=http, terminate_on_close=False, max_sse_event_size=262_144,
        ) as streams:
            async with ClientSession(*streams, read_timeout_seconds=30.0) as session:
                await session.initialize()
                yield session
