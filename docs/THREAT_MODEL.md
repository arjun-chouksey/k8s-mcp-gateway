# Threat Model: Team MCP Gateway

**Version:** 1.0, 2026-10-12  
**Scope:** One team with admin/member roles, one WooCommerce store, a dynamic MCP gateway and three or more upstreams running on Kubernetes. Security must support the Urumi mandatory functionality; this is a concrete first-pass threat model, not a formal penetration-test report.

## 1. Assets and trust boundaries

**Assets:** Gateway per-user API keys, dashboard sessions, upstream bearer/header credentials, WooCommerce REST consumer key and secret, WordPress administrator credentials, database passwords, LLM API key, encryption/signing/pepper keys, customer/order data, product-write capability, registry/tool definitions, audit log integrity, Kubernetes API permissions and persistent volumes.

**Boundaries:**
1. Internet/user/browser → Traefik → dashboard `/api` and gateway `/mcp` (external input always untrusted).
2. Gateway → upstream MCP servers (trusted transport only after registry validation and authentication; returned content and tool descriptions remain untrusted).
3. Woo MCP → WooCommerce REST (separate WooCommerce read/write key; no end-user credentials passed through).
4. Gateway → external LLM (may disclose tool data; minimize order/customer fields).
5. Pods → databases/Secrets/cluster network (Kubernetes RBAC, ServiceAccounts, NetworkPolicies; root-level access to cluster remains in trusted admin boundary).

## 2. Primary threats and concrete defenses

| Threat | Attack path / failure mode | Required defense | How to test |
|---|---|---|---|
| API key theft/replay | User B key obtained or accidentally logged | 256-bit random secret, show once, keyed hash at rest, 401 on revocation, mask logs | Revoke B and immediately reuse old key; verify denied |
| Credential passthrough | Downstream Authorization header forwarded to malicious upstream | Gateway constructs new outbound headers using *only* per-upstream credentials | Mock upstream records inbound headers: no `mcpgw_` or chat JWT |
| Unauthorized admin actions | Member calls server registry or member-management API | Server-side RBAC for every route, never only UI gating | Member POST `/api/servers` returns 403 |
| Excess privilege through shared Woo key | Member can invoke `update_order_status` with no authorization | Stand-out tool ACL: tool filtered in `tools/list`, denied in `tools/call`; scoped Woo key | Member direct invocation denied; admin allowed |
| Cross-user key exposure | `GET /api/keys` or team page reveals another user's secret | Own-key scoping, hashes only; admin can generate but old plaintext never retrievable | Query IDs as second member; deny/mask |
| Compromised upstream MCP | Malicious tool descriptions prompt model to leak credentials | Treat descriptions/results as data, minimal model context, output caps, optional admin tool-definition reapproval | Inject instruction-like tool description; model should not receive credentials |
| SSRF during registration | Admin registers cloud metadata, loopback, cluster management endpoint, DNS-rebinding host | HTTPS for public hosts; explicit safe internal service allowlist; block metadata/link-local/unsafe IPs and redirects; revalidate resolved target; short timeouts | Reject `169.254.169.254`, localhost, non-HTTPS public endpoint, redirect to blocked IP |
| Internal network pivot | Other Pods call Woo MCP or MariaDB directly | Ingress NetworkPolicies, only gateway→MCP; Woo MCP→WordPress; WordPress→MariaDB; gateway→Postgres | Unauthorized debug Pod blocked; authorized Pod succeeds |
| Malicious upstream leaking data | Third-party MCP receives sensitive tool args/data | Distinct least-privilege upstream secrets; users must not pass customer PII to unrelated tools by default; redact outputs | Verify credential scopes and no broad header forwarding |
| Tool-name collision/hijack | Two servers both offer `list_products` | Immutable `slug`, exact `public_alias → upstream/tool` mapping, no ambiguous parsing | Register collision, invoke both aliases separately |
| Tool catalog rug pull | Tool description/schema changes after approval | Store definition hash; show updated tools and last refresh, optionally flag changes for admin approval | Change fake server schema; verify refresh diff visible |
| Tool call after disable | External client cached a tool before admin disabled it | **Recheck** server enabled and permission on each `tools/call` | Disable; invoke stale alias directly; reject |
| Denial of service from dead upstream | Tool listing or other server calls block on slow server | Cache listing; per-upstream timeout, semaphore and isolated errors | Scale down utility and call Woo/policy successfully |
| Duplicate mutations | Network timeout triggers retry after product was created | No automatic retry for writes; expose uncertainty; optional idempotency key if API supports it | Simulate timeout after upstream commit; no duplicate automatic retry |
| Stored XSS / malicious content | Tool description or product name displayed as HTML | React escapes text; don't render arbitrary HTML; sanitize markdown if used | Inject HTML in tool description; displayed as text |
| CSRF | Browser sends cookie on unwanted mutating request | CSRF token and/or strict Origin enforcement on `/api`, `SameSite` cookies | Submit cross-origin mutation; deny |
| Admin password brute force | Public login endpoint | Argon2 hash, throttling/rate limit, lockout policy as suitable | Repeated failed auth triggers configured limit |
| Audit tampering/PII | Audit loses identity, includes secrets, or can be edited by members | Append-only user attribution, no raw args/tokens, admin/all vs member/own permission | Inspect audit on allowed/denied/failed paths and role scoping |
| Secret exposure in repo/Helm | Values file or rendered manifest contains private keys | Existing Kubernetes Secrets created out of band, `.gitignore`, pre-commit secret scan, protect release metadata | Scan tracked files and rendered charts for token patterns |
| WordPress/plugin compromise | Vulnerable PHP/plugin modifies shop and steals data | Pin image/plugin version, use supported plugins, backups, limit admin surface, least-privilege key | Document update/backup and web exposure |
| Lost storage / rollback | PVC deletion, VPS disk failure, irreversible DB migration | Backup MariaDB/Postgres/uploads off-node; test restore; avoid destructive schema migrations | Delete Pod (not PVC) and verify data; rehearse backup/restore |

## 3. Credential flow: explicit do's and don'ts

```text
User A browser session ───> Gateway REST /api
                       \─> Chat backend ──(short-lived actor JWT)──> Gateway /mcp
User B personal key ──────────────────────────────────────> Gateway /mcp
                                                           │
                      gateway authentication + role/tool permission + audit
                                                           │
                           per-server stored credential, decrypted in gateway
                                                           ▼
                                                  Upstream Woo MCP
                                                           │
                                Woo REST key/secret from Woo MCP Kubernetes Secret
                                                           ▼
                                                WooCommerce REST API
```

**Never:** send a user's gateway API key to an upstream; include upstream credentials in `/api/servers`; log raw key/order payloads; put real passwords into Helm values; allow LLM-supplied text to choose arbitrary internal URLs; let browser bypass gateway and invoke upstream MCP directly.

## 4. Role and data isolation

- Admin: invites members, operates registry, issues/revokes team keys, views global audit; product/order writes as allowed by configured tool policy.
- Member: own API keys, tools that policy allows, own audit rows, own conversations; **cannot** administer servers/team or retrieve others' credentials/history.
- Required baseline allows authorized team members to use registered tools. **Tool-level restrictions are an explicit standout enhancement** and must not break User A's mandatory product-creation demo (designate User A admin).
- Upstream WooCommerce key has read/write privileges needed for five tools; that does **not** imply every gateway user can perform every write when optional tool ACLs are enabled.
- An MCP server may expose a malicious tool that echoes request data, so do not pass sensitive or unrelated secrets in arguments; minimize tool content sent to the LLM.

## 5. Kubernetes security limits

- Namespace separation is **organization/policy scope, not an independent hard security boundary**.
- NetworkPolicy controls network flows, not HTTP user identity or permitted MCP method. It must be supported by the cluster's actual networking implementation and verified with negative tests.
- The built-in k3s policy controller is a deployment assumption to check, not a substitute for tests. Traffic from authorized gateway Pods is still subject to gateway application auth/authorization.
- An attacker with broad Kubernetes RBAC allowing Pod creation/label manipulation may bypass simple label-based policies; restrict human/automation Kubernetes API access and use dedicated ServiceAccounts with token auto-mount disabled for ordinary services.
- Kubernetes Secrets are not synonymous with encryption at rest; restrict access and configure encryption/secret management if available on VPS.
- Public WordPress/wp-admin remains an Internet-facing service and must be patched and configured safely.

## 6. Operational controls and residual risks

**Minimum operations:** credential/key rotation procedure; image and dependency version pinning; container logs with redaction; backups and restore steps; release upgrade/rollback; resource limits; readiness/liveness; health-monitoring of each upstream; rate limiting if time permits.

**Residual risks to state during review:**
- Shared upstream credentials let authorized users exercise delegated permissions even when they never see plaintext; compromise of an upstream may disclose its own credential or data supplied to it.
- Gateway compromise exposes decrypted upstream credentials and possibly user data; encryption at rest helps with database-only compromise, not a compromised gateway process.
- One-node k3s is not high availability against VPS failure; network and disk outages affect the entire platform.
- A remote hosted MCP integration can change schemas or break availability; the mandatory local three-server demo must be independent of it.
- “Prompt injection resistant” is not a guarantee. System prompts alone are insufficient; constrain tool availability/arguments, sanitize outputs, use permissions, and prevent upstream tools from receiving bearer tokens meant for gateway.
- NetworkPolicy and URL checks cannot guarantee protection from a cluster administrator or every proxy/DNS trick. Document tested cases and remaining limits.

## 7. Threat-model demo questions

1. Can User B view the WooCommerce API secret? **No**; it's mounted into Woo MCP only; B's gateway key is separate and scoped to gateway.
2. If B obtains a tool name from before a server was disabled, does it still work? **No**; call-time policy and enabled-state check rejects it.
3. Why not pass B's API key to GitHub MCP? **Different token audience**; upstream must receive its own scoped credential, never B's gateway authentication token.
4. What happens if a malicious upstream describes a tool as “ignore previous instructions”? **Description is untrusted**; tool filtering and security constraints still apply; cannot grant new permissions or retrieve gateway-held secrets.
5. What can a member do to another member? **Only** the shared business effects of tools their role allows; they cannot manage each other's keys, chat histories, or audit rows.
6. If a Pod dies, does the order survive? **If underlying DB/PVC survives**, yes; disk corruption or VPS failure needs backups.

## 8. References

- Original Urumi assignment, threat model requirements on page 8 and controls throughout.
- `HLD.md` security boundaries and `LLD.md` concrete implementation controls.
- https://modelcontextprotocol.io/specification/
- https://developer.woocommerce.com/docs/apis/rest-api/authentication
- https://kubernetes.io/docs/concepts/services-networking/network-policies/
