#!/usr/bin/env bash
set -euo pipefail

context="${KUBE_CONTEXT:-k3d-k8s-mcp-gateway}"
namespace="${MCP_NAMESPACE:-mcp}"
secret_name="${WOO_API_SECRET_NAME:-woo-mcp}"
pod_name="woo-api-auth-smoke"
image="${WOO_API_TEST_IMAGE:-python:3.13-alpine}"

[[ "$(kubectl config current-context)" == "$context" ]] || {
  echo "refusing to test context other than $context" >&2
  exit 1
}
kubectl --context "$context" -n "$namespace" get secret "$secret_name" >/dev/null

cleanup() {
  kubectl --context "$context" -n "$namespace" delete pod "$pod_name" \
    --ignore-not-found --wait=true >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup

overrides="$(cat <<JSON
{"apiVersion":"v1","spec":{"automountServiceAccountToken":false,"securityContext":{"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"$pod_name","image":"$image","command":["sleep","300"],"envFrom":[{"secretRef":{"name":"$secret_name"}}],"resources":{"requests":{"cpu":"10m","memory":"32Mi"},"limits":{"cpu":"100m","memory":"64Mi"}},"securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}}]}}
JSON
)"

kubectl --context "$context" -n "$namespace" run "$pod_name" \
  --image="$image" --restart=Never --overrides="$overrides" >/dev/null
kubectl --context "$context" -n "$namespace" wait --for=condition=Ready \
  "pod/$pod_name" --timeout=180s >/dev/null
kubectl --context "$context" -n "$namespace" exec -i "$pod_name" -- \
  python - <"$(dirname "$0")/woo-api-auth.py"
