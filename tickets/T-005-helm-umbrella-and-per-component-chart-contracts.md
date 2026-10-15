# T-005 — Helm umbrella and per-component chart contracts

**Tier:** MANDATORY  
**Phase:** 1 · Kubernetes foundation  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-004  
**Acceptance IDs:** A18, A19  
**Architecture decisions:** ADR-07 ADR-18  
**Design references:** HLD §7; LLD §2, §10

## Objective

Freeze chart names, values/Secret/service conventions and demonstrate multi-namespace rendering.

## Exact implementation scope

Create umbrella chart and six subcharts: store, woo-mcp, aux-mcp, gateway, platform-db, dashboard. Declare file:// dependencies and explicit per-resource namespaces. Set shared values contract for image tags, Service names/ports, existingSecret refs, probes, storage class and hosts. Use templates only where resources have clear contract; do not generate dozens of placeholders. Ensure externalized secrets and local/vps values.

## Interfaces, data structures and contracts

DNS: woocommerce-mcp.mcp.svc.cluster.local, wordpress.store.svc.cluster.local, postgres.platform.svc.cluster.local, plus chart-established currency/policy Services. Single Helm release stored in platform namespace. Chart templates identical across values.

## Expected files/modules (proposed; inspect actual tree first)

charts/platform/{Chart.yaml,values.yaml,values-local.yaml,values-vps.yaml}; charts/{store,woo-mcp,aux-mcp,gateway,platform-db,dashboard}/; scripts/chart-check.sh

## Explicit non-goals / constraints

No hardcoded passwords, separate local/prod templates, premature resource creation or multi-store provisioning.

## Verification commands and tests

```bash
helm dependency update charts/platform
helm lint charts/platform -f charts/platform/values-local.yaml
helm template urumi charts/platform -n platform -f charts/platform/values-local.yaml >/tmp/urumi-local.yaml
helm template urumi charts/platform -n platform -f charts/platform/values-vps.yaml >/tmp/urumi-vps.yaml
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

All charts lint/render; namespaces and Secret references correct; diff is driven by values; exact shared interfaces remain consistent with HLD/LLD.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
