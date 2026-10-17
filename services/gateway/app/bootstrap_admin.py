from __future__ import annotations

import asyncio
import os

from sqlalchemy import func, select

from app.database import make_engine, make_session_factory
from app.models import User
from app.security.web_sessions import hash_password
from app.settings import DatabaseSettings


async def bootstrap_admin(email: str, password: str, database_url: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or len(normalized) > 320:
        raise ValueError("bootstrap admin email is invalid")
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    try:
        async with sessions() as db:
            existing_admin = await db.scalar(select(User).where(User.role == "admin"))
            if existing_admin is not None:
                return "existing-admin-preserved"
            existing_email = await db.scalar(select(User).where(func.lower(User.email) == normalized))
            if existing_email is not None:
                raise RuntimeError("bootstrap email already belongs to a non-admin user")
            db.add(User(email=normalized, password_hash=hash_password(password), role="admin", active=True))
            await db.commit()
            return "admin-created"
    finally:
        await engine.dispose()


def main() -> None:
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "")
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    result = asyncio.run(bootstrap_admin(email, password, DatabaseSettings.from_env().url))
    print(result)


if __name__ == "__main__":
    main()
