from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


EXPECTED_TABLES = {
    "alembic_version", "users", "web_sessions", "invites", "api_keys", "upstreams",
    "upstream_tools", "audit_events", "conversations", "messages", "tool_permissions",
}


def alembic_config(url: str) -> Config:
    root = Path(__file__).parents[1]
    config = Config(root / "alembic.ini")
    config.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = url
    return config


@pytest.fixture(scope="module")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    return url


def test_upgrade_head_is_repeatable_and_schema_is_complete(database_url: str):
    config = alembic_config(database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert EXPECTED_TABLES == set(inspector.get_table_names())
    assert {"user_id", "started_at"} <= {
        column for index in inspector.get_indexes("audit_events")
        for column in index["column_names"]
    }
    assert {"server_slug", "started_at"} <= {
        column for index in inspector.get_indexes("audit_events")
        for column in index["column_names"]
    }
    assert "credential_ciphertext" in {column["name"] for column in inspector.get_columns("upstreams")}
    assert "credential" not in {column["name"] for column in inspector.get_columns("upstreams")}
    engine.dispose()


def test_constraints_reject_invalid_role_and_case_insensitive_duplicate_email(database_url: str):
    engine = create_engine(database_url)
    with engine.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(text(
                "INSERT INTO users (id,email,password_hash,role) VALUES (:id,'bad@example.com','hash','owner')"
            ), {"id": uuid4()})
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (id,email,password_hash,role) VALUES (:id,'Case@Example.com','hash','member')"
        ), {"id": uuid4()})
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (id,email,password_hash,role) VALUES (:id,'case@example.com','hash','member')"
        ), {"id": uuid4()})
    engine.dispose()
