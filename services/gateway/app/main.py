from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI
from sqlalchemy import text
import uvicorn

from app.api.auth import create_auth_router
from app.api.keys import create_keys_router
from app.api.servers import create_servers_router
from app.api.team import create_team_router
from app.database import make_engine, make_session_factory
from app.mcp_gateway.catalog import CatalogService
from app.mcp_gateway.endpoint import create_mcp_endpoint
from app.mcp_gateway.router import GatewayRouter
from app.settings import AppSettings
from app.security.mcp_auth import MCPApiKeyMiddleware
from app.security.upstream_crypto import CredentialCipher


def create_app(settings: AppSettings | None = None) -> FastAPI:
    config = settings or AppSettings.from_env()
    engine = make_engine(config.database_url)
    sessions = make_session_factory(engine)
    cipher = CredentialCipher(config.upstream_credential_key)
    catalog = CatalogService(
        sessions, cipher, refresh_seconds=config.upstream_refresh_seconds,
    )
    public_host = urlsplit(config.allowed_origin).netloc
    mcp_endpoint = create_mcp_endpoint(
        GatewayRouter(sessions, catalog, cipher),
        allowed_hosts=[
            public_host, "gateway:8000", "gateway.platform.svc.cluster.local:8000",
            "127.0.0.1:*", "localhost:*",
        ],
        allowed_origins=[config.allowed_origin],
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with mcp_endpoint.router.lifespan_context(mcp_endpoint):
            catalog.start()
            try:
                yield
            finally:
                await catalog.stop()
                await engine.dispose()

    app = FastAPI(title="Team MCP Gateway", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.sessions = sessions
    app.state.settings = config
    app.state.api_key_pepper = config.api_key_pepper.encode()
    app.state.upstream_cipher = cipher
    app.state.catalog = catalog
    app.include_router(create_auth_router(config))
    app.include_router(create_keys_router())
    app.include_router(create_servers_router())
    app.include_router(create_team_router())
    app.add_middleware(
        MCPApiKeyMiddleware, session_factory=sessions, pepper=config.api_key_pepper.encode(),
        internal_jwt_secret=config.internal_jwt_secret,
    )

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz() -> dict[str, str]:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.mount("/", mcp_endpoint)

    return app


def run() -> None:
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
