#!/usr/bin/env bash
# Validate the documented Hardware IP CSV shape without importing real data.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT/api"
SAMPLE="$ROOT/docs/examples/hardware_ips.sample.csv"
REAL_CSV="$API_DIR/hardware_ips.csv"

if [ ! -x "$API_DIR/venv/bin/python" ]; then
  echo "Missing api/venv. Create it with: cd api && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

cd "$API_DIR"
"$API_DIR/venv/bin/python" migrate_data.py >/tmp/beaverview-migrate-for-hardware-check.log
"$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$SAMPLE"

if [ -f "$REAL_CSV" ]; then
  "$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$REAL_CSV"
else
  echo "No real api/hardware_ips.csv present; sample validation only."
fi
