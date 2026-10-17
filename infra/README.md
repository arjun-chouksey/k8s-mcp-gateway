# Local cluster bootstrap

Install Docker, k3d, kubectl, and Helm, then start Docker. Create the pinned local
cluster and its namespaces from the repository root:

```bash
k3d cluster create k8s-mcp-gateway \
  --image rancher/k3s:v1.35.5-k3s1 \
  --api-port 127.0.0.1:6550 \
  --port 127.0.0.1:8080:80@loadbalancer \
  --wait
kubectl config use-context k3d-k8s-mcp-gateway
kubectl apply -f infra/namespaces.yaml
kubectl -n kube-system rollout status deployment/traefik --timeout=180s
kubectl -n kube-system rollout status deployment/local-path-provisioner --timeout=180s
```

Local hosts are `shop.127.0.0.1.nip.io` and `app.127.0.0.1.nip.io`. Confirm
that both resolve to `127.0.0.1`. If nip.io is unavailable, add equivalent
entries to `/etc/hosts` manually and use matching chart host values later:

```text
127.0.0.1 shop.local app.local
```

Import an already-built local image when required:

```bash
k3d image import --cluster k8s-mcp-gateway name:tag
```

A registry can be added later if the image workflow requires it; this repository
does not currently publish images.

Before installing the Helm chart, create the existing Kubernetes Secrets named
by `charts/platform/values.yaml`. Real credentials must remain outside Git.

Build the umbrella chart dependencies and install it after its required images
and Secrets are available:

```bash
helm dependency update charts/platform
helm upgrade --install urumi charts/platform \
  --namespace platform \
  --values charts/platform/values-local.yaml \
  --wait \
  --timeout 15m
```

To delete the local cluster, first verify the current context and then run:

```bash
kubectl config current-context
k3d cluster delete k8s-mcp-gateway
```
