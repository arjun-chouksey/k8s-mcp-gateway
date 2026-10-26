from __future__ import annotations

import asyncio
import os

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


TOOLS = {
    "summarize_sales", "get_top_products", "get_order_status_breakdown",
    "calculate_sales_trend",
}


async def run() -> None:
    url = os.environ["MCP_URL"]
    token = os.environ["ANALYTICS_MCP_BEARER_TOKEN"]
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, trust_env=False,
    ) as http:
        async with Client(streamable_http_client(url, http_client=http)) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools.tools} == TOOLS
            result = await client.call_tool("summarize_sales", {"orders": []})
            assert not result.is_error


asyncio.run(run())
