# T-013 — Platform PostgreSQL and Alembic data model

**Tier:** MANDATORY  
**Phase:** 4 · Gateway core  
**Initial status:** `NOT_STARTED` (planning only)  
**Dependencies:** T-005  
**Acceptance IDs:** A06, A08, A16, A18  
**Architecture decisions:** ADR-05 ADR-17  
**Design references:** HLD §3; LLD §3, §10

## Objective

Create durable platform database and schema for registry, users, keys, audit and chat.

## Exact implementation scope

Deploy PostgreSQL StatefulSet/Service/PVC with Secret refs and probes in platform namespace. Implement async SQLAlchemy models and Alembic migrations for users, web_sessions, invites, api_keys, upstreams, upstream_tools, audit_events, conversations and messages per LLD. Migration run exactly once via Job or documented explicit command. Include uniqueness/indexing and UTC timestamps.

## Interfaces, data structures and contracts

UUID ids; upstream slug immutable unique; aliases unique; hashed key digests; ciphertext rather than plaintext; audit indexed by actor/time. Do not create separate event broker.

## Expected files/modules (proposed; inspect actual tree first)

charts/platform-db/templates/*.yaml; services/gateway/app/{database.py,models.py,settings.py}; services/gateway/alembic/*; services/gateway/tests/test_migrations.py; charts/gateway/templates/migration-job.yaml

## Explicit non-goals / constraints

No REST handlers, dashboard UI, implicit create_all() at app startup, or production passwords in chart.

## Verification commands and tests

```bash
python -m pytest services/gateway/tests/test_migrations.py -q
# alembic upgrade head against disposable Postgres
kubectl -n platform get pods,pvc,job
```

**Evidence rule:** Verification commands below are **planned** commands, not claims of runs; if source trees/test targets differ after implementation, record actual paths/commands and explain the divergence. Manual/external checks must be reported as manual, not automatically passed. Always inspect current repository state before acting.

## Acceptance criteria and Definition of Done

Migration works on fresh DB and repeat run is no-op; all required tables and constraints exist; PVC bound; secret references used.

All ticket-specific tests actually executed/passed or clearly blocked; required negative tests completed where applicable; documentation/tests kept in sync; changed paths inspected for secrets and diff noise; no unapproved architecture deviation. Mark `VERIFIED` only after an independent review of evidence. 

## Expected Codex completion report

Codex completion report **must** include: ticket ID and status (`CODE_COMPLETE`, `BLOCKED`, or `VERIFIED` only with evidence); changes and files; exact commands run and outcomes (pass/fail/skipped with reason); acceptance criteria and evidence; security/negative tests; deviations and approval IDs; open risks; commit SHA if one exists; recommended next dependency-ready ticket. Never imply an unrun command passed.
