# T-004 — Local k3d cluster namespaces and networking

**Tier:** MANDATORY  
**Phase:** 1 · Kubernetes foundation  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-001  
**Acceptance IDs:** A17, A18, A19  
**Architecture decisions:** ADR-06 ADR-08 ADR-18  
**Design references:** HLD §7; LLD §10

## Objective

Produce repeatable local cluster bootstrap with three namespaces and ingress resolution.

## Exact implementation scope

Create idempotent k3d setup script and Makefile targets; create platform/mcp/store namespaces before chart install; verify k3s Traefik routing, local-path StorageClass and NetworkPolicy enforcement capability (do not assume). Document local nip.io or hosts fallback, registry/image import strategy and kube context safeguards. No real secrets in scripts.

## Interfaces, data structures and contracts

Namespace names fixed: store, mcp, platform. Hosts initially shop.127.0.0.1.nip.io and app.127.0.0.1.nip.io, subject to DNS checks; ports and hostnames configurable.

## Expected files/modules (proposed; inspect actual tree first)

infra/namespaces.yaml; scripts/cluster-up.sh; Makefile; README setup section only if authorized

## Explicit non-goals / constraints

No app business logic, prod VPS provisioning or publishing images.

## Verification commands and tests

```bash
make cluster-up
kubectl get ns store mcp platform
kubectl get storageclass
kubectl -n kube-system get deployments
kubectl config current-context
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Fresh local cluster usable; namespaces labelled; local routing and policy implementation assessed with actual outputs.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
