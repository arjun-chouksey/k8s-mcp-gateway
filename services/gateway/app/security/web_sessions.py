from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, WebSession


PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65_536, parallelism=4)
DUMMY_HASH = PASSWORD_HASHER.hash("not-a-real-password-for-timing-only")
SESSION_COOKIE = "mcpgw_session"


def hash_password(password: str) -> str:
    if len(password) < 12 or len(password) > 256:
        raise ValueError("password must be between 12 and 256 characters")
    return PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def session_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class SessionActor:
    id: UUID
    email: str
    role: str


@dataclass(frozen=True)
class CreatedSession:
    token: str
    expires_at: datetime
    actor: SessionActor


class LoginThrottle:
    def __init__(self, max_failures: int, window_seconds: int) -> None:
        self._max_failures = max_failures
        self._window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def blocked(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            failures = self._failures[key]
            while failures and now - failures[0] >= self._window:
                failures.popleft()
            return len(failures) >= self._max_failures

    def failure(self, key: str) -> None:
        with self._lock:
            self._failures[key].append(time.monotonic())

    def success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


async def create_session(
    db: AsyncSession, email: str, password: str, ttl_seconds: int
) -> CreatedSession | None:
    result = await db.execute(select(User).where(func.lower(User.email) == email.strip().lower()))
    user = result.scalar_one_or_none()
    stored_hash = user.password_hash if user else DUMMY_HASH
    valid = verify_password(stored_hash, password)
    if user is None or not valid or not user.active:
        return None
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    db.add(WebSession(
        id=uuid4(), user_id=user.id, session_digest=session_digest(token),
        expires_at=expires_at,
    ))
    await db.commit()
    return CreatedSession(token, expires_at, SessionActor(user.id, user.email, user.role))


async def resolve_session(db: AsyncSession, token: str | None) -> SessionActor | None:
    if not token:
        return None
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(User).join(WebSession, WebSession.user_id == User.id).where(
            WebSession.session_digest == session_digest(token),
            WebSession.revoked_at.is_(None), WebSession.expires_at > now, User.active.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    return None if user is None else SessionActor(user.id, user.email, user.role)


async def revoke_session(db: AsyncSession, token: str) -> bool:
    result = await db.execute(
        update(WebSession).where(
            WebSession.session_digest == session_digest(token), WebSession.revoked_at.is_(None)
        ).values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return bool(result.rowcount)
