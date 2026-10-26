from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ToolPermission


MEMBER_WRITE_TOOLS = frozenset({"create_product", "update_order_status"})


class PermissionPolicy:
    """Resolve explicit role overrides before applying the documented defaults."""

    @staticmethod
    def default_allowed(role: str, original_tool: str, annotations: dict | None) -> bool:
        if role == "admin":
            return True
        if role != "member":
            return False
        if (annotations or {}).get("readOnlyHint") is False:
            return False
        return original_tool not in MEMBER_WRITE_TOOLS

    async def is_allowed(
        self,
        db: AsyncSession,
        *,
        role: str,
        upstream_id: UUID,
        original_tool: str,
        annotations: dict | None,
    ) -> bool:
        override = await db.scalar(select(ToolPermission).where(
            ToolPermission.role == role,
            ToolPermission.upstream_id == upstream_id,
            ToolPermission.original_tool == original_tool,
        ))
        if override is not None:
            return override.allowed
        return self.default_allowed(role, original_tool, annotations)

    async def overrides(
        self, db: AsyncSession, role: str,
    ) -> dict[tuple[UUID, str], bool]:
        rows = (await db.scalars(
            select(ToolPermission).where(ToolPermission.role == role)
        )).all()
        return {(row.upstream_id, row.original_tool): row.allowed for row in rows}
