from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.database import make_engine, make_session_factory
from app.models import Upstream, User


@pytest.fixture(scope="module")
def catalog_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for catalog tests")
    root = Path(__file__).parents[1]
    config = Config(root / "alembic.ini")
    config.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = url
    command.upgrade(config, "head")
    return url


@pytest_asyncio.fixture(autouse=True)
async def clean_catalog(catalog_database_url: str):
    engine = make_engine(catalog_database_url)
    sessions = make_session_factory(engine)
    async with sessions() as db:
        await db.execute(delete(Upstream))
        await db.execute(delete(User))
        await db.commit()
    await engine.dispose()
