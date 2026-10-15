# T-025 — Audit log and upstream status dashboard

**Tier:** MANDATORY  
**Phase:** 5 · Dashboard  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-021, T-023  
**Acceptance IDs:** A06, A15, A16  
**Architecture decisions:** ADR-04 ADR-11  
**Design references:** LLD §9; DEMO §2

## Objective

Make per-server health and per-user tool invocation evidence easy to inspect.

## Exact implementation scope

Add audit table with filters by user/server/outcome/time, pagination and self-only member visibility. Display server connected/unreachable/disabled, tool count, last checked and error details. Show polling/refresh behaviour and clear error messages. Avoid printing raw tool payloads or credential values in UI. Match backend outcomes; no hardcoded success badges.

## Interfaces, data structures and contracts

GET /api/audit with actor-bound filtering; GET /api/servers and /api/servers/{id}/tools for status; UI view not auth boundary.

## Expected files/modules (proposed; inspect actual tree first)

web/dashboard/src/pages/Audit.tsx; components/{AuditTable,ServerStatus}.tsx; tests/*

## Explicit non-goals / constraints

No Grafana or live log streaming, no independent status probes from browser.

## Verification commands and tests

```bash
cd web/dashboard && npm run typecheck && npm test -- --run && npm run build
# execute success+denied+timeout then verify matching rows/status in dashboard
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Admin global audit, member self audit, accurate 3-state status, no secrets in API/UI.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
