#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
INSPECTOR="$ROOT/spikes/mcp-compat/node_modules/.bin/mcp-inspector"
PORT=${WOO_MCP_LOCAL_PORT:-18000}
CONFIG=$(mktemp -t woo-mcp-inspector.XXXXXX)
PF_LOG=$(mktemp -t woo-mcp-port-forward.XXXXXX)
chmod 600 "$CONFIG" "$PF_LOG"

cleanup() {
  if [[ -n "${PF_PID:-}" ]]; then kill "$PF_PID" 2>/dev/null || true; fi
  rm -f "$CONFIG" "$PF_LOG"
}
trap cleanup EXIT

[[ -x "$INSPECTOR" ]] || { echo "Run npm ci in spikes/mcp-compat first" >&2; exit 1; }
TOKEN=$(kubectl -n mcp get secret woo-mcp -o jsonpath='{.data.MCP_BEARER_TOKEN}' | base64 --decode)
[[ -n "$TOKEN" ]] || { echo "MCP_BEARER_TOKEN is missing" >&2; exit 1; }

kubectl -n mcp port-forward service/woocommerce-mcp "$PORT:8000" >"$PF_LOG" 2>&1 &
PF_PID=$!
for _ in {1..30}; do
  if curl --fail --silent "http://127.0.0.1:$PORT/healthz" >/dev/null; then break; fi
  sleep 1
done
curl --fail --silent "http://127.0.0.1:$PORT/healthz" >/dev/null

python3 - "$CONFIG" "$PORT" "$TOKEN" <<'PY'
import json, pathlib, sys
path, port, token = sys.argv[1:]
pathlib.Path(path).write_text(json.dumps({"mcpServers": {"woo": {
    "type": "http", "url": f"http://127.0.0.1:{port}/mcp",
    "headers": {"Authorization": f"Bearer {token}"}
}}}))
PY

BASE=("$INSPECTOR" --cli --config "$CONFIG" --server woo --format json)
"${BASE[@]}" --method tools/list | python3 -c 'import json,sys; d=json.load(sys.stdin); assert len(d["result"]["tools"]) == 5'
"${BASE[@]}" --method tools/call --tool-name list_products --tool-args-json '{"per_page":1}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["result"]["isError"] is False'

echo "PASS MCP Inspector discovered five tools and called list_products"
