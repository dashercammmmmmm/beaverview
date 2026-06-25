#!/usr/bin/env bash
# Browser-level admin panel smoke check for BeaverView v2.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT/api"

if [ ! -x "$API_DIR/venv/bin/python" ]; then
  echo "Missing api/venv. Create it with: cd api && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if [ -n "${BEAVERVIEW_ADMIN_BROWSER_PORT:-}" ]; then
  PORT="$BEAVERVIEW_ADMIN_BROWSER_PORT"
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

PLAYWRIGHT_PY=""
for candidate in "$API_DIR/venv/bin/python" python3 /Library/Developer/CommandLineTools/usr/bin/python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "from playwright.sync_api import sync_playwright" >/dev/null 2>&1; then
    PLAYWRIGHT_PY="$candidate"
    break
  fi
done

if [ -z "$PLAYWRIGHT_PY" ]; then
  echo "Python Playwright is required for admin browser smoke checks. Install it or run the fast smoke check instead: scripts/smoke_check.sh" >&2
  exit 1
fi

cd "$API_DIR"
"$API_DIR/venv/bin/uvicorn" main:app --host 127.0.0.1 --port "$PORT" > "$TMP_DIR/beaverview-admin-browser-smoke.log" 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" >/dev/null 2>&1 || true; rm -rf "$TMP_DIR"' EXIT

for _ in $(seq 1 40); do
  if curl -fsS "$BASE_URL/api/health" >"$TMP_DIR/beaverview-admin-browser-health.json" 2>/dev/null; then
    break
  fi
  sleep 0.25
done

curl -fsS "$BASE_URL/api/health" | grep -q '"status":"ok"'
"$PLAYWRIGHT_PY" "$ROOT/scripts/check_admin_browser.py" "$BASE_URL"
