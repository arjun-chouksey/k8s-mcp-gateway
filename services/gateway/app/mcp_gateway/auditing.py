from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ApiKey, AuditEvent, User
from app.security.api_keys import ApiKeyActor


logger = logging.getLogger(__name__)


@dataclass
class AuditAttempt:
    actor: ApiKeyActor
    public_tool: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _started_monotonic: float = field(default_factory=time.monotonic)
    server_slug: str = "unknown"
    original_tool: str = "unknown"
    outcome: str = "denied"
    error_summary: str | None = None

    @property
    def duration_ms(self) -> int:
        return max(0, round((time.monotonic() - self._started_monotonic) * 1000))


class AuditRecorder:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(self, attempt: AuditAttempt) -> bool:
        """Persist one sanitized event without reusing the tool-call transaction."""
        try:
            async with self._sessions() as db:
                user_id = attempt.actor.id if await db.get(User, attempt.actor.id) else None
                api_key_id = (
                    attempt.actor.key_id
                    if attempt.actor.key_id is not None
                    and await db.get(ApiKey, attempt.actor.key_id) is not None
                    else None
                )
                db.add(AuditEvent(
                    request_id=uuid4(), user_id=user_id, api_key_id=api_key_id,
                    channel=attempt.actor.channel[:32],
                    server_slug=attempt.server_slug[:80],
                    public_tool=attempt.public_tool[:340],
                    original_tool=attempt.original_tool[:255],
                    started_at=attempt.started_at, duration_ms=attempt.duration_ms,
                    outcome=attempt.outcome, error_summary=attempt.error_summary,
                ))
                await db.commit()
            return True
        except Exception:
            logger.exception("Failed to persist tool-call audit event")
            return False
