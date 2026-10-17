from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey, User


KEY_PREFIX_RE = re.compile(r"^[a-f0-9]{12}$")


@dataclass(frozen=True)
class ApiKeyActor:
    id: UUID
    email: str
    role: str
    key_id: UUID | None
    channel: str


@dataclass(frozen=True)
class IssuedApiKey:
    record: ApiKey
    plaintext: str


def api_key_digest(plaintext: str, pepper: bytes) -> str:
    return hmac.new(pepper, plaintext.encode(), hashlib.sha256).hexdigest()


def parse_public_prefix(plaintext: str) -> str | None:
    parts = plaintext.split("_", 2)
    if len(parts) != 3 or parts[0] != "mcpgw" or not KEY_PREFIX_RE.fullmatch(parts[1]):
        return None
    if len(parts[2]) < 43 or len(plaintext) > 256:
        return None
    return parts[1]


async def issue_api_key(
    db: AsyncSession, user_id: UUID, name: str, pepper: bytes,
) -> IssuedApiKey | None:
    user = await db.scalar(select(User).where(User.id == user_id, User.active.is_(True)))
    if user is None:
        return None
    prefix = secrets.token_hex(6)
    plaintext = f"mcpgw_{prefix}_{secrets.token_urlsafe(32)}"
    record = ApiKey(
        user_id=user.id, prefix=prefix, key_digest=api_key_digest(plaintext, pepper), name=name,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return IssuedApiKey(record=record, plaintext=plaintext)


async def authenticate_api_key(
    db: AsyncSession, plaintext: str, pepper: bytes,
) -> ApiKeyActor | None:
    prefix = parse_public_prefix(plaintext)
    record = None
    user = None
    if prefix is not None:
        row = (await db.execute(
            select(ApiKey, User).join(User, User.id == ApiKey.user_id).where(ApiKey.prefix == prefix)
        )).one_or_none()
        if row is not None:
            record, user = row
    candidate = api_key_digest(plaintext, pepper)
    expected = record.key_digest if record is not None else "0" * 64
    digest_matches = hmac.compare_digest(candidate, expected)
    if (
        not digest_matches or record is None or user is None
        or record.revoked_at is not None or not user.active
    ):
        return None
    record.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiKeyActor(
        id=user.id, email=user.email, role=user.role, key_id=record.id, channel="mcp",
    )
