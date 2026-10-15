# T-009 — Build WooCommerce REST client and error policy

**Tier:** MANDATORY  
**Phase:** 2 · Real store  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-008  
**Acceptance IDs:** A03  
**Architecture decisions:** ADR-16 ADR-20  
**Design references:** LLD §7; THREAT_MODEL §§2–3

## Objective

Create an isolated, testable REST client for WooCommerce v3.

## Exact implementation scope

Implement typed async HTTP client, OAuth1 signing using tested library for internal HTTP, timeouts and error mapping; expose list/create products and list/get/update orders as client methods. No automatic retry for create or status update; safe timeout ambiguity exposed. Redact credentials and customer PII in errors. Validate timezone/date handling and numeric/Decimal price conversion.

## Interfaces, data structures and contracts

WCClient methods: list_products(filters), create_product(payload), list_orders(filters), get_order(id), update_order_status(id,status). Use /wp-json/wc/v3 paths per LLD; credentials from mounted Secret.

## Expected files/modules (proposed; inspect actual tree first)

services/woo-mcp/{wc_client.py,models.py,tests/test_wc_client.py,pyproject.toml}; relevant env config

## Explicit non-goals / constraints

No MCP transport handlers yet, no direct SQL, no authentication table changes.

## Verification commands and tests

```bash
python -m pytest services/woo-mcp/tests/test_wc_client.py -q
# real cluster read/write smoke against secret-backed WC client, with no credentials printed
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Client unit tests cover HTTP 4xx/5xx, auth, timezone boundary, timeout and write non-retry; real WC read/write smoke passes.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
