from __future__ import annotations

import asyncio
import os

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


async def verify() -> None:
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {os.environ['CURRENCY_MCP_BEARER_TOKEN']}"},
        trust_env=False,
    ) as http:
        async with Client(streamable_http_client(os.environ["MCP_URL"], http_client=http)) as client:
            tools = await client.list_tools()
            if {tool.name for tool in tools.tools} != {"convert_currency", "get_demo_rates"}:
                raise RuntimeError("unexpected currency MCP tool catalog")
            result = await client.call_tool(
                "convert_currency",
                {"amount": "998.00", "from_currency": "INR", "to_currency": "EUR"},
            )
            if result.is_error or "NOT live FX" not in str(result.content):
                raise RuntimeError("currency conversion failed or omitted demo-rate label")
    print("PASS in-cluster currency MCP discovery and conversion")


if __name__ == "__main__":
    asyncio.run(verify())
