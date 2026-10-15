# T-003 LLM tool-calling spike

This spike implements the minimal provider contract `get_completion(messages, tools)` using GroqCloud's Responses-compatible HTTP endpoint. It preserves model-generated call IDs and parses JSON arguments. The live check asks for one fake read and one fake write-like preview, validates both argument objects, returns results using the same call IDs, and requires final text after the tool results. Neither tool persists data.

## Run

```sh
python3 -m unittest discover -s spikes/llm-toolcalls -p 'test_*.py'
set -a
source spikes/llm-toolcalls/.env.local
set +a
python3 spikes/llm-toolcalls/live_check.py
```

Optional configuration:

- `LLM_BASE_URL` defaults to `https://api.groq.com/openai/v1`.
- `LLM_MODEL` defaults to `openai/gpt-oss-20b`.
- `LLM_API_KEY_ENV` names the environment variable containing the secret and defaults to `GROQ_API_KEY`.

## Provider decision evidence

GroqCloud with `openai/gpt-oss-20b` is the selected primary. On October 15, 2026, the live check completed two correlated tool calls over three model turns in 1,925 ms, then returned final text based on both fake results. This verified the supplied key, free-plan quota, requested model access, JSON arguments, call IDs, and multi-turn function outputs. A deliberately invalid model failed safely with HTTP 404. OpenAI's Responses API is the configuration-compatible fallback, but remains unverified because no OpenAI API credential is available.

Expected failure behavior is explicit and sanitized: missing configuration fails before network access; HTTP authentication, model-access, and quota errors report only the status code; malformed function calls fail closed. Quota-exhaustion behavior was not exercised because the free quota was available.
