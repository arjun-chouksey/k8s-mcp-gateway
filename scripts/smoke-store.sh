#!/usr/bin/env bash
set -euo pipefail

expected_context="k3d-k8s-mcp-gateway"
namespace="store"

if [[ "$(kubectl config current-context)" != "$expected_context" ]]; then
  echo "refusing to test outside $expected_context" >&2
  exit 1
fi

kubectl -n "$namespace" wait --for=condition=complete job/store-bootstrap --timeout=10m
kubectl -n "$namespace" wait --for=condition=available deployment/wordpress --timeout=5m

wordpress_pod="$(kubectl -n "$namespace" get pod -l app.kubernetes.io/name=wordpress -o jsonpath='{.items[0].metadata.name}')"
kubectl -n "$namespace" exec "$wordpress_pod" -c wordpress -- php -r '
require "/var/www/html/wp-load.php";
$errors = [];
if (!is_plugin_active("woocommerce/woocommerce.php")) $errors[] = "WooCommerce inactive";
if (get_option("timezone_string") !== "Asia/Kolkata") $errors[] = "timezone mismatch";
if (get_woocommerce_currency() !== "INR") $errors[] = "currency mismatch";
$cod = get_option("woocommerce_cod_settings", []);
if (($cod["enabled"] ?? "no") !== "yes") $errors[] = "COD disabled";
$id = wc_get_product_id_by_sku("urumi-demo-virtual");
$product = $id ? wc_get_product($id) : false;
if (!$product) $errors[] = "demo product missing";
if ($product && (!$product->is_virtual() || $product->get_regular_price() !== "499.00")) $errors[] = "demo product mismatch";
if (home_url() !== "http://shop.127.0.0.1.nip.io:8080") $errors[] = "home URL mismatch: " . home_url();
if ($errors) { fwrite(STDERR, implode("; ", $errors) . PHP_EOL); exit(1); }
echo "PASS store configuration and demo product" . PHP_EOL;
'

product_count="$(kubectl -n "$namespace" exec "$wordpress_pod" -c wordpress -- php -r '
require "/var/www/html/wp-load.php";
$query = new WP_Query(["post_type" => "product", "meta_key" => "_sku", "meta_value" => "urumi-demo-virtual", "fields" => "ids", "posts_per_page" => -1]);
echo count($query->posts);
')"
[[ "$product_count" == "1" ]] || { echo "expected one demo product, found $product_count" >&2; exit 1; }

for path in /shop/ /cart/; do
  status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
    --header 'Host: shop.127.0.0.1.nip.io:8080' "http://127.0.0.1:8080$path")"
  [[ "$status" == "200" ]] || { echo "$path returned HTTP $status" >&2; exit 1; }
done

checkout_headers="$(curl --silent --head --header 'Host: shop.127.0.0.1.nip.io:8080' \
  'http://127.0.0.1:8080/checkout/')"
grep -Eq '^HTTP/[^ ]+ 302' <<<"$checkout_headers" || {
  echo "empty checkout did not redirect" >&2
  exit 1
}
grep -Eiq '^location: http://shop\.127\.0\.0\.1\.nip\.io:8080/cart/' <<<"$checkout_headers" || {
  echo "empty checkout redirected to an unexpected location" >&2
  exit 1
}

echo "PASS public shop/cart and empty-checkout redirect"
echo "PASS idempotency guard: exactly one demo product"
