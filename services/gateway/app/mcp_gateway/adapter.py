from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError
from mcp.types import CallToolResult, Tool


class UpstreamError(Exception):
    """A safe, classified upstream failure."""


class UpstreamConfigurationError(UpstreamError):
    pass


class UpstreamTimeoutError(UpstreamError):
    pass


class UpstreamConnectionError(UpstreamError):
    pass


class UpstreamProtocolError(UpstreamError):
    pass


class UpstreamResultTooLargeError(UpstreamError):
    pass


@dataclass(frozen=True)
class UpstreamConfig:
    url: str
    auth_type: str
    auth_header: str | None
    connect_timeout_ms: int
    call_timeout_ms: int


class UpstreamAdapter:
    """Short-lived, authenticated MCP client for one registered upstream."""

    def __init__(
        self,
        config: UpstreamConfig,
        credential: str | None,
        *,
        max_result_bytes: int = 1_048_576,
        max_concurrency: int = 4,
    ) -> None:
        if config.connect_timeout_ms <= 0 or config.call_timeout_ms <= 0:
            raise UpstreamConfigurationError("upstream timeouts must be positive")
        if max_result_bytes <= 0 or max_concurrency <= 0:
            raise UpstreamConfigurationError("adapter limits must be positive")
        self.config = config
        self._headers = self._build_headers(config, credential)
        self._max_result_bytes = max_result_bytes
        self._semaphore = asyncio.Semaphore(max_concurrency)

    @staticmethod
    def _build_headers(config: UpstreamConfig, credential: str | None) -> dict[str, str]:
        if config.auth_type == "none":
            return {}
        if not credential:
            raise UpstreamConfigurationError("authenticated upstream requires a credential")
        if config.auth_type == "bearer":
            return {"Authorization": f"Bearer {credential}"}
        if config.auth_type == "header" and config.auth_header:
            return {config.auth_header: credential}
        raise UpstreamConfigurationError("unsupported upstream authentication configuration")

    async def list_tools(self) -> list[Tool]:
        async with self._semaphore:
            return await self._run_list_tools()

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> CallToolResult:
        # Calls intentionally execute once. Retrying a timed-out write can duplicate side effects.
        async with self._semaphore:
            result = await self._run_call_tool(name, arguments or {})
        if len(result.model_dump_json(by_alias=True).encode()) > self._max_result_bytes:
            raise UpstreamResultTooLargeError("upstream result exceeded the configured size limit")
        return result

    async def _run_list_tools(self) -> list[Tool]:
        tools: list[Tool] = []
        cursor: str | None = None
        while True:
            page = await self._execute("list", cursor=cursor)
            tools.extend(page.tools)
            cursor = page.next_cursor
            if not cursor:
                return tools

    async def _run_call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        return await self._execute("call", name=name, arguments=arguments)

    async def _execute(self, operation: str, **kwargs: Any) -> Any:
        connect_seconds = self.config.connect_timeout_ms / 1000
        operation_seconds = (
            connect_seconds if operation == "list" else self.config.call_timeout_ms / 1000
        )
        http_timeout = httpx2.Timeout(connect_seconds)
        try:
            async with asyncio.timeout(connect_seconds + operation_seconds):
                async with httpx2.AsyncClient(
                    headers=self._headers,
                    timeout=http_timeout,
                    trust_env=False,
                    follow_redirects=False,
                ) as http:
                    async with Client(
                        streamable_http_client(self.config.url, http_client=http),
                        read_timeout_seconds=operation_seconds,
                    ) as client:
                        if operation == "list":
                            return await client.list_tools(cursor=kwargs["cursor"], cache_mode="reload")
                        return await client.call_tool(
                            kwargs["name"], kwargs["arguments"], read_timeout_seconds=operation_seconds
                        )
        except (TimeoutError, httpx2.TimeoutException) as error:
            raise UpstreamTimeoutError("upstream request timed out") from error
        except UpstreamError:
            raise
        except (httpx2.HTTPError, OSError) as error:
            raise UpstreamConnectionError("upstream could not be reached") from error
        except Exception as error:
            if self._contains_timeout(error):
                raise UpstreamTimeoutError("upstream request timed out") from error
            raise UpstreamProtocolError("upstream returned an invalid MCP response") from error

    @classmethod
    def _contains_timeout(cls, error: BaseException) -> bool:
        if isinstance(error, (TimeoutError, httpx2.TimeoutException)):
            return True
        if isinstance(error, MCPError) and error.error.code == -32001:
            return True
        if isinstance(error, BaseExceptionGroup):
            return any(cls._contains_timeout(child) for child in error.exceptions)
        return error.__cause__ is not None and cls._contains_timeout(error.__cause__)
