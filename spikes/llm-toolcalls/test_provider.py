import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from provider import ProviderError, ResponsesProvider, validate_arguments


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class ProviderTests(unittest.TestCase):
    def test_parses_text_and_stable_tool_call(self):
        body = {
            "output": [
                {
                    "type": "function_call",
                    "call_id": "call_123",
                    "name": "lookup_inventory",
                    "arguments": '{"product":"Demo mug"}',
                },
                {"type": "message", "content": [{"type": "output_text", "text": "done"}]},
            ]
        }
        provider = ResponsesProvider(base_url="https://example.test/v1", model="test", api_key="secret")
        with patch("urllib.request.urlopen", return_value=FakeResponse(json.dumps(body).encode())):
            result = provider.get_completion([{"role": "user", "content": "test"}], [])
        self.assertEqual(result.calls[0].id, "call_123")
        self.assertEqual(result.calls[0].arguments, {"product": "Demo mug"})
        self.assertEqual(result.text, "done")

    def test_rejects_arguments_outside_schema(self):
        schema = {
            "properties": {"product": {"type": "string"}},
            "required": ["product"],
            "additionalProperties": False,
        }
        with self.assertRaisesRegex(ValueError, "unexpected"):
            validate_arguments({"product": "mug", "admin": True}, schema)

    def test_http_error_is_sanitized(self):
        provider = ResponsesProvider(base_url="https://example.test/v1", model="bad", api_key="do-not-print")
        error = urllib.error.HTTPError(provider.endpoint, 401, "secret server body", {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(ProviderError, "HTTP 401") as raised:
                provider.get_completion([], [])
        self.assertNotIn("do-not-print", str(raised.exception))
        self.assertNotIn("secret server body", str(raised.exception))

    def test_environment_configuration_requires_model_and_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "GROQ_API_KEY"):
                ResponsesProvider.from_env()

    def test_environment_configuration_uses_groq_defaults(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "local-only"}, clear=True):
            provider = ResponsesProvider.from_env()
        self.assertEqual(provider.endpoint, "https://api.groq.com/openai/v1/responses")
        self.assertEqual(provider.model, "openai/gpt-oss-20b")


if __name__ == "__main__":
    unittest.main()
