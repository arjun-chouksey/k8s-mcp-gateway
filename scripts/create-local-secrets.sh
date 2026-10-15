#!/usr/bin/env bash
set -euo pipefail

namespace="${STORE_NAMESPACE:-store}"
context="${KUBE_CONTEXT:-k3d-k8s-mcp-gateway}"
db_secret="store-mariadb"
wordpress_secret="store-wordpress"

[[ "$(kubectl config current-context)" == "$context" ]] || {
  echo "refusing to create credentials outside context $context" >&2
  exit 1
}

db_exists=false
wordpress_exists=false
kubectl --context "$context" -n "$namespace" get secret "$db_secret" >/dev/null 2>&1 && db_exists=true
kubectl --context "$context" -n "$namespace" get secret "$wordpress_secret" >/dev/null 2>&1 && wordpress_exists=true

if $db_exists && $wordpress_exists; then
  echo "Local store Secrets already exist; leaving them unchanged."
  exit 0
fi
if $db_exists || $wordpress_exists; then
  echo "refusing partial credential state; remove or repair both store Secrets manually" >&2
  exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
chmod 700 "$tmp_dir"
printf '%s' wordpress >"$tmp_dir/database"
printf '%s' wordpress >"$tmp_dir/username"
openssl rand -hex 32 >"$tmp_dir/password"
openssl rand -hex 32 >"$tmp_dir/root-password"
chmod 600 "$tmp_dir"/*

kubectl --context "$context" -n "$namespace" create secret generic "$db_secret" \
  --from-file=database="$tmp_dir/database" \
  --from-file=username="$tmp_dir/username" \
  --from-file=password="$tmp_dir/password" \
  --from-file=root-password="$tmp_dir/root-password" \
  --dry-run=client -o yaml | kubectl --context "$context" apply -f - >/dev/null

kubectl --context "$context" -n "$namespace" create secret generic "$wordpress_secret" \
  --from-file=database="$tmp_dir/database" \
  --from-file=username="$tmp_dir/username" \
  --from-file=password="$tmp_dir/password" \
  --dry-run=client -o yaml | kubectl --context "$context" apply -f - >/dev/null

echo "Created local store Secrets without printing credential values."
