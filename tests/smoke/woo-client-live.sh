#!/usr/bin/env bash
set -euo pipefail

context="${KUBE_CONTEXT:-k3d-k8s-mcp-gateway}"
secret_name="${WOO_API_SECRET_NAME:-woo-mcp}"
local_port="${WOO_API_LOCAL_PORT:-18080}"
python="${PYTHON:-.venv/bin/python}"

[[ "$(kubectl config current-context)" == "$context" ]] || {
  echo "refusing to test context other than $context" >&2
  exit 1
}
[[ -x "$python" ]] || {
  echo "missing test environment; install services/woo-mcp[test] into .venv" >&2
  exit 1
}
kubectl --context "$context" -n mcp get secret "$secret_name" >/dev/null

log_file="$(mktemp)"
kubectl --context "$context" -n store port-forward service/wordpress \
  "$local_port:80" >"$log_file" 2>&1 &
forward_pid=$!
cleanup() {
  kill "$forward_pid" >/dev/null 2>&1 || true
  wait "$forward_pid" >/dev/null 2>&1 || true
  rm -f "$log_file"
}
trap cleanup EXIT

for _ in {1..50}; do
  if grep -q "Forwarding from" "$log_file"; then
    break
  fi
  if ! kill -0 "$forward_pid" 2>/dev/null; then
    cat "$log_file" >&2
    exit 1
  fi
  sleep 0.1
done
grep -q "Forwarding from" "$log_file" || {
  echo "WordPress port-forward did not become ready" >&2
  exit 1
}

read_secret() {
  kubectl --context "$context" -n mcp get secret "$secret_name" \
    -o "jsonpath={.data.$1}" | base64 --decode
}

export WOOCOMMERCE_BASE_URL="http://127.0.0.1:$local_port"
export WOOCOMMERCE_OAUTH_BASE_URL="$(read_secret WOOCOMMERCE_OAUTH_BASE_URL)"
export WOOCOMMERCE_CONSUMER_KEY="$(read_secret WOOCOMMERCE_CONSUMER_KEY)"
export WOOCOMMERCE_CONSUMER_SECRET="$(read_secret WOOCOMMERCE_CONSUMER_SECRET)"

"$python" tests/smoke/woo-client-live.py
