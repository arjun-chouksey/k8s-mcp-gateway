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
        async with self._sessions() as db:
            user = await db.get(User, actor.id)
            if user is None or not user.active or user.role not in {"admin", "member"}:
                raise MCPError(-32600, "Actor is no longer authorized")
            row = (await db.execute(
                select(UpstreamTool, Upstream)
                .join(Upstream, Upstream.id == UpstreamTool.upstream_id)
                .where(UpstreamTool.public_alias == alias)
            )).one_or_none()
            if row is None:
                raise MCPError(-32602, "Unknown tool alias")
            tool, upstream = row
            if not upstream.enabled:
                raise MCPError(-32602, "Tool upstream is disabled")
            if upstream.status == "unreachable":
                return self._error("Upstream is currently unreachable; call was not attempted.")
            try:
                Draft202012Validator(tool.input_schema).validate(arguments or {})
            except ValidationError as error:
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
            return await adapter.call_tool(original_name, arguments or {})
        except UpstreamTimeoutError:
            return self._error("Upstream timed out; call was not retried.")
        except (UpstreamConnectionError, UpstreamProtocolError):
            return self._error("Upstream is unavailable; call was not retried.")
        except UpstreamResultTooLargeError:
            return self._error("Upstream result exceeded the configured size limit.")
        except UpstreamError:
            return self._error("Upstream call failed; call was not retried.")

    @staticmethod
    def _error(message: str) -> CallToolResult:
        return CallToolResult(isError=True, content=[TextContent(type="text", text=message)])
