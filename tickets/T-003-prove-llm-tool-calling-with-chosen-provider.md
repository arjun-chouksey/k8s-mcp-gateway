# T-003 — Prove LLM tool calling with chosen provider

**Tier:** MANDATORY  
**Phase:** 0 · Foundation  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-001  
**Acceptance IDs:** A10, A11, A12  
**Architecture decisions:** ADR-19  
**Design references:** HLD §4, §9; LLD §1 and §9

## Objective

Verify a usable LLM API supports multiple tool-call turns before chat work begins.

## Exact implementation scope

Test candidate provider(s) with one read tool and one write-like fake tool, stable tool_call IDs, argument JSON and a second round that includes tool results. Verify key/quota/model access and latency; record chosen provider and fallback with evidence. Keep provider configurable by base URL/model/Secret. Ask user approval on paid billing or changing the approved pluggable-provider principle.

## Interfaces, data structures and contracts

Provider adapter contract: get_completion(messages, tools) -> text and zero-or-more named calls with IDs and JSON arguments. Secrets never print; no real WooCommerce mutations.

## Expected files/modules (proposed; inspect actual tree first)

spikes/llm-toolcalls/; docs/STATUS.md; optionally docs/DECISIONS.md if chosen provider/model impacts assumptions

## Explicit non-goals / constraints

No full agent, dashboard, user auth or provider-specific rewrite of architecture.

## Verification commands and tests

```bash
python -m pytest spikes/llm-toolcalls -q
# live provider call (manually authorized); record HTTP response metadata without secrets
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

At least one actual model two-turn tools exchange; invalid/model/quota failure documented honestly; provider selection recorded.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
