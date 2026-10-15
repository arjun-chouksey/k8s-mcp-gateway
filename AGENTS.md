# Working Agreement for Codex: k8s-mcp-gateway

**Repository:** `arjun-chouksey/k8s-mcp-gateway`  
**Task:** Urumi AI FDE Round 1 — WooCommerce hosting with a Team MCP Gateway on Kubernetes.  
**Deadline target:** October 26, 2026.  
**Mode:** Ticket-driven incremental implementation. The user must understand and be able to explain every subsystem. Work on one user-selected ticket at a time; the instruction to implement that ticket authorizes normal local changes within its scope.

## 1. Sources of truth and conflict order

1. **Original 8-page Urumi assignment PDF** (acceptance requirements, mandatory vs bonus).
2. `docs/HLD.md` (locked architecture and tradeoffs).
3. `docs/LLD.md` (contracts, schema and behaviour).
4. Root `ROADMAP.md` (milestones and exit criteria).
5. `docs/THREAT_MODEL.md` and `docs/DEMO.md` (security and acceptance verification).

If sources conflict, **stop, identify the conflict and propose the smallest correction**. Never silently relax the assignment to simplify implementation. The user-supplied earlier roadmap informed these documents but is superseded wherever different.

## 2. Ticket execution scope

1. Work on one approved implementation ticket at a time. A user's instruction to implement a ticket is approval to make normal local changes required by that ticket.
2. Read the selected ticket, only the relevant HLD/LLD sections, and the existing source files and tests affected by the work. Do not routinely read or update `docs/STATUS.md` or `docs/DECISIONS.md`.
3. Inspect repository status, branch, applicable files, existing tests and relevant package versions before editing. Avoid broad repeated repository reads.
4. Implement the ticket directly as a small vertical slice. Do not create separate planning, documentation or review phases for routine ticket work, and avoid unrelated refactors or untested placeholder scaffolding.
5. Stop and ask only when a required architectural decision is missing, the implementation conflicts with the approved HLD/LLD, a serious blocker requires user input, or the next action is destructive, creates credentials, deploys external resources or pushes commits.
6. Do not automatically start the next ticket. Wait for the user to select it.
7. Do not claim something is tested, deployed, secure or complete unless verified in real tool output.

## 3. Core invariants that must never break

- One WooCommerce store with real checkout/order persistence, custom five-tool WooCommerce MCP server, **at least three independent upstream MCP servers**.
- Gateway is both MCP server (downstream) and MCP client (upstream), with **one authenticated Streamable HTTP MCP endpoint**.
- Dashboard chat and external clients call upstream tools **only through gateway**. Chat must invoke its own gateway `/mcp` as the real logged-in user, not bypass the router.
- Admin server CRUD, member invite, own key creation, admin issue/revoke, hashed key storage, audit logs, credential isolation and key revocation on next call are mandatory.
- `slug__tool` namespacing, exact persisted alias mapping, dynamic discovery, safe timeouts and isolation when one upstream dies.
- Private MCP upstreams must have no Ingress; enforce gateway-only connectivity via tested NetworkPolicy and appropriate upstream credential.
- WordPress and database content on PVCs; probes and requests/limits on every workload; no hardcoded secrets.
- Same Helm chart templates for k3d and k3s; values/secrets/hosts may change, templates may not fork.
- Original 8-page PDF's definition-of-done flows with Users A and B take precedence over optional bonuses.

## 4. Technical guardrails

- Official MCP Python SDK **v2**, pinned to a tested exact release. Read v2 API docs and **do not use v1 FastMCP / `@server.list_tools` snippets**. For dynamic gateway use low-level constructor handlers and **explicit JSON Schema validation**. Confirm external client interoperability before building further layers.
- Do not invent REST endpoints, SDK methods, argument names or package exports. Check versioned docs/package source if uncertain, test minimal examples, and note what was verified.
- Prefer typed Python functions (Pydantic), SQLAlchemy migrations, modular gateway internal packages and simple React components.
- All DB migrations use Alembic and a single migration job; no ad hoc schema creation on every startup.
- Never put plaintext credentials into Git, Helm values, logs, demo video, browser API responses or test snapshots. External clients' gateway bearer keys are **not** forwarded to upstream servers.
- For WooCommerce REST over HTTP, follow official OAuth 1.0a requirements (or test HTTPS Basic); don't use unverified Basic over internal HTTP and don't write directly into private WooCommerce authentication tables.
- Never silently retry side-effecting MCP write tools after timeouts; product duplication is worse than an explicit uncertain result.
- Ensure auth check on **every** MCP HTTP request and current enabled/permission check on **every** `tools/call`. UI hiding is not authorization.
- Do not overengineer: no Kubernetes operator, event bus, full service mesh, distributed cache or multi-store provisioner before the mandatory acceptance matrix is green.

## 5. Work process per ticket

For each user-selected ticket:

1. Implement only the selected ticket and write focused tests for its behavior.
2. Run the relevant lint, test, build and ticket verification commands; prefer repeatable commands such as `make test`, `make smoke`, `helm lint` and `helm template` when they exist.
3. Run a negative test when implementing security or failure isolation, such as wrong role, disabled server, revoked key or unreachable upstream.
4. Inspect the diff for secret leakage, unused code, hardcoded hostnames, incompatible APIs, missing tests and gratuitous formatting changes.
5. Report completion in four or five lines: what was implemented; tests passed, failed or not run; and any blockers or significant architectural deviations. Never claim an unexecuted test passed.
6. Record or escalate only significant architectural deviations. If architecture changes are needed, stop and ask before changing the approved HLD/LLD.
7. Do **not** push to GitHub, deploy external resources, create credentials, perform destructive actions or delete persisted volumes without explicit user authorization.

## 6. Parallel Codex work boundaries

- **Infra lane:** `charts/`, `infra/`, `scripts/`.
- **Gateway lane:** `services/gateway/`, database schema and API contract.
- **Adapter lane:** `services/woo-mcp/`, `services/aux-mcp/`.
- **UI lane:** `web/dashboard/`.
- **Integrator:** shared docs, root values contract, test wiring and user-visible acceptance.

Freeze service addresses, route names, data schemas and Secret identifiers before parallel work. Do not let multiple agents concurrently edit shared migrations/Helm values/root docs. Each lane must provide a reproducible exit test; integration owner verifies the complete user flow. If tools are limited, proceed sequentially.

## 7. Required final verification

Use `docs/DEMO.md` and the full acceptance matrix **A01–A20**, including:

- Admin User A creates a product via chat and retrieves the real order placed afterward.
- Invited member User B connects an external client using only gateway URL/key, performs one prompt using two upstreams, and is denied on next request after key revocation.
- Disabling an upstream hides tools and denies stale calls; killing/scaling an upstream to zero shows unreachable while others continue functioning.
- Audit rows are user-attributed and include server, tool, timestamp, duration and outcome.
- NetworkPolicy prevents unauthorized Pods from calling private upstreams; the actual gateway can call them.
- The same Helm templates deploy locally and render/install on VPS k3s with environment-specific values and existing Secrets.
- README, threat model, design/tradeoffs and video can be explained end-to-end without unsupported claims.

**When uncertain, ask and validate. Never fabricate command output, screenshots, successful tests, repo state or final submission status.**
