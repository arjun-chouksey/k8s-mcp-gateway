# T-032 — Validate local/VPS values parity and k3s deployment guide

**Tier:** MANDATORY  
**Phase:** 6 · Infra and verification  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-030  
**Acceptance IDs:** A19, A20  
**Architecture decisions:** ADR-07 ADR-08 ADR-18  
**Design references:** HLD §7; LLD §10; ROADMAP §3

## Objective

Prove the architecture is deployable unchanged to single-node k3s with environment-only overrides.

## Exact implementation scope

Render same umbrella charts with values-local and values-vps; validate all hostnames, storage, images, Secrets and ingress settings; document VPS requirements, DNS/TLS, creation of existing Secrets, registry access, backups, storage and the fact single-node VPS is not HA. If VPS available with explicit authorization, test actual install; otherwise do not claim deployed. Same chart templates must be reused.

## Interfaces, data structures and contracts

values-vps.yaml references real domain placeholders, TLS ingress, pinned registry tags, appropriately sized PVCs, existing secrets. No forked chart template.

## Expected files/modules (proposed; inspect actual tree first)

charts/platform/values-vps.yaml; scripts/deploy-vps.sh (non-executed template unless authorized); docs/DEPLOYMENT.md or README subsection (prefer README per assignment); docs/STATUS.md

## Explicit non-goals / constraints

No provisioning/billing external VPS without approval; no live DNS claims; no silent Secret creation.

## Verification commands and tests

```bash
helm dependency update charts/platform
helm lint charts/platform -f charts/platform/values-vps.yaml
helm template urumi charts/platform -n platform -f charts/platform/values-vps.yaml >/tmp/urumi-vps.yaml
# compare resource kinds/names and exact host/Secret refs to local template
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Same templates successfully render for two values; steps describe a real deployable single-node k3s environment; limitations explicit.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
