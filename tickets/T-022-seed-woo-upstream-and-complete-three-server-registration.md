# T-022 — Seed Woo upstream and complete three-server registration

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-010, T-011, T-012, T-019, T-020  
**Acceptance IDs:** A04, A05, A07, A12  
**Architecture decisions:** ADR-09 ADR-11  
**Design references:** HLD §7; LLD §6, §8

## Objective

Prove the gateway is data-driven, pre-registers Woo and accepts other servers at runtime.

## Exact implementation scope

Implement idempotent Woo upstream seed from Secret/config (Woo appears first in dashboard). Register currency and policy via admin API without changing/redeploying gateway. Confirm correct three catalogs and collision aliases; run cross-server calls and test restart retains registry. Never create a hardcoded conditional routing per server type.

## Interfaces, data structures and contracts

Bootstrap woo slug stable; admin POST /api/servers for currency and policy; tool aliases from Postgres. Reset/demo seed instructions documented.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/bootstrap.py; charts/gateway/templates/bootstrap*.yaml if needed; scripts/seed-demo-servers.sh; tests/integration/test_three_upstreams.py

## Explicit non-goals / constraints

No fourth remote server, no multi-store provisioning, no special code path for currency/policy.

## Verification commands and tests

```bash
python -m pytest tests/integration/test_three_upstreams.py -q
# admin registers currency/policy, tools/list sees all three, call both colliding aliases
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Woo preseed exists once; two servers added at runtime; aliases callable; registry survives restart.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
