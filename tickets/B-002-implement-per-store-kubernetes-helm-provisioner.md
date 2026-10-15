# B-002 — Implement per-store Kubernetes Helm provisioner

**Tier:** BONUS_NOT_APPROVED  
**Phase:** 9 · Deferred bonus  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** B-001  
**Acceptance IDs:** Bonus-specific, not A01–A20  
**Architecture decisions:** ADR-09 ADR-17  
**Design references:** Original assignment bonus section

## Objective

After B-001 approval, create/delete isolated Woo stores with observable provisioning state.

## Exact implementation scope

Admin/create-store form, idempotent reconciler, per-store namespaces/DB/PVC/Secrets/Ingress, Helm release, correct K8s RBAC/quota/timeout and rollback/partial-state cleanup; concurrent stores safe. Ticket may need subdivision after design approval.

## Interfaces, data structures and contracts

Store states Provisioning/Ready/Failed; one namespace per store; never reuse Secret or database across stores.

## Expected files/modules (proposed; inspect actual tree first)

Proposed: services/gateway/app/provisioning/*; charts/store/*; api/stores.py; web/dashboard/src/pages/Stores.tsx

## Explicit non-goals / constraints

No assumption extra VPS resources are free; no hardcoded second store.

## Verification commands and tests

```bash
# fresh install of two stores and concurrent creation, crash/retry, delete and PV cleanup tests (after approval)
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Multiple stores independent and status-visible with safe retry semantics; tests pass and teardown verified.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
