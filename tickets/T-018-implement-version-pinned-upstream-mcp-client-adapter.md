# T-018 — Implement version-pinned upstream MCP client adapter

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-002, T-017  
**Acceptance IDs:** A04, A09, A15  
**Architecture decisions:** ADR-02 ADR-03 ADR-11  
**Design references:** LLD §6; THREAT_MODEL §2

## Objective

Create generic authenticated Streamable HTTP adapter for any registered server.

## Exact implementation scope

Using exact T-002 pinned SDK public APIs, implement connect/list_tool(s)/call_tool with per-upstream decryptable headers; bounded connect/call timeouts, result size limits, no downstream Authorization passthrough, no write retries, clear failure classes. Handle multiple upstreams in isolation, not hardcoded Woo names; include cancellable cleanup and semaphore concurrency controls.

## Interfaces, data structures and contracts

Generic UpstreamAdapter(server config, secret) -> tool definitions and typed tool results; supports bearer/custom headers and none; never returns auth headers to caller.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/mcp_gateway/adapter.py; services/gateway/tests/test_adapter.py; tests/integration/test_upstream_adapter.py

## Explicit non-goals / constraints

No catalog caching, downstream /mcp endpoint or assumptions of globally shared session state.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_adapter.py tests/integration/test_upstream_adapter.py -q
# simulate slow server and success to prove bounded timeout and unrelated server still works
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Three transport types (none/bearer/custom-header) handled where applicable; timeouts bounded; no secret passthrough or write retry.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
