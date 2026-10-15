# T-021 — Durable per-user tool-call audit and security failures

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-013, T-016, T-020  
**Acceptance IDs:** A16  
**Architecture decisions:** ADR-13 ADR-15  
**Design references:** LLD §3, §6; THREAT_MODEL §§2–4

## Objective

Write non-sensitive, actor-attributed audit records for every attempted tool invocation.

## Exact implementation scope

Insert audit on successful, failed, denied, disabled and timed-out calls with user, api_key_id when applicable, channel, server, alias/original, started_at, duration_ms, outcome, error_summary. Record authenticated denied attempts. Invalid/unattributed key attempts go to sanitized security logs or separate security_events if implemented, never invent user identity. Never log secrets or raw arguments. Provide paginated filtered GET /api/audit with admin-all/member-own isolation.

## Interfaces, data structures and contracts

Audit fields align LLD §3; outcomes ok/tool_error/upstream_error/timeout/denied; GET /api/audit paginated server/time/outcome filters.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/mcp_gateway/auditing.py; services/gateway/app/api/audit.py; tests/{test_audit,test_audit_access}.py

## Explicit non-goals / constraints

No analytics database, raw request dumps or event broker.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_audit.py services/gateway/tests/test_audit_access.py -q
# run allowed, denied and timeout and verify DB row attribution
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Audit rows accurate with actor and duration; member cannot view others' events; tool failure does not leak args/tokens.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
