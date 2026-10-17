from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from .database import Base


def uuid_pk() -> Mapped[UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)


def created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'member')", name="role"),
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )


class WebSession(Base):
    __tablename__ = "web_sessions"
    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_digest: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (CheckConstraint("role IN ('admin', 'member')", name="role"),)
    id: Mapped[UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(16))
    token_digest: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = created_at()


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    prefix: Mapped[str] = mapped_column(String(64), unique=True)
    key_digest: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = created_at()
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class Upstream(Base):
    __tablename__ = "upstreams"
    __table_args__ = (
        CheckConstraint("auth_type IN ('none', 'bearer', 'header')", name="auth_type"),
        CheckConstraint("status IN ('connected', 'unreachable', 'disabled', 'checking')", name="status"),
        CheckConstraint("connect_timeout_ms > 0", name="connect_timeout_positive"),
        CheckConstraint("call_timeout_ms > 0", name="call_timeout_positive"),
    )
    id: Mapped[UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(160))
    url: Mapped[str] = mapped_column(Text)
    auth_type: Mapped[str] = mapped_column(String(16), default="none", server_default="none")
    auth_header: Mapped[str | None] = mapped_column(String(120))
    credential_ciphertext: Mapped[bytes | None]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    status: Mapped[str] = mapped_column(String(16), default="checking", server_default="checking")
    connect_timeout_ms: Mapped[int] = mapped_column(Integer, default=3000, server_default="3000")
    call_timeout_ms: Mapped[int] = mapped_column(Integer, default=20000, server_default="20000")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UpstreamTool(Base):
    __tablename__ = "upstream_tools"
    __table_args__ = (UniqueConstraint("upstream_id", "original_name"),)
    id: Mapped[UUID] = uuid_pk()
    upstream_id: Mapped[UUID] = mapped_column(ForeignKey("upstreams.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    public_alias: Mapped[str] = mapped_column(String(340), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    annotations: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    definition_hash: Mapped[str] = mapped_column(String(128))
    discovered_at: Mapped[datetime] = created_at()


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("duration_ms >= 0", name="duration_nonnegative"),
        Index("ix_audit_events_user_started", "user_id", "started_at"),
        Index("ix_audit_events_server_started", "server_slug", "started_at"),
    )
    id: Mapped[UUID] = uuid_pk()
    request_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), unique=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    api_key_id: Mapped[UUID | None] = mapped_column(ForeignKey("api_keys.id", ondelete="SET NULL"))
    channel: Mapped[str] = mapped_column(String(32))
    server_slug: Mapped[str] = mapped_column(String(80))
    public_tool: Mapped[str] = mapped_column(String(340))
    original_tool: Mapped[str] = mapped_column(String(255))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration_ms: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(32))
    error_summary: Mapped[str | None] = mapped_column(Text)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant', 'tool', 'system')", name="role"),)
    id: Mapped[UUID] = uuid_pk()
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    tool_calls_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at()


class ToolPermission(Base):
    __tablename__ = "tool_permissions"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'member')", name="role"),
        UniqueConstraint("role", "upstream_id", "original_tool"),
    )
    id: Mapped[UUID] = uuid_pk()
    role: Mapped[str] = mapped_column(String(16))
    upstream_id: Mapped[UUID] = mapped_column(ForeignKey("upstreams.id", ondelete="CASCADE"), index=True)
    original_tool: Mapped[str] = mapped_column(String(255))
    allowed: Mapped[bool] = mapped_column(Boolean)
