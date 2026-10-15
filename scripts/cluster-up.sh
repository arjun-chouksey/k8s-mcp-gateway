#!/usr/bin/env bash
set -euo pipefail

cluster_name="${K3D_CLUSTER_NAME:-k8s-mcp-gateway}"
api_port="${K3D_API_PORT:-6550}"
http_port="${K3D_HTTP_PORT:-8080}"
k3s_image="${K3D_IMAGE:-rancher/k3s:v1.35.5-k3s1}"
expected_context="k3d-${cluster_name}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for command in docker k3d kubectl; do
  command -v "$command" >/dev/null || {
    echo "required command is missing: $command" >&2
    exit 1
  }
done

docker info >/dev/null 2>&1 || {
  echo "Docker is not running; start Docker Desktop and retry." >&2
  exit 1
}

if ! k3d cluster list --no-headers | awk '{print $1}' | grep -Fxq "$cluster_name"; then
  k3d cluster create "$cluster_name" \
    --image "$k3s_image" \
    --api-port "127.0.0.1:${api_port}" \
    --port "127.0.0.1:${http_port}:80@loadbalancer" \
    --wait
fi

kubectl config use-context "$expected_context" >/dev/null
actual_context="$(kubectl config current-context)"
if [[ "$actual_context" != "$expected_context" ]]; then
  echo "refusing to continue: expected context $expected_context, got $actual_context" >&2
  exit 1
fi

kubectl --context "$expected_context" apply -f "$repo_root/infra/namespaces.yaml"

wait_for_deployment() {
  local deployment="$1"
  for _ in {1..60}; do
    if kubectl --context "$expected_context" -n kube-system get deployment "$deployment" >/dev/null 2>&1; then
      kubectl --context "$expected_context" -n kube-system rollout status \
        "deployment/$deployment" --timeout=180s
      return
    fi
    sleep 2
  done
  echo "timed out waiting for deployment/$deployment to be created" >&2
  exit 1
}

wait_for_deployment traefik
wait_for_deployment local-path-provisioner

echo "Cluster $cluster_name is ready on context $expected_context."
echo "Ingress: http://shop.127.0.0.1.nip.io:${http_port} and http://app.127.0.0.1.nip.io:${http_port}"
