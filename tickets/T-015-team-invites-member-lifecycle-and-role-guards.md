# T-015 — Team invites, member lifecycle and role guards

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-014  
**Acceptance IDs:** A08  
**Architecture decisions:** ADR-13  
**Design references:** LLD §4–5; DEMO §2

## Objective

Allow admin invitation and team management while preserving member boundaries.

## Exact implementation scope

Implement single-use expiring invite-token issuance and acceptance, role validation, member listing/deactivation, admin management APIs and member denial cases. Invitation link may be copied from UI; email transport optional. Guarantee inactive members cannot authenticate/use keys. Admin may initiate key issuance/revocation via existing/next key module.

## Interfaces, data structures and contracts

POST /api/invites, POST /api/invites/accept, GET /api/members, PATCH /api/members/{id} (exact verb per LLD). Store token digest only. Reuse session guards.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/api/{invites,members}.py; security/permissions.py; tests/test_team.py

## Explicit non-goals / constraints

No OAuth provider, mail infrastructure, or member ability to manage another member.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_team.py -q
# admin invite -> accept -> member login; expired/replayed invite denied
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Two distinct users can exist; member cannot manage servers/users; inactive user access denied; invite expires and is single-use.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
