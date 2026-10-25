# k8s-mcp-gateway

A Kubernetes-native WooCommerce store and team MCP gateway. One authenticated
Streamable HTTP endpoint aggregates a custom five-tool WooCommerce server and
independent currency and policy servers. The React dashboard provides team,
key, server, audit, and AI-chat workflows; both chat and external MCP clients
use the same gateway policy and audit path.

## Kubernetes architecture

The installation uses `store`, `mcp`, and `platform` namespaces. WordPress,
MariaDB, PostgreSQL, the dashboard, gateway, and all three MCP servers run in
Kubernetes. Only the shop and dashboard/gateway have Ingress routes; upstream
MCP services remain private ClusterIP services protected by NetworkPolicy.

![Kubernetes Architecture](docs/images/kubernetes-architecture.png)

## Prerequisites

- Docker, k3d, kubectl, and Helm 3 for local development.
- A Linux VPS with a public IPv4 address, at least 2 vCPU, 4 GiB RAM, and 30 GiB
  free disk for the documented single-node k3s deployment.
- Four application images built from this repository: `gateway`, `woo-mcp`,
  `aux-mcp`, and `dashboard`.
- A Groq API key for dashboard chat and a domain you control for VPS TLS.

All image tags in the VPS values are immutable release labels rather than
`latest`. Before a VPS install, publish the four `0.1.0` images to the configured
GHCR paths or replace only their repositories and tags in
`charts/platform/values-vps.yaml`.

## Local deployment

Create the pinned k3d cluster and namespaces:

```bash
k3d cluster create k8s-mcp-gateway \
  --image rancher/k3s:v1.35.5-k3s1 \
  --api-port 127.0.0.1:6550 \
  --port 127.0.0.1:8080:80@loadbalancer \
  --wait
kubectl config use-context k3d-k8s-mcp-gateway
kubectl apply -f infra/namespaces.yaml
```

Build the application images with the tags in `values.yaml` and import them:

```bash
docker build -f services/gateway/Dockerfile \
  -t k8s-mcp-gateway/gateway:0.1.0-local .
docker build -t k8s-mcp-gateway/woo-mcp:0.1.0-local services/woo-mcp
docker build -t k8s-mcp-gateway/aux-mcp:0.1.0-local services/aux-mcp
docker build -f web/dashboard/Dockerfile \
  -t k8s-mcp-gateway/dashboard:0.1.0-local .
k3d image import --cluster k8s-mcp-gateway \
  k8s-mcp-gateway/gateway:0.1.0-local \
  k8s-mcp-gateway/woo-mcp:0.1.0-local \
  k8s-mcp-gateway/aux-mcp:0.1.0-local \
  k8s-mcp-gateway/dashboard:0.1.0-local
```

Create the existing Secrets described below, including your local
`GROQ_API_KEY`, then install:

```bash
helm dependency update charts/platform
helm upgrade --install urumi charts/platform \
  --namespace platform \
  --values charts/platform/values-local.yaml \
  --wait --timeout 15m
```

Open `http://shop.127.0.0.1.nip.io:8080` and
`http://app.127.0.0.1.nip.io:8080`.

## Existing Secrets

The Helm chart renders references to pre-created Secrets and never renders
secret values. Create these resources before installation:

| Namespace | Secret | Required keys |
| --- | --- | --- |
| `store` | `store-mariadb` | `database`, `username`, `password`, `root-password` |
| `store` | `store-wordpress` | `database`, `username`, `password` |
| `store` | `store-wordpress-admin` | `username`, `password`, `email` |
| `mcp` | `woo-mcp` | `MCP_BEARER_TOKEN`, `WOOCOMMERCE_BASE_URL`, `WOOCOMMERCE_OAUTH_BASE_URL`, `WOOCOMMERCE_CONSUMER_KEY`, `WOOCOMMERCE_CONSUMER_SECRET` |
| `mcp` | `aux-mcp` | `CURRENCY_MCP_BEARER_TOKEN`, `POLICY_MCP_BEARER_TOKEN` |
| `platform` | `platform-postgres` | `database`, `username`, `password`, `database-url` |
| `platform` | `gateway` | `api-key-pepper`, `upstream-credential-key`, `internal-jwt-secret`, `groq-api-key` |
| `platform` | `gateway-bootstrap-admin` | `email`, `password` |
| `platform` | `gateway-upstreams` | `woo-credential` |

Use local files excluded by `.gitignore`, restrict them with `chmod 600`, and
apply them without putting values in shell history. For example:

```bash
kubectl -n platform create secret generic gateway \
  --from-env-file=.env.gateway-vps
```

Apply each Secret from a separate local file so key ownership remains clear:

```bash
kubectl -n store create secret generic store-mariadb --from-env-file=.env.store-mariadb
kubectl -n store create secret generic store-wordpress --from-env-file=.env.store-wordpress
kubectl -n store create secret generic store-wordpress-admin --from-env-file=.env.store-admin
kubectl -n mcp create secret generic woo-mcp --from-env-file=.env.woo-mcp
kubectl -n mcp create secret generic aux-mcp --from-env-file=.env.aux-mcp
kubectl -n platform create secret generic platform-postgres --from-env-file=.env.platform-postgres
kubectl -n platform create secret generic gateway --from-env-file=.env.gateway-vps
kubectl -n platform create secret generic gateway-bootstrap-admin --from-env-file=.env.gateway-admin
kubectl -n platform create secret generic gateway-upstreams --from-env-file=.env.gateway-upstreams
```

The MariaDB username/password/database must match the WordPress Secret. The
PostgreSQL `database-url` must be built from its other three values. The
`gateway-upstreams` `woo-credential` must equal the Woo MCP
`MCP_BEARER_TOKEN`. Generate the API pepper and JWT secret with a cryptographic
random generator and generate `upstream-credential-key` as a Fernet key.

Create the Woo Secret initially with placeholder REST key fields, complete the
store bootstrap, then issue a read/write REST key through **WooCommerce admin →
Settings → Advanced → REST API**. Replace the two REST key fields and restart
`deployment/woo-mcp`. Never write directly to WooCommerce authentication tables.

## Single-node k3s VPS deployment

1. Point `shop.example.com` and `app.example.com` A/AAAA records at the VPS,
   replace those placeholders in `charts/platform/values-vps.yaml`, and wait
   for public DNS resolution.
2. Install the pinned k3s release with its bundled Traefik enabled and confirm
   the node is ready. Review the downloaded installer before running it:

   ```bash
   curl -sfL https://get.k3s.io -o /tmp/install-k3s.sh
   less /tmp/install-k3s.sh
   sudo env INSTALL_K3S_VERSION=v1.35.5+k3s1 sh /tmp/install-k3s.sh
   sudo k3s kubectl get nodes
   ```

   Keep `/etc/rancher/k3s/k3s.yaml` readable only by the deployment operator.
3. Apply `infra/namespaces.yaml` and create every Secret from the table above.
4. Provide TLS Secret `platform-ingress-tls` in **both** `store` and `platform`
   namespaces. Kubernetes Secrets are namespace-scoped. A cert-manager setup may
   issue these certificates, or they may be created from an existing certificate:

   ```bash
   kubectl -n store create secret tls platform-ingress-tls \
     --cert=shop-fullchain.pem --key=shop-private-key.pem
   kubectl -n platform create secret tls platform-ingress-tls \
     --cert=app-fullchain.pem --key=app-private-key.pem
   ```

5. If GHCR packages are private, create a registry pull Secret in all three
   namespaces and attach it to each namespace's default ServiceAccount. Public
   GHCR packages need no registry credential.
6. Review the storage class and PVC sizes in `values-vps.yaml`. The default
   `local-path` class works on standard k3s but keeps data on that single host.
7. Render and inspect before installing:

   ```bash
   helm dependency update charts/platform
   helm lint charts/platform -f charts/platform/values-vps.yaml
   helm template urumi charts/platform --namespace platform \
     -f charts/platform/values-vps.yaml > /tmp/urumi-vps.yaml
   ```

8. Install the same umbrella chart used locally:

   ```bash
   helm upgrade --install urumi charts/platform \
     --namespace platform \
     --values charts/platform/values-vps.yaml \
     --wait --timeout 15m
   kubectl get pods -A
   kubectl get ingress -A
   ```

9. Verify HTTPS, complete the supported WooCommerce REST-key rotation, register
   the currency and policy servers through the dashboard, and run the required
   two-user acceptance flow.

No VPS, DNS record, certificate, or registry package is provisioned by this
repository. A documented render is not evidence of a live VPS deployment.

## Upgrades, rollback, and backups

Before every upgrade, back up MariaDB, PostgreSQL, and the WordPress uploads
stored on the `wordpress-content` PVC. Copy backups off the VPS and test a
restore. A PVC protects data from ordinary Pod replacement but not disk or VPS
loss.

```bash
helm history urumi -n platform
helm upgrade urumi charts/platform -n platform \
  -f charts/platform/values-vps.yaml --wait --timeout 15m
helm rollback urumi REVISION -n platform --wait --timeout 15m
```

Helm rollback restores Kubernetes manifests; it does not reverse database
migrations or restore database contents. `helm uninstall` also leaves retained
PVCs that must be reviewed and deleted manually only when data loss is intended.

This topology is intentionally single-node and is **not highly available**. A
node, disk, or provider failure can take down every workload. Off-server backups,
monitoring, OS security updates, firewall rules for 22/80/443, and tested restore
procedures are operational requirements for a real deployment.
