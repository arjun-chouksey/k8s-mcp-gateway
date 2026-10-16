#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
INSPECTOR="$ROOT/spikes/mcp-compat/node_modules/.bin/mcp-inspector"
PORT=${CURRENCY_MCP_LOCAL_PORT:-18001}
CONFIG=$(mktemp -t currency-mcp-inspector.XXXXXX)
PF_LOG=$(mktemp -t currency-mcp-port-forward.XXXXXX)
OUT=$(mktemp -t currency-mcp-output.XXXXXX)
chmod 600 "$CONFIG" "$PF_LOG" "$OUT"

cleanup() {
  if [[ -n "${PF_PID:-}" ]]; then kill "$PF_PID" 2>/dev/null || true; fi
  rm -f "$CONFIG" "$PF_LOG" "$OUT"
}
trap cleanup EXIT

[[ -x "$INSPECTOR" ]] || { echo "Run npm ci in spikes/mcp-compat first" >&2; exit 1; }
TOKEN=$(kubectl -n mcp get secret aux-mcp -o jsonpath='{.data.CURRENCY_MCP_BEARER_TOKEN}' | base64 --decode)
[[ -n "$TOKEN" ]] || { echo "CURRENCY_MCP_BEARER_TOKEN is missing" >&2; exit 1; }

kubectl -n mcp port-forward service/currency-mcp "$PORT:8000" >"$PF_LOG" 2>&1 &
PF_PID=$!
for _ in {1..30}; do
  curl --fail --silent "http://127.0.0.1:$PORT/healthz" >/dev/null && break
  sleep 1
done
curl --fail --silent "http://127.0.0.1:$PORT/healthz" >/dev/null

python3 - "$CONFIG" "$PORT" "$TOKEN" <<'PY'
import json, pathlib, sys
path, port, token = sys.argv[1:]
pathlib.Path(path).write_text(json.dumps({"mcpServers": {"currency": {
    "type": "http", "url": f"http://127.0.0.1:{port}/mcp",
    "headers": {"Authorization": f"Bearer {token}"}
}}}))
PY

BASE=("$INSPECTOR" --cli --config "$CONFIG" --server currency --format json)
"${BASE[@]}" --method tools/list >"$OUT"
python3 - "$OUT" <<'PY'
import json, sys
tools = json.load(open(sys.argv[1]))["result"]["tools"]
assert {tool["name"] for tool in tools} == {"convert_currency", "get_demo_rates"}
PY
"${BASE[@]}" --method tools/call --tool-name convert_currency \
  --tool-args-json '{"amount":"998.00","from_currency":"INR","to_currency":"EUR"}' >"$OUT"
python3 - "$OUT" <<'PY'
import json, sys
result = json.load(open(sys.argv[1]))["result"]
assert result["isError"] is False
assert result["structuredContent"]["converted_amount"] == "10.479000"
assert "NOT live FX" in result["structuredContent"]["rate_label"]
PY

echo "PASS MCP Inspector discovered two currency tools and converted INR to EUR"
