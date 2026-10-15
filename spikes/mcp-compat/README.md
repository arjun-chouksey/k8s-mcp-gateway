# T-002 MCP interoperability spike

This isolated spike proves one authenticated Streamable HTTP path:

`MCP Inspector or Codex CLI -> low-level proxy -> fixed MCP server -> result`

It pins the official Python MCP SDK to `2.3.0` and MCP Inspector to `2.11.0`. The fixed server uses `MCPServer` and `@server.tool()`. The proxy uses the public low-level `Server` constructor with `on_list_tools` and `on_call_tool`, validates cached input schemas with `Draft202012Validator`, prefixes the upstream tool as `probe__add`, and returns the typed upstream result. Bearer authentication runs on every downstream HTTP request. The downstream bearer is never forwarded upstream.

## Setup and automated tests

```bash
cd spikes/mcp-compat
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
npm ci
.venv/bin/python -m pytest -q
```

The tests use two real loopback HTTP listeners. They cover discovery and calls, two concurrent actors, invalid arguments, unknown tools, missing/wrong/revoked credentials, credential separation, bounded timeout without retry, cached listing after upstream shutdown, and a sanitized unavailable result.

## Real-client verification

```bash
.venv/bin/python verify_clients.py
```

This runs MCP Inspector and the installed Codex CLI against fresh loopback servers. It requires a logged-in Codex CLI and makes one model request. Test credentials are generated per run, stored only in a mode-`0600` temporary file or child-process environment, never printed, and deleted on exit. The script requires both clients to discover and call `probe__add`, requires the Inspector wrong-token check to receive HTTP 401, and prints only versions, call count and PASS after all assertions succeed.

Codex CLI is intentionally configured with only `probe__add` enabled and its approval mode set to `approve`; otherwise non-interactive `codex exec` rejects the call because it cannot present an approval prompt. This is client policy for the known loopback test tool, not a gateway authentication bypass.
