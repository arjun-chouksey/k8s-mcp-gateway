# Implementation Tickets — Dependency Roadmap and Traceability

**Status:** PLANNED ONLY. This repository may contain no application implementation yet. The core source of truth is the original Urumi assignment and the approved HLD/LLD; this index is a workflow plan, not an amendment to them.

## How to run tickets

1. Review `AGENTS.md`, the chosen ticket, and only referenced HLD/LLD sections. Do not reread every doc and file for every task.
2. The user explicitly authorizes a specific ticket for implementation in a new Codex turn. Selecting a ticket is not approval for cloud spend, secret publication, destructive cleanup, a remote push or architecture change.
3. One ticket per working session/branch. Implement, test, show exact output, report and request review.
4. `CODE_COMPLETE` is not `VERIFIED`; status moves to `VERIFIED` only with actual evidence and a review.
5. A BLOCKED ticket cannot silently be skipped if its acceptance IDs are mandatory. Resolve or explicitly obtain approval for a changed implementation plan.

**Scheduling:** dependency-based, not fixed-date gates. Planning submission target: **2026-10-26**. Exact submission time is **UNVERIFIED** pending the authoritative invitation; the assignment PDF specifies two weeks, not a calendar cutoff. Prioritize complete mandatory demonstrations before stand-outs.

## Ordered ticket list

| Ticket and title | Phase | Tier | Requires | A-criteria |
|---|---|---|---|---|
| [T-001 — Establish approved documentation baseline](T-001-establish-approved-documentation-baseline.md) | 0 · Foundation | MANDATORY | — | A20 |
| [T-002 — Pin SDK v2 and prove MCP client interoperability](T-002-pin-sdk-v2-and-prove-mcp-client-interoperability.md) | 0 · Foundation | MANDATORY | T-001 | A09 |
| [T-003 — Prove LLM tool calling with chosen provider](T-003-prove-llm-tool-calling-with-chosen-provider.md) | 0 · Foundation | MANDATORY | T-001 | A10, A11, A12 |
| [T-004 — Local k3d cluster namespaces and networking](T-004-local-k3d-cluster-namespaces-and-networking.md) | 1 · Kubernetes foundation | MANDATORY | T-001 | A17, A18, A19 |
| [T-005 — Helm umbrella and per-component chart contracts](T-005-helm-umbrella-and-per-component-chart-contracts.md) | 1 · Kubernetes foundation | MANDATORY | T-004 | A18, A19 |
| [T-006 — Deploy MariaDB and WordPress with durable PVCs](T-006-deploy-mariadb-and-wordpress-with-durable-pvcs.md) | 2 · Real store | MANDATORY | T-005 | A02, A18 |
| [T-007 — Initialize WooCommerce and prove checkout](T-007-initialize-woocommerce-and-prove-checkout.md) | 2 · Real store | MANDATORY | T-006 | A01, A02 |
| [T-008 — Issue supported WooCommerce REST credentials and verify auth](T-008-issue-supported-woocommerce-rest-credentials-and-verify-auth.md) | 2 · Real store | MANDATORY | T-007 | A03, A18 |
| [T-009 — Build WooCommerce REST client and error policy](T-009-build-woocommerce-rest-client-and-error-policy.md) | 2 · Real store | MANDATORY | T-008 | A03 |
| [T-010 — Expose five secure WooCommerce MCP tools](T-010-expose-five-secure-woocommerce-mcp-tools.md) | 2 · Real store | MANDATORY | T-002, T-009 | A03, A17 |
| [T-011 — Deploy independent currency MCP server](T-011-deploy-independent-currency-mcp-server.md) | 3 · Additional upstreams | MANDATORY | T-002, T-005 | A04, A12 |
| [T-012 — Deploy independent policy MCP and deliberate collision](T-012-deploy-independent-policy-mcp-and-deliberate-collision.md) | 3 · Additional upstreams | MANDATORY | T-002, T-005 | A04, A07 |
| [T-013 — Platform PostgreSQL and Alembic data model](T-013-platform-postgresql-and-alembic-data-model.md) | 4 · Gateway core | MANDATORY | T-005 | A06, A08, A16, A18 |
| [T-014 — Bootstrap admin and secure browser sessions](T-014-bootstrap-admin-and-secure-browser-sessions.md) | 4 · Gateway core | MANDATORY | T-013 | A08 |
| [T-015 — Team invites, member lifecycle and role guards](T-015-team-invites-member-lifecycle-and-role-guards.md) | 4 · Gateway core | MANDATORY | T-014 | A08 |
| [T-016 — Personal MCP API keys and immediate revocation](T-016-personal-mcp-api-keys-and-immediate-revocation.md) | 4 · Gateway core | MANDATORY | T-014 | A08, A09, A13 |
| [T-017 — Encrypted upstream registry and secure admin CRUD](T-017-encrypted-upstream-registry-and-secure-admin-crud.md) | 4 · Gateway core | MANDATORY | T-013, T-014 | A05, A06 |
| [T-018 — Implement version-pinned upstream MCP client adapter](T-018-implement-version-pinned-upstream-mcp-client-adapter.md) | 4 · Gateway core | MANDATORY | T-002, T-017 | A04, A09, A15 |
| [T-019 — Persist discovered tools and monitor upstream health](T-019-persist-discovered-tools-and-monitor-upstream-health.md) | 4 · Gateway core | MANDATORY | T-017, T-018 | A04, A05, A06, A07, A14, A15 |
| [T-020 — Unified authenticated MCP endpoint and tool router](T-020-unified-authenticated-mcp-endpoint-and-tool-router.md) | 4 · Gateway core | MANDATORY | T-016, T-018, T-019 | A05, A07, A09, A13, A14, A15 |
| [T-021 — Durable per-user tool-call audit and security failures](T-021-durable-per-user-tool-call-audit-and-security-failures.md) | 4 · Gateway core | MANDATORY | T-013, T-016, T-020 | A16 |
| [T-022 — Seed Woo upstream and complete three-server registration](T-022-seed-woo-upstream-and-complete-three-server-registration.md) | 4 · Gateway core | MANDATORY | T-010, T-011, T-012, T-019, T-020 | A04, A05, A07, A12 |
| [T-023 — Dashboard shell, sessions and upstream management UI](T-023-dashboard-shell-sessions-and-upstream-management-ui.md) | 5 · Dashboard | MANDATORY | T-014, T-017, T-019, T-022 | A05, A06, A08 |
| [T-024 — Team, invitations and personal API key dashboard](T-024-team-invitations-and-personal-api-key-dashboard.md) | 5 · Dashboard | MANDATORY | T-015, T-016, T-023 | A08, A09, A13 |
| [T-025 — Audit log and upstream status dashboard](T-025-audit-log-and-upstream-status-dashboard.md) | 5 · Dashboard | MANDATORY | T-021, T-023 | A06, A15, A16 |
| [T-026 — Chat agent executes only via gateway as logged-in user](T-026-chat-agent-executes-only-via-gateway-as-logged-in-user.md) | 5 · Chat | MANDATORY | T-003, T-016, T-020, T-021, T-022 | A10, A11, A12, A16 |
| [T-027 — Chat dashboard with tool traces and conversation persistence](T-027-chat-dashboard-with-tool-traces-and-conversation-persistence.md) | 5 · Chat | MANDATORY | T-023, T-026 | A10, A11, A16 |
| [T-028 — Apply required NetworkPolicies, probes and Secret boundaries](T-028-apply-required-networkpolicies-probes-and-secret-boundaries.md) | 6 · Infra and verification | MANDATORY | T-004, T-005, T-006, T-010, T-011, T-012, T-013, T-020 | A17, A18 |
| [T-029 — Automated gateway integration and adversarial tests](T-029-automated-gateway-integration-and-adversarial-tests.md) | 6 · Infra and verification | MANDATORY | T-020, T-021, T-022, T-028 | A05, A07, A13, A14, A15, A16, A17 |
| [T-030 — Clean k3d install, Helm lifecycle and release robustness](T-030-clean-k3d-install-helm-lifecycle-and-release-robustness.md) | 6 · Infra and verification | MANDATORY | T-023, T-024, T-025, T-027, T-028, T-029 | A01, A02, A17, A18, A19 |
| [T-031 — Two-user definition-of-done end-to-end rehearsal](T-031-two-user-definition-of-done-end-to-end-rehearsal.md) | 6 · Infra and verification | MANDATORY | T-024, T-025, T-027, T-030 | A01, A03, A04, A05, A06, A08, A09, A10, A11, A12, A13, A14, A15, A16, A17 |
| [T-032 — Validate local/VPS values parity and k3s deployment guide](T-032-validate-local-vps-values-parity-and-k3s-deployment-guide.md) | 6 · Infra and verification | MANDATORY | T-030 | A19, A20 |
| [T-033 — Finalize README, design, threat model and verification records](T-033-finalize-readme-design-threat-model-and-verification-records.md) | 7 · Submission | MANDATORY | T-031, T-032 | A16, A18, A19, A20 |
| [T-034 — Record demo, package submission and final approval](T-034-record-demo-package-submission-and-final-approval.md) | 7 · Submission | MANDATORY | T-033 | A20 |
| [S-001 — Actually deploy to VPS with TLS and restoreable backups](S-001-actually-deploy-to-vps-with-tls-and-restoreable-backups.md) | 8 · Stand-outs | OPTIONAL | T-032, T-033 | A19 |
| [S-002 — Enforce role-aware tool allowlist at list and call](S-002-enforce-role-aware-tool-allowlist-at-list-and-call.md) | 8 · Stand-outs | OPTIONAL | T-020, T-021, T-025 | A08, A14 |
| [S-003 — Per-upstream Prometheus-compatible latency and failure metrics](S-003-per-upstream-prometheus-compatible-latency-and-failure-metrics.md) | 8 · Stand-outs | OPTIONAL | T-021, T-025 | A15, A16 |
| [S-004 — Register real remote MCP as fourth optional upstream](S-004-register-real-remote-mcp-as-fourth-optional-upstream.md) | 8 · Stand-outs | OPTIONAL | T-017, T-020, T-022 | A05, A06, A09 |
| [S-005 — Scale stateless gateway to two replicas safely](S-005-scale-stateless-gateway-to-two-replicas-safely.md) | 8 · Stand-outs | OPTIONAL | T-019, T-030 | A15, A16 |
| [B-001 — Approve bonus multi-store provisioning design and isolation contract](B-001-approve-bonus-multi-store-provisioning-design-and-isolation-contract.md) | 9 · Deferred bonus | BONUS_NOT_APPROVED | T-034 | — |
| [B-002 — Implement per-store Kubernetes Helm provisioner](B-002-implement-per-store-kubernetes-helm-provisioner.md) | 9 · Deferred bonus | BONUS_NOT_APPROVED | B-001 | — |
| [B-003 — Automatic per-store MCP registration and cross-store chat verification](B-003-automatic-per-store-mcp-registration-and-cross-store-chat-verification.md) | 9 · Deferred bonus | BONUS_NOT_APPROVED | B-002 | — |

## Vertical-slice gates (actual executable proof)

- **G0 — Design baseline:** T-001. Source documents are available, no feature falsely marked implemented.
- **G1 — MCP protocol:** T-002. External MCP client lists/calls one gateway-proxied tool using auth, independent of WooCommerce.
- **G2 — Real store:** T-006–T-010. Real checkout and five custom Woo MCP tools work on persistent WordPress/MariaDB.
- **G3 — Three upstream gateway:** T-011–T-013, T-017–T-022. Dynamic registration, aliased listing and tool call across three independent servers.
- **G4 — Multi-user security:** T-014–T-016, T-021, T-024–T-025. Role-bound access, keys, revocation, audit.
- **G5 — Chat:** T-003, T-026–T-027. Chat invokes its own /mcp and produces real side effects/answers as logged-in user.
- **G6 — Kubernetes/full acceptance:** T-028–T-032. Policies, probes, Helm lifecycle, end-to-end A/B, local/VPS portability.
- **G7 — Documentation/submission:** T-033–T-034. Fresh-clone evidence and video.

Gates express verification targets, **not project status**. Multiple tickets can progress out of numeric order when their dependencies are satisfied. `S-*` stand-outs and `B-*` bonus tickets are unapproved non-blockers until explicitly authorized.

## Mandatory acceptance coverage (implementation planned, not verified)

| Acceptance | Requirement | Planned tickets |
|---|---|---|
| A01 | Real storefront, cart, COD checkout and wp-admin order | T-007, T-030, T-031 |
| A02 | WordPress/MariaDB persistent data after Pod replacement | T-006, T-007, T-030 |
| A03 | Custom Woo MCP with all five required tools | T-008, T-009, T-010, T-031 |
| A04 | At least three independently deployed upstream MCP servers | T-011, T-012, T-018, T-019, T-022, T-031 |
| A05 | Runtime server registration and tool discovery | T-017, T-019, T-020, T-022, T-023, T-029, T-031 |
| A06 | Admin add/edit/disable/remove; status and tools | T-013, T-017, T-019, T-023, T-025, T-031 |
| A07 | Deterministic collision-safe aliases | T-012, T-019, T-020, T-022, T-029 |
| A08 | Two roles, invitations, member management and own keys | T-013, T-014, T-015, T-016, T-023, T-024, T-031 |
| A09 | External client via one gateway URL + bearer key | T-002, T-016, T-018, T-020, T-024, T-031 |
| A10 | User A chat creates visible product | T-003, T-026, T-027, T-031 |
| A11 | User A chat retrieves today’s real order | T-003, T-026, T-027, T-031 |
| A12 | User B prompt invokes two distinct upstreams | T-003, T-011, T-022, T-026, T-031 |
| A13 | Revoked key denied on next request | T-016, T-020, T-024, T-029, T-031 |
| A14 | Disabled upstream hidden and stale direct call denied | T-019, T-020, T-029, T-031 |
| A15 | Dead upstream isolated, status Unreachable | T-018, T-019, T-020, T-025, T-029, T-031 |
| A16 | Attributed per-tool audit incl outcomes and duration | T-013, T-021, T-025, T-026, T-027, T-029, T-031, T-033 |
| A17 | Private upstreams and enforced NetworkPolicy | T-004, T-010, T-028, T-029, T-030, T-031 |
| A18 | K8s probes, limits, Secrets, PVCs and stable ingress | T-004, T-005, T-006, T-008, T-013, T-028, T-030, T-033 |
| A19 | Same Helm templates on local k3d and VPS k3s | T-004, T-005, T-030, T-032, T-033 |
| A20 | GitHub repo, video and README/design/threat documents | T-001, T-032, T-033, T-034 |

> LLD A04 now states **at least three** independent upstreams, matching the assignment. The approved baseline remains **three in-cluster servers**, with a fourth remote server optional. This approved wording correction is recorded as CL-001 in `docs/DECISIONS.md`; no architecture change was made.

## Verification and sign-off policy

- Unit tests substantiate algorithms/contracts; integration tests exercise real SDK Streamable HTTP, DB, and authenticated HTTP; smoke tests exercise deployed Kubernetes and browser/external client flows.
- Security tests must include invalid/revoked keys, forbidden roles, blocked network callers, secret non-disclosure, stale aliases and upstream failures.
- For an unrun manual, VPS, LLM or client test, record `NOT_RUN (why)`; do not mark green.
- Completion reports state the commit or diff, test evidence, blockers, and architectural deviations. Ticket files remain implementation instructions rather than progress logs.
- A final pass requires **A01–A20** fully VERIFIED; stand-outs/BONUS do not compensate for missing mandatory acceptance.
