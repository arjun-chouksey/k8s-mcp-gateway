from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import uvicorn

from app.api.auth import create_auth_router
from app.api.audit import create_audit_router
from app.api.chat import create_chat_router
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
from app.chat.agent import ChatAgent


def create_app(settings: AppSettings | None = None) -> FastAPI:
    config = settings or AppSettings.from_env()
    engine = make_engine(config.database_url)
    sessions = make_session_factory(engine)
    cipher = CredentialCipher(config.upstream_credential_key)
    catalog = CatalogService(
        sessions, cipher, refresh_seconds=config.upstream_refresh_seconds,
    )
    migration_root = Path(__file__).resolve().parents[1]
    migration_config = Config(str(migration_root / "alembic.ini"))
    migration_config.set_main_option("script_location", str(migration_root / "alembic"))
    migration_heads = set(ScriptDirectory.from_config(migration_config).get_heads())
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
    app.state.chat_agent = ChatAgent(sessions, config)
    app.include_router(create_auth_router(config))
    app.include_router(create_audit_router())
    app.include_router(create_chat_router())
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
        try:
            async with engine.connect() as connection:
                versions = set((await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )).scalars())
        except SQLAlchemyError as error:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Database schema is not ready"
            ) from error
        if versions != migration_heads:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Database schema is not current"
            )
        return {"status": "ok"}

    app.mount("/", mcp_endpoint)

    return app


def run() -> None:
    settings = AppSettings.from_env()
    uvicorn.run(
        create_app(settings), host="0.0.0.0", port=8000,
        proxy_headers=True, forwarded_allow_ips=settings.forwarded_allow_ips,
    )


if __name__ == "__main__":
    run()
