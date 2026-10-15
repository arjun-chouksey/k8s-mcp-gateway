# T-024 — Team, invitations and personal API key dashboard

**Tier:** MANDATORY  
**Phase:** 5 · Dashboard  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-015, T-016, T-023  
**Acceptance IDs:** A08, A09, A13  
**Architecture decisions:** ADR-04 ADR-13  
**Design references:** LLD §4–5, §9; DEMO §2

## Objective

Complete account flows in the UI and provide external-client connection instructions.

## Exact implementation scope

Add Admin Team page: invite member via copy link, view/deactivate users, issue/revoke keys. Add My Keys: generate/view-prefix/show-once/copy/revoke and client snippets for MCP Inspector/Cursor/Claude Code using one gateway URL and bearer key. Accept Invite screen and logout. Observe expiry and denied members. Never reload/redisplay plaintext after modal dismissal.

## Interfaces, data structures and contracts

Use T-015/016 routes only. Display gateway key exactly once. Do not store plaintext key in localStorage or logs. Copy snippet generated locally with key only at creation time.

## Expected files/modules (proposed; inspect actual tree first)

web/dashboard/src/pages/{Members,InviteAccept,MyKeys}.tsx; web/dashboard/src/components/KeyOnceModal.tsx; tests/*

## Explicit non-goals / constraints

No emails, OAuth login, account payment or extra dashboards.

## Verification commands and tests

```bash
cd web/dashboard && npm run typecheck && npm test -- --run && npm run build
# browser A invites B; B accepts and creates key; revoke then next real /mcp call 401
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Two identities manageable; UI enforces visibility; revocation immediately reflected; external client setup instructions accurate.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
