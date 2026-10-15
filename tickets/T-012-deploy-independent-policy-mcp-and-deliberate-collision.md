# T-012 — Deploy independent policy MCP and deliberate collision

**Tier:** MANDATORY  
**Phase:** 3 · Additional upstreams  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-002, T-005  
**Acceptance IDs:** A04, A07  
**Architecture decisions:** ADR-03 ADR-09 ADR-10  
**Design references:** HLD §3; LLD §8

## Objective

Provide third upstream and a repeatable tool-name collision case.

## Exact implementation scope

Create independent policy server exposing list_store_policies, get_store_policy(topic) from versioned sample data. If required by alias acceptance, expose a harmless explicitly labeled list_products tool name from second upstream to demonstrate a collision without accessing WooCommerce. Add bearer token, probes, resource bounds and Helm resources. Keep it a distinct process, Pod and Service.

## Interfaces, data structures and contracts

Static policy fixture; no WooCommerce access; identical original tool name must be distinct at gateway after aliasing.

## Expected files/modules (proposed; inspect actual tree first)

services/aux-mcp/policy/{app.py,policies.json,Dockerfile,tests/}; charts/aux-mcp/templates/policy*.yaml

## Explicit non-goals / constraints

No actual store data mutation or hardcoded gateway routing rules.

## Verification commands and tests

```bash
python -m pytest services/aux-mcp/policy/tests -q
# Inspector tool listing + example policy retrieval, record evidence
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Third independent upstream works, tool collision defined with exact name, and no direct store access.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
