# S-004 — Register real remote MCP as fourth optional upstream

**Tier:** OPTIONAL  
**Phase:** 8 · Stand-outs  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-017, T-020, T-022  
**Acceptance IDs:** A05, A06, A09  
**Architecture decisions:** ADR-09 ADR-15  
**Design references:** HLD §3, §8; LLD §8

## Objective

Show gateway integrates a real external HTTPS MCP server, beyond locally controlled servers.

## Exact implementation scope

Select read-only public/authorized remote MCP; register via dashboard URL with optional scoped bearer/custom header and no code changes. Prove tool discovery and calls. Handle upstream errors and remote downtime without affecting three local demo servers. Never commit PAT or place user gateway token upstream.

## Interfaces, data structures and contracts

Remote URL must pass SSRF guard; server credentials held encrypted in registry. Four servers permissible: assignment requires at least three.

## Expected files/modules (proposed; inspect actual tree first)

docs/DEMO.md optional evidence; scripts/remote-smoke.sh optional; no product-specific gateway logic

## Explicit non-goals / constraints

No dependency of mandatory acceptance on public external service availability.

## Verification commands and tests

```bash
# actual dashboard registration and external MCP tool call; record only sanitized tool IDs
make test-integration
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Remote external server works once with scoped auth or clearly documented public mode; local three-server baseline unaffected.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
