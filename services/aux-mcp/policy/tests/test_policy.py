from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import socket

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
import pytest
import uvicorn

from policy_mcp import Settings, create_app, load_policies


def test_versioned_policy_catalog_and_collision_fixture_are_static():
    catalog = load_policies()
    listed = catalog.list_policies()
    assert listed["version"] == "2026-10-demo-v1"
    assert {item["topic"] for item in listed["policies"]} == {"refunds", "shipping", "privacy"}
    assert catalog.get_policy(" REFUNDS ")["topic"] == "refunds"
    collision = catalog.collision_fixture(None, 1, 20)
    assert collision["items"][0]["source"] == "policy-mcp static collision fixture"
    assert "NOT WooCommerce" in collision["items"][0]["label"]


def test_unknown_policy_and_invalid_pagination_are_rejected():
    catalog = load_policies()
    with pytest.raises(ValueError, match="unsupported policy topic"):
        catalog.get_policy("warranty")
    with pytest.raises(ValueError, match="page must be positive"):
        catalog.collision_fixture(None, 0, 20)
    with pytest.raises(ValueError, match="per_page"):
        catalog.collision_fixture(None, 1, 51)


async def request_asgi(app, path: str, authorization: bytes | None = None):
    messages = []
    headers = [] if authorization is None else [(b"authorization", authorization)]
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(
        {"type": "http", "asgi": {"version": "3.0"}, "method": "GET", "path": path,
         "raw_path": path.encode(), "query_string": b"", "headers": headers,
         "scheme": "http", "server": ("test", 80), "client": ("test", 1)},
        receive, send,
    )
    return next(m["status"] for m in messages if m["type"] == "http.response.start")


@pytest.mark.asyncio
async def test_probes_and_bearer_rejection():
    app = create_app(Settings("policy-test-token"))
    assert await request_asgi(app, "/healthz") == 200
    assert await request_asgi(app, "/readyz") == 200
    assert await request_asgi(app, "/mcp") == 401
    assert await request_asgi(app, "/mcp", b"Bearer wrong") == 401


@asynccontextmanager
async def running_app(app):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    task = asyncio.create_task(server.serve())
    while not server.started and not task.done():
        await asyncio.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        await task


@pytest.mark.asyncio
async def test_real_mcp_tools_collision_and_invalid_topic():
    async with running_app(create_app(Settings("policy-test-token"))) as url:
        async with httpx2.AsyncClient(
            headers={"Authorization": "Bearer policy-test-token"}, trust_env=False
        ) as http:
            async with Client(streamable_http_client(url, http_client=http)) as client:
                tools = await client.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "list_store_policies", "get_store_policy", "list_products"
                }
                policy = await client.call_tool("get_store_policy", {"topic": "shipping"})
                assert not policy.is_error and "virtual products" in str(policy.content)
                collision = await client.call_tool("list_products", {"per_page": 1})
                assert not collision.is_error and "NOT WooCommerce" in str(collision.content)
                invalid = await client.call_tool("get_store_policy", {"topic": "unknown"})
                assert invalid.is_error
