from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey, Invite, User, WebSession
from app.security.permissions import database, require_admin, require_same_origin
from app.security.web_sessions import SessionActor, hash_password, session_digest


class InviteCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: Literal["admin", "member"] = "member"


class InviteResponse(BaseModel):
    id: UUID
    email: str
    role: str
    invite_url: str
    expires_at: datetime


class InviteAccept(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=256)


class MemberResponse(BaseModel):
    id: UUID
    email: str
    role: str
    active: bool
    created_at: datetime


class MemberUpdate(BaseModel):
    role: Literal["admin", "member"] | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> MemberUpdate:
        if self.role is None and self.active is None:
            raise ValueError("role or active is required")
        return self


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    local, separator, domain = email.partition("@")
    if not separator or not local or not domain or " " in email or len(email) > 320:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid email")
    return email


def member_response(user: User) -> MemberResponse:
    return MemberResponse(
        id=user.id, email=user.email, role=user.role,
        active=user.active, created_at=user.created_at,
    )


def create_team_router() -> APIRouter:
    router = APIRouter()

    @router.post("/api/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
    async def create_invite(
        payload: InviteCreate, request: Request,
        db: AsyncSession = Depends(database), admin: SessionActor = Depends(require_admin),
    ) -> InviteResponse:
        require_same_origin(request)
        email = normalize_email(payload.email)
        if await db.scalar(select(User.id).where(func.lower(User.email) == email)) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=request.app.state.settings.invite_ttl_seconds
        )
        invite = Invite(
            email=email, role=payload.role, token_digest=session_digest(token),
            expires_at=expires_at, created_by=admin.id,
        )
        db.add(invite)
        await db.commit()
        await db.refresh(invite)
        url = f"{request.app.state.settings.allowed_origin}/invite?token={quote(token)}"
        return InviteResponse(
            id=invite.id, email=invite.email, role=invite.role,
            invite_url=url, expires_at=invite.expires_at,
        )

    @router.post("/api/invites/accept", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
    async def accept_invite(
        payload: InviteAccept, db: AsyncSession = Depends(database),
    ) -> MemberResponse:
        now = datetime.now(timezone.utc)
        invite = await db.scalar(
            select(Invite).where(Invite.token_digest == session_digest(payload.token)).with_for_update()
        )
        if invite is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")
        if invite.accepted_at is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Invite has already been used")
        if invite.expires_at <= now:
            raise HTTPException(status.HTTP_410_GONE, "Invite has expired")
        if await db.scalar(select(User.id).where(func.lower(User.email) == invite.email.lower())) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")
        user = User(
            email=invite.email.lower(), password_hash=hash_password(payload.password),
            role=invite.role, active=True,
        )
        db.add(user)
        invite.accepted_at = now
        try:
            await db.commit()
        except IntegrityError as error:
            await db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, "A user with this email already exists"
            ) from error
        await db.refresh(user)
        return member_response(user)

    @router.get("/api/members", response_model=list[MemberResponse])
    async def list_members(
        db: AsyncSession = Depends(database), _admin: SessionActor = Depends(require_admin),
    ) -> list[MemberResponse]:
        users = (await db.scalars(select(User).order_by(User.created_at, User.email))).all()
        return [member_response(user) for user in users]

    @router.patch("/api/members/{member_id}", response_model=MemberResponse)
    async def update_member(
        member_id: UUID, payload: MemberUpdate, request: Request,
        db: AsyncSession = Depends(database), _admin: SessionActor = Depends(require_admin),
    ) -> MemberResponse:
        require_same_origin(request)
        user = await db.scalar(select(User).where(User.id == member_id).with_for_update())
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
        next_role = payload.role if payload.role is not None else user.role
        next_active = payload.active if payload.active is not None else user.active
        removes_active_admin = user.role == "admin" and user.active and (
            next_role != "admin" or not next_active
        )
        if removes_active_admin:
            active_admin_ids = (await db.scalars(
                select(User.id).where(User.role == "admin", User.active.is_(True)).with_for_update()
            )).all()
            if len(active_admin_ids) == 1:
                raise HTTPException(status.HTTP_409_CONFLICT, "The final active admin cannot be removed")
        was_active = user.active
        user.role = next_role
        user.active = next_active
        user.updated_at = datetime.now(timezone.utc)
        if was_active and not next_active:
            revoked_at = datetime.now(timezone.utc)
            await db.execute(update(WebSession).where(
                WebSession.user_id == user.id, WebSession.revoked_at.is_(None),
            ).values(revoked_at=revoked_at))
            await db.execute(update(ApiKey).where(
                ApiKey.user_id == user.id, ApiKey.revoked_at.is_(None),
            ).values(revoked_at=revoked_at))
        await db.commit()
        await db.refresh(user)
        return member_response(user)

    return router
