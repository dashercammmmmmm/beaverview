#!/usr/bin/env bash
# Fast local verification for BeaverView v2.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT/api"

if [ ! -x "$API_DIR/venv/bin/python" ]; then
  echo "Missing api/venv. Create it with: cd api && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if [ -n "${BEAVERVIEW_SMOKE_PORT:-}" ]; then
  PORT="$BEAVERVIEW_SMOKE_PORT"
else
  PORT="$("$API_DIR/venv/bin/python" - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
fi
BASE_URL="http://127.0.0.1:${PORT}"
TMP_DIR="$(mktemp -d)"

"$API_DIR/venv/bin/python" -m py_compile \
  "$API_DIR/main.py" \
  "$API_DIR/data_mock.py" \
  "$API_DIR/migrate_data.py" \
  "$API_DIR/import_device_ips.py" \
  "$API_DIR/connectors/chat.py" \
  "$API_DIR/connectors/servicenow.py"

"$API_DIR/venv/bin/python" -c "import fastapi, httpx, msal, starlette_sessions"
node --check "$ROOT/dashboard/app.js" >/dev/null

cd "$API_DIR"
"$API_DIR/venv/bin/uvicorn" main:app --host 127.0.0.1 --port "$PORT" > "$TMP_DIR/beaverview-smoke.log" 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" >/dev/null 2>&1 || true; rm -rf "$TMP_DIR"' EXIT

for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/api/health" >"$TMP_DIR/beaverview-health.json" 2>/dev/null; then
    break
  fi
  sleep 0.2
done

curl -fsS "$BASE_URL/api/health" | grep -q '"status":"ok"'
curl -fsS "$BASE_URL/api/me" | grep -q '"role":"admin"'
curl -fsS "$BASE_URL/api/campus/corvallis/schedule" | grep -q '"mode":"mock"'
curl -fsS "$BASE_URL/api/connectors/servicenow/test" | grep -q '"status":"mock"'
curl -fsS "$BASE_URL/api/connectors/chat/test" | grep -q '"status":"mock"'
curl -fsS "$BASE_URL/api/rooms/corvallis-kad-101/launch/screenconnect" | grep -q '"url":null'
curl -fsS "$BASE_URL/api/rooms/corvallis-kad-101/launch/sharepoint" | grep -q '"url":null'

proxy_status="$(curl -sS -o "$TMP_DIR/beaverview-proxy.json" -w "%{http_code}" "$BASE_URL/api/rooms/corvallis-kad-101/proxy/xpanel/")"
if [ "$proxy_status" = "501" ]; then
  echo "Device proxy is still the old 501 stub" >&2
  exit 1
fi

wattbox_status="$(curl -sS -o "$TMP_DIR/beaverview-wattbox.json" -w "%{http_code}" "$BASE_URL/api/rooms/corvallis-kad-101/wattbox/outlets")"
if [ "$wattbox_status" != "400" ] || ! grep -q "WattBox OvrC credentials are not configured" "$TMP_DIR/beaverview-wattbox.json"; then
  echo "WattBox offline guardrail changed unexpectedly" >&2
  exit 1
fi

ptz_status="$(curl -sS -o "$TMP_DIR/beaverview-ptz.json" -w "%{http_code}" -X POST "$BASE_URL/api/rooms/corvallis-kad-101/ptz/home")"
if [ "$ptz_status" != "400" ] || ! grep -q "ptz proxy credentials are not configured" "$TMP_DIR/beaverview-ptz.json"; then
  echo "PTZ offline guardrail changed unexpectedly" >&2
  exit 1
fi

echo "BeaverView smoke checks passed at $BASE_URL"
