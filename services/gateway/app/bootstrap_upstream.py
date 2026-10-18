from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy import select

from app.database import make_engine, make_session_factory
from app.models import Upstream
from app.security.upstream_crypto import CredentialCipher
from app.settings import DatabaseSettings


@dataclass(frozen=True)
class UpstreamSeed:
    slug: str
    display_name: str
    url: str
    credential: str
    connect_timeout_ms: int = 3000
    call_timeout_ms: int = 20_000


async def seed_upstream(
    database_url: str, encryption_key: str, seed: UpstreamSeed,
) -> str:
    parsed = urlsplit(seed.url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("bootstrap upstream URL must be absolute HTTP(S)")
    if not seed.credential:
        raise ValueError("bootstrap upstream credential is required")
    engine = make_engine(database_url)
    sessions = make_session_factory(engine)
    try:
        async with sessions() as db:
            existing = await db.scalar(select(Upstream).where(Upstream.slug == seed.slug))
            if existing is not None:
                return "existing-upstream-preserved"
            db.add(Upstream(
                slug=seed.slug, display_name=seed.display_name, url=seed.url,
                auth_type="bearer",
                credential_ciphertext=CredentialCipher(encryption_key).encrypt(seed.credential),
                enabled=True, status="checking",
                connect_timeout_ms=seed.connect_timeout_ms,
                call_timeout_ms=seed.call_timeout_ms,
            ))
            await db.commit()
            return "upstream-created"
    finally:
        await engine.dispose()


def main() -> None:
    seed = UpstreamSeed(
        slug=os.getenv("BOOTSTRAP_UPSTREAM_SLUG", "woo"),
        display_name=os.getenv("BOOTSTRAP_UPSTREAM_DISPLAY_NAME", "WooCommerce"),
        url=os.getenv("BOOTSTRAP_UPSTREAM_URL", ""),
        credential=os.getenv("BOOTSTRAP_UPSTREAM_CREDENTIAL", ""),
        connect_timeout_ms=int(os.getenv("BOOTSTRAP_UPSTREAM_CONNECT_TIMEOUT_MS", "3000")),
        call_timeout_ms=int(os.getenv("BOOTSTRAP_UPSTREAM_CALL_TIMEOUT_MS", "20000")),
    )
    result = asyncio.run(seed_upstream(
        DatabaseSettings.from_env().url,
        os.getenv("UPSTREAM_CREDENTIAL_KEY", ""),
        seed,
    ))
    print(result)


if __name__ == "__main__":
    main()
