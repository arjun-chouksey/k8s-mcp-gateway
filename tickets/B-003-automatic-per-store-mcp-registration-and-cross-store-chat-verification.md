# B-003 — Automatic per-store MCP registration and cross-store chat verification

**Tier:** BONUS_NOT_APPROVED  
**Phase:** 9 · Deferred bonus  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** B-002  
**Acceptance IDs:** Bonus-specific, not A01–A20  
**Architecture decisions:** ADR-10 ADR-14  
**Design references:** Original assignment bonus section

## Objective

Attach a Woo MCP adapter to each dynamically provisioned store and verify complete lifecycle.

## Exact implementation scope

Provision separate MCP server per store, automatically register unique slug into same gateway, enforce cross-store policies, remove registration on store deletion; ask chat to compare today orders across two stores then delete one and prove tools/resources removed.

## Interfaces, data structures and contracts

Store slug prefixes identifiable; no unauthorized cross-store database connectivity.

## Expected files/modules (proposed; inspect actual tree first)

Proposed: provisioning MCP lifecycle module; charts/woo-mcp/*; tests/integration/test_multistore.py; docs/DEMO.md

## Explicit non-goals / constraints

No company-wide SaaS tenancy, no replacing approved mandatory first-store deployment.

## Verification commands and tests

```bash
# full two-store order comparison, NetworkPolicy negative isolation and teardown smoke (after approval)
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Optional bonus demo passes with no leftover resources, retriable partial failure and policy isolation.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
