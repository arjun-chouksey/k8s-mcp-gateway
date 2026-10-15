#!/usr/bin/env bash
set -euo pipefail

expected_context="k3d-k8s-mcp-gateway"
namespace="store"
secret="store-wordpress-admin"

if [[ "$(kubectl config current-context)" != "$expected_context" ]]; then
  echo "refusing to create credentials outside $expected_context" >&2
  exit 1
fi

kubectl get namespace "$namespace" >/dev/null

if kubectl -n "$namespace" get secret "$secret" >/dev/null 2>&1; then
  echo "$secret already exists; leaving it unchanged"
  exit 0
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
chmod 700 "$tmp_dir"
printf '%s' 'urumi-admin' >"$tmp_dir/username"
printf '%s' 'admin@local.invalid' >"$tmp_dir/email"
openssl rand -base64 32 | tr -d '\n' >"$tmp_dir/password"
chmod 600 "$tmp_dir"/*

kubectl -n "$namespace" create secret generic "$secret" \
  --from-file=username="$tmp_dir/username" \
  --from-file=password="$tmp_dir/password" \
  --from-file=email="$tmp_dir/email" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

echo "created $secret in namespace $namespace; values were not printed"
