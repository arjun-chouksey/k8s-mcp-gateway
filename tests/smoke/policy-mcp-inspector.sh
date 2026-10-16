#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
INSPECTOR="$ROOT/spikes/mcp-compat/node_modules/.bin/mcp-inspector"
PORT=${POLICY_MCP_LOCAL_PORT:-18002}
CONFIG=$(mktemp -t policy-mcp-inspector.XXXXXX)
PF_LOG=$(mktemp -t policy-mcp-port-forward.XXXXXX)
OUT=$(mktemp -t policy-mcp-output.XXXXXX)
chmod 600 "$CONFIG" "$PF_LOG" "$OUT"

cleanup() {
  if [[ -n "${PF_PID:-}" ]]; then kill "$PF_PID" 2>/dev/null || true; fi
  rm -f "$CONFIG" "$PF_LOG" "$OUT"
}
trap cleanup EXIT

[[ -x "$INSPECTOR" ]] || { echo "Run npm ci in spikes/mcp-compat first" >&2; exit 1; }
TOKEN=$(kubectl -n mcp get secret aux-mcp -o jsonpath='{.data.POLICY_MCP_BEARER_TOKEN}' | base64 --decode)
[[ -n "$TOKEN" ]] || { echo "POLICY_MCP_BEARER_TOKEN is missing" >&2; exit 1; }

kubectl -n mcp port-forward service/policy-mcp "$PORT:8000" >"$PF_LOG" 2>&1 &
PF_PID=$!
for _ in {1..30}; do
  curl --fail --silent "http://127.0.0.1:$PORT/healthz" >/dev/null && break
  sleep 1
done
curl --fail --silent "http://127.0.0.1:$PORT/healthz" >/dev/null

python3 - "$CONFIG" "$PORT" "$TOKEN" <<'PY'
import json, pathlib, sys
path, port, token = sys.argv[1:]
pathlib.Path(path).write_text(json.dumps({"mcpServers": {"policy": {
    "type": "http", "url": f"http://127.0.0.1:{port}/mcp",
    "headers": {"Authorization": f"Bearer {token}"}
}}}))
PY

BASE=("$INSPECTOR" --cli --config "$CONFIG" --server policy --format json)
"${BASE[@]}" --method tools/list >"$OUT"
python3 - "$OUT" <<'PY'
import json, sys
tools = json.load(open(sys.argv[1]))["result"]["tools"]
assert {tool["name"] for tool in tools} == {
    "list_store_policies", "get_store_policy", "list_products"
}
PY
"${BASE[@]}" --method tools/call --tool-name get_store_policy \
  --tool-args-json '{"topic":"refunds"}' >"$OUT"
python3 - "$OUT" <<'PY'
import json, sys
result = json.load(open(sys.argv[1]))["result"]
assert result["isError"] is False
assert result["structuredContent"]["topic"] == "refunds"
assert result["structuredContent"]["version"] == "2026-10-demo-v1"
PY
"${BASE[@]}" --method tools/call --tool-name list_products \
  --tool-args-json '{"per_page":1}' >"$OUT"
python3 - "$OUT" <<'PY'
import json, sys
result = json.load(open(sys.argv[1]))["result"]
assert result["isError"] is False
assert "NOT WooCommerce" in result["structuredContent"]["items"][0]["label"]
PY

echo "PASS MCP Inspector discovered three policy tools and verified the collision fixture"
