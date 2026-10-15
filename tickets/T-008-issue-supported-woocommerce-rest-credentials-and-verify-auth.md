# T-008 — Issue supported WooCommerce REST credentials and verify auth

**Tier:** MANDATORY  
**Phase:** 2 · Real store  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-007  
**Acceptance IDs:** A03, A18  
**Architecture decisions:** ADR-15 ADR-16  
**Design references:** HLD §4, §9; LLD §7 bootstrap; THREAT_MODEL §3

## Objective

Provision a scoped Woo REST credential without unsupported database mutations.

## Exact implementation scope

Select supported WooCommerce Admin REST-key UI or verified supported app authorization workflow. Issue read/write key, store as Kubernetes Secret in mcp namespace via documented secret-safe script, and test authenticated product GET and POST on the internal WordPress URL. Confirm OAuth 1.0a on plain HTTP or demonstrated HTTPS Basic. Never expose consumer secret in logs/curl transcripts.

## Interfaces, data structures and contracts

Credential data consumed by Woo MCP only; gateway receives separate upstream bearer. Woo URLs internal service DNS; names from chart values.

## Expected files/modules (proposed; inspect actual tree first)

scripts/woo-credentials-setup.md or scripts/woo-credentials.sh when supported; tests/smoke/woo-api-auth.sh

## Explicit non-goals / constraints

No direct writes to wp_woocommerce_api_keys and no API key in chart values, Git or frontend.

## Verification commands and tests

```bash
bash tests/smoke/woo-api-auth.sh  # redacted output
kubectl -n mcp get secret  # names only, no -o yaml in logs
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Read/write REST calls verified against real store; source/rotation approach and successful status codes documented.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.

## Stop condition / special risk

STOP if authentication cannot be demonstrated; ask user before selecting a nonstandard protocol/route.
