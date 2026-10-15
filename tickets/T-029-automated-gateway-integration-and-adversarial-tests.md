# T-029 — Automated gateway integration and adversarial tests

**Tier:** MANDATORY  
**Phase:** 6 · Infra and verification  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-020, T-021, T-022, T-028  
**Acceptance IDs:** A05, A07, A13, A14, A15, A16, A17  
**Architecture decisions:** ADR-10–15 ADR-20  
**Design references:** LLD §6, §11; THREAT_MODEL §2

## Objective

Exercise dynamic gateway under collisions, revocation, upstream outages and malicious inputs.

## Exact implementation scope

Build integration harness with two or more real Streamable HTTP mock servers (normal, slow, dead, colliding tool). Test runtime add/edit/disable/delete; stale alias denial; per-request key revocation, wrong-role requests, schema invalid args, errors and timeout; catalog listing cache-only; simultaneous upstream resilience, no credential passthrough, URL SSRF rejection and audit on failures. Include a write timeout case proving no auto retry.

## Interfaces, data structures and contracts

Harness uses actual SDK v2 transport, not REST mocks in place of MCP; reproducible local commands, deterministic timeouts.

## Expected files/modules (proposed; inspect actual tree first)

tests/integration/{test_gateway_lifecycle,test_failures,test_auth_isolation,test_write_retries}.py; scripts/test-integration.sh; Makefile integration target

## Explicit non-goals / constraints

No real cloud billing, no flaky requirement on remote fourth server.

## Verification commands and tests

```bash
make test-integration
# manually scale down currency and confirm Woo + policy remain available and list fast
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

All acceptance-negative paths verified in integration tests; failures and output captured without secrets.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
