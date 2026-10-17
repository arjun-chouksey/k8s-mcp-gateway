from __future__ import annotations

from mcp.server import Server, ServerRequestContext
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import MCPError
from mcp.types import (
    CallToolRequestParams, ListToolsResult, PaginatedRequestParams,
)

from app.mcp_gateway.router import GatewayRouter
from app.security.api_keys import ApiKeyActor


def _actor(context: ServerRequestContext) -> ApiKeyActor:
    request = context.request
    actor = getattr(getattr(request, "state", None), "mcp_actor", None)
    if not isinstance(actor, ApiKeyActor):
        raise MCPError(-32600, "Authenticated actor context is missing")
    return actor


def create_mcp_endpoint(
    router: GatewayRouter, *, allowed_hosts: list[str], allowed_origins: list[str],
):
    async def list_tools(
        context: ServerRequestContext, _params: PaginatedRequestParams | None,
    ) -> ListToolsResult:
        return ListToolsResult(tools=await router.list_tools(_actor(context)))

    async def call_tool(context: ServerRequestContext, params: CallToolRequestParams):
        return await router.call_tool(_actor(context), params.name, params.arguments)

    server = Server(
        "team-mcp-gateway", version="0.1.0",
        on_list_tools=list_tools, on_call_tool=call_tool,
    )
    return server.streamable_http_app(
        stateless_http=True, json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        ),
    )
