# T-019 — Persist discovered tools and monitor upstream health

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-017, T-018  
**Acceptance IDs:** A04, A05, A06, A07, A14, A15  
**Architecture decisions:** ADR-10 ADR-11 ADR-12  
**Design references:** LLD §3, §6; HLD §5.4

## Objective

Build fast, failure-isolated registry discovery and stable alias mapping.

## Exact implementation scope

Refresh tools immediately after successful registration/edit, asynchronously bounded; store original_name, JSON Schemas, annotations, definition_hash and exact public_alias in PostgreSQL. Periodically probe enabled servers; mark connected/unreachable/disabled with last_error and last_checked_at. An unreachable enabled server retains previous cache; a disabled/deleted server omitted from new lists. Ensure tool list never contacts upstream synchronously. Alias slug__original_name no collision. Single-replica loop sufficient; document multi-replica coordination gate.

## Interfaces, data structures and contracts

CatalogService.list_tools(actor) reads Postgres; refresh_upstream(id) contacts adapter; status values checking|connected|unreachable|disabled. Must support pagination if chosen SDK requires it.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/mcp_gateway/{catalog,aliases}.py; tests/{test_catalog,test_health,test_aliases}.py; chart gateway background worker config

## Explicit non-goals / constraints

No LLM calls, no client-facing tool dispatch yet, no advanced rug-pull approval workflow.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_catalog.py services/gateway/tests/test_health.py services/gateway/tests/test_aliases.py -q
# enabled dead cached entry retained, disabled absent, simulated slow probe doesn't block list
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Three tool catalogs can be stored; duplicate names resolve to distinct aliases; health transitions correct; listing cache-only under outage.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
