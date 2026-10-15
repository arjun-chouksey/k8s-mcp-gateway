"""Minimal configurable Responses API adapter for the T-003 spike."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class ProviderError(RuntimeError):
    """A sanitized provider failure safe to show in logs."""


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
        if not api_key:
            raise ValueError("API key is required")
        self.endpoint = f"{base_url.rstrip('/')}/responses"
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "ResponsesProvider":
        key_env = os.getenv("LLM_API_KEY_ENV", "GROQ_API_KEY")
        api_key = os.getenv(key_env, "")
        if not api_key:
            raise ValueError(f"required credential {key_env} is not set")
        return cls(
            base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            model=os.getenv("LLM_MODEL", "openai/gpt-oss-20b"),
            api_key=api_key,
        )

    def get_completion(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> Completion:
        payload = json.dumps(
            {"model": self.model, "input": messages, "tools": tools}
        ).encode()
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "k8s-mcp-gateway-t003/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"provider returned HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderError(f"provider request failed: {type(exc).__name__}") from None

        output = body.get("output")
        if not isinstance(output, list):
            raise ProviderError("provider response has no output list")

        calls: list[ToolCall] = []
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "function_call":
                try:
                    arguments = json.loads(item["arguments"])
                    if not isinstance(arguments, dict):
                        raise TypeError
                    calls.append(ToolCall(item["call_id"], item["name"], arguments))
                except (KeyError, TypeError, json.JSONDecodeError):
                    raise ProviderError("provider returned a malformed function call") from None
            elif item.get("type") == "message":
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "output_text":
                        text_parts.append(str(content.get("text", "")))
        return Completion("\n".join(text_parts), tuple(calls), tuple(output))


def validate_arguments(arguments: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate the small JSON Schema subset used by this spike."""
    properties = schema.get("properties", {})
    missing = set(schema.get("required", [])) - arguments.keys()
    extra = arguments.keys() - properties.keys()
    if missing:
        raise ValueError(f"missing required arguments: {sorted(missing)}")
    if schema.get("additionalProperties") is False and extra:
        raise ValueError(f"unexpected arguments: {sorted(extra)}")
    python_types = {"string": str, "number": (int, float), "integer": int}
    for name, value in arguments.items():
        expected = python_types.get(properties.get(name, {}).get("type"))
        if expected and (not isinstance(value, expected) or isinstance(value, bool)):
            raise ValueError(f"argument {name} has the wrong type")
