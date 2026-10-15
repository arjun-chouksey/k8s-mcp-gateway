# T-006 — Deploy MariaDB and WordPress with durable PVCs

**Tier:** MANDATORY  
**Phase:** 2 · Real store  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-005  
**Acceptance IDs:** A02, A18  
**Architecture decisions:** ADR-05 ADR-18  
**Design references:** HLD §3, §7; LLD §7, §10

## Objective

Run durable WordPress and MariaDB workloads through Helm.

## Exact implementation scope

MariaDB StatefulSet, Service, PVC via volumeClaimTemplates, stable existingSecret refs and probes. WordPress one-replica Deployment, Recreate rollout strategy for RWO, Service, separate content PVC, config and probes. Handle WordPress ownership/perms appropriately. Namespace store. Validate DB connection and both PVC mounts.

## Interfaces, data structures and contracts

Kubernetes Secret refs e.g. store-db-credentials and wordpress-admin; actual Secret names from frozen chart contract. Database/service credentials available only to needed Pods; health probes do not destructively query DB.

## Expected files/modules (proposed; inspect actual tree first)

charts/store/templates/{mariadb,wordpress}*.yaml; charts/store/values.yaml; scripts/create-local-secrets.sh (redacting output); tests/smoke/store-persistence.sh

## Explicit non-goals / constraints

No WooCommerce APIs, bootstrap, gateway or prod changes.

## Verification commands and tests

```bash
helm dependency update charts/platform
helm upgrade --install urumi charts/platform -n platform -f charts/platform/values-local.yaml --wait
kubectl get pods,pvc,svc -n store
kubectl describe pvc -n store
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Both workloads Ready and bound PVCs; WordPress reaches DB; deleting one noncritical Pod does not delete volume data.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
