# S-005 — Scale stateless gateway to two replicas safely

**Tier:** OPTIONAL  
**Phase:** 8 · Stand-outs  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-019, T-030  
**Acceptance IDs:** A15, A16  
**Architecture decisions:** ADR-17  
**Design references:** HLD §4, §8; LLD §10

## Objective

Demonstrate safe gateway replica scaling without actor bleed or duplicated health polling.

## Exact implementation scope

Separate catalog polling into leader-elected worker or Postgres advisory lock; verify request-scoped identity, cached catalog consistency, concurrent calls, audit uniqueness, independent /mcp HTTP requests and Secret rotation; set gateway replica=2 with appropriate PDB/rolling readiness if supportable on node. Fail/recover replica while active.

## Interfaces, data structures and contracts

Gateway remains stateless; Postgres holds shared state; no sticky sessions required for chosen verified transport.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/mcp_gateway/catalog.py; tests/integration/test_two_replicas.py; charts/gateway/templates/deployment.yaml; values-vps.yaml

## Explicit non-goals / constraints

No HPA, redis, multi-region or durable distributed queue.

## Verification commands and tests

```bash
python -m pytest tests/integration/test_two_replicas.py -q
# scale to 2, route several users/tools, kill replica, inspect audit and single poll owner
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Two replicas maintain tool/auth behaviour without shared-memory assumptions or duplicate status workers.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
