# T-007 — Initialize WooCommerce and prove checkout

**Tier:** MANDATORY  
**Phase:** 2 · Real store  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-006  
**Acceptance IDs:** A01, A02  
**Architecture decisions:** ADR-16 ADR-20  
**Design references:** HLD §5, §7; LLD §7 bootstrap; DEMO §2

## Objective

Create a real testable store with idempotent setup, products and COD checkout.

## Exact implementation scope

Implement WP core install, WooCommerce plugin activation, permalinks, timezone/currency, COD, demo virtual product and admin setup; prefer tested WP-CLI Job or script with idempotent guards. Configure local site/home URL. Confirm checkout produces a real order in WooCommerce admin. Document recovery/re-run and probe startup. Verify WordPress and MariaDB durability after Pod recreation.

## Interfaces, data structures and contracts

Store remains source of truth for orders/products. Credentials from precreated Secrets. WP bootstrap must not write into WooCommerce private key tables.

## Expected files/modules (proposed; inspect actual tree first)

charts/store/templates/bootstrap-job.yaml if validated; scripts/store-bootstrap.sh; scripts/smoke-store.sh; docs/STATUS.md

## Explicit non-goals / constraints

No direct SQL product/order insertion, no live payment gateway, no multi-store operator.

## Verification commands and tests

```bash
bash scripts/smoke-store.sh
kubectl -n store get pods,pvc
# real browser COD purchase + screenshot/order ID (recorded manually)
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

A real COD order visible in wp-admin; repeated bootstrap doesn't duplicate data; order persists after controlled Pod replacement.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
