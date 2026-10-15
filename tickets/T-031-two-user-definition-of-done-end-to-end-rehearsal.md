# T-031 — Two-user definition-of-done end-to-end rehearsal

**Tier:** MANDATORY  
**Phase:** 6 · Infra and verification  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-024, T-025, T-027, T-030  
**Acceptance IDs:** A01, A03, A04, A05, A06, A08, A09, A10, A11, A12, A13, A14, A15, A16, A17  
**Architecture decisions:** ADR-09–16  
**Design references:** LLD §11; DEMO §§1–3

## Objective

Prove the entire original Urumi acceptance script with two distinct users and real tools.

## Exact implementation scope

Run storefront COD order, User A chat creates product and queries newly placed order, User B external client with one URL/key lists all enabled tools, obtains order and performs Woo+currency two-server prompt. Revoke B key next request 401; disable server list absent and stale call denied; kill Pod and scale to zero to sustain outage, confirm other upstreams work and dashboard Unreachable; inspect attributed audit. Capture sanitized evidence and exact steps. Fix failures only via separately authorized scoped ticket or followup.

## Interfaces, data structures and contracts

All calls use actual deployed gateway; screenshots/logs are evidence not substitutes for requests. Keep fixed demo FX labeled synthetic.

## Expected files/modules (proposed; inspect actual tree first)

docs/DEMO.md checkboxes with evidence links; tests/smoke/two-user-e2e.sh; screenshots in docs/evidence/ only sanitized

## Explicit non-goals / constraints

No polished video, speculative pass checkmarks, or relaxed acceptance requirements.

## Verification commands and tests

```bash
make smoke-local
bash tests/smoke/two-user-e2e.sh
# browser+external client manual verified steps logged in docs/DEMO.md
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Every mandatory two-user step actually passes, backed by timestamps/test outputs; outstanding failures explicitly BLOCKED.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
