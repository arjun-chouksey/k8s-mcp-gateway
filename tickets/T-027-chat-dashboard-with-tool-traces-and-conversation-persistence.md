# T-027 — Chat dashboard with tool traces and conversation persistence

**Tier:** MANDATORY  
**Phase:** 5 · Chat  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-023, T-026  
**Acceptance IDs:** A10, A11, A16  
**Architecture decisions:** ADR-04 ADR-14  
**Design references:** LLD §9; DEMO §2

## Objective

Provide simple usable chat and make real tool execution visible to reviewer.

## Exact implementation scope

Implement Chat screen with conversation list, message input, streaming text and inline tool-card events (alias, args redacted, duration, result status), final answer and clear failures. Show tool calls without exposing raw order PII. Conversation history isolated per user; stop/cancel where supported. Integrate actual SSE not mock data.

## Interfaces, data structures and contracts

Consume POST /api/chat event contract from T-026 and conversation REST per LLD. No frontend upstream MCP connection.

## Expected files/modules (proposed; inspect actual tree first)

web/dashboard/src/pages/Chat.tsx; components/{ChatTranscript,ToolCallCard}.tsx; lib/chat.ts; tests/*

## Explicit non-goals / constraints

No advanced AI framework, vector search, rich markdown rendering or independent tool invoker.

## Verification commands and tests

```bash
cd web/dashboard && npm run typecheck && npm test -- --run && npm run build
# browser A create product and retrieve orders with visible tool cards
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Tool cards reflect actual SSE events and persisted conversation; refresh preserves history; no secret disclosures.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
