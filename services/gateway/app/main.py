from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
import uvicorn

from app.api.auth import create_auth_router
from app.database import make_engine, make_session_factory
from app.settings import AppSettings


def create_app(settings: AppSettings | None = None) -> FastAPI:
    config = settings or AppSettings.from_env()
    engine = make_engine(config.database_url)
    sessions = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        await engine.dispose()

    app = FastAPI(title="Team MCP Gateway", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.sessions = sessions
    app.state.settings = config
    app.include_router(create_auth_router(config))

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz() -> dict[str, str]:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


def run() -> None:
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
