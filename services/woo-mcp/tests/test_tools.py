from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
import socket

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
import pytest
import uvicorn

from woo_mcp.app import Settings, create_app
from woo_mcp.models import OrderDetail, OrderStatus, OrderSummary, ProductSummary


PRODUCT = ProductSummary(
    id=7, name="Demo", status="publish", regular_price="19.90", price="19.90",
    virtual=True, permalink="http://shop.example/products/demo",
)
ORDER = OrderDetail(
    id=12, status="processing", currency="INR", total="998.00",
    date_created="2026-10-16T09:00:00+05:30", payment_method="cod",
    line_items=[{"product_id": 7, "name": "Demo", "quantity": 1, "total": "998.00"}],
)


class FakeWCClient:
    def __init__(self) -> None:
        self.created = 0
        self.updated = 0
        self.ready = True

    async def list_products(self, filters):
        if not self.ready:
            raise RuntimeError("private upstream detail")
        return [PRODUCT]

    async def create_product(self, product):
        self.created += 1
        return PRODUCT.model_copy(update={"name": product.name, "regular_price": product.regular_price})

    async def list_orders(self, filters):
        return [OrderSummary.model_validate(ORDER.model_dump())]

    async def get_order(self, order_id):
        if order_id <= 0:
            raise ValueError("positive ID required")
        return ORDER

    async def update_order_status(self, order_id, status):
        self.updated += 1
        return ORDER.model_copy(update={"status": status.value})


def settings() -> Settings:
    return Settings("http://woo", "http://public", "ck_test", "cs_test", "mcp-test-token")


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
    return messages


def status(messages) -> int:
    return next(message["status"] for message in messages if message["type"] == "http.response.start")


@pytest.mark.asyncio
async def test_probes_and_bearer_authentication():
    client = FakeWCClient()
    app = create_app(settings(), client)
    assert status(await request_asgi(app, "/healthz")) == 200
    assert status(await request_asgi(app, "/readyz")) == 200
    assert status(await request_asgi(app, "/mcp")) == 401
    assert status(await request_asgi(app, "/mcp", b"Bearer wrong")) == 401
    client.ready = False
    assert status(await request_asgi(app, "/readyz")) == 503


@asynccontextmanager
async def running_app(app):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started and not task.done():
        await asyncio.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        await task


@asynccontextmanager
async def mcp_client(url: str):
    async with httpx2.AsyncClient(
        headers={"Authorization": "Bearer mcp-test-token"}, trust_env=False
    ) as http:
        async with Client(streamable_http_client(url, http_client=http)) as client:
            yield client


@pytest.mark.asyncio
async def test_five_tools_discover_execute_validate_and_bound_outputs():
    backend = FakeWCClient()
    async with running_app(create_app(settings(), backend)) as url:
        async with mcp_client(url) as client:
            discovered = await client.list_tools()
            assert {tool.name for tool in discovered.tools} == {
                "list_products", "create_product", "list_orders", "get_order", "update_order_status"
            }

            products = await client.call_tool("list_products", {"per_page": 1})
            assert not products.is_error
            assert "meta_data" not in str(products.content)

            created = await client.call_tool(
                "create_product", {"name": "MCP product", "regular_price": "10.50", "status": "draft"}
            )
            assert not created.is_error and backend.created == 1

            orders = await client.call_tool("list_orders", {"date": "today"})
            assert not orders.is_error
            assert "billing" not in str(orders.content) and "shipping" not in str(orders.content)
            assert "line_items" in str(orders.content) and "Demo" in str(orders.content)

            order = await client.call_tool("get_order", {"order_id": 12})
            assert not order.is_error

            updated = await client.call_tool(
                "update_order_status", {"order_id": 12, "status": OrderStatus.COMPLETED.value}
            )
            assert not updated.is_error and backend.updated == 1

            invalid = await client.call_tool("list_products", {"per_page": 51})
            assert invalid.is_error
            invalid_status = await client.call_tool(
                "update_order_status", {"order_id": 12, "status": "invented"}
            )
            assert invalid_status.is_error and backend.updated == 1
