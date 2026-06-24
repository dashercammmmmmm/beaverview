#!/usr/bin/env bash
# Fast local verification for BeaverView v2.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT/api"
PORT="${BEAVERVIEW_SMOKE_PORT:-8017}"
BASE_URL="http://127.0.0.1:${PORT}"

if [ ! -x "$API_DIR/venv/bin/python" ]; then
  echo "Missing api/venv. Create it with: cd api && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

"$API_DIR/venv/bin/python" -m py_compile \
  "$API_DIR/main.py" \
  "$API_DIR/data_mock.py" \
  "$API_DIR/migrate_data.py" \
  "$API_DIR/import_device_ips.py" \
  "$API_DIR/connectors/chat.py" \
  "$API_DIR/connectors/servicenow.py"

"$API_DIR/venv/bin/python" -c "import fastapi, httpx, msal, starlette_sessions"

cd "$API_DIR"
"$API_DIR/venv/bin/uvicorn" main:app --host 127.0.0.1 --port "$PORT" > /tmp/beaverview-smoke.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/api/health" >/tmp/beaverview-health.json 2>/dev/null; then
    break
  fi
  sleep 0.2
done

curl -fsS "$BASE_URL/api/health" | grep -q '"status":"ok"'
curl -fsS "$BASE_URL/api/me" | grep -q '"role":"admin"'
curl -fsS "$BASE_URL/api/connectors/servicenow/test" | grep -q '"status":"mock"'
curl -fsS "$BASE_URL/api/connectors/chat/test" | grep -q '"status":"mock"'

echo "BeaverView smoke checks passed at $BASE_URL"
