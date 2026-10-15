# T-033 — Finalize README, design, threat model and verification records

**Tier:** MANDATORY  
**Phase:** 7 · Submission  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-031, T-032  
**Acceptance IDs:** A16, A18, A19, A20  
**Architecture decisions:** ADR-01–20  
**Design references:** LLD §11–12; DEMO §4; THREAT_MODEL §§1–8

## Objective

Ensure the repository is explainable and reproducible from a fresh clone.

## Exact implementation scope

Update (not replace) root README with architecture, prerequisites, install, secrets handling, COD checkout, external MCP client commands and chat usage, local + VPS instructions, backup/rollback and demo script. Confirm docs/HLD/LLD reflect approved decisions and only note verified implementation deltas in DECISIONS after approval. Threat model addresses token passthrough, untrusted upstream tools, members, SSRF, network policy. Map code to DEMO and tests; scan for secret leaks; mark unresolved items accurately.

## Interfaces, data structures and contracts

README is public entrypoint; HLD/LLD architecture remains locked unless approved deviation. Link all evidence to actual test run and commit.

## Expected files/modules (proposed; inspect actual tree first)

README.md; docs/{DEMO,THREAT_MODEL,STATUS,DECISIONS}.md; scripts/verify-docs.sh if useful

## Explicit non-goals / constraints

No feature creep, false production claims, unverified screenshots, or rewriting approved architectural tradeoffs.

## Verification commands and tests

```bash
git diff --check
# validate all README commands against a clean checkout and actual environment
# secret scan (document chosen scanner)
make smoke-local
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Reader can reproduce mandatory demo from README; verified steps linked; source/doc integrity and secret scan checked.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
