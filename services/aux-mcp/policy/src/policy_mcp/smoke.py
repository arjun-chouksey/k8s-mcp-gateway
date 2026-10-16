from __future__ import annotations

import asyncio
import os

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


async def verify() -> None:
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {os.environ['POLICY_MCP_BEARER_TOKEN']}"},
        trust_env=False,
    ) as http:
        async with Client(streamable_http_client(os.environ["MCP_URL"], http_client=http)) as client:
            tools = await client.list_tools()
            expected = {"list_store_policies", "get_store_policy", "list_products"}
            if {tool.name for tool in tools.tools} != expected:
                raise RuntimeError("unexpected policy MCP tool catalog")
            policy = await client.call_tool("get_store_policy", {"topic": "refunds"})
            collision = await client.call_tool("list_products", {"per_page": 1})
            if policy.is_error or collision.is_error or "NOT WooCommerce" not in str(collision.content):
                raise RuntimeError("policy or collision-fixture call failed")
    print("PASS in-cluster policy MCP retrieval and collision fixture")


if __name__ == "__main__":
    asyncio.run(verify())
