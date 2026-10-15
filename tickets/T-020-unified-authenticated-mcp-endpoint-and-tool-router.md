# T-020 — Unified authenticated MCP endpoint and tool router

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-016, T-018, T-019  
**Acceptance IDs:** A05, A07, A09, A13, A14, A15  
**Architecture decisions:** ADR-02 ADR-03 ADR-10 ADR-14 ADR-20  
**Design references:** LLD §6; HLD §5.2, §5.4

## Objective

Expose a real SDK v2 MCP endpoint that lists aggregate tools and routes invocation safely.

## Exact implementation scope

Mount SDK v2 low-level Server on FastAPI /mcp. Authenticate request-scoped actor via personal key or short-lived internal JWT. list_tools uses catalog only and applies current scope. call_tool resolves exact stored alias, checks current upstream enabled/user active/role, JSON Schema 2020-12 validates args, forwards to original tool through adapter, maps success/failure/timeouts to typed MCP results and catches stale aliases. Keep actor context request-scoped; prevent token passthrough. No request may bypass the router.

## Interfaces, data structures and contracts

HTTP /mcp Streamable HTTP; alias `<slug>__<original_name>`; JSON-RPC tools/list, tools/call; transport paths from pinned SDK; errors distinguish protocol vs tool errors. ID/role from security boundary only.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/mcp_gateway/{endpoint,router}.py; app/main.py; tests/{test_router,test_schema_validation,test_mcp_endpoint}.py; tests/integration/test_gateway_mcp.py

## Explicit non-goals / constraints

No frontend, no chat, no arbitrary upstream invocation from browser, no automatic retry of write operations.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_router.py services/gateway/tests/test_schema_validation.py services/gateway/tests/test_mcp_endpoint.py tests/integration/test_gateway_mcp.py -q
# real external client lists+calls with one URL/key; stale disabled call rejects
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

End-to-end proxied tool works; server collisions safe; bad schema refused; bearer verified on every request; timeouts isolated.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
