# B-001 — Approve bonus multi-store provisioning design and isolation contract

**Tier:** BONUS_NOT_APPROVED  
**Phase:** 9 · Deferred bonus  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-034  
**Acceptance IDs:** Bonus-specific, not A01–A20  
**Architecture decisions:** ADR-09 ADR-17  
**Design references:** Original assignment bonus; HLD §8

## Objective

Only if explicitly authorized after core submission readiness, define provisioning interface and failure semantics for stores.

## Exact implementation scope

Propose minimal state machine, ownership, namespace/PVC naming, store quota and cleanup, Kubernetes API RBAC, Helm release ownership, reconcile idempotency and concurrent store requests. Return user approval before any code.

## Interfaces, data structures and contracts

Proposed routes POST/DELETE /api/stores; status Provisioning|Ready|Failed; no contracts locked until approval.

## Expected files/modules (proposed; inspect actual tree first)

docs/DECISIONS.md proposed ADR; future bonus ticket(s) only after approval

## Explicit non-goals / constraints

No implementation, infrastructure action or modification to core single-store scope.

## Verification commands and tests

```bash
# design review only; no coding commands
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

User explicitly approves or declines multi-store extension, with impact and new acceptance plan documented.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
