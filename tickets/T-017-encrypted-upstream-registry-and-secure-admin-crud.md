# T-017 — Encrypted upstream registry and secure admin CRUD

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-013, T-014  
**Acceptance IDs:** A05, A06  
**Architecture decisions:** ADR-10 ADR-15  
**Design references:** LLD §4–5, §6; THREAT_MODEL §2

## Objective

Persist admin-managed servers safely and expose CRUD operations without redeployment.

## Exact implementation scope

Create upstream CRUD with immutable unique slug; typed URL/auth configuration; encrypted optional bearer/custom-header credential at rest; credential set/replace/clear actions; validation of timeouts and names. SSRF protection: explicitly allow approved in-cluster Service DNS/ports; require HTTPS for public endpoints; block loopback/link-local/cloud-metadata targets and unsafe redirects/resolutions. API responses expose only has_credential. Any change updates status/catalog through later catalog service.

## Interfaces, data structures and contracts

GET/POST /api/servers; PATCH/DELETE /api/servers/{id}; status enabled vs observational connected/unreachable/disabled; never return credential_ciphertext or plaintext. Need approved internal URL allowlist.

## Expected files/modules (proposed; inspect actual tree first)

services/gateway/app/security/{upstream_crypto,url_policy}.py; services/gateway/app/api/servers.py; services/gateway/tests/{test_registry,test_crypto,test_url_policy}.py

## Explicit non-goals / constraints

No tool discovery or MCP network calls in model serializers; no arbitrary localhost/metadata URLs.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_registry.py services/gateway/tests/test_crypto.py services/gateway/tests/test_url_policy.py -q
# nonadmin CRUD denied, injected metadata URL denied, response never contains secret
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Server CRUD works; encrypted credentials persisted; external response sanitized; URL abuse cases fail; disabled flag authoritative.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
