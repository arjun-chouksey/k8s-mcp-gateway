# Acceptance Test and Demo Script

**Purpose:** Prove every original Urumi mandatory scenario with observable output. This is a plan, **not a record of tests already run**. Update checkboxes and capture evidence only after the commands genuinely succeed.

## 1. Preconditions

- [ ] Helm release installed in k3d; `kubectl get pods -A` shows workloads ready; three namespaces exist.
- [ ] Traefik resolves `shop` and `app` local hostnames; dashboard/API and `/mcp` reachable.
- [ ] Store has COD enabled, at least one priced purchasable test item and Woo admin account.
- [ ] Gateway admin **User A**, invite-accepted member **User B**, each with own gateway credentials.
- [ ] Three upstreams registered: WooCommerce MCP, currency MCP, policy MCP; status **Connected**; tool catalogs visible.
- [ ] No real customer PII, production API keys, or private passwords appear in demo video or terminal history.

## 2. Run the mandatory two-user scenario

**Step 1 — Storefront and persistence**
1. Open `shop.<domain>`, add a product to cart, check out with COD/dummy method.
2. Log into wp-admin, show the same order ID.
3. Demonstrate DB/WordPress PVCs and explain why orders survive Pod replacement. Optionally delete/recreate an app Pod and confirm the order remains (never delete a PVC for this test).
4. Evidence: visible storefront/order, `kubectl get pvc -n store`.

**Step 2 — User A, dashboard chat**
1. Log in as **User A (admin)** at `app.<domain>`.
2. Ask: `Create a product named Urumi Mug with price 499`.
3. Show chat tool-call card (aliased `woo__create_product`) and successful result containing created product ID.
4. Refresh store catalog; product exists at the requested price.
5. Manually place a COD order for the new product.
6. Ask chat: `What orders came in today?` and verify it identifies the actual order ID.
7. Evidence: chat trace, product, order, audit with `user=A`, `channel=chat`.

**Step 3 — User B, external MCP client**
1. Admin invites User B; B accepts the invite and generates their personal API key in the dashboard.
2. Configure **only** the one gateway URL (`https://app.<domain>/mcp`) and B's bearer token in MCP Inspector / Claude Code / Cursor (use a test key for video; never show full secret).
3. List tools. Show separate `woo__*`, `currency__*`, `policy__*` groups.
4. Ask `What orders came in today?` and show result.
5. Ask `List today's order totals and convert the sum from INR to EUR using the demo currency rates.` Show tool invocations against Woo **and** Currency upstreams. State that rates are fixed demonstration values, not live FX.
6. Evidence: actual external client's tool list and call results, audits with `user=B`, `channel=mcp`.

**Step 4 — API key revocation**
1. Admin revokes B's key (or B revokes own key in dashboard).
2. Attempt **another MCP request** using same key. It must return unauthorized (HTTP 401 or client equivalent). No previous authentication cache may allow it.
3. Issue a new B key if needed for subsequent tests; do not mistake reconnected client with a different key for proof of revocation.
4. Evidence: audit/security event for rejected attempt where feasible; A still works.

**Step 5 — Disable and collision**
1. Show two upstream tools that originally have the **same** name, if collision fixture enabled; aliases are distinct and independently callable.
2. Disable `currency` (or `policy`) in admin UI; request fresh `tools/list` from gateway. Its aliases are absent.
3. Manually invoke an old cached alias; the gateway rejects it even if the client remembers it.
4. Re-enable server, refresh and verify tools return. No gateway redeploy.
5. Evidence: server status, list before/after, denied invocation/audit.

**Step 6 — Dead upstream/failure isolation**
1. Delete an upstream Pod and explain the Deployment's auto-replacement. To make an outage persist long enough, **scale the upstream Deployment to zero** (Helm may later reconcile during upgrade).
2. Wait for the gateway health interval. Dashboard shows **Unreachable** and a bounded reason. Other upstream server tools remain usable; `tools/list` remains responsive.
3. Restore the Deployment's replica count and show status recovery. Record one failed tool result/audit if appropriate.
4. Evidence: `kubectl get pods -n mcp`, status panel, successful unrelated tool call, failure audit.

**Step 7 — Kubernetes, Helm, Secrets and protection**
1. Show `kubectl get deploy,statefulset,svc,ingress,pvc,networkpolicy -A` and `kubectl get pods -A`.
2. Explain three namespaces; why upstream servers have ClusterIP only; why only gateway may call them.
3. From a **non-gateway debug Pod**, attempt to reach Woo MCP: expect deny. From gateway Pod/client, expect success. Demonstrate policy works in actual cluster.
4. Explain Secrets **by name only**; do not print values. Explain where WooCommerce credentials live and why downstream client key is never forwarded upstream.
5. Show resource requests/limits, probes and storage. Show `helm template` with local and VPS values, release upgrades/history/rollback strategy, and domain/TLS/storage/secret differences. Actual VPS demo if completed.
6. Evidence: Helm output, cluster resources, denied network test, no credential exposure.

**Step 8 — Audit and closing**
1. Show audit rows: User A create product and read orders, User B read orders and call second server; success/error, server, tool, timestamp and duration.
2. Point to repo README, HLD, LLD, threat model and both Helm values files.
3. Explain biggest tradeoffs honestly: stateless gateway, cached discovery, last-known tools during outage, one-node VPS limitations, tool-write retries, absence of multi-store bonus if omitted.

## 3. Suggested demo flow / time budget

| Portion | Indicative duration |
|---|---:|
| Architecture + public/private boundaries | 1–2 min |
| Storefront + Woo agent test | 2–3 min |
| External MCP + two upstreams | 2–3 min |
| Revocation/disable/outage/audit | 2–3 min |
| Kubernetes/Helm/security/deployability | 2–3 min |

Prefer a cohesive live recording over long theoretical commentary. Video duration is not mandated by the PDF; prioritize completeness and legibility.

## 4. Mandatory deliverables

- [ ] GitHub source repository (frontend, backend, chat, all MCP servers, charts, scripts).
- [ ] README with local/VPS install steps and end-user instructions.
- [ ] `docs/HLD.md` / design tradeoffs and `docs/THREAT_MODEL.md`.
- [ ] Demo video link, accessible to evaluators.
- [ ] Submitted official application form; confirm URLs and recording permissions.
- [ ] Clearly list optional standout features actually finished, not planned ones.

**Official assignment submission link:** https://forms.gle/nftwgyNeenSDmiRb6
