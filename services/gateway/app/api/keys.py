from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey
from app.security.api_keys import IssuedApiKey, issue_api_key
from app.security.permissions import current_actor, database, require_admin, require_same_origin
from app.security.web_sessions import SessionActor


class KeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class KeyMetadata(BaseModel):
    id: UUID
    user_id: UUID
    prefix: str
    name: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class IssuedKeyResponse(KeyMetadata):
    key: str


def metadata(record: ApiKey) -> KeyMetadata:
    return KeyMetadata(
        id=record.id, user_id=record.user_id, prefix=record.prefix, name=record.name,
        created_at=record.created_at, last_used_at=record.last_used_at,
        revoked_at=record.revoked_at,
    )


def issued_response(issued: IssuedApiKey) -> IssuedKeyResponse:
    return IssuedKeyResponse(**metadata(issued.record).model_dump(), key=issued.plaintext)


async def revoke_owned_key(
    db: AsyncSession, key_id: UUID, user_id: UUID,
) -> bool:
    record = await db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id))
    if record is None:
        return False
    if record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    return True


def create_keys_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/keys", response_model=list[KeyMetadata])
    async def list_own_keys(
        db: AsyncSession = Depends(database), actor: SessionActor = Depends(current_actor),
    ) -> list[KeyMetadata]:
        records = (await db.scalars(
            select(ApiKey).where(ApiKey.user_id == actor.id).order_by(ApiKey.created_at.desc())
        )).all()
        return [metadata(record) for record in records]

    @router.post("/api/keys", response_model=IssuedKeyResponse, status_code=status.HTTP_201_CREATED)
    async def create_own_key(
        payload: KeyCreate, request: Request, db: AsyncSession = Depends(database),
        actor: SessionActor = Depends(current_actor),
    ) -> IssuedKeyResponse:
        require_same_origin(request)
        issued = await issue_api_key(
            db, actor.id, payload.name.strip(), request.app.state.api_key_pepper,
        )
        if issued is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "User is inactive")
        return issued_response(issued)

    @router.delete("/api/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_own_key(
        key_id: UUID, request: Request, db: AsyncSession = Depends(database),
        actor: SessionActor = Depends(current_actor),
    ) -> Response:
        require_same_origin(request)
        if not await revoke_owned_key(db, key_id, actor.id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/api/members/{member_id}/keys", response_model=IssuedKeyResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_member_key(
        member_id: UUID, payload: KeyCreate, request: Request,
        db: AsyncSession = Depends(database), _admin: SessionActor = Depends(require_admin),
    ) -> IssuedKeyResponse:
        require_same_origin(request)
        issued = await issue_api_key(
            db, member_id, payload.name.strip(), request.app.state.api_key_pepper,
        )
        if issued is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Active member not found")
        return issued_response(issued)

    @router.delete("/api/members/{member_id}/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_member_key(
        member_id: UUID, key_id: UUID, request: Request,
        db: AsyncSession = Depends(database), _admin: SessionActor = Depends(require_admin),
    ) -> Response:
        require_same_origin(request)
        if not await revoke_owned_key(db, key_id, member_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
