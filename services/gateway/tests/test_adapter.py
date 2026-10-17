from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import socket

import pytest
import uvicorn
from mcp.server import MCPServer
from starlette.responses import JSONResponse

from app.mcp_gateway.adapter import (
    UpstreamAdapter,
    UpstreamConfig,
    UpstreamConfigurationError,
    UpstreamResultTooLargeError,
    UpstreamTimeoutError,
)


class HeaderGuard:
    def __init__(self, app, expected: tuple[bytes, bytes] | None, seen: list[dict[bytes, bytes]]):
        self.app, self.expected, self.seen = app, expected, seen

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            self.seen.append(headers)
            if self.expected and headers.get(self.expected[0]) != self.expected[1]:
                await JSONResponse({"error": "Unauthorized"}, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def mcp_app(expected=None, *, delay: float = 0, payload_size: int = 0, calls: list[str] | None = None):
    server = MCPServer("adapter-test", version="0.1.0")

    @server.tool()
    async def echo(value: str) -> str:
        """Return a test value."""
        if calls is not None:
            calls.append(value)
        await asyncio.sleep(delay)
        return "x" * payload_size if payload_size else value

    seen: list[dict[bytes, bytes]] = []
    return HeaderGuard(server.streamable_http_app(stateless_http=True), expected, seen), seen


@asynccontextmanager
async def serve(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    config = uvicorn.Config(
        app, log_level="critical", lifespan="on", timeout_graceful_shutdown=1
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve(sockets=[sock]))
    while not server.started:
        await asyncio.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        await task


def config(url: str, auth_type="none", auth_header=None, timeout_ms=500):
    return UpstreamConfig(url, auth_type, auth_header, timeout_ms, timeout_ms)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("auth_type", "auth_header", "credential", "expected"),
    [
        ("none", None, None, None),
        ("bearer", None, "upstream-only", (b"authorization", b"Bearer upstream-only")),
        ("header", "X-MCP-Key", "custom-only", (b"x-mcp-key", b"custom-only")),
    ],
)
async def test_auth_modes_list_and_call_without_downstream_passthrough(
    auth_type, auth_header, credential, expected
):
    app, seen = mcp_app(expected)
    async with serve(app) as url:
        adapter = UpstreamAdapter(config(url, auth_type, auth_header), credential)
        assert [tool.name for tool in await adapter.list_tools()] == ["echo"]
        result = await adapter.call_tool("echo", {"value": "ok"})
    assert result.is_error is False
    assert all(b"downstream-secret" not in b" ".join(headers.values()) for headers in seen)


@pytest.mark.asyncio
async def test_timeout_is_bounded_and_call_is_not_retried():
    calls: list[str] = []
    slow, _ = mcp_app(delay=0.25, calls=calls)
    fast, _ = mcp_app()
    async with serve(slow) as slow_url, serve(fast) as fast_url:
        slow_adapter = UpstreamAdapter(config(slow_url, timeout_ms=60), None)
        fast_adapter = UpstreamAdapter(config(fast_url), None)
        started = asyncio.get_running_loop().time()
        with pytest.raises(UpstreamTimeoutError):
            await slow_adapter.call_tool("echo", {"value": "write"})
        elapsed = asyncio.get_running_loop().time() - started
        result = await fast_adapter.call_tool("echo", {"value": "still-works"})
    assert elapsed < 0.5
    assert calls == ["write"]
    assert result.is_error is False


@pytest.mark.asyncio
async def test_result_size_is_bounded():
    app, _ = mcp_app(payload_size=2_000)
    async with serve(app) as url:
        adapter = UpstreamAdapter(config(url), None, max_result_bytes=500)
        with pytest.raises(UpstreamResultTooLargeError):
            await adapter.call_tool("echo", {"value": "ignored"})


def test_invalid_auth_configuration_is_rejected_without_exposing_secret():
    with pytest.raises(UpstreamConfigurationError, match="requires a credential") as error:
        UpstreamAdapter(config("https://example.test/mcp", "bearer"), None)
    assert "secret" not in str(error.value)
