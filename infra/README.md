# Local cluster bootstrap

`make cluster-up` creates the `k8s-mcp-gateway` k3d cluster with pinned image `rancher/k3s:v1.35.5-k3s1` and creates the `store`, `mcp`, and `platform` namespaces. It maps local port `8080` to Traefik port 80 and changes the active kube context to `k3d-k8s-mcp-gateway`. Override `K3D_CLUSTER_NAME`, `K3D_API_PORT`, `K3D_HTTP_PORT`, or `K3D_IMAGE` when needed.

Local hosts are `shop.127.0.0.1.nip.io` and `app.127.0.0.1.nip.io`. `make cluster-verify` checks that both resolve to `127.0.0.1`. If nip.io is unavailable, add equivalent entries to `/etc/hosts` manually and use matching chart host values later:

```text
127.0.0.1 shop.local app.local
```

`make image-import IMAGE=name:tag` imports an already-built local image into k3d. A registry can be added later if the image workflow requires it; this ticket does not publish images.

`make cluster-down` deletes the named local cluster and therefore requires `CONFIRM=1`. Always inspect `kubectl config current-context` before manual Kubernetes commands.
