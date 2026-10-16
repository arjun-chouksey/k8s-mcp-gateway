from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
import socket

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
import pytest
import uvicorn

from currency_mcp import Settings, create_app, load_rates


def test_exact_decimal_conversion_and_metadata_label():
    rates = load_rates()
    result = rates.convert(Decimal("998.00"), "inr", "eur")
    assert result["converted_amount"] == "10.479000"
    assert result["rate"] == "0.0105"
    assert result["rate_version"] == "2026-10-demo-v1"
    assert "NOT live FX" in result["rate_label"]
    assert "NOT live FX" in rates.metadata()["label"]


@pytest.mark.parametrize(
    ("amount", "source", "target"),
    [(Decimal("-1"), "INR", "EUR"), (Decimal("NaN"), "INR", "EUR"),
     (Decimal("1"), "JPY", "EUR"), (Decimal("1"), "INR", "CAD")],
)
def test_invalid_amounts_and_unsupported_currencies_are_rejected(amount, source, target):
    with pytest.raises(ValueError):
        load_rates().convert(amount, source, target)


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
    app = create_app(Settings("currency-test-token"))
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
async def test_real_mcp_discovery_calls_and_invalid_arguments():
    app = create_app(Settings("currency-test-token"))
    async with running_app(app) as url:
        async with httpx2.AsyncClient(
            headers={"Authorization": "Bearer currency-test-token"}, trust_env=False
        ) as http:
            async with Client(streamable_http_client(url, http_client=http)) as client:
                tools = await client.list_tools()
                assert {tool.name for tool in tools.tools} == {"convert_currency", "get_demo_rates"}
                rates = await client.call_tool("get_demo_rates", {})
                assert not rates.is_error and "NOT live FX" in str(rates.content)
                converted = await client.call_tool(
                    "convert_currency",
                    {"amount": "998.00", "from_currency": "INR", "to_currency": "EUR"},
                )
                assert not converted.is_error and "10.479000" in str(converted.content)
                unsupported = await client.call_tool(
                    "convert_currency",
                    {"amount": "1", "from_currency": "JPY", "to_currency": "EUR"},
                )
                assert unsupported.is_error
                malformed = await client.call_tool(
                    "convert_currency",
                    {"amount": "not-a-number", "from_currency": "INR", "to_currency": "EUR"},
                )
                assert malformed.is_error
