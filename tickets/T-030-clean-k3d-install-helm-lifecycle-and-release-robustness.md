# T-030 — Clean k3d install, Helm lifecycle and release robustness

**Tier:** MANDATORY  
**Phase:** 6 · Infra and verification  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-023, T-024, T-025, T-027, T-028, T-029  
**Acceptance IDs:** A01, A02, A17, A18, A19  
**Architecture decisions:** ADR-07 ADR-08 ADR-18  
**Design references:** HLD §7; LLD §10–11; DEMO §3

## Objective

Validate a clean-clone local Helm install and upgrade/rollback without losing durable state.

## Exact implementation scope

Build local setup and idempotent secret/bootstrap documentation/scripts; build/tag/import images; deploy umbrella release across three namespaces; verify routes, PVCs, endpoints, readiness, local user bootstrap and upstream registration. Exercise helm lint/template/install/upgrade/rollback for stateless component and note DB rollback limits. Verify deliberate Pod replacement retains Woo orders, both DBs, and dashboard/API remain accessible.

## Interfaces, data structures and contracts

Same chart templates for local/VPS values; three namespaces created first. Do not embed Secret values in Helm release metadata.

## Expected files/modules (proposed; inspect actual tree first)

Makefile; scripts/{build-images,deploy-local,smoke-local}.sh; charts/platform/*; tests/smoke/*; docs/STATUS.md

## Explicit non-goals / constraints

No destructive uninstall of volumes without approval, no VPS deployment in this ticket.

## Verification commands and tests

```bash
make cluster-up && make deploy-local && make smoke-local
helm lint charts/platform -f charts/platform/values-local.yaml
helm history urumi -n platform
kubectl get pods,pvc,ingress,networkpolicy -A
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Fresh local install and smoke pass; upgrade/rollback stateless path verified; products/orders and platform data persist across Pod replacement.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
