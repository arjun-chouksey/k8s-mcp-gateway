# T-034 — Record demo, package submission and final approval

**Tier:** MANDATORY  
**Phase:** 7 · Submission  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-033  
**Acceptance IDs:** A20  
**Architecture decisions:** ADR-01–20  
**Design references:** DEMO §§1–4; original assignment page 7–8

## Objective

Produce required evidence and submission assets without claiming work not performed.

## Exact implementation scope

Rehearse and capture live two-user demo video: system architecture, checkout, chat product/order tools, external MCP client two-upstream prompt, revocation, disable, dead-upstream and audit, Kubernetes resources and isolation, Helm environment parity, threat choices. Record GitHub commit SHA and clean setup. Ensure no passwords/keys visible in recording. Prepare submission URL and file checklist. User performs any actual external form submission unless explicitly authorized.

## Interfaces, data structures and contracts

Required files: demo video, GitHub repo URL, README setup, HLD/tradeoffs, threat model, charts and source. Planning submission target: 2026-10-26. Exact submission time is UNVERIFIED pending the authoritative invitation; the assignment PDF specifies two weeks, not a calendar cutoff.

## Expected files/modules (proposed; inspect actual tree first)

docs/DEMO.md evidence and final checklist; README.md verification link; demo video artifact outside repo until approved

## Explicit non-goals / constraints

No claiming submitted form without confirmation, no publishing raw credentials, no architecture changes.

## Verification commands and tests

```bash
# Replay docs/DEMO.md live and review recording with credentials masked
# verify repository commit/version and screenshots against tested build
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

All required deliverables present, video covers definition-of-done; actual form submission status recorded only after user's confirmation.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
