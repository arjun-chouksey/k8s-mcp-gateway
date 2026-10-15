# T-028 — Apply required NetworkPolicies, probes and Secret boundaries

**Tier:** MANDATORY  
**Phase:** 6 · Infra and verification  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-004, T-005, T-006, T-010, T-011, T-012, T-013, T-020  
**Acceptance IDs:** A17, A18  
**Architecture decisions:** ADR-06 ADR-18  
**Design references:** HLD §7; LLD §10; THREAT_MODEL §5

## Objective

Enforce gateway-only connectivity to MCP upstreams and production-relevant workload health.

## Exact implementation scope

Implement/test NetworkPolicies: Traefik ingress to WordPress/dashboard/gateway, gateway-only MCP ingress, Woo MCP to WordPress, WordPress to MariaDB, gateway to PostgreSQL, necessary DNS and external LLM egress. Validate real policy CNI. Verify probes/startup probes, requests/limits, ServiceAccounts and token automount disabled, existing Secrets, no upstream Ingress. Use appropriate nonroot contexts as images permit. Negative connectivity tests from unauthorized Pods are required.

## Interfaces, data structures and contracts

Ingress at shop/app only; /mcp and /api served via app host; Service types internal ClusterIP; policy matches namespace labels AND Pod selectors.

## Expected files/modules (proposed; inspect actual tree first)

charts/{store,woo-mcp,aux-mcp,gateway,platform-db,dashboard}/templates/networkpolicy*.yaml; infra/network-policy-tests.sh; tests/smoke/policy.sh

## Explicit non-goals / constraints

No cluster-wide policy that accidentally blocks DNS/Traefik, no unsupported FQDN NetworkPolicy claims, no assumption namespaces alone isolate.

## Verification commands and tests

```bash
bash tests/smoke/policy.sh
kubectl get networkpolicy -A
kubectl get ingress -A
# unauthorized debug Pod blocked; authorized gateway MCP call succeeds
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Gateway-to-MCP permitted, unauthorized direct access denied, no public MCP upstream; all workloads have validated resource/probe/Secret configuration.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
