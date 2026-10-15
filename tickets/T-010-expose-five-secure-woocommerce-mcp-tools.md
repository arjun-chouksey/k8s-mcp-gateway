# T-010 — Expose five secure WooCommerce MCP tools

**Tier:** MANDATORY  
**Phase:** 2 · Real store  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-002, T-009  
**Acceptance IDs:** A03, A17  
**Architecture decisions:** ADR-02 ADR-03 ADR-15 ADR-16  
**Design references:** HLD §3; LLD §7; DEMO §2

## Objective

Implement custom Streamable HTTP Woo MCP server with all required operations.

## Exact implementation scope

Use pinned SDK v2 MCPServer API from T-002; register list_products, create_product, list_orders, get_order, update_order_status, typed schemas and bounded outputs. Protected bearer token distinct from Woo REST key. Provide /healthz and /readyz, container image, chart Deployment/Service ClusterIP only. Test real tool calls with Inspector via port-forward and in-cluster client.

## Interfaces, data structures and contracts

Tool params and corresponding REST paths exactly LLD §7. Tool annotations informational only. No public ingress. Woo MCP may call WordPress REST; never let browser/chat connect upstream directly.

## Expected files/modules (proposed; inspect actual tree first)

services/woo-mcp/{app.py,models.py,Dockerfile,tests/test_tools.py}; charts/woo-mcp/templates/{deployment,service,config}.yaml; tests/integration/test_woo_mcp.py

## Explicit non-goals / constraints

No admin registry, chat, advanced ACL or generic gateway implementation.

## Verification commands and tests

```bash
python -m pytest services/woo-mcp/tests -q
python -m pytest tests/integration/test_woo_mcp.py -q
# MCP Inspector direct via temporary port-forward; record five calls
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

All five tools discover and execute; create and update mutate store as intended; invalid arguments and bearer token are rejected; not publicly exposed.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
