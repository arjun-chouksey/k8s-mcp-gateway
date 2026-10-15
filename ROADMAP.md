# Implementation Roadmap: Urumi AI FDE — Kubernetes Team MCP Gateway

**Version:** 1.0, 2026-10-12  
**Target:** Complete and submit by **2026-10-26** (confirm exact cut-off time in original invitation).  
**Principle:** **Every mandatory capability ships.** We use speed gained from Codex to improve testing and documentation, not to eliminate acceptance requirements.

## 1. What we are delivering

One working WooCommerce storefront (persistent WordPress/MariaDB); a custom five-tool WooCommerce MCP server; two other independent MCP servers; a **dynamic, multi-user MCP gateway** exposed as one Streamable HTTP endpoint; a React dashboard with server administration, invites, personal keys, server status, audit logs and user-scoped chat; and Helm deployability on **k3d locally and k3s VPS with the same templates**.

**Definition of done:** All A01–A20 acceptance checks in `docs/LLD.md` and the live two-user script in `docs/DEMO.md` pass. Requirements come from the user's original Urumi brief; do not silently narrow them.

## 2. Architecture baseline

See `docs/HLD.md` for diagrams/decisions and `docs/LLD.md` for exact module/API/data contracts. Locked directions:

- **Namespaces:** `store`, `mcp`, `platform`; enforced Kubernetes NetworkPolicies.
- **Helm:** component charts (`store`, `woo-mcp`, `aux-mcp`, `gateway`, `platform-db`, `dashboard`) combined in one umbrella platform release; environment overrides only.
- **Backend:** modular FastAPI gateway with PostgreSQL; React/TypeScript/Vite frontend.
- **MCP:** official Python SDK v2; fixed tools with `MCPServer`, dynamic gateway using low-level `on_list_tools`/`on_call_tool`, explicit input schema validation, Streamable HTTP.
- **Catalog:** Postgres cached upstream tools, deterministic `slug__tool` aliases, fail-isolated routing and bounded health probes.
- **Identity:** web sessions, admin/member roles, own key generation, admin key issue/revoke, hashed gateway keys, server-side encrypted upstream secrets, audited actor propagation through chat's own MCP client.
- **Store:** WooCommerce REST v3 via supported read/write REST key and correct HTTP OAuth1/HTTPS auth; no direct auth-table writes.
- **Demo default:** User A = admin using dashboard chat; User B = invited member using external MCP client. Three in-cluster servers ensure the main demonstration doesn't depend on external availability.

## 3. Delivery strategy: integration-first, evidence at each boundary

**Never build six services in isolation and integrate on the last day.** Keep a continuously working vertical slice: client → gateway → upstream → result → audit. Add features while preserving that slice.

Each milestone has **entry dependency, exit test and a documented acceptance outcome**. Do not move to UI polish or extra features with failed critical path gates.

### Day 1 — Oct 13: foundation and protocol spikes

- Confirm exact SDK v2 package patch, `MCPServer` and dynamic low-level API, modern/legacy client support, and a real external MCP client test over Streamable HTTP.
- Run gateway hello-world proxy to a fixed upstream with an API-key-guarded MCP endpoint.
- Test chosen LLM provider with a real function/tool-call round trip, lock provider adapter contract.
- Create namespaces, k3d cluster, chart skeleton, lockfile, Dockerfiles and minimal CI (`helm lint`, `helm template`, Python/TS basic checks).
- **Exit:** External MCP client lists and invokes one gateway-proxied tool; no direct upstream URL supplied to client; chart rendering works for both values variants.

### Days 2–3 — Oct 14–15: stateful store and custom Woo MCP

- Deploy MariaDB and WordPress with PVCs, probes and resource limits. Activate WooCommerce, COD checkout, persistent product/order. Document or automate idempotent setup where supported.
- Create WooCommerce read/write REST key through supported method, store only in Kubernetes Secret, verify correct OAuth1 or HTTPS authentication.
- Implement all **five mandatory Woo tools**, validate arguments and dates, integrate HTTP REST client and isolated bearer credentials.
- **Exit:** Manual COD checkout visible in wp-admin; delete/recreate Pod and data survives; MCP Inspector calls list/create products and list/get/update orders using the custom MCP server.

### Day 4 — Oct 16: three upstreams and gateway catalog

- Create separate currency MCP and policy MCP services (different processes and Services) with clean tool names and documented data provenance.
- Implement Postgres migrations for upstreams/tools, encrypted credential storage, registry create/edit/disable/delete, discovery and cached catalog. Bootstrap Woo as first registration; add Currency and Policy through admin flow.
- Implement `slug__name` alias mapping and deliberate tool-name collision test.
- **Exit:** Add third server via an API/admin flow **without gateway redeploy**; a single MCP endpoint lists/routs tools from all three.

### Days 5–6 — Oct 17–18: users, keys, trust and audit

- Implement admin login, session cookies, invite link acceptance, admin/member access control, own key issuance and admin issue/revoke, hashed keys, per-call auth.
- Implement tool execution pipeline: current enabled/permissions checks; JSON Schema validation; no token passthrough; upstream timeouts; safe error results; one durable audit row per tool attempt.
- Health refresh with `Connected/Unreachable/Disabled`; fail-isolated cached listing; cluster NetworkPolicy allow/deny tests.
- **Exit:** User B connects via one URL and own key, then is revoked and denied next call; disable removes tools and rejects stale invocation; killed/scaled-down server shows unreachable without breaking others; audit correctly identifies users.

### Days 7–8 — Oct 19–20: dashboard, chat and complete user stories

- Finish React screens: login/invite, servers CRUD/status/tools, team management, own API keys, audit list and chat.
- Chat uses internal JWT + SDK MCP **client to gateway's real `/mcp` endpoint**, not direct adapter/REST. Implement bounded LLM tool loop, visible tool cards, user attribution, clear failures.
- **Exit:** User A asks chat to create a named/priced product; product appears on storefront; after COD order, chat retrieves that order. User B asks a two-server prompt through real external client. Everything audited.

### Day 9 — Oct 21: mandatory hardening and complete local acceptance

- Repeat test from clean cluster/config (or clean database with safe reset script); no implicit local developer state.
- Fix probes, resource limits, Secret mounts, NetworkPolicies, concurrency, availability detection, masked credentials, all REST permission checks.
- Verify helm install, upgrade and rollback scenario; run entire `docs/DEMO.md` and automated tests.
- **Exit:** A01–A18 pass locally, with screenshot/command/video evidence. Zero known mandatory functional gaps.

### Day 10 — Oct 22: deployment portability and documentation

- Freeze component chart templates; render with `values-vps.yaml`; deploy to VPS k3s if practical, with DNS/TLS and explicitly pre-created Secrets. Test one real checkout and one MCP call remotely.
- Document VPS resource budgets, backup/restore, stored credentials and deployment issues. Finish README and core design/tradeoffs/threat-model documents.
- **Exit:** Same charts deploy or at least are demonstrably deployable on k3s with config-only changes, as required; actual successful VPS demonstration earns standout credit.

### Days 11–12 — Oct 23–24: high-impact stand-outs only

Priority order, stop whenever risk to core appears:

1. **Per-role tool permissions**: admin write, member read; both discoverability and invocation enforcement, plus denied audit.
2. **Observability**: per-upstream call/error/latency metrics and useful diagnostic display; a deliberate outage demo.
3. **Fourth external MCP server**: HTTPS, optional scoped credential; prove arbitrary registration without impacting offline three-server workflow.
4. **Second gateway replica** only after heartbeat/health-refresh coordination is safe, concurrency audit passes, and two-user operations remain correctly scoped.

Do not attempt multi-store provisioning unless the complete core, VPS story and demo are finished with buffer remaining.

### Day 13 — Oct 25: freeze and film

- Full fresh-clone smoke test; rerun all original assignment definition-of-done scenarios; collect `kubectl`/Helm evidence.
- Record 8–12 minute demo (length flexible): architecture, live two-user flow, K8s boundaries, failure case, audit, secrets, local/VPS.
- Verify GitHub source, README, setup instructions, demo video sharing permissions, threat model, screenshots and no credential leakage.
- **Exit:** All deliverables ready; submission form dry run with non-sensitive URLs.

### Day 14 — Oct 26: contingency and submit

- Buffer for integration regression, packaging, editing demo and **submission**. Do not begin major new features.
- Submit video + repo through the official form well ahead of the deadline and record confirmation.

## 4. Testing gates and priority

| Gate | Cannot compromise | Pass/fail evidence |
|---|---|---|
| G1 Protocol | Real v2 gateway interoperates with real external client | tools/list + tools/call with API key |
| G2 Store | Real, durable WooCommerce checkout | Order in wp-admin after Pod replacement |
| G3 MCP adapters | Custom five Woo tools + two auxiliary servers | Inspector real calls across three servers |
| G4 Dynamic gateway | Add/remove/disable without restart; collision-safe; dead upstream isolated | Integration tests + dashboard status |
| G5 Team security | Two identities, hashed/revocable keys, secret isolation, per-call auth | 401 revoked; no creds in browser; B cannot manage servers |
| G6 Chat | Calls same gateway endpoint **as user** | Tool cards + A audit entry + actual side effect |
| G7 Infra | Three namespaces, private upstream policies, probes, PVCs, ingress, secrets, Helm | `kubectl` evidence + negative network test |
| G8 Portability | Same charts for k3d/k3s | Helm render/install + documented differences |
| G9 Submission | Demo + repo + README + design + threat model | Checklist in `docs/DEMO.md` |

## 5. What Codex can work on in parallel

Parallel work is useful only after the shared contracts are stable. Suggested ownership boundaries:

- **Infra lane:** charts, Docker builds, k3d/k3s, namespaces, NetworkPolicies, test scripts. Owns `charts/`, `infra/`, `scripts/`.
- **Backend lane:** gateway SDK integration, DB migrations, auth and registry, `services/gateway/`.
- **Store/adapter lane:** WordPress/Woo bridge and auxiliary MCP servers, `services/woo-mcp/`, `services/aux-mcp/`.
- **UI lane:** React pages and API client, `web/dashboard/`, using typed response contracts defined by backend.

**Do not** concurrently edit shared Helm values, central API contracts, DB migrations or root docs without a designated owner. Each lane must pass checks before its output is integrated. One integrator owns the end-to-end verification. Use the `AGENTS.md` instructions for Codex safety and handoff expectations.

## 6. Backlog policy: never trade a mandatory requirement for polish

**P0:** Every requirement in original brief and acceptance matrix A01–A20, even if visually plain.  
**P1:** Robust idempotent bootstrap, actual VPS deployment, tool permissions, metrics and fourth external integration.  
**P2:** Two gateway replicas, rate limiting, more refined UX and richer tool-change alerts.  
**P3, explicitly optional:** Multi-store provisioning, hosted image-based MCP servers, OAuth, ten-server/hundreds-of-tools retrieval, complete observability stack.

If timeline slips, remove P2/P3 first, then nonessential styling. **Do not remove P0.** If a mandatory scenario still cannot be demonstrated, record the blocker honestly and prioritize resolving it before optional work.

## 7. Submission and quality checklist

- [ ] GitHub repo builds from a clean clone; no secrets in commit history.
- [ ] README: architecture, prerequisites, local installation, how to order, external MCP connection, chat, VPS/k3s instructions, troubleshooting.
- [ ] Source: dashboard, gateway backend and chat, custom Woo MCP, other upstream servers.
- [ ] Helm chart + local and VPS values; correct namespace/Secret/PVC/Ingress/policy behaviour.
- [ ] `docs/HLD.md`, `docs/LLD.md`, `docs/THREAT_MODEL.md`, `docs/DEMO.md`, system design/tradeoffs.
- [ ] Working demo with **two users**, a real store, three upstreams and visible audit entries.
- [ ] Test evidence for enable/disable, revoked next call, unreachable upstream, tool-name collision, two-upstream prompt.
- [ ] Explain WooCommerce OAuth/API keys; auth credential propagation; security boundaries; Helm upgrade/rollback and storage/backups.
- [ ] Video accessible with working share link; official submission form completed.

## 8. Assumptions to verify before spending time

1. Exact MCP SDK 2.x package version and external client's ability to use the endpoint.
2. Selected LLM provider's real tool-call support and remaining quota.
3. DNS for local `*.127.0.0.1.nip.io` and Traefik route mapping.
4. WooCommerce internal HTTP OAuth1 request signing and POST behaviour.
5. Host Mac memory budget / VPS CPU-RAM budget for 8 workloads and two databases.
6. Exact deadline time and submission form accessibility.

*This supersedes the uploaded original `ROADMAP.md` plan, while preserving its core ideas and all mandatory assignment requirements.*
