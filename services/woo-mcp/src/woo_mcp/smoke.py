from __future__ import annotations

import asyncio
import os

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


EXPECTED_TOOLS = {
    "list_products", "create_product", "list_orders", "get_order", "update_order_status"
}


async def verify() -> None:
    url = os.environ["MCP_URL"]
    token = os.environ["MCP_BEARER_TOKEN"]
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, trust_env=False
    ) as http:
        async with Client(streamable_http_client(url, http_client=http)) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            if names != EXPECTED_TOOLS:
                raise RuntimeError(f"Unexpected WooCommerce tool catalog: {sorted(names)}")
            result = await client.call_tool("list_products", {"per_page": 1})
            if result.is_error:
                raise RuntimeError("list_products returned an MCP tool error")
    print("PASS in-cluster WooCommerce MCP discovery and list_products")


def main() -> None:
    asyncio.run(verify())


if __name__ == "__main__":
    main()
