# S-001 — Actually deploy to VPS with TLS and restoreable backups

**Tier:** OPTIONAL  
**Phase:** 8 · Stand-outs  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-032, T-033  
**Acceptance IDs:** A19  
**Architecture decisions:** ADR-08 ADR-18  
**Design references:** HLD §7–8; LLD §10; THREAT_MODEL §6

## Objective

Demonstrate an actual production-like VPS running the identical Helm templates.

## Exact implementation scope

With explicit user authorization and vetted cost, provision/use existing k3s VPS. Configure public DNS, TLS certificate, secure registry credentials and Secrets, storage, backup scripts/off-node export. Run same values-vps install, smoke checkout + MCP, restart workloads, document limits and evidence.

## Interfaces, data structures and contracts

No change to core templates; all VPS-specific changes values/Secrets/DNS/bootstrap only.

## Expected files/modules (proposed; inspect actual tree first)

scripts/deploy-vps.sh; charts/platform/values-vps.yaml; README VPS section; docs/DEMO.md

## Explicit non-goals / constraints

No paid infrastructure without approval, no promise of host HA, no multi-store.

## Verification commands and tests

```bash
helm upgrade --install urumi charts/platform -n platform -f charts/platform/values-vps.yaml --wait
make smoke-vps  # create target if chosen
# cert + DNS + backup restore proof
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Actual VPS endpoint and TLS work; sanitized smoke and backup evidence captured; user authorized deployment.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
