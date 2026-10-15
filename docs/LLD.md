# Low-Level Design: Team MCP Gateway + WooCommerce on Kubernetes

**Status:** Implementation contract v1.0, 2026-10-12. **Not yet built or integration-tested.**  
**Companions:** `HLD.md`, `THREAT_MODEL.md`, `DEMO.md`, root `ROADMAP.md` and `AGENTS.md`.  
**Rules:** Preserve mandatory functionality; keep all tool execution through gateway; make tests observable; explicitly record failures and risks. The actual Urumi assignment supersedes this design if inconsistent.

## 1. Locked technology choices and open gates

- Python 3.11+; FastAPI, async SQLAlchemy, PostgreSQL, Alembic, Pydantic; `httpx`/`httpx2` as required by the selected official MCP SDK v2 transport.
- **Official `mcp` Python SDK 2.x**, pin exact tested version/lockfile **after Day 1 interoperability spike**. Do **not** import legacy `FastMCP` or `@server.list_tools()` in new code. Fixed-function MCP servers use `MCPServer` and `@mcp.tool()`. Gateway uses low-level `Server(on_list_tools=..., on_call_tool=...)`, explicitly returning `ListToolsResult` / `CallToolResult` and explicitly validating dynamic tool arguments with JSON Schema 2020-12. Use only public SDK APIs documented by pinned version.
- React, TypeScript, Vite, React Router and TanStack Query; small reusable UI components. Chat events over SSE from REST backend. No frontend requests directly to upstream servers.
- WordPress official Apache-based image + WooCommerce plugin + MariaDB; one WordPress replica and PVC. Woo REST v3 via an OAuth1-capable Python HTTP client for internal HTTP (test in real cluster) or verified HTTPS Basic Auth; don't assume ordinary Basic Auth over HTTP works.
- k3d/k3s with Traefik, built-in policy controller when enabled, and configured StorageClass. Docker images published/imported with pinned versions. Existing Kubernetes Secrets, never Helm-generated sensitive values committed in git.
- LLM provider API compatible with the selected Python adapter, with **tested tool-call round trips** before implementation. No assumption that all “OpenAI-compatible” endpoints implement tool calls identically.

### Day 1 technical gates (blockers)

1. Expose one fixed MCP server and a minimal dynamic low-level gateway over Streamable HTTP; connect MCP Inspector **and one actual external client**; list and call a proxied tool. Exercise actual Bearer auth.
2. Run a model tool-call round trip using actual provider/plan/quota and a minimal tool schema, or change provider before building chat.
3. Confirm the chosen Woo REST authentication approach against actual internal WordPress URL after store is up (by Day 2/3).
4. `helm template` locally and for VPS with namespaces and image/secret references; inspect generated Service, Ingress, NetworkPolicies.

## 2. Proposed monorepo layout

```text
k8s-mcp-gateway/
├── README.md
├── ROADMAP.md
├── AGENTS.md
├── Makefile
├── .gitignore                  # .DS_Store, .env*, secrets files (not example templates)
├── docs/
│   ├── HLD.md
│   ├── LLD.md
│   ├── THREAT_MODEL.md
│   ├── DEMO.md
│   └── images/kubernetes-architecture.png
├── services/
│   ├── gateway/
│   │   ├── app/
│   │   │   ├── main.py           # FastAPI + MCP ASGI mount + lifespan
│   │   │   ├── settings.py       # validated env and Secret paths
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── security/
│   │   │   │   ├── web_sessions.py
│   │   │   │   ├── api_keys.py
│   │   │   │   ├── upstream_crypto.py
│   │   │   │   ├── internal_tokens.py
│   │   │   │   ├── permissions.py
│   │   │   │   └── url_policy.py
│   │   │   ├── mcp_gateway/
│   │   │   │   ├── endpoint.py    # SDK v2 low-level Server handlers
│   │   │   │   ├── adapter.py     # MCP client to upstream
│   │   │   │   ├── catalog.py     # tool discovery/cache/status
│   │   │   │   ├── aliases.py
│   │   │   │   ├── router.py
│   │   │   │   └── auditing.py
│   │   │   ├── chat/
│   │   │   │   ├── agent.py       # LLM tool loop; self-MCP client
│   │   │   │   ├── provider.py
│   │   │   │   └── stream.py      # browser SSE events
│   │   │   └── api/              # auth, me, members, invites, keys,
│   │   │                         # servers, tools, audit, chat
│   │   ├── alembic/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   ├── woo-mcp/
│   │   ├── app.py               # SDK v2 MCPServer + health routes
│   │   ├── wc_client.py         # REST, OAuth1, retry policy
│   │   ├── models.py
│   │   ├── tests/
│   │   └── Dockerfile
│   └── aux-mcp/
│       ├── currency/           # separate MCP process + Deployment
│       └── policy/             # separate MCP process + Deployment
├── web/dashboard/
│   ├── src/pages/             # Login, Servers, Team, Keys, Audit, Chat
│   ├── src/components/
│   ├── src/lib/api.ts
│   └── Dockerfile
├── charts/
│   ├── platform/              # umbrella release; dependencies file://../...
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-local.yaml
│   │   └── values-vps.yaml
│   ├── store/                 # WordPress + MariaDB + PVCs
│   ├── woo-mcp/
│   ├── aux-mcp/               # two Deployments/Services
│   ├── gateway/
│   ├── platform-db/          # PostgreSQL StatefulSet
│   └── dashboard/
├── infra/namespaces.yaml
├── scripts/                   # local/VPS setup, bootstrap, reset, smoke
└── tests/integration/         # two mock MCP servers + E2E smoke
```

Names are recommendations; module responsibilities and externally visible contracts are what must be stable. Do not create unused code/files just to match a tree.

## 3. PostgreSQL schema

Use UUID primary keys, UTC `timestamptz`, migrations, foreign keys, unique constraints and indices. Do not create a second DB for audit or a separate message broker.

| Table | Key columns | Constraints / purpose |
|---|---|---|
| `users` | `id`, `email`, `password_hash`, `role`, `active`, `created_at`, `updated_at` | email unique case-insensitively; role `admin|member`; Argon2 password hash |
| `web_sessions` | `id`, `user_id`, `session_digest`, `expires_at`, `revoked_at`, `created_at` | opaque cookie; persist digest only; index expiry |
| `invites` | `id`, `email`, `role`, `token_digest`, `expires_at`, `accepted_at`, `created_by` | single-use, expiring invite links; no external mail service mandatory |
| `api_keys` | `id`, `user_id`, `prefix`, `key_digest`, `name`, `created_at`, `last_used_at`, `revoked_at` | hash/HMAC full random key; unique prefix; no plaintext key storage |
| `upstreams` | `id`, `slug`, `display_name`, `url`, `auth_type`, `auth_header`, `credential_ciphertext`, `enabled`, `status`, `connect_timeout_ms`, `call_timeout_ms`, `last_checked_at`, `last_error`, `created_at`, `updated_at` | slug unique/immutable; URLs and secret changes admin-only; no secrets in REST responses |
| `upstream_tools` | `id`, `upstream_id`, `original_name`, `public_alias`, `description`, `input_schema`, `output_schema NULL`, `annotations`, `definition_hash`, `discovered_at` | `(upstream_id, original_name)` unique; `public_alias` unique; schema stored as JSONB |
| `audit_events` | `id`, `request_id`, `user_id NULL`, `api_key_id NULL`, `channel`, `server_slug`, `public_tool`, `original_tool`, `started_at`, `duration_ms`, `outcome`, `error_summary` | index `(user_id,started_at)`, `(server_slug,started_at)`; no raw arguments/customer PII/tokens |
| `conversations` | `id`, `user_id`, `title`, `created_at`, `updated_at` | owner can access only own conversations |
| `messages` | `id`, `conversation_id`, `role`, `text`, `tool_calls_json`, `created_at` | cap/redact stored tool previews; separate from audit |
| `tool_permissions` **(stand-out)** | `id`, `role`, `upstream_id`, `original_tool`, `allowed` | optional explicit overrides; default policy documented and unit-tested |

`status` is one of `connected|unreachable|disabled|checking`; `enabled` is authoritative user configuration, `status` is observational. Reject unknown enum strings at API boundaries. An optional append-only `security_events` table may record malformed/invalid-key requests that cannot be attributed to a valid user; it is not a substitute for required authenticated tool-call auditing.

### Schema migration ordering

`users → sessions/invites/keys → upstreams/tools → audits → conversations/messages → permissions`. Run migrations **once** using a Kubernetes Job (Helm pre-upgrade hook or explicit migration command), not in each FastAPI replica's startup. Migration rollout must tolerate an old API briefly coexisting with a new schema; keep database backup/rollback plan.

## 4. Identity, credentials and authorization

### Web sessions and invite flow

- Bootstrap one admin from **pre-created Secret** on first install; do not reseed/overwrite later logins.
- Admin can generate a member invitation for an email; UI displays a **copyable expiring invite URL** (sending real email is an optional enhancement). Recipient accepts it once, sets password, then authenticates.
- Password hashing: Argon2id, sensible password policy and login throttling. Browser receives opaque session cookie `HttpOnly`, `SameSite=Lax` or `Strict`; `Secure` in VPS HTTPS. Store only session-token digest; logout revokes it. Add CSRF defense on mutating cookie-authenticated requests (Origin/CSRF token), not just SameSite alone.
- `GET /api/me` supplies role/identity but never exposes password/session internals. Members see only their own keys and audits; admins manage team/server registry.

### External MCP API keys

- Format `mcpgw_<publicprefix>_<randomsecret>`; use `secrets.token_urlsafe`/CSPRNG at >=256-bit secret entropy; show plaintext key **only once**.
- Store `HMAC-SHA256(key_pepper, full_key)` or equivalent keyed digest and index by public prefix. Keep pepper in a Kubernetes Secret. Constant-time digest comparison.
- Check **for every `/mcp` request**, including repeated requests from an established external client: key digest, revoked timestamp, user active state, actor role/tool policy. Revoked key gets HTTP 401 immediately; no stale authentication cache. If the digest identifies a revoked key, also log a **denied security/audit event attributed to that user** (when safely possible), without invoking any tool. A completely unknown key may be logged as an anonymous security event.
- Admin can issue/revoke for other users **without displaying other users' plaintext keys** after issuance. Members issue/revoke own keys. UI displays key prefix and timestamps only after first reveal.

### Chat-specific gateway identity

- `/api/chat` validates web session, mints signed JWT (`sub` user ID, `aud` gateway-MCP, `iss` platform-chat, `iat/exp`, 2–5-minute TTL, optional `channel=chat`). Gateway auth adapter validates this internal token independently from opaque API keys.
- The chat backend uses the gateway's **internal ClusterIP `/mcp`** service, not direct DB/router or any upstream URL. It invokes `tools/list` then `tools/call` exactly as an external client would.
- Protect signing keys in Secrets; do not accept arbitrary browser-supplied JWTs as gateway internal identity. Prefer token audience/issuer/channel checks and short TTL.
- Both API-key and chat identity resolve to a common immutable `Actor(id, role, channel, key_id?)` object passed through request-scoped context. Never keep current actor in a process-global mutable variable.

### Credential separation

- API-key/JWT belonging to User A or User B terminates at gateway; not forwarded as a request header upstream.
- Gateway's upstream registry contains an encrypted **server-specific bearer or custom-header credential**, decrypted only at call time and used only for the corresponding upstream. Only `has_credential: boolean` is visible to browser/admin.
- Woo MCP *separately* has its WooCommerce REST consumer key/secret as Kubernetes Secrets, and its own gateway-facing bearer token. Users never receive either.
- Encryption: use tested Fernet/AES-GCM with master key in K8s Secret and documented rotation; avoid rolling new random keys every Helm upgrade, which would make credentials undecryptable.

### Authorization matrix

| Action | Admin | Member |
|---|---:|---:|
| View server status and catalog | Yes | Yes, filtered by allowed tools |
| Register/edit/disable/remove upstream | Yes | No |
| Invite/deactivate users and manage others' keys | Yes | No |
| Create/revoke own API keys | Yes | Yes |
| View all audit rows | Yes | No |
| View own audit rows | Yes | Yes |
| Invoke currently allowed tools | Yes | Yes |
| Invoke restricted write tools (stand-out) | Yes | Only if explicitly permitted |

For the mandatory demo, designate **User A as admin** (authorized to create products) and **User B as member**. If tool-level permissions are implemented, remember `create_product` must still work for User A through chat; permissions must be enforced on both `tools/list` **and** `tools/call`.

## 5. REST API contract

All `/api` responses use stable typed DTOs, pagination where lists grow, predictable 400/401/403/404/409/502 responses and redacted errors.

| Route | Authorization | Contract |
|---|---|---|
| `POST /api/auth/login`, `/logout` | Public / session | Create/revoke opaque web session cookie |
| `GET /api/me` | Session | Actor and role |
| `POST /api/invites` | Admin | Single-use expiring invite URL |
| `POST /api/invites/accept` | Invite token | Create member and consume invite |
| `GET /api/members`, `PATCH /api/members/{id}` | Admin | View/change role/active (protect final admin) |
| `POST /api/members/{id}/keys`, `DELETE /api/members/{id}/keys/{key_id}` | Admin | Issue/revoke a member key; one-time reveal on issuance |
| `GET /api/keys`, `POST /api/keys`, `DELETE /api/keys/{key_id}` | Session / self | Own API keys, generation, revocation |
| `GET /api/servers` | Session | List status, error summary, tool counts, no secret |
| `POST /api/servers` | Admin | Register server with URL, slug, optional header/bearer; immediate bounded probe |
| `PATCH /api/servers/{id}` | Admin | Edit URL/credential/enabled/name; slug immutable |
| `DELETE /api/servers/{id}` | Admin | Remove server and catalog; old aliases immediately rejected |
| `GET /api/servers/{id}/tools` | Session | Cached, authorized tool definitions |
| `GET /api/audit` | Session | Role-scoped, paginated, filterable events |
| `GET /api/conversations`, `GET /api/conversations/{id}` | Session / owner | Own conversation history |
| `POST /api/chat` | Session | SSE events with chat and tool execution |
| `GET /healthz`, `/readyz` | Kubelet | Liveness / DB readiness; no need for upstreams to be healthy |
| `GET /metrics` (optional) | Cluster-internal | Prometheus-compatible counters/histograms |

Example server response has `id`, `slug`, `display_name`, `enabled`, `status`, `tool_count`, `last_checked_at`, `last_error`, `has_credential`; **never** `credential_ciphertext` or an upstream Authorization header.

## 6. Dynamic MCP gateway: protocol and contracts

### v2 SDK composition

- Fixed Woo/currency/policy servers: SDK v2 `MCPServer` with typed `@mcp.tool()` functions, Streamable HTTP ASGI and no public Ingress.
- Gateway: low-level SDK v2 `Server(name=..., on_list_tools=..., on_call_tool=...)`, mounted with its supported Streamable HTTP ASGI helper and properly entered lifespan/session manager. **Check exact code against the pinned version**. The modern protocol is request-stateless; the v2 SDK can also accept supported legacy clients.
- Handler signatures follow the v2 guide: list receives `(ctx, params)` and returns `ListToolsResult`; call receives `(ctx, params)` and returns `CallToolResult`. The low-level gateway explicitly validates provided arguments with JSON Schema; decorator conveniences from v1 **do not apply**. Map MCP metadata, name and schemas into typed SDK objects; do not manually improvise JSON-RPC envelopes unless testing protocol conformance.
- Bearer authentication is applied to every downstream MCP HTTP request. Middleware must avoid accidentally capturing a user's identity in a long-lived connection-wide/global field. Verify tool listing and calls for two simultaneous identities.

### Catalog and registration state machine

**Registration**: `created/checking → connected` (valid Streamable HTTP + tool catalog), otherwise `unreachable` with bounded sanitized error. Re-probe on edit or re-enable; preserve previous cached catalog on transient failure when enabled. Disabled status is admin-controlled, with no background probe.

**Refresh**: single-gateway background loop (e.g. 15s–30s during demo; configurable longer production interval). For each enabled server, use independent timeout and semaphore. Get all pages of `tools/list` where supported. In one DB transaction, atomically replace its validated tool rows, store tool-definition hash/fingerprint, new status and checked time; do not expose a partial catalog. Ensure a stale refresh cannot overwrite a freshly disabled/deleted server via version/updated_at check.

**Scaling later**: to run two replicas without duplicate refreshes, move polling to a dedicated worker or use PostgreSQL advisory lock. No in-memory authoritative registry, per-session routing, or sticky-session requirement.

### Name collision and aliasing

- Upstream `slug` is unique, immutable and regex-constrained, e.g. `[a-z][a-z0-9-]{0,30}`.
- Publish `public_alias = slug + "__" + original_tool_name`, e.g. `woo__list_orders`. Store the **exact alias → upstream_id, original_name** relationship. Do not rely solely on splitting on `__` (an upstream name could itself contain that delimiter).
- If two servers export `list_orders`, aliases remain distinct: `woo__list_orders` and `warehouse__list_orders`.
- Validate allowed characters, length and valid JSON Schema at registration. For oversized/unrepresentable tool names, either reject with a clear validation error or apply documented deterministic shortening plus hash; never publish a malformed name silently.
- Return aliased descriptions that identify the upstream and purpose. Tool descriptions, even admin-provided ones, are **untrusted model input**.

### Tool listing policy

- `tools/list` queries **Postgres cache only** and filters by `upstreams.enabled=true`, actor permissions, and valid tool definitions. It makes **zero remote MCP calls**.
- An **unreachable but enabled** upstream retains its last-known discoverable tools; dashboard marks `Unreachable`, and attempted calls return a bounded, truthful error. A newly registered unreachable server with no prior catalog contributes no tools.
- A **disabled or deleted** upstream vanishes on the next fresh `tools/list`. An external client's previously cached alias must be rejected on `tools/call`. Refresh/reconnect external clients to demonstrate disappearance in their UI (the client may cache tool lists).
- Paginate `tools/list` if the SDK/transport requires it; no need for advanced search-tool indirection with only three upstreams.

### Tool invocation pipeline

1. Parse inbound MCP request and authenticate actor **on that request**; attach `request_id` and `channel=mcp|chat`.
2. Look up exact `public_alias`; require upstream enabled, user active, role/tool permission valid. Unknown, disabled and forbidden aliases must be rejected even if cached by the caller.
3. Validate `arguments` with `Draft202012Validator` (or compatible JSON Schema semantics). Return an appropriate protocol validation error rather than dispatching malformed input.
4. Start timer; retrieve the specific upstream's secret; open SDK v2 MCP client using configured auth headers and connect/read timeout. Cap concurrency per upstream. Do **not** forward the client's `Authorization` or session headers.
5. Invoke the upstream's **original** tool name. Wrap results into SDK v2 `CallToolResult`; bound text size and redact obvious secrets/customer PII. For upstream tool failures set `is_error=True` and a concise message. Preserve protocol error vs tool error distinctions; handle timeout/unreachable without leaking stack traces.
6. Write an audit row in a `finally`-style guaranteed path with actor, original/public name, server, timestamp, latency, outcome and request ID, including failed/denied invocations. Authentication denials before dispatch must be captured separately, as explained in API-key handling. Logging failure must be visible operationally and should not silently cause duplicate tool execution.
7. Do not automatically retry writes (`create_product`, `update_order_status`); uncertain timeouts must be surfaced as uncertain outcomes. Optional retries for safely idempotent read tools only.

**Initial timeouts:** connect ~3 seconds, tool execution ~20 seconds configurable per upstream; health probe shorter. Treat values as adjustable after measured local performance, not immutable protocol requirements.

## 7. Custom WooCommerce MCP server

### Tool contract

| Tool | Parameters | WooCommerce REST v3 | Essential checks |
|---|---|---|---|
| `list_products` | `search?`, `page=1`, `per_page=20` | `GET /wp-json/wc/v3/products` | max page size; cap returned fields |
| `create_product` | `name`, `regular_price`, `description?`, `status='publish'` | `POST /wp-json/wc/v3/products` | non-empty name; decimal string price; explicit write; no auto retry |
| `list_orders` | `status?`, `after?`, `before?`, `date='today'?`, `page`, `per_page` | `GET /wp-json/wc/v3/orders` | timezone-aware boundaries; safe PII projection |
| `get_order` | `order_id` | `GET /wp-json/wc/v3/orders/{id}` | positive integer, sanitized details |
| `update_order_status` | `order_id`, `status` allowed enum | `PUT /wp-json/wc/v3/orders/{id}` | valid WooCommerce states and permission; no auto retry |

- MCP tool definitions generated by the SDK from type-hinted functions; add read-only/destructive annotations as **hints**, not a security boundary. Permission checks belong in gateway code.
- Woo API client obtains REST consumer key/secret from Woo-specific Kubernetes Secret. On the **plain internal HTTP** WordPress service use OAuth 1.0a one-legged signing with tested library; or use **verified HTTPS** route with Basic Auth if deliberately provisioned. Follow WooCommerce official authentication rules; test GET and POST early.
- Gateway-facing Woo MCP requires a distinct bearer credential kept server-side, plus NetworkPolicy only allowing the gateway to connect. Don't expose Woo MCP via Ingress.
- `/healthz` only checks process health; `/readyz` tests readiness without turning transient WooCommerce availability into a crash loop. Use startup probe while store is being initialized.
- WooCommerce products/orders remain authoritative in MariaDB; gateway caches only tool definitions, **not order content**. Order timestamps use WooCommerce/store timezone (e.g. Asia/Kolkata) and a correct date-range query for “today”. Sanitize customer billing/shipping PII before sending to LLM when not necessary.

### WordPress/WooCommerce bootstrap

1. Deploy MariaDB StatefulSet + PVC; deploy WordPress Deployment + **separate** WordPress content PVC. Use one WP replica, appropriate Recreate rollout with RWO local-path storage.
2. Apply WordPress core installation, WooCommerce plugin install/activation, permalinks, COD, basic currency/timezone and example **virtual product**. Prefer idempotent WP-CLI Job/scripts; verify WordPress image has populated persistent content before invoking WP-CLI. Kubernetes Job sharing the WP PVC requires correct file permissions and same-node placement when using RWO storage. Do not assume a job can safely share a PVC across nodes.
3. Issue a Woo REST **read/write** key through supported WooCommerce Admin UI (`WooCommerce → Settings → Advanced → REST API → Add key`) or explicitly verified supported app authorization flow. Save into a Kubernetes Secret via secure setup command; show the manual key step in README if not automated. **Never create keys by writing directly to private `wp_woocommerce_api_keys` tables.**
4. Seed a product if not present, place order via COD test checkout, confirm wp-admin order and persistence across Pod recreation; then validate Woo MCP's full five-tool contract.
5. Set WordPress site/home URL per environment (`WP_HOME`, `WP_SITEURL` configuration); note that WooCommerce may also persist absolute links/settings requiring testing when moving between URLs. Prefer fresh environment installs, not reusing the same database between local and VPS.

## 8. Auxiliary MCP servers

**`currency-mcp`** is a separate MCP server providing `convert_currency(amount, from_currency, to_currency)` and `get_demo_rates()`. Use explicitly labeled *fixed demonstration rates*, with exact Decimal handling, not claims about current FX rates. Include one deliberate original name collision such as `list_products` only if it improves the collision demo; functionality can be harmless illustrative data.

**`policy-mcp`** is another separate MCP server with `get_store_policy(topic)` and `list_store_policies()`, using a small versioned example JSON/markdown config. It must **not** call the WooCommerce API directly (only Woo MCP accesses that store) or another upstream server.

**Optional real external integration:** add a fourth remote HTTPS MCP using the same admin registration contract and a separate scoped bearer/header credential. Prefer read-only, least-privilege account. Its availability must never block the mandatory local three-server demo.

**Two-upstream prompt:** "List today's orders from WooCommerce, sum their order totals, and convert the amount from INR to EUR using our labeled demonstration FX rates." Tool history must show invocations against both Woo and currency upstreams. The currency result is a demo conversion, not a claim of live FX accuracy.

## 9. Chat agent and dashboard

### Chat loop (backend)

1. Authenticate user's browser session. Load authorized conversation; mint short-lived internal user JWT.
2. Connect MCP v2 client to **gateway's own internal `/mcp`** endpoint, retrieve `tools/list` for actor.
3. Translate tool definitions/input schemas into the chosen LLM provider's tool-call schema. Add current store timezone/date. Limit total description size, tool count, turns and tool-result tokens.
4. Submit user prompt and available tools to model. For each returned tool call: show tool event to UI, validate/parse tool name and arguments, invoke via MCP `tools/call` (not direct SDK or Woo REST), show tool result/error event, append result to model history.
5. Repeat until text answer or maximum 6–8 LLM rounds / bounded total time reached. Never claim a write succeeded unless a real tool result confirms it. Persist conversation text/tool metadata without raw secret-bearing payloads.
6. Return final answer to UI; audit belongs to gateway MCP call path, not a separate chat-only logger.

**SSE browser event types (suggested)**: `text_delta`, `tool_call`, `tool_result`, `error`, `done`; each includes a stable `conversation_id`, tool `call_id` where applicable, and redacted structured preview. SSE here is a frontend feature; it is distinct from MCP Streamable HTTP streaming semantics.

### Minimum dashboard screens

| Screen | Must support |
|---|---|
| Login / Accept Invite | Log in, accept time-limited invite, logout |
| Servers | Show connected/unreachable/disabled with tools and last error; admin add URL/optional credential, edit, enable, disable, remove, and retry status refresh |
| Team | Admin invite via shareable link, list members, deactivate, issue and revoke keys |
| My Keys | Generate own key, show once, copy client connection instructions, revoke own key |
| Audit | Search/filter user/server/tool/time/outcome; admin all/member only own |
| Chat | Ask, tool cards showing name/duration/outcome, final answers, errors; basic conversation persistence |

Styling can be modest; correct account boundaries, visible tool traces and clear error states are not optional. Raw upstream credentials must not appear in any browser-facing API or page.

## 10. Helm / Kubernetes implementation details

### Chart structure and release mechanics

- `charts/platform` umbrella dependencies: `store`, `woo-mcp`, `aux-mcp`, `gateway`, `platform-db`, `dashboard`; use `helm dependency update`, `helm lint`, `helm template` in CI.
- One Helm release installed **in** `platform` namespace; subcharts can render objects with explicit `metadata.namespace: store|mcp|platform`. The three namespaces are created **first** via `infra/namespaces.yaml` (names have stable labels such as `kubernetes.io/metadata.name`). Do not assume `--create-namespace` creates all three. Test release lifecycle across namespaces, not just `helm template`.
- Cross-namespace service references use FQDNs such as `woocommerce-mcp.mcp.svc.cluster.local`, `wordpress.store.svc.cluster.local`, `postgres.platform.svc.cluster.local`.
- `values.yaml` defaults and `values-local.yaml` / `values-vps.yaml` overrides control DNS hosts, ingress TLS, image tags/registries, requests/limits, StorageClasses, PV sizes, logging, WC URL and existingSecret names. **Same chart templates** in local and VPS.
- Secrets are created separately via local/VPS setup and passed as **references** (`existingSecret`). No LLM key, API secret, password or encryption key stored in chart values rendered into Helm release history.

### Resource inventory

| Namespace | Resources | Exposure and persistence |
|---|---|---|
| `store` | WordPress Deployment/Service/PVC; MariaDB StatefulSet/Service/PVC; WordPress/MariaDB ConfigMaps/Secret refs; Ingress for shop | WordPress + DB volumes retained during ordinary Pod replacements |
| `mcp` | Woo MCP Deployment/Service; currency Deployment/Service; policy Deployment/Service; MCP NetworkPolicies, Secret refs | ClusterIP **only**, gateway-restricted ingress |
| `platform` | Gateway Deployment/Service; dashboard Deployment/Service; Postgres StatefulSet/Service/PVC; platform Ingress; migration Job; policies | Dashboard/API/MCP exposed via app host only; DB private |

Every workload: readiness and liveness checks, resource requests/limits; slow-starting WordPress/MariaDB startup probes; non-root where supported by image; `automountServiceAccountToken: false` for workloads that don't access the K8s API. Set Secret and PVC file permissions safely for actual upstream images. MariaDB/Postgres initial DB passwords are stable existing Secrets, never regenerated on reinstall/upgrade.

### NetworkPolicy rules (verify with actual traffic tests)

1. Default-deny ingress for **selected private** application Pods; allow gateway-labelled Pods **from namespace `platform`** to connect on each MCP server's port in `mcp`.
2. Allow Woo MCP to connect to WordPress Service port in `store`; allow Traefik namespace to connect to WordPress frontend/HTTP, dashboard and gateway; no public MCP-upstream Ingress.
3. WordPress can connect to MariaDB; gateway can connect to PostgreSQL. DBs deny other sources.
4. With egress restrictions, explicitly permit cluster DNS, service destinations, and gateway outbound HTTPS to LLM/external MCP endpoints. Kubernetes NetworkPolicy has no portable FQDN allowlist; avoid promising hostname-level egress blocking when not supported. Start with correct ingress isolation, then tighten egress and run negative tests.
5. An ordinary unauthorized debug Pod must fail to reach Woo MCP. Gateway must succeed. Denying a Pod by label is not a protection against a cluster administrator who can create arbitrary labelled Pods; Kubernetes API permissions form a separate control layer.

### Availability and readiness

- Gateway `/healthz` checks only process responsiveness. Gateway `/readyz` checks local service readiness (e.g. Postgres), **not all external MCP servers**; otherwise one bad upstream would remove every gateway instance from service endpoints.
- Each MCP upstream health status comes from gateway's timeout-bounded probe loop. A killed upstream may get recreated automatically by its Deployment before probe sees failure; for the **required outage demo**, scale that Deployment to 0 (or reliably prevent replacement) after showing the Pod kill, then restore replica count.
- WordPress and stateful databases have independent readiness criteria; an application temporarily waiting for DB must not be restarted forever by an over-aggressive liveness probe.

### Upgrade / rollback / data safety

- Image versions pinned; no `latest` in VPS. `helm upgrade --install --wait` then inspect rollouts. Save `helm history`; test `helm rollback` for a stateless component.
- Helm rollback doesn't undo database migrations or WooCommerce orders. Back up both MariaDB and PostgreSQL (ideally off the VPS), and WordPress uploaded files. Document `helm uninstall` and PVC retention semantics to avoid accidental data loss.
- No replica 2 until a multi-replica smoke test proves request-scoped actor identity and single-ownership catalog polling (Postgres advisory lock or dedicated poll worker); otherwise a duplicate background loop may race.

## 11. Tests and acceptance matrix

Each acceptance item is a **real executable test**, not a screenshot of source code.

| ID | Requirement | Test evidence |
|---|---|---|
| A01 | Checkout/store is real | Open shop, add product, COD checkout, order appears in wp-admin |
| A02 | Persistence | Delete/recreate WordPress and MariaDB Pods, product/order remain |
| A03 | Custom Woo MCP | Inspector calls all **five** required tools, including write tools |
| A04 | At least three independent MCP upstreams | Approved baseline: three in-cluster servers (Woo/currency/policy), each backed by its own Pod/service and visible through `tools/list`; a fourth remote server remains optional |
| A05 | Dynamic registration | Admin adds policy (or a fourth server) through dashboard; tools appear without redeploy |
| A06 | Admin registry operations | Edit credential/URL, enable, disable, delete; correct status and catalog updates |
| A07 | Collision-safe aliases | Two upstreams with original name `list_products` map to distinct callable aliases |
| A08 | Team/user roles | Admin invites B; B signs in; member denied management APIs; own API key issued |
| A09 | External MCP interoperability | Real Inspector/Cursor/Claude Code connects with only app URL and B key; tools/list and call work |
| A10 | Chat tool execution | A asks to create product (name/price) and observes storefront side effect |
| A11 | Chat orders | After manual purchase, A asks for today's orders, correct order returned |
| A12 | Two-upstream prompt | B's external client asks orders + fixed FX conversion; logs show calls to two distinct servers |
| A13 | Key revocation | Revoke B key; next MCP request HTTP 401, A remains operational |
| A14 | Disable upstream | Aliases absent on new discovery and stale direct alias invocation denied |
| A15 | Dead upstream isolation | Scale utility Deployment to 0; status Unreachable; Woo/policy still work and tool listing fast |
| A16 | Audit | Each A/B authenticated tool attempt records correct actor, tool, server, start time, duration and outcome |
| A17 | Private upstream/network policy | Debug Pod from other namespace denied; gateway success; no public upstream host |
| A18 | Kubernetes mandatory | Probes and requests/limits on all, Secrets not hardcoded, PVCs, stable store/app Ingress |
| A19 | Helm portability | Same umbrella templates render for local and VPS values; clean k3d install; verified VPS install or documented k3s deployability |
| A20 | Required deliverables | Demo video, GitHub repo, README setup, system-design/tradeoffs and threat-model docs |

**Unit tests:** user/key hashing/revocation; collision and exact alias mapping; schema validation; admin/member guards; tool permission list+call enforcement; date boundaries; URL/redirect validation; crypto encryption/decryption; health state transitions; status/disable concurrency.

**Integration tests:** two lightweight mock Streamable HTTP upstreams (normal and slow/dead) + gateway; API-key middleware authentication; tool listing under outage; error shape; audit written on failure; stale-tool invocation rejected; internal chat JWT identity; Woo REST mocked separately from real-cluster smoke.

## 12. Handoffs, practical constraints and deferred extras

- API/backend and Kubernetes/Helm can proceed in parallel **only once interfaces, ports, Secret names and SDK version are frozen in a small contract**. Dashboard can mock responses using the contract, then switch to the real backend.
- Preserve live README and a short decisions log. Every milestone ends with commands/tests that another developer can run from clean clone.
- **No mandatory features are deferred.** Only actual two-replica gateway demonstration, read/write tool ACL, richer metrics, TLS/VPS proof and fourth external MCP are stretch/stand-out tiers after the acceptance baseline passes (tool ACL + VPS deployment are first stand-outs).
- Explicitly **deferred**: multi-store provisioner, OAuth for external MCP clients, Kubernetes Operators/CRDs, hosted container-based MCP deployer, fine-tuning/model hosting, service mesh and a full Prometheus/Grafana stack.

## 13. Primary references

- User-provided Urumi AI FDE assignment (8 pages, authoritative).
- User-provided original `ROADMAP.md` (considered, superseded where differing).
- https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md
- https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/advanced/low-level-server.md
- https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/client/index.md
- https://developer.woocommerce.com/docs/apis/rest-api/authentication
- https://docs.k3s.io/networking/networking-services
