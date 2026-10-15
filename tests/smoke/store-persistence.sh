#!/usr/bin/env bash
set -euo pipefail

context="${KUBE_CONTEXT:-k3d-k8s-mcp-gateway}"
namespace="${STORE_NAMESPACE:-store}"

[[ "$(kubectl config current-context)" == "$context" ]] || {
  echo "refusing to test context other than $context" >&2
  exit 1
}

for secret in store-mariadb store-wordpress; do
  kubectl --context "$context" -n "$namespace" get secret "$secret" >/dev/null
done

kubectl --context "$context" -n "$namespace" rollout status statefulset/mariadb --timeout=300s
kubectl --context "$context" -n "$namespace" rollout status deployment/wordpress --timeout=300s

kubectl --context "$context" -n "$namespace" exec mariadb-0 -- sh -ceu '
  mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE" <<SQL
CREATE TABLE IF NOT EXISTS t006_persistence (id INT PRIMARY KEY, value_text VARCHAR(64) NOT NULL);
INSERT INTO t006_persistence (id, value_text) VALUES (1, "survives-restart")
  ON DUPLICATE KEY UPDATE value_text = VALUES(value_text);
SQL
'

wordpress_pod="$(kubectl --context "$context" -n "$namespace" get pod \
  -l app.kubernetes.io/name=wordpress -o jsonpath='{.items[0].metadata.name}')"
kubectl --context "$context" -n "$namespace" exec "$wordpress_pod" -- \
  sh -ceu 'printf "%s" survives-restart >/var/www/html/.t006-persistence'
kubectl --context "$context" -n "$namespace" exec "$wordpress_pod" -- \
  php -r '$socket = @fsockopen("mariadb", 3306, $errno, $errstr, 5); if (!$socket) { exit(1); } fclose($socket);'

auth_result="$(kubectl auth can-i get secret/store-mariadb \
  --as=system:serviceaccount:store:default --namespace "$namespace" || true)"
[[ "$auth_result" == "no" ]] || {
  echo "default store ServiceAccount unexpectedly reads database Secret" >&2
  exit 1
}

kubectl --context "$context" -n "$namespace" delete pod mariadb-0 "$wordpress_pod" --wait=true
kubectl --context "$context" -n "$namespace" rollout status statefulset/mariadb --timeout=300s
kubectl --context "$context" -n "$namespace" rollout status deployment/wordpress --timeout=300s

value="$(kubectl --context "$context" -n "$namespace" exec mariadb-0 -- sh -ceu \
  'mariadb -N -B -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE" -e "SELECT value_text FROM t006_persistence WHERE id=1"')"
[[ "$value" == "survives-restart" ]] || {
  echo "MariaDB persistence marker was lost" >&2
  exit 1
}

wordpress_pod="$(kubectl --context "$context" -n "$namespace" get pod \
  -l app.kubernetes.io/name=wordpress -o jsonpath='{.items[0].metadata.name}')"
marker="$(kubectl --context "$context" -n "$namespace" exec "$wordpress_pod" -- \
  cat /var/www/html/.t006-persistence)"
[[ "$marker" == "survives-restart" ]] || {
  echo "WordPress persistence marker was lost" >&2
  exit 1
}

for claim in wordpress-content mariadb-data-mariadb-0; do
  phase="$(kubectl --context "$context" -n "$namespace" get pvc "$claim" -o jsonpath='{.status.phase}')"
  [[ "$phase" == "Bound" ]] || {
    echo "PVC $claim is not Bound" >&2
    exit 1
  }
done

echo "PASS WordPress-to-MariaDB connectivity, Secret denial, and both PVC persistence checks"
