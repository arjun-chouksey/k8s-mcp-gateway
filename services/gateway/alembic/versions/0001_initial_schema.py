"""Create the platform persistence schema."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def identity_columns() -> list[sa.Column]:
    return [sa.Column("id", UUID, primary_key=True, nullable=False)]


def upgrade() -> None:
    op.create_table(
        "users", *identity_columns(), sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False), sa.Column("role", sa.String(16), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_users_role"),
    )
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "web_sessions", *identity_columns(), sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_digest", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", TZ, nullable=False), sa.Column("revoked_at", TZ),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_web_sessions_user_id", "web_sessions", ["user_id"])
    op.create_index("ix_web_sessions_expires_at", "web_sessions", ["expires_at"])

    op.create_table(
        "invites", *identity_columns(), sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(16), nullable=False), sa.Column("token_digest", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", TZ, nullable=False), sa.Column("accepted_at", TZ),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_invites_role"),
    )
    op.create_index("ix_invites_expires_at", "invites", ["expires_at"])
    op.create_index("ix_invites_created_by", "invites", ["created_by"])

    op.create_table(
        "api_keys", *identity_columns(), sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prefix", sa.String(64), nullable=False, unique=True),
        sa.Column("key_digest", sa.String(128), nullable=False, unique=True), sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", TZ), sa.Column("revoked_at", TZ),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_revoked_at", "api_keys", ["revoked_at"])

    op.create_table(
        "upstreams", *identity_columns(), sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(160), nullable=False), sa.Column("url", sa.Text(), nullable=False),
        sa.Column("auth_type", sa.String(16), server_default="none", nullable=False),
        sa.Column("auth_header", sa.String(120)), sa.Column("credential_ciphertext", sa.LargeBinary()),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("status", sa.String(16), server_default="checking", nullable=False),
        sa.Column("connect_timeout_ms", sa.Integer(), server_default="3000", nullable=False),
        sa.Column("call_timeout_ms", sa.Integer(), server_default="20000", nullable=False),
        sa.Column("last_checked_at", TZ), sa.Column("last_error", sa.Text()),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("auth_type IN ('none', 'bearer', 'header')", name="ck_upstreams_auth_type"),
        sa.CheckConstraint("status IN ('connected', 'unreachable', 'disabled', 'checking')", name="ck_upstreams_status"),
        sa.CheckConstraint("connect_timeout_ms > 0", name="ck_upstreams_connect_timeout_positive"),
        sa.CheckConstraint("call_timeout_ms > 0", name="ck_upstreams_call_timeout_positive"),
    )
    op.create_index("ix_upstreams_enabled", "upstreams", ["enabled"])

    op.create_table(
        "upstream_tools", *identity_columns(), sa.Column("upstream_id", UUID, sa.ForeignKey("upstreams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False), sa.Column("public_alias", sa.String(340), nullable=False, unique=True),
        sa.Column("description", sa.Text()), sa.Column("input_schema", postgresql.JSONB(), nullable=False),
        sa.Column("output_schema", postgresql.JSONB()), sa.Column("annotations", postgresql.JSONB()),
        sa.Column("definition_hash", sa.String(128), nullable=False),
        sa.Column("discovered_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("upstream_id", "original_name", name="uq_upstream_tools_upstream_name"),
    )
    op.create_index("ix_upstream_tools_upstream_id", "upstream_tools", ["upstream_id"])

    op.create_table(
        "audit_events", *identity_columns(), sa.Column("request_id", UUID, nullable=False, unique=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("api_key_id", UUID, sa.ForeignKey("api_keys.id", ondelete="SET NULL")),
        sa.Column("channel", sa.String(32), nullable=False), sa.Column("server_slug", sa.String(80), nullable=False),
        sa.Column("public_tool", sa.String(340), nullable=False), sa.Column("original_tool", sa.String(255), nullable=False),
        sa.Column("started_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False), sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("error_summary", sa.Text()),
        sa.CheckConstraint("duration_ms >= 0", name="ck_audit_events_duration_nonnegative"),
    )
    op.create_index("ix_audit_events_user_started", "audit_events", ["user_id", "started_at"])
    op.create_index("ix_audit_events_server_started", "audit_events", ["server_slug", "started_at"])

    op.create_table(
        "conversations", *identity_columns(), sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TZ, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages", *identity_columns(), sa.Column("conversation_id", UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False), sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tool_calls_json", postgresql.JSONB()),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'tool', 'system')", name="ck_messages_role"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "tool_permissions", *identity_columns(), sa.Column("role", sa.String(16), nullable=False),
        sa.Column("upstream_id", UUID, sa.ForeignKey("upstreams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_tool", sa.String(255), nullable=False), sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_tool_permissions_role"),
        sa.UniqueConstraint("role", "upstream_id", "original_tool", name="uq_tool_permissions_role_upstream_tool"),
    )
    op.create_index("ix_tool_permissions_upstream_id", "tool_permissions", ["upstream_id"])


def downgrade() -> None:
    for table in (
        "tool_permissions", "messages", "conversations", "audit_events", "upstream_tools",
        "upstreams", "api_keys", "invites", "web_sessions", "users",
    ):
        op.drop_table(table)
