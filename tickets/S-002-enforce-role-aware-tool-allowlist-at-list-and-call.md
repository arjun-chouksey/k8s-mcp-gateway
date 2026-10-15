# S-002 — Enforce role-aware tool allowlist at list and call

**Tier:** OPTIONAL  
**Phase:** 8 · Stand-outs  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-020, T-021, T-025  
**Acceptance IDs:** A08, A14  
**Architecture decisions:** ADR-13 ADR-15  
**Design references:** LLD §3 tool_permissions, §4, §6; THREAT_MODEL §4

## Objective

Add per-role tool visibility and invocation restrictions without breaking required product creation.

## Exact implementation scope

Migrate tool_permissions; admin can define allow/deny for role+server+tool. Filter tool listing and reject direct stale/forbidden calls at execution. Show admin-only write tool on UI, authenticated member denied with audit. Preserve mandatory A creates product (A admin).

## Interfaces, data structures and contracts

DB tool_permissions(role,upstream_id,original_tool,allowed). Server enabled and user active checks remain dominant; annotations only hints.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/security/permissions.py; migration; api/tool_permissions.py; web/dashboard/src/pages/Servers.tsx; tests/test_tool_acl.py

## Explicit non-goals / constraints

No OAuth or policy engine such as OPA; not mandatory user-rights rewrite.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_tool_acl.py -q
# list hides forbidden alias and call rejects it with audit
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Read/write separation proven both list-time and call-time; baseline required demo remains green.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
