#!/usr/bin/env bash
set -euo pipefail

cluster_name="${K3D_CLUSTER_NAME:-k8s-mcp-gateway}"
expected_context="k3d-${cluster_name}"
test_namespace="t004-policy-test"

actual_context="$(kubectl config current-context)"
if [[ "$actual_context" != "$expected_context" ]]; then
  echo "refusing to test context $actual_context; expected $expected_context" >&2
  exit 1
fi

cleanup() {
  kubectl --context "$expected_context" delete namespace "$test_namespace" \
    --wait=true --timeout=60s --ignore-not-found >/dev/null
}
trap cleanup EXIT

kubectl --context "$expected_context" get namespace store mcp platform
kubectl --context "$expected_context" get storageclass local-path
kubectl --context "$expected_context" -n kube-system get deployment traefik local-path-provisioner

for host in shop.127.0.0.1.nip.io app.127.0.0.1.nip.io; do
  resolved="$(python3 -c 'import socket, sys; print(socket.gethostbyname(sys.argv[1]))' "$host")"
  [[ "$resolved" == "127.0.0.1" ]] || {
    echo "$host resolved to $resolved, expected 127.0.0.1" >&2
    exit 1
  }
done

kubectl --context "$expected_context" create namespace "$test_namespace"
kubectl --context "$expected_context" -n "$test_namespace" create deployment server --image=nginx:1.27.4-alpine
kubectl --context "$expected_context" -n "$test_namespace" expose deployment server --port=80
kubectl --context "$expected_context" -n "$test_namespace" run client \
  --image=curlimages/curl:8.12.1 --command -- sleep 300
kubectl --context "$expected_context" -n "$test_namespace" rollout status deployment/server --timeout=180s
kubectl --context "$expected_context" -n "$test_namespace" wait --for=condition=Ready pod/client --timeout=180s
kubectl --context "$expected_context" -n "$test_namespace" exec client -- \
  curl --connect-timeout 2 --max-time 5 --fail --silent http://server >/dev/null

kubectl --context "$expected_context" -n "$test_namespace" apply -f - <<'YAML'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-server-ingress
spec:
  podSelector:
    matchLabels:
      app: server
  policyTypes:
    - Ingress
YAML

sleep 2
if kubectl --context "$expected_context" -n "$test_namespace" exec client -- \
  curl --connect-timeout 2 --max-time 5 --fail --silent http://server >/dev/null 2>&1; then
  echo "NetworkPolicy enforcement failed: denied request succeeded" >&2
  exit 1
fi

echo "PASS namespaces, Traefik, local-path storage, nip.io DNS, and NetworkPolicy enforcement"
