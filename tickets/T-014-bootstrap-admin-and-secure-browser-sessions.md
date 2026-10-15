# T-014 — Bootstrap admin and secure browser sessions

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-013  
**Acceptance IDs:** A08  
**Architecture decisions:** ADR-13  
**Design references:** LLD §4, §5; THREAT_MODEL §§2–4

## Objective

Implement login/logout/me and one-time admin bootstrap with durable session cookies.

## Exact implementation scope

Bootstrap admin from Kubernetes Secret once; password Argon2id. Implement login throttling, cookie with HttpOnly, SameSite appropriate to same origin, Secure on HTTPS, persisted session-token digest, logout invalidation, GET /api/me and a tested CSRF/Origin guard on mutating cookie-authenticated calls. No session plaintext persisted. Active/inactive user semantics.

## Interfaces, data structures and contracts

POST /api/auth/login; POST /api/auth/logout; GET /api/me; session cookie never returned as JSON. Fields and error codes as specified in LLD API table.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/security/web_sessions.py; services/gateway/app/api/auth.py; services/gateway/tests/test_sessions.py; bootstrap script/job wiring

## Explicit non-goals / constraints

No email delivery, API keys, teams UI or upstream registry.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_sessions.py -q
# HTTP smoke login/me/logout and cross-origin mutation blocked
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Admin seeded once, login session works, logout invalidates, role identity loaded, CSRF and invalid credentials denied.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
