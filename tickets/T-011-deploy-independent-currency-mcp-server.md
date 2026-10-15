# T-011 — Deploy independent currency MCP server

**Tier:** MANDATORY  
**Phase:** 3 · Additional upstreams  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-002, T-005  
**Acceptance IDs:** A04, A12  
**Architecture decisions:** ADR-03 ADR-09  
**Design references:** HLD §3; LLD §8

## Objective

Provide a deterministic independent MCP upstream for a two-server tool prompt.

## Exact implementation scope

Implement separate SDK v2 Streamable HTTP service with convert_currency(Decimal amount, from_currency, to_currency) and get_demo_rates. Use versioned fixed demonstration rates prominently labeled NOT live FX. Add bearer check, probes and CPU/memory limits. Deploy separate currency pod/service through aux chart.

## Interfaces, data structures and contracts

Return precise currency value and rate metadata; reject unsupported pairs and malformed inputs. Currency server must not call WooCommerce directly.

## Expected files/modules (proposed; inspect actual tree first)

services/aux-mcp/currency/{app.py,rates.json,Dockerfile,tests/}; charts/aux-mcp/templates/currency*.yaml

## Explicit non-goals / constraints

No third-party FX API, database, tool-by-tool permissions or chat.

## Verification commands and tests

```bash
python -m pytest services/aux-mcp/currency/tests -q
helm template urumi charts/platform -n platform -f charts/platform/values-local.yaml >/tmp/platform.yaml
# Inspector list/call currency tools
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Currency server independently callable via Streamable HTTP; output explicitly states rates are demo-only; Helm chart renders.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
