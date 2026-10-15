#!/usr/bin/env bash
set -euo pipefail

expected_context="k3d-k8s-mcp-gateway"
namespace="store"
order_id="${1:?usage: order-persistence.sh ORDER_ID}"

if [[ "$(kubectl config current-context)" != "$expected_context" ]]; then
  echo "refusing to replace Pods outside $expected_context" >&2
  exit 1
fi
[[ "$order_id" =~ ^[0-9]+$ ]] || { echo "order ID must be numeric" >&2; exit 1; }

verify_order() {
  local pod
  pod="$(kubectl -n "$namespace" get pod -l app.kubernetes.io/name=wordpress -o jsonpath='{.items[0].metadata.name}')"
  kubectl -n "$namespace" exec "$pod" -c wordpress -- php -r '
    require "/var/www/html/wp-load.php";
    $order = wc_get_order((int) $argv[1]);
    if (!$order || $order->get_payment_method() !== "cod") {
      fwrite(STDERR, "COD order not found" . PHP_EOL);
      exit(1);
    }
    echo "PASS order " . $order->get_id() . " payment=cod total=" . $order->get_total() . " status=" . $order->get_status() . PHP_EOL;
  ' "$order_id"
}

verify_order
kubectl -n "$namespace" delete pod -l app.kubernetes.io/name=wordpress --wait=true
kubectl -n "$namespace" delete pod mariadb-0 --wait=true
kubectl -n "$namespace" rollout status deployment/wordpress --timeout=10m
kubectl -n "$namespace" rollout status statefulset/mariadb --timeout=10m
verify_order
echo "PASS COD order persisted after WordPress and MariaDB Pod replacement"
