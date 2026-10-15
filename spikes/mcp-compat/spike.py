"""T-002 only: one fixed SDK v2 tool and a bearer-protected HTTP proxy."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hmac
from typing import AsyncIterator

import httpx2
from jsonschema import Draft202012Validator
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server import MCPServer, Server, ServerRequestContext
from mcp.shared.exceptions import MCPError
from mcp.types import CallToolRequestParams, CallToolResult, ListToolsResult, PaginatedRequestParams, TextContent, Tool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


@dataclass
class Probe:
    """Non-secret counters for integration evidence, not a production audit log."""
    calls: int = 0
    actors: list[str] = field(default_factory=list)


class BearerGuard:
    """Check every HTTP request; credentials are never logged or forwarded."""
    def __init__(self, app: ASGIApp, tokens: dict[str, str]) -> None:
        if not tokens or any(not token for token in tokens):
            raise ValueError("Non-empty bearer credentials required")
        self.app = app
        self.tokens = tokens

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] == 'http':
            headers = [value for key, value in scope['headers'] if key.lower() == b'authorization']
            actor = None
            if len(headers) == 1:
                for token, name in self.tokens.items():
                    if hmac.compare_digest(headers[0], f'Bearer {token}'.encode()):
                        actor = name
            if actor is None:
                response = JSONResponse({'error': 'Unauthorized'}, status_code=401,
                                        headers={'WWW-Authenticate': 'Bearer'})
                await response(scope, receive, send)
                return
            scope = {**scope, 'state': {**scope.get('state', {}), 'actor': actor}}
        await self.app(scope, receive, send)


@asynccontextmanager
async def connect(url: str, token: str, timeout: float = 2.0) -> AsyncIterator[Client]:
    async with httpx2.AsyncClient(headers={'Authorization': f'Bearer {token}'},
                                  timeout=httpx2.Timeout(timeout), trust_env=False) as http:
        async with Client(streamable_http_client(url, http_client=http),
                          read_timeout_seconds=timeout) as client:
            yield client


def fixed_app(token: str, probe: Probe, delay: float = 0) -> ASGIApp:
    server = MCPServer('t002-fixed', version='0.1.0')

    @server.tool()
    async def add(a: int, b: int) -> int:
        """Add two integers for the protocol compatibility spike."""
        probe.calls += 1
        await asyncio.sleep(delay)
        return a + b

    return BearerGuard(server.streamable_http_app(stateless_http=True), {token: 'gateway'})


def proxy_app(upstream_url: str, upstream_token: str, tokens: dict[str, str],
              probe: Probe, timeout: float = 2.0) -> ASGIApp:
    catalog: dict[str, Tool] = {}

    @asynccontextmanager
    async def lifespan(server: Server) -> AsyncIterator[dict]:
        async with asyncio.timeout(timeout):
            async with connect(upstream_url, upstream_token, timeout) as client:
                discovered = await client.list_tools()
        for tool in discovered.tools:
            Draft202012Validator.check_schema(tool.input_schema)
            catalog[f'probe__{tool.name}'] = tool
        yield {}

    async def list_tools(ctx: ServerRequestContext,
                         params: PaginatedRequestParams | None) -> ListToolsResult:
        return ListToolsResult(tools=[tool.model_copy(update={'name': alias})
                                     for alias, tool in catalog.items()])

    async def call_tool(ctx: ServerRequestContext,
                        params: CallToolRequestParams) -> CallToolResult:
        tool = catalog.get(params.name)
        if tool is None:
            raise MCPError(-32602, 'Unknown tool')
        args = params.arguments or {}
        if not Draft202012Validator(tool.input_schema).is_valid(args):
            raise MCPError(-32602, 'Arguments do not match tool schema')
        # Identity is attached to this request, never to a shared client session.
        probe.actors.append(ctx.request.state.actor)
        try:
            async with asyncio.timeout(timeout):
                async with connect(upstream_url, upstream_token, timeout) as client:
                    return await client.call_tool(tool.name, args)
        except Exception:
            # No retry; never expose upstream URLs, credentials or exception text.
            return CallToolResult(is_error=True, content=[TextContent(
                type='text', text='Upstream unavailable or timed out; call was not retried.')])

    server = Server('t002-proxy', version='0.1.0', lifespan=lifespan,
                    on_list_tools=list_tools, on_call_tool=call_tool)
    return BearerGuard(server.streamable_http_app(stateless_http=True), tokens)
