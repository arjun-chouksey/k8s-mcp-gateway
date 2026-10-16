K3D_CLUSTER_NAME ?= k8s-mcp-gateway
K3D_API_PORT ?= 6550
K3D_HTTP_PORT ?= 8080
K3D_IMAGE ?= rancher/k3s:v1.35.5-k3s1

.PHONY: cluster-up cluster-verify cluster-context image-import cluster-down chart-check store-secrets store-deploy store-persistence store-admin store-bootstrap store-smoke order-persistence woo-api-secret woo-api-auth woo-client-test woo-client-live woo-mcp-test woo-mcp-inspector currency-mcp-test currency-mcp-inspector policy-mcp-test policy-mcp-inspector

chart-check:
	./scripts/chart-check.sh

store-secrets:
	./scripts/create-local-secrets.sh

store-deploy: store-secrets
	helm dependency update charts/platform
	helm upgrade --install urumi charts/platform --namespace platform --values charts/platform/values-local.yaml --wait --timeout 10m

store-persistence:
	./tests/smoke/store-persistence.sh

store-admin:
	./scripts/create-local-store-admin.sh

store-bootstrap: store-admin
	helm dependency update charts/platform
	helm upgrade --install urumi charts/platform --namespace platform --values charts/platform/values-local.yaml --wait --timeout 15m

store-smoke:
	./scripts/smoke-store.sh

order-persistence:
	@test -n "$(ORDER_ID)" || (echo "usage: make order-persistence ORDER_ID=123" >&2; exit 1)
	./tests/smoke/order-persistence.sh "$(ORDER_ID)"

woo-api-secret:
	./scripts/create-local-woo-api-secret.sh

woo-api-auth:
	./tests/smoke/woo-api-auth.sh

woo-client-test:
	.venv/bin/python -m pytest services/woo-mcp/tests/test_wc_client.py -q

woo-client-live:
	./tests/smoke/woo-client-live.sh

woo-mcp-test:
	.venv/bin/python -m pytest services/woo-mcp/tests -q

woo-mcp-inspector:
	./tests/smoke/woo-mcp-inspector.sh

currency-mcp-test:
	.venv/bin/python -m pytest services/aux-mcp/currency/tests -q

currency-mcp-inspector:
	./tests/smoke/currency-mcp-inspector.sh

policy-mcp-test:
	.venv/bin/python -m pytest services/aux-mcp/policy/tests -q

policy-mcp-inspector:
	./tests/smoke/policy-mcp-inspector.sh

cluster-up:
	K3D_CLUSTER_NAME=$(K3D_CLUSTER_NAME) K3D_API_PORT=$(K3D_API_PORT) K3D_HTTP_PORT=$(K3D_HTTP_PORT) K3D_IMAGE=$(K3D_IMAGE) ./scripts/cluster-up.sh

cluster-verify:
	K3D_CLUSTER_NAME=$(K3D_CLUSTER_NAME) ./scripts/verify-cluster.sh

cluster-context:
	@kubectl config current-context

image-import:
	@test -n "$(IMAGE)" || (echo "usage: make image-import IMAGE=name:tag" >&2; exit 1)
	k3d image import --cluster $(K3D_CLUSTER_NAME) $(IMAGE)

cluster-down:
	@test "$(CONFIRM)" = "1" || (echo "cluster deletion requires CONFIRM=1" >&2; exit 1)
	@test "$$(kubectl config current-context)" = "k3d-$(K3D_CLUSTER_NAME)" || (echo "refusing to delete from unexpected context" >&2; exit 1)
	k3d cluster delete $(K3D_CLUSTER_NAME)
