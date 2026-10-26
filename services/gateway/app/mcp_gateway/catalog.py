from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Callable
from uuid import UUID

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from mcp.types import Tool
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.mcp_gateway.adapter import UpstreamAdapter, UpstreamConfig, UpstreamError
from app.mcp_gateway.aliases import public_alias
from app.mcp_gateway.permissions import PermissionPolicy
from app.models import Upstream, UpstreamTool
from app.security.upstream_crypto import CredentialCipher


@dataclass(frozen=True)
class CachedTool:
    public_alias: str
    original_name: str
    upstream_id: UUID
    upstream_slug: str
    description: str | None
    input_schema: dict
    output_schema: dict | None
    annotations: dict | None


AdapterFactory = Callable[[UpstreamConfig, str | None], UpstreamAdapter]
logger = logging.getLogger(__name__)


class CatalogService:
    """Single-replica catalog refresher; PostgreSQL remains authoritative."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        cipher: CredentialCipher,
        *,
        refresh_seconds: int = 30,
        max_parallel_refreshes: int = 4,
        adapter_factory: AdapterFactory = UpstreamAdapter,
    ) -> None:
        self._sessions = sessions
        self._cipher = cipher
        self._refresh_seconds = refresh_seconds
        self._refresh_limit = asyncio.Semaphore(max_parallel_refreshes)
        self._adapter_factory = adapter_factory
        self._permissions = PermissionPolicy()
        self._queue: asyncio.Queue[UUID] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def request_refresh(self, upstream_id: UUID) -> None:
        self._queue.put_nowait(upstream_id)

    async def _run(self) -> None:
        while True:
            try:
                try:
                    upstream_id = await asyncio.wait_for(
                        self._queue.get(), timeout=self._refresh_seconds
                    )
                except TimeoutError:
                    await self.refresh_all()
                else:
                    await self.refresh_upstream(upstream_id)
            except Exception:
                logger.exception("Catalog refresh iteration failed; refresher will continue")
                await asyncio.sleep(min(1, self._refresh_seconds))

    async def refresh_all(self) -> None:
        async with self._sessions() as db:
            ids = list(await db.scalars(select(Upstream.id).where(Upstream.enabled.is_(True))))
        await asyncio.gather(*(self.refresh_upstream(upstream_id) for upstream_id in ids))

    async def refresh_upstream(self, upstream_id: UUID) -> None:
        async with self._refresh_limit:
            snapshot = await self._load_snapshot(upstream_id)
            if snapshot is None or not snapshot["enabled"]:
                return
            try:
                credential = (
                    self._cipher.decrypt(snapshot["credential_ciphertext"])
                    if snapshot["credential_ciphertext"] else None
                )
                adapter = self._adapter_factory(
                    UpstreamConfig(
                        url=snapshot["url"], auth_type=snapshot["auth_type"],
                        auth_header=snapshot["auth_header"],
                        connect_timeout_ms=snapshot["connect_timeout_ms"],
                        call_timeout_ms=snapshot["call_timeout_ms"],
                    ), credential,
                )
                tools = await adapter.list_tools()
                rows = self._validated_rows(snapshot["slug"], tools)
            except (UpstreamError, ValueError, SchemaError) as error:
                await self._record_failure(upstream_id, snapshot["updated_at"], error)
                return
            await self._store_success(upstream_id, snapshot["updated_at"], rows)

    async def _load_snapshot(self, upstream_id: UUID) -> dict | None:
        async with self._sessions() as db:
            upstream = await db.scalar(select(Upstream).where(Upstream.id == upstream_id))
            if upstream is None:
                return None
            return {
                field: getattr(upstream, field) for field in (
                    "slug", "url", "auth_type", "auth_header", "credential_ciphertext",
                    "enabled", "connect_timeout_ms", "call_timeout_ms", "updated_at",
                )
            }

    @staticmethod
    def _validated_rows(slug: str, tools: list[Tool]) -> list[dict]:
        rows: list[dict] = []
        seen: set[str] = set()
        for tool in tools:
            alias = public_alias(slug, tool.name)
            if tool.name in seen:
                raise ValueError("upstream returned duplicate tool names")
            seen.add(tool.name)
            Draft202012Validator.check_schema(tool.input_schema)
            if tool.output_schema is not None:
                Draft202012Validator.check_schema(tool.output_schema)
            annotations = (
                tool.annotations.model_dump(by_alias=True, exclude_none=True)
                if tool.annotations else None
            )
            definition = {
                "name": tool.name, "description": tool.description,
                "inputSchema": tool.input_schema, "outputSchema": tool.output_schema,
                "annotations": annotations,
            }
            rows.append({
                "original_name": tool.name, "public_alias": alias,
                "description": tool.description, "input_schema": tool.input_schema,
                "output_schema": tool.output_schema, "annotations": annotations,
                "definition_hash": hashlib.sha256(json.dumps(
                    definition, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                ).encode()).hexdigest(),
            })
        return rows

    async def _store_success(self, upstream_id: UUID, expected_updated_at: datetime, rows: list[dict]) -> None:
        async with self._sessions() as db:
            upstream = await db.scalar(
                select(Upstream).where(Upstream.id == upstream_id).with_for_update()
            )
            if upstream is None or not upstream.enabled or upstream.updated_at != expected_updated_at:
                return
            await db.execute(delete(UpstreamTool).where(UpstreamTool.upstream_id == upstream_id))
            for row in rows:
                db.add(UpstreamTool(upstream_id=upstream_id, **row))
            upstream.status = "connected"
            upstream.last_checked_at = datetime.now(timezone.utc)
            upstream.last_error = None
            await db.commit()

    async def _record_failure(
        self, upstream_id: UUID, expected_updated_at: datetime, error: Exception,
    ) -> None:
        async with self._sessions() as db:
            upstream = await db.scalar(
                select(Upstream).where(Upstream.id == upstream_id).with_for_update()
            )
            if upstream is None or not upstream.enabled or upstream.updated_at != expected_updated_at:
                return
            upstream.status = "unreachable"
            upstream.last_checked_at = datetime.now(timezone.utc)
            upstream.last_error = self._safe_error(error)
            await db.commit()

    @staticmethod
    def _safe_error(error: Exception) -> str:
        if isinstance(error, UpstreamError):
            return str(error)[:240]
        return "Upstream tool catalog is invalid"

    async def list_tools(self, db: AsyncSession, actor: object | None = None) -> list[CachedTool]:
        rows = (await db.execute(
            select(UpstreamTool, Upstream.slug)
            .join(Upstream, Upstream.id == UpstreamTool.upstream_id)
            .where(Upstream.enabled.is_(True))
            .order_by(UpstreamTool.public_alias)
        )).all()
        role = getattr(actor, "role", None)
        overrides = await self._permissions.overrides(db, role) if role else {}
        permitted = []
        for tool, slug in rows:
            if role:
                allowed = overrides.get(
                    (tool.upstream_id, tool.original_name),
                    self._permissions.default_allowed(role, tool.original_name, tool.annotations),
                )
                if not allowed:
                    continue
            permitted.append((tool, slug))
        return [CachedTool(
            public_alias=tool.public_alias, original_name=tool.original_name,
            upstream_id=tool.upstream_id, upstream_slug=slug,
            description=tool.description, input_schema=tool.input_schema,
            output_schema=tool.output_schema, annotations=tool.annotations,
        ) for tool, slug in permitted]
