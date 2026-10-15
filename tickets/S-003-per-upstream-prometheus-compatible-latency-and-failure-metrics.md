# S-003 — Per-upstream Prometheus-compatible latency and failure metrics

**Tier:** OPTIONAL  
**Phase:** 8 · Stand-outs  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-021, T-025  
**Acceptance IDs:** A15, A16  
**Architecture decisions:** ADR-11 ADR-17  
**Design references:** HLD §8; LLD §6, §10

## Objective

Expose simple service-health and tool-call telemetry useful for debugging.

## Exact implementation scope

Instrument tool call count, timeout/error count and latency histogram by upstream/tool/outcome without user emails or high-cardinality labels. Expose protected/internal /metrics. Dashboard optional summary; test increments on success and outage.

## Interfaces, data structures and contracts

Metrics counters/histograms bounded labels; logs and audit remain source for actor-specific tracing.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/metrics.py; tests/test_metrics.py; chart Service annotations if chosen; docs/DEMO.md

## Explicit non-goals / constraints

No full Prometheus/Grafana stack, OpenTelemetry collector or cluster-wide monitoring.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_metrics.py -q
# internal GET /metrics pre/post calls, inspect increments without PII
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Health and error metrics correct; no secrets/PII in metric label set.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
