#!/usr/bin/env bash
# Validate the documented Hardware IP CSV shape without importing real data.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT/api"
SAMPLE="$ROOT/docs/examples/hardware_ips.sample.csv"
REAL_CSV="$API_DIR/hardware_ips.csv"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [ ! -x "$API_DIR/venv/bin/python" ]; then
  echo "Missing api/venv. Create it with: cd api && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

cd "$API_DIR"
"$API_DIR/venv/bin/python" migrate_data.py >/tmp/beaverview-migrate-for-hardware-check.log
"$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$SAMPLE"

DUPLICATE_CSV="$TMP_DIR/hardware_ips.duplicate.csv"
cat >"$DUPLICATE_CSV" <<'CSV'
room_id,device_type,ip_address,notes
corvallis-kad-101,xpanel,10.20.1.45,first mapping
corvallis-kad-101,xpanel,10.20.1.46,duplicate mapping
CSV

if output="$("$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$DUPLICATE_CSV" 2>&1)"; then
  echo "Expected duplicate room/device mapping validation to fail." >&2
  exit 1
fi
if ! grep -q "duplicate room/device mapping" <<<"$output"; then
  echo "Duplicate validation failed with an unexpected message: $output" >&2
  exit 1
fi

PUBLIC_CSV="$TMP_DIR/hardware_ips.public.csv"
cat >"$PUBLIC_CSV" <<'CSV'
room_id,device_type,ip_address,notes
corvallis-kad-101,xpanel,8.8.8.8,public address should require review
CSV

if output="$("$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$PUBLIC_CSV" 2>&1)"; then
  echo "Expected public IP validation to fail." >&2
  exit 1
fi
if ! grep -q "public IP address" <<<"$output"; then
  echo "Public IP validation failed with an unexpected message: $output" >&2
  exit 1
fi
if grep -q "8.8.8.8" <<<"$output"; then
  echo "Public IP validation leaked the raw IP address." >&2
  exit 1
fi

if [ -f "$REAL_CSV" ]; then
  "$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$REAL_CSV"
else
  echo "No real api/hardware_ips.csv present; sample validation only."
fi
