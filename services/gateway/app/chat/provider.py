from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class ProviderError(RuntimeError):
    """Sanitized provider failure safe to return to the dashboard."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Completion:
    text: str
    calls: tuple[ToolCall, ...]
    output_items: tuple[dict[str, Any], ...]


class ResponsesProvider:
    def __init__(self, *, base_url: str, model: str, api_key: str, timeout: float = 30.0):
        self.endpoint = f"{base_url.rstrip('/')}/responses"
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Completion:
        if not self.api_key:
            raise ProviderError("LLM provider is not configured")
        return await asyncio.to_thread(self._complete_sync, messages, tools)

    def _complete_sync(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Completion:
        payload = json.dumps({"model": self.model, "input": messages, "tools": tools}).encode()
        request = urllib.request.Request(self.endpoint, data=payload, headers={
            "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
            "User-Agent": "k8s-mcp-gateway/0.1",
        }, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except urllib.error.HTTPError as error:
            raise ProviderError(f"provider returned HTTP {error.code}") from None
        except (urllib.error.URLError, TimeoutError):
            raise ProviderError("provider request failed") from None
        output = body.get("output")
        if not isinstance(output, list):
            raise ProviderError("provider response has no output list")
        calls: list[ToolCall] = []
        text: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "function_call":
                try:
                    arguments = json.loads(item["arguments"])
                    if not isinstance(arguments, dict):
                        raise TypeError
                    calls.append(ToolCall(str(item["call_id"]), str(item["name"]), arguments))
                except (KeyError, TypeError, json.JSONDecodeError):
                    raise ProviderError("provider returned a malformed function call") from None
            elif item.get("type") == "message":
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "output_text":
                        text.append(str(content.get("text", "")))
        return Completion("\n".join(text), tuple(calls), tuple(output))
