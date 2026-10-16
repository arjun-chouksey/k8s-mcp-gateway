from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from decimal import Decimal

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
import uvicorn

from .rates import DemoRates, load_rates


@dataclass(frozen=True)
class Settings:
    bearer_token: str
    allowed_hosts: tuple[str, ...] = ("127.0.0.1:*", "localhost:*")

    @classmethod
    def from_env(cls) -> Settings:
        token = os.getenv("CURRENCY_MCP_BEARER_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Missing required environment variable: CURRENCY_MCP_BEARER_TOKEN")
        hosts = tuple(
            host.strip()
            for host in os.getenv("MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*").split(",")
            if host.strip()
        )
        return cls(bearer_token=token, allowed_hosts=hosts)


def create_mcp_server(rates: DemoRates) -> MCPServer:
    server = MCPServer("currency-mcp", version="0.1.0")

    @server.tool()
    async def convert_currency(
        amount: Decimal, from_currency: str, to_currency: str
    ) -> dict[str, str]:
        """Convert using fixed demonstration rates. Results are NOT live FX."""
        return rates.convert(amount, from_currency, to_currency)

    @server.tool()
    async def get_demo_rates() -> dict[str, object]:
        """Return the versioned fixed demonstration rates, explicitly NOT live FX."""
        return rates.metadata()

    return server


class CurrencyApp:
    def __init__(self, mcp_app: ASGIApp, bearer_token: str) -> None:
        if not bearer_token:
            raise ValueError("A non-empty currency MCP bearer token is required")
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


def create_app(settings: Settings, rates: DemoRates | None = None) -> ASGIApp:
    server = create_mcp_server(rates or load_rates())
    mcp_app = server.streamable_http_app(
        stateless_http=True,
        transport_security=TransportSecuritySettings(allowed_hosts=list(settings.allowed_hosts)),
    )
    return CurrencyApp(mcp_app, settings.bearer_token)


def main() -> None:
    uvicorn.run(create_app(Settings.from_env()), host="0.0.0.0", port=8000)
