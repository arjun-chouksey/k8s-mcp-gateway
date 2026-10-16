from __future__ import annotations

import hmac
import os
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
import uvicorn

from .policies import PolicyCatalog, load_policies


@dataclass(frozen=True)
class Settings:
    bearer_token: str
    allowed_hosts: tuple[str, ...] = ("127.0.0.1:*", "localhost:*")

    @classmethod
    def from_env(cls) -> Settings:
        token = os.getenv("POLICY_MCP_BEARER_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Missing required environment variable: POLICY_MCP_BEARER_TOKEN")
        hosts = tuple(
            host.strip()
            for host in os.getenv("MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*").split(",")
            if host.strip()
        )
        return cls(token, hosts)


def create_mcp_server(catalog: PolicyCatalog) -> MCPServer:
    server = MCPServer("policy-mcp", version="0.1.0")

    @server.tool()
    async def list_store_policies() -> dict[str, object]:
        """List the versioned demonstration store-policy topics."""
        return catalog.list_policies()

    @server.tool()
    async def get_store_policy(topic: str) -> dict[str, str]:
        """Get one versioned demonstration store policy by topic."""
        return catalog.get_policy(topic)

    @server.tool()
    async def list_products(
        search: str | None = None, page: int = 1, per_page: int = 20
    ) -> dict[str, object]:
        """Return static policy-demo data for collision testing; never queries WooCommerce."""
        return catalog.collision_fixture(search, page, per_page)

    return server


class PolicyApp:
    def __init__(self, mcp_app: ASGIApp, bearer_token: str) -> None:
        if not bearer_token:
            raise ValueError("A non-empty policy MCP bearer token is required")
        self._mcp_app = mcp_app
        self._authorization = f"Bearer {bearer_token}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._mcp_app(scope, receive, send)
            return
        if scope.get("path", "") in {"/healthz", "/readyz"}:
            await JSONResponse({"status": "ok"})(scope, receive, send)
            return
        headers = [value for key, value in scope["headers"] if key.lower() == b"authorization"]
        if len(headers) != 1 or not hmac.compare_digest(headers[0], self._authorization):
            await JSONResponse(
                {"error": "Unauthorized"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
            return
        await self._mcp_app(scope, receive, send)


def create_app(settings: Settings, catalog: PolicyCatalog | None = None) -> ASGIApp:
    server = create_mcp_server(catalog or load_policies())
    mcp_app = server.streamable_http_app(
        stateless_http=True,
        transport_security=TransportSecuritySettings(allowed_hosts=list(settings.allowed_hosts)),
    )
    return PolicyApp(mcp_app, settings.bearer_token)


def main() -> None:
    uvicorn.run(create_app(Settings.from_env()), host="0.0.0.0", port=8000)
