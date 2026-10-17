from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Upstream, UpstreamTool
from app.security.permissions import current_actor, database, require_admin, require_same_origin
from app.security.url_policy import validate_upstream_url
from app.security.web_sessions import SessionActor


SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
HEADER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,63}$")


class ServerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=1, max_length=31)
    display_name: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=1, max_length=2048)
    auth_type: Literal["none", "bearer", "header"] = "none"
    auth_header: str | None = Field(default=None, max_length=64)
    credential: str | None = Field(default=None, max_length=4096)
    enabled: bool = True
    connect_timeout_ms: int = Field(default=3000, ge=100, le=30_000)
    call_timeout_ms: int = Field(default=20_000, ge=100, le=120_000)

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, value: str) -> str:
        if not SLUG_RE.fullmatch(value):
            raise ValueError("slug must match [a-z][a-z0-9-]{0,30}")
        return value

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("display_name must not be blank")
        return value

    @model_validator(mode="after")
    def valid_auth(self) -> ServerCreate:
        validate_auth_fields(self.auth_type, self.auth_header, self.credential, require_credential=True)
        return self


class ServerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    auth_type: Literal["none", "bearer", "header"] | None = None
    auth_header: str | None = Field(default=None, max_length=64)
    credential_action: Literal["keep", "set", "clear"] = "keep"
    credential: str | None = Field(default=None, max_length=4096)
    enabled: bool | None = None
    connect_timeout_ms: int | None = Field(default=None, ge=100, le=30_000)
    call_timeout_ms: int | None = Field(default=None, ge=100, le=120_000)

    @model_validator(mode="after")
    def valid_update(self) -> ServerUpdate:
        changed = self.model_fields_set - {"credential_action"}
        if not changed and self.credential_action == "keep":
            raise ValueError("at least one server field must change")
        if self.display_name is not None and not self.display_name.strip():
            raise ValueError("display_name must not be blank")
        if self.credential_action == "set" and not self.credential:
            raise ValueError("credential is required when credential_action is set")
        if self.credential_action != "set" and self.credential is not None:
            raise ValueError("credential is only accepted when credential_action is set")
        return self


class ServerResponse(BaseModel):
    id: UUID
    slug: str
    display_name: str
    url: str
    auth_type: str
    auth_header: str | None
    has_credential: bool
    enabled: bool
    status: str
    connect_timeout_ms: int
    call_timeout_ms: int
    tool_count: int
    last_checked_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


def validate_auth_fields(
    auth_type: str, auth_header: str | None, credential: str | None, *, require_credential: bool,
) -> None:
    if auth_type == "none":
        if auth_header is not None or credential is not None:
            raise ValueError("auth_type none cannot include a header or credential")
        return
    if require_credential and not credential:
        raise ValueError("authenticated upstreams require a credential")
    if auth_type == "bearer" and auth_header is not None:
        raise ValueError("bearer authentication uses the Authorization header")
    if auth_type == "header" and (not auth_header or not HEADER_RE.fullmatch(auth_header)):
        raise ValueError("custom-header authentication requires a valid header name")


async def response_for(db: AsyncSession, upstream: Upstream) -> ServerResponse:
    tool_count = await db.scalar(
        select(func.count()).select_from(UpstreamTool).where(UpstreamTool.upstream_id == upstream.id)
    )
    return ServerResponse(
        id=upstream.id, slug=upstream.slug, display_name=upstream.display_name,
        url=upstream.url, auth_type=upstream.auth_type, auth_header=upstream.auth_header,
        has_credential=upstream.credential_ciphertext is not None, enabled=upstream.enabled,
        status=upstream.status, connect_timeout_ms=upstream.connect_timeout_ms,
        call_timeout_ms=upstream.call_timeout_ms, tool_count=tool_count or 0,
        last_checked_at=upstream.last_checked_at, last_error=upstream.last_error,
        created_at=upstream.created_at, updated_at=upstream.updated_at,
    )


def create_servers_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/servers", response_model=list[ServerResponse])
    async def list_servers(
        db: AsyncSession = Depends(database), _actor: SessionActor = Depends(current_actor),
    ) -> list[ServerResponse]:
        rows = (await db.scalars(select(Upstream).order_by(Upstream.slug))).all()
        return [await response_for(db, upstream) for upstream in rows]

    @router.post("/api/servers", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
    async def create_server(
        payload: ServerCreate, request: Request, db: AsyncSession = Depends(database),
        _admin: SessionActor = Depends(require_admin),
    ) -> ServerResponse:
        require_same_origin(request)
        try:
            url = await validate_upstream_url(
                payload.url, request.app.state.settings.upstream_internal_allowlist,
            )
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
        upstream = Upstream(
            slug=payload.slug, display_name=payload.display_name, url=url,
            auth_type=payload.auth_type, auth_header=payload.auth_header,
            credential_ciphertext=(
                request.app.state.upstream_cipher.encrypt(payload.credential)
                if payload.credential is not None else None
            ),
            enabled=payload.enabled, status="checking" if payload.enabled else "disabled",
            connect_timeout_ms=payload.connect_timeout_ms,
            call_timeout_ms=payload.call_timeout_ms,
        )
        db.add(upstream)
        try:
            await db.commit()
        except IntegrityError as error:
            await db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Server slug already exists") from error
        await db.refresh(upstream)
        if upstream.enabled:
            request.app.state.catalog.request_refresh(upstream.id)
        return await response_for(db, upstream)

    @router.patch("/api/servers/{server_id}", response_model=ServerResponse)
    async def update_server(
        server_id: UUID, payload: ServerUpdate, request: Request,
        db: AsyncSession = Depends(database), _admin: SessionActor = Depends(require_admin),
    ) -> ServerResponse:
        require_same_origin(request)
        upstream = await db.scalar(select(Upstream).where(Upstream.id == server_id).with_for_update())
        if upstream is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Server not found")
        auth_type = payload.auth_type if payload.auth_type is not None else upstream.auth_type
        auth_header = payload.auth_header if "auth_header" in payload.model_fields_set else upstream.auth_header
        credential_present = upstream.credential_ciphertext is not None
        if payload.credential_action == "set":
            credential_present = True
        elif payload.credential_action == "clear":
            credential_present = False
        try:
            validate_auth_fields(auth_type, auth_header, "present" if credential_present else None, require_credential=True)
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
        if payload.url is not None:
            try:
                upstream.url = await validate_upstream_url(
                    payload.url, request.app.state.settings.upstream_internal_allowlist,
                )
            except ValueError as error:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
        if payload.display_name is not None:
            upstream.display_name = payload.display_name.strip()
        upstream.auth_type = auth_type
        upstream.auth_header = auth_header
        if payload.credential_action == "set":
            assert payload.credential is not None
            upstream.credential_ciphertext = request.app.state.upstream_cipher.encrypt(payload.credential)
        elif payload.credential_action == "clear":
            upstream.credential_ciphertext = None
        if payload.enabled is not None:
            upstream.enabled = payload.enabled
        if payload.connect_timeout_ms is not None:
            upstream.connect_timeout_ms = payload.connect_timeout_ms
        if payload.call_timeout_ms is not None:
            upstream.call_timeout_ms = payload.call_timeout_ms
        upstream.status = "checking" if upstream.enabled else "disabled"
        upstream.last_checked_at = None
        upstream.last_error = None
        upstream.updated_at = func.now()
        await db.commit()
        await db.refresh(upstream)
        if upstream.enabled:
            request.app.state.catalog.request_refresh(upstream.id)
        return await response_for(db, upstream)

    @router.delete("/api/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_server(
        server_id: UUID, request: Request, db: AsyncSession = Depends(database),
        _admin: SessionActor = Depends(require_admin),
    ) -> Response:
        require_same_origin(request)
        upstream = await db.scalar(select(Upstream).where(Upstream.id == server_id))
        if upstream is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Server not found")
        await db.delete(upstream)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
