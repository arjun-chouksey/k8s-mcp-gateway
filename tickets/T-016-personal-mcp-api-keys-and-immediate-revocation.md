# T-016 — Personal MCP API keys and immediate revocation

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-014  
**Acceptance IDs:** A08, A09, A13  
**Architecture decisions:** ADR-13 ADR-15  
**Design references:** LLD §4, §5; THREAT_MODEL §§2–4

## Objective

Issue one-time visible high-entropy API keys and validate them on every MCP request.

## Exact implementation scope

Implement personal key generation, admin issuance/revocation, member self-service, prefix lookup, keyed digest HMAC (pepper in Secret), constant-time compare, last-used updates and revoked/disabled-user rejection. Bearer middleware must validate every MCP HTTP request, including a previously established client. Invalid/revoked keys => HTTP 401; unauthorized role => 403. Do not forward key upstream.

## Interfaces, data structures and contracts

API key format mcpgw_<public-prefix>_<random-secret>; POST/GET/DELETE /api/keys; admin member-key routes per LLD. Credential shown once, never retrievable. Every /mcp POST must authenticate.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/security/api_keys.py; services/gateway/app/api/keys.py; tests/test_api_keys.py; tests/test_mcp_auth.py

## Explicit non-goals / constraints

No OAuth for external clients; no key caching that delays revocation.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_api_keys.py services/gateway/tests/test_mcp_auth.py -q
# create key, call /mcp, revoke, same next request must yield 401
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

A and B have separate keys; revoke B immediately without affecting A; database stores keyed digests only; credentials absent from logs.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
