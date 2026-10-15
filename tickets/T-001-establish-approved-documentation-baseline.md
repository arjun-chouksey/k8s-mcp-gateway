# T-001 — Establish approved documentation baseline

**Tier:** MANDATORY  
**Phase:** 0 · Foundation  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** None  
**Acceptance IDs:** A20  
**Architecture decisions:** ADR-01–20  
**Design references:** HLD §1–10; LLD §1–13; AGENTS §§1–7; DEMO §§1–4

## Objective

Import the exact approved source documents into the existing repository without overwriting its README or diagram, and initialize ticket progress tracking.

## Exact implementation scope

Inspect git status and current tracked files; copy approved HLD, LLD, ROADMAP, AGENTS, threat model, demo checklist, decisions, and tickets index without rewriting architecture. Preserve existing README and docs/images. Add ignore rules for secrets, .env and private assignment source if needed.

## Interfaces, data structures and contracts

Authoritative order: original assignment > HLD > LLD > ROADMAP > security/demo notes > tickets.

## Expected files/modules (proposed; inspect actual tree first)

AGENTS.md; ROADMAP.md; docs/{HLD,LLD,THREAT_MODEL,DEMO,DECISIONS}.md; tickets/*.md; .gitignore only if needed

## Explicit non-goals / constraints

No app code, no package installs, no remote push, no replacement of existing README.

## Verification commands and tests

```bash
git status --short
git diff --check
git ls-files README.md docs/images/kubernetes-architecture.png
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Approved documents present; existing README/diagram preserved; exact file additions checked with git diff --stat.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
