# T-026 — Chat agent executes only via gateway as logged-in user

**Tier:** MANDATORY  
**Phase:** 5 · Chat  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-003, T-016, T-020, T-021, T-022  
**Acceptance IDs:** A10, A11, A12, A16  
**Architecture decisions:** ADR-14 ADR-19  
**Design references:** LLD §4, §9; HLD §5.3

## Objective

Implement bounded LLM tool loop that uses the gateway MCP endpoint, never direct upstreams.

## Exact implementation scope

Web session authenticates actor and verifies conversation ownership. Mint short-lived internal user token scoped to gateway, use SDK MCP client to gateway internal /mcp URL to list authorized tools and call them. Adapt tool definitions to tested provider, emit tool call/result SSE events and final text, set model round/tool limit and total timeout, cap output/PII, preserve audit channel=chat and actor. Store conversation/messages without secrets. Correctly handle failed/uncertain write results.

## Interfaces, data structures and contracts

POST /api/chat -> SSE events text_delta, tool_call, tool_result, error, done; conversation_id/call_id stable; JWT aud=gateway-mcp sub=user ID exp~5m; tool route is exclusively gateway /mcp.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/chat/{agent,provider,stream}.py; security/internal_tokens.py; api/chat.py; tests/{test_chat,test_internal_tokens}.py; tests/integration/test_chat_self_mcp.py

## Explicit non-goals / constraints

No bypass by calling adapter/router directly, no self-hosted model, no unlimited recursive calls.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_chat.py services/gateway/tests/test_internal_tokens.py tests/integration/test_chat_self_mcp.py -q
# chat create product and orders-today against real cluster; audit actor is A
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Real gateway calls proven from chat, matching actor/channel audit, bounded rounds and a truthful answer from tool results.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
