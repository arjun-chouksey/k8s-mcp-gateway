from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent
from app.security.permissions import current_actor, database
from app.security.web_sessions import SessionActor


AuditOutcome = Literal["ok", "tool_error", "upstream_error", "timeout", "denied"]


class AuditEventResponse(BaseModel):
    id: UUID
    request_id: UUID
    user_id: UUID | None
    api_key_id: UUID | None
    channel: str
    server_slug: str
    public_tool: str
    original_tool: str
    started_at: datetime
    duration_ms: int
    outcome: str
    error_summary: str | None


class AuditPage(BaseModel):
    items: list[AuditEventResponse]
    total: int
    limit: int
    offset: int


def create_audit_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/audit", response_model=AuditPage)
    async def list_audit(
        server: str | None = Query(default=None, max_length=80),
        outcome: AuditOutcome | None = None,
        started_after: datetime | None = None,
        started_before: datetime | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        db: AsyncSession = Depends(database),
        actor: SessionActor = Depends(current_actor),
    ) -> AuditPage:
        if started_after and started_before and started_after > started_before:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "started_after must not be later than started_before",
            )
        filters = []
        if actor.role != "admin":
            filters.append(AuditEvent.user_id == actor.id)
        if server:
            filters.append(AuditEvent.server_slug == server)
        if outcome:
            filters.append(AuditEvent.outcome == outcome)
        if started_after:
            filters.append(AuditEvent.started_at >= started_after)
        if started_before:
            filters.append(AuditEvent.started_at <= started_before)

        total = await db.scalar(select(func.count()).select_from(AuditEvent).where(*filters))
        rows = (await db.scalars(
            select(AuditEvent).where(*filters)
            .order_by(AuditEvent.started_at.desc(), AuditEvent.id.desc())
            .limit(limit).offset(offset)
        )).all()
        return AuditPage(
            items=[AuditEventResponse.model_validate(row, from_attributes=True) for row in rows],
            total=total or 0, limit=limit, offset=offset,
        )

    return router
