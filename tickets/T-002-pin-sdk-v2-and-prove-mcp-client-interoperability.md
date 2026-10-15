# T-002 — Pin SDK v2 and prove MCP client interoperability

**Tier:** MANDATORY  
**Phase:** 0 · Foundation  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-001  
**Acceptance IDs:** A09  
**Architecture decisions:** ADR-02 ADR-03 ADR-13  
**Design references:** HLD §4, §9; LLD §1 Day 1, §6

## Objective

Eliminate MCP SDK and external-client compatibility risk with a tiny temporary integration spike.

## Exact implementation scope

Choose and pin a tested official MCP Python SDK v2 patch release; build one minimal fixed-function Streamable HTTP server and one dynamic low-level proxy endpoint using publicly documented v2 APIs. Require bearer authentication on the downstream endpoint. Discover and invoke the tool with MCP Inspector AND one actual external client (Claude Code or Cursor). Capture request/error semantics and version evidence. Keep spike independent of business features and delete/retain only useful tests/docs per approval.

## Interfaces, data structures and contracts

Document exact SDK methods, version, transport route, auth header, tool list/call request shapes, error behaviour; low-level tool arguments explicitly validated by JSON Schema. No untested v1 compatibility claims.

## Expected files/modules (proposed; inspect actual tree first)

spikes/mcp-compat/ (or services/gateway/tests/integration/test_mcp_transport.py); services/woo-mcp/pyproject.toml once selected; docs/DECISIONS.md only if selection deviates

## Explicit non-goals / constraints

No WooCommerce, full gateway DB, React or anonymous production endpoint. No broad refactor.

## Verification commands and tests

```bash
python -m pytest spikes/mcp-compat -q
# real MCP Inspector and external-client listing+call; exact steps and outputs in ticket report
python -m pip show mcp
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Two distinct real clients can discover and call a proxied tool with bearer auth; wrong token denied; pinned release and actual compatibility evidence captured.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.

## Stop condition / special risk

STOP if pinned v2 cannot implement or interoperate using public API; report evidence and ask approval for compatibility remedy.
