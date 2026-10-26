from __future__ import annotations

import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
import uvicorn

from .models import OrderFilters, OrderStatus, ProductCreate, ProductFilters
from .wc_client import WCClient


@dataclass(frozen=True)
class Settings:
    base_url: str
    oauth_base_url: str
    consumer_key: str
    consumer_secret: str
    bearer_token: str
    store_timezone: str = "Asia/Kolkata"
    allowed_hosts: tuple[str, ...] = ("127.0.0.1:*", "localhost:*")

    @classmethod
    def from_env(cls) -> Settings:
        required = {
            "base_url": "WOOCOMMERCE_BASE_URL",
            "oauth_base_url": "WOOCOMMERCE_OAUTH_BASE_URL",
            "consumer_key": "WOOCOMMERCE_CONSUMER_KEY",
            "consumer_secret": "WOOCOMMERCE_CONSUMER_SECRET",
            "bearer_token": "MCP_BEARER_TOKEN",
        }
        values: dict[str, str] = {}
        missing: list[str] = []
        for field, variable in required.items():
            value = os.getenv(variable, "").strip()
            if value:
                values[field] = value
            else:
                missing.append(variable)
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        values["store_timezone"] = os.getenv("STORE_TIMEZONE", "Asia/Kolkata")
        values["allowed_hosts"] = tuple(
            host.strip() for host in os.getenv("MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*").split(",")
            if host.strip()
        )
        return cls(**values)


def _json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return [_json(item) for item in value]


def create_mcp_server(client: WCClient) -> MCPServer:
    server = MCPServer("woocommerce-mcp", version="0.1.0")

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_products(
        search: str | None = None, page: int = 1, per_page: int = 20
    ) -> list[dict[str, Any]]:
        """List a bounded page of WooCommerce products."""
        return _json(await client.list_products(ProductFilters(search=search, page=page, per_page=per_page)))

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False))
    async def create_product(
        name: str,
        regular_price: Decimal,
        description: str | None = None,
        status: str = "publish",
    ) -> dict[str, Any]:
        """Create one virtual WooCommerce product. Writes are never retried."""
        product = ProductCreate(
            name=name, regular_price=regular_price, description=description, status=status
        )
        return _json(await client.create_product(product))

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_orders(
        status: OrderStatus | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
        date: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> list[dict[str, Any]]:
        """List a bounded page of orders without customer billing or shipping data."""
        filters = OrderFilters(
            status=status, after=after, before=before, date=date, page=page, per_page=per_page
        )
        return _json(await client.list_orders(filters))

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_order(order_id: int) -> dict[str, Any]:
        """Get one order and its line items without customer PII."""
        return _json(await client.get_order(order_id))

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False))
    async def update_order_status(order_id: int, status: OrderStatus) -> dict[str, Any]:
        """Update one order status. This write is never retried."""
        return _json(await client.update_order_status(order_id, status))

    return server


class WooMCPApp:
    def __init__(self, mcp_app: ASGIApp, client: WCClient, bearer_token: str) -> None:
        if not bearer_token:
            raise ValueError("A non-empty MCP bearer token is required")
        self._mcp_app = mcp_app
        self._client = client
        self._authorization = f"Bearer {bearer_token}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._mcp_app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == "/healthz":
            await JSONResponse({"status": "ok"})(scope, receive, send)
            return
        if path == "/readyz":
            try:
                await self._client.list_products(ProductFilters(per_page=1))
            except Exception:
                await JSONResponse({"status": "not ready"}, status_code=503)(scope, receive, send)
            else:
                await JSONResponse({"status": "ready"})(scope, receive, send)
            return
        headers = [value for key, value in scope["headers"] if key.lower() == b"authorization"]
        if len(headers) != 1 or not hmac.compare_digest(headers[0], self._authorization):
            await JSONResponse(
                {"error": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
            return
        await self._mcp_app(scope, receive, send)


def create_app(settings: Settings, client: WCClient | None = None) -> ASGIApp:
    woo_client = client or WCClient(
        base_url=settings.base_url,
        oauth_base_url=settings.oauth_base_url,
        consumer_key=settings.consumer_key,
        consumer_secret=settings.consumer_secret,
        store_timezone=settings.store_timezone,
    )
    mcp_app = create_mcp_server(woo_client).streamable_http_app(
        stateless_http=True,
        transport_security=TransportSecuritySettings(allowed_hosts=list(settings.allowed_hosts)),
    )
    # OAuth query parameters include credential material and must never enter logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return WooMCPApp(mcp_app, woo_client, settings.bearer_token)


def main() -> None:
    uvicorn.run(create_app(Settings.from_env()), host="0.0.0.0", port=8000)


app = create_app(Settings.from_env()) if os.getenv("MCP_BEARER_TOKEN") else None
