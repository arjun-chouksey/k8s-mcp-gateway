#!/usr/bin/env bash
set -euo pipefail

context="${KUBE_CONTEXT:-k3d-k8s-mcp-gateway}"
namespace="${MCP_NAMESPACE:-mcp}"
secret_name="${WOO_API_SECRET_NAME:-woo-mcp}"
base_url="${WOOCOMMERCE_BASE_URL:-http://wordpress.store.svc.cluster.local}"
oauth_base_url="${WOOCOMMERCE_OAUTH_BASE_URL:-http://shop.127.0.0.1.nip.io:8080}"

[[ "$(kubectl config current-context)" == "$context" ]] || {
  echo "refusing to create credentials outside context $context" >&2
  exit 1
}
kubectl --context "$context" -n "$namespace" get namespace "$namespace" >/dev/null

if kubectl --context "$context" -n "$namespace" get secret "$secret_name" >/dev/null 2>&1; then
  echo "Secret $namespace/$secret_name already exists; refusing to overwrite it." >&2
  echo "Revoke the old WooCommerce key and remove the Secret explicitly before rotation." >&2
  exit 1
fi

read -r -s -p "WooCommerce consumer key (ck_...): " consumer_key
printf '\n'
read -r -s -p "WooCommerce consumer secret (cs_...): " consumer_secret
printf '\n'

[[ "$consumer_key" == ck_* ]] || {
  echo "consumer key must start with ck_" >&2
  exit 1
}
[[ "$consumer_secret" == cs_* ]] || {
  echo "consumer secret must start with cs_" >&2
  exit 1
}

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
chmod 700 "$tmp_dir"
printf '%s' "$consumer_key" >"$tmp_dir/consumer-key"
printf '%s' "$consumer_secret" >"$tmp_dir/consumer-secret"
printf '%s' "$base_url" >"$tmp_dir/base-url"
printf '%s' "$oauth_base_url" >"$tmp_dir/oauth-base-url"
chmod 600 "$tmp_dir"/*
unset consumer_key consumer_secret

kubectl --context "$context" -n "$namespace" create secret generic "$secret_name" \
  --from-file=WOOCOMMERCE_CONSUMER_KEY="$tmp_dir/consumer-key" \
  --from-file=WOOCOMMERCE_CONSUMER_SECRET="$tmp_dir/consumer-secret" \
  --from-file=WOOCOMMERCE_BASE_URL="$tmp_dir/base-url" \
  --from-file=WOOCOMMERCE_OAUTH_BASE_URL="$tmp_dir/oauth-base-url" \
  --dry-run=client -o yaml | kubectl --context "$context" apply -f - >/dev/null

echo "Created $namespace/$secret_name without printing credential values."
