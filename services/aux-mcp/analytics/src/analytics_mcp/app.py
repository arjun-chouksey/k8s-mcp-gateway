from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from typing import Literal

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
import uvicorn

from . import analytics
from .models import OrderInput


@dataclass(frozen=True)
class Settings:
    bearer_token: str
    allowed_hosts: tuple[str, ...] = ("127.0.0.1:*", "localhost:*")

    @classmethod
    def from_env(cls) -> Settings:
        token = os.getenv("ANALYTICS_MCP_BEARER_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Missing required environment variable: ANALYTICS_MCP_BEARER_TOKEN")
        hosts = tuple(
            host.strip()
            for host in os.getenv("MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*").split(",")
            if host.strip()
        )
        return cls(token, hosts)


def create_mcp_server() -> MCPServer:
    server = MCPServer("analytics-mcp", version="0.1.0")

    @server.tool()
    async def summarize_sales(orders: list[OrderInput]) -> dict[str, object]:
        """Summarize booked order value from supplied, non-sensitive WooCommerce order fields."""
        return analytics.summarize_sales(orders)

    @server.tool()
    async def get_top_products(
        orders: list[OrderInput], limit: int = 10,
        rank_by: Literal["quantity", "revenue"] = "revenue",
    ) -> dict[str, object]:
        """Rank products from eligible supplied orders by quantity or booked order value."""
        return analytics.get_top_products(orders, limit, rank_by)

    @server.tool()
    async def get_order_status_breakdown(orders: list[OrderInput]) -> dict[str, object]:
        """Count supplied orders and order value per status without claiming settled revenue."""
        return analytics.get_order_status_breakdown(orders)

    @server.tool()
    async def calculate_sales_trend(
        orders: list[OrderInput], interval: Literal["day", "week", "month"],
    ) -> dict[str, object]:
        """Bucket eligible supplied order value by day, Monday-based week, or month."""
        return analytics.calculate_sales_trend(orders, interval)

    return server


class AnalyticsApp:
    def __init__(self, mcp_app: ASGIApp, bearer_token: str) -> None:
        if not bearer_token:
            raise ValueError("A non-empty analytics MCP bearer token is required")
        self._mcp_app = mcp_app
        self._authorization = f"Bearer {bearer_token}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._mcp_app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path in {"/healthz", "/readyz"}:
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


def create_app(settings: Settings) -> ASGIApp:
    mcp_app = create_mcp_server().streamable_http_app(
        stateless_http=True,
        transport_security=TransportSecuritySettings(allowed_hosts=list(settings.allowed_hosts)),
    )
    return AnalyticsApp(mcp_app, settings.bearer_token)


def main() -> None:
    uvicorn.run(create_app(Settings.from_env()), host="0.0.0.0", port=8000)
