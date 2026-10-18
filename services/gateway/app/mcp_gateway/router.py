from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from mcp.shared.exceptions import MCPError
from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.mcp_gateway.adapter import (
    UpstreamAdapter, UpstreamConfig, UpstreamConnectionError, UpstreamError,
    UpstreamProtocolError, UpstreamResultTooLargeError, UpstreamTimeoutError,
)
from app.mcp_gateway.catalog import CatalogService
from app.mcp_gateway.auditing import AuditAttempt, AuditRecorder
from app.models import Upstream, UpstreamTool, User
from app.security.api_keys import ApiKeyActor
from app.security.upstream_crypto import CredentialCipher


class GatewayRouter:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], catalog: CatalogService,
        cipher: CredentialCipher, adapter_factory=UpstreamAdapter,
    ) -> None:
        self._sessions = sessions
        self._catalog = catalog
        self._cipher = cipher
        self._adapter_factory = adapter_factory
        self._audit = AuditRecorder(sessions)

    async def list_tools(self, actor: ApiKeyActor) -> list[Tool]:
        async with self._sessions() as db:
            user = await db.get(User, actor.id)
            if user is None or not user.active or user.role not in {"admin", "member"}:
                raise MCPError(-32600, "Actor is no longer authorized")
            cached = await self._catalog.list_tools(db, actor)
        return [Tool(
            name=item.public_alias,
            description=f"[{item.upstream_slug}] {item.description or item.original_name}",
            inputSchema=item.input_schema,
            outputSchema=item.output_schema,
            annotations=(
                ToolAnnotations.model_validate(item.annotations) if item.annotations else None
            ),
        ) for item in cached]

    async def call_tool(
        self, actor: ApiKeyActor, alias: str, arguments: dict[str, Any] | None,
    ) -> CallToolResult:
        audit = AuditAttempt(actor=actor, public_tool=alias)
        try:
            async with self._sessions() as db:
                user = await db.get(User, actor.id)
                if user is None or not user.active or user.role not in {"admin", "member"}:
                    audit.error_summary = "Actor is no longer authorized"
                    raise MCPError(-32600, "Actor is no longer authorized")
                row = (await db.execute(
                    select(UpstreamTool, Upstream)
                    .join(Upstream, Upstream.id == UpstreamTool.upstream_id)
                    .where(UpstreamTool.public_alias == alias)
                )).one_or_none()
                if row is None:
                    audit.error_summary = "Unknown tool alias"
                    raise MCPError(-32602, "Unknown tool alias")
                tool, upstream = row
                audit.server_slug = upstream.slug
                audit.original_tool = tool.original_name
                if not upstream.enabled:
                    audit.error_summary = "Tool upstream is disabled"
                    raise MCPError(-32602, "Tool upstream is disabled")
                if upstream.status == "unreachable":
                    audit.outcome = "upstream_error"
                    audit.error_summary = "Upstream is currently unreachable"
                    return self._error("Upstream is currently unreachable; call was not attempted.")
                try:
                    Draft202012Validator(tool.input_schema).validate(arguments or {})
                except ValidationError as error:
                    audit.error_summary = "Arguments do not match tool schema"
                    raise MCPError(-32602, "Arguments do not match tool schema") from error
                credential = (
                    self._cipher.decrypt(upstream.credential_ciphertext)
                    if upstream.credential_ciphertext else None
                )
                config = UpstreamConfig(
                    url=upstream.url, auth_type=upstream.auth_type,
                    auth_header=upstream.auth_header,
                    connect_timeout_ms=upstream.connect_timeout_ms,
                    call_timeout_ms=upstream.call_timeout_ms,
                )
                original_name = tool.original_name
            adapter = self._adapter_factory(config, credential)
            try:
                result = await adapter.call_tool(original_name, arguments or {})
                audit.outcome = "tool_error" if result.is_error else "ok"
                audit.error_summary = "Upstream tool returned an error" if result.is_error else None
                return result
            except UpstreamTimeoutError:
                audit.outcome = "timeout"
                audit.error_summary = "Upstream timed out"
                return self._error("Upstream timed out; call was not retried.")
            except (UpstreamConnectionError, UpstreamProtocolError):
                audit.outcome = "upstream_error"
                audit.error_summary = "Upstream is unavailable"
                return self._error("Upstream is unavailable; call was not retried.")
            except UpstreamResultTooLargeError:
                audit.outcome = "upstream_error"
                audit.error_summary = "Upstream result exceeded the configured size limit"
                return self._error("Upstream result exceeded the configured size limit.")
            except UpstreamError:
                audit.outcome = "upstream_error"
                audit.error_summary = "Upstream call failed"
                return self._error("Upstream call failed; call was not retried.")
        except MCPError:
            raise
        except Exception:
            audit.outcome = "upstream_error"
            audit.error_summary = "Gateway could not complete the upstream call"
            raise
        finally:
            await self._audit.record(audit)

    @staticmethod
    def _error(message: str) -> CallToolResult:
        return CallToolResult(isError=True, content=[TextContent(type="text", text=message)])
