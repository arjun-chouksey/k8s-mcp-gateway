# T-023 — Dashboard shell, sessions and upstream management UI

**Tier:** MANDATORY  
**Phase:** 5 · Dashboard  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-014, T-017, T-019, T-022  
**Acceptance IDs:** A05, A06, A08  
**Architecture decisions:** ADR-04 ADR-13  
**Design references:** LLD §5, §9; HLD §5.1

## Objective

Build React frontend that supports login and complete admin upstream registry management.

## Exact implementation scope

Vite React TS app with same-origin /api client, session handling, route protection and admin/member nav. Screens: login, servers list/status/tools, add/edit URL/credential (write-only), enable/disable/delete, last error/checked. Dynamic updates without redeploy. Credential response only has_credential. Use accessible error states, avoid secret localStorage or XSS HTML rendering.

## Interfaces, data structures and contracts

API consumes contracts from T-014/017/019; frontend never calls upstream MCP directly. Admin-only mutation buttons and backend-authorized guards.

## Expected files/modules (proposed; inspect actual tree first)

web/dashboard/{package.json,src/main.tsx,src/pages/{Login,Servers}.tsx,src/components/*,src/lib/api.ts,Dockerfile}; charts/dashboard/templates/*.yaml; web/dashboard/tests/*

## Explicit non-goals / constraints

No full chat, team management, cosmetic animation or SSR framework.

## Verification commands and tests

```bash
cd web/dashboard && npm ci && npm run typecheck && npm test -- --run && npm run build
# browser add/edit/disable/delete + status/tool list; member cannot mutate via API
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Login works; server CRUD usable end-to-end; credentials never shown; role-sensitive UI and errors accurate.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
