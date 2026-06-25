#!/usr/bin/env bash
# Validate the documented Hardware IP CSV shape without importing real data.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT/api"
SAMPLE="$ROOT/docs/examples/hardware_ips.sample.csv"
REAL_CSV="$API_DIR/hardware_ips.csv"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

assert_no_raw_ip_output() {
  local output="$1"
  local context="$2"
  if grep -Eq '([0-9]{1,3}\.){3}[0-9]{1,3}' <<<"$output"; then
    echo "$context leaked a raw IP address." >&2
    exit 1
  fi
}

if [ ! -x "$API_DIR/venv/bin/python" ]; then
  echo "Missing api/venv. Create it with: cd api && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

cd "$API_DIR"
"$API_DIR/venv/bin/python" migrate_data.py >/tmp/beaverview-migrate-for-hardware-check.log
if ! output="$("$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$SAMPLE" 2>&1)"; then
  echo "$output" >&2
  exit 1
fi
assert_no_raw_ip_output "$output" "Sample Hardware IP dry-run"
echo "$output"

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
assert_no_raw_ip_output "$output" "Duplicate Hardware IP validation"

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
assert_no_raw_ip_output "$output" "Public Hardware IP validation"

UNKNOWN_ROOM_CSV="$TMP_DIR/hardware_ips.unknown-room.csv"
cat >"$UNKNOWN_ROOM_CSV" <<'CSV'
room_id,device_type,ip_address,notes
corvallis-kad-999,xpanel,10.20.1.47,room is not in seeded inventory
CSV

if output="$("$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$UNKNOWN_ROOM_CSV" 2>&1)"; then
  echo "Expected unknown room_id validation to fail." >&2
  exit 1
fi
if ! grep -q "unknown room_id" <<<"$output"; then
  echo "Unknown room validation failed with an unexpected message: $output" >&2
  exit 1
fi
assert_no_raw_ip_output "$output" "Unknown-room Hardware IP validation"

MISSING_COLUMN_CSV="$TMP_DIR/hardware_ips.missing-column.csv"
cat >"$MISSING_COLUMN_CSV" <<'CSV'
room_id,device_type,notes
corvallis-kad-101,xpanel,missing IP column
CSV

if output="$("$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$MISSING_COLUMN_CSV" 2>&1)"; then
  echo "Expected missing column validation to fail." >&2
  exit 1
fi
if ! grep -q "CSV missing required columns: ip_address" <<<"$output"; then
  echo "Missing column validation failed with an unexpected message: $output" >&2
  exit 1
fi
assert_no_raw_ip_output "$output" "Missing-column Hardware IP validation"

BLANK_FIELD_CSV="$TMP_DIR/hardware_ips.blank-field.csv"
cat >"$BLANK_FIELD_CSV" <<'CSV'
room_id,device_type,ip_address,notes
corvallis-kad-101,,10.20.1.48,blank device type
CSV

if output="$("$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$BLANK_FIELD_CSV" 2>&1)"; then
  echo "Expected blank field validation to fail." >&2
  exit 1
fi
if ! grep -q "missing required field(s): device_type" <<<"$output"; then
  echo "Blank field validation failed with an unexpected message: $output" >&2
  exit 1
fi
assert_no_raw_ip_output "$output" "Blank-field Hardware IP validation"

INVALID_IP_CSV="$TMP_DIR/hardware_ips.invalid-ip.csv"
cat >"$INVALID_IP_CSV" <<'CSV'
room_id,device_type,ip_address,notes
corvallis-kad-101,xpanel,999.20.1.49,invalid IP should fail by row only
CSV

if output="$("$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$INVALID_IP_CSV" 2>&1)"; then
  echo "Expected invalid IP validation to fail." >&2
  exit 1
fi
if ! grep -q "invalid IP address in CSV row" <<<"$output"; then
  echo "Invalid IP validation failed with an unexpected message: $output" >&2
  exit 1
fi
assert_no_raw_ip_output "$output" "Invalid Hardware IP validation"

if [ -f "$REAL_CSV" ]; then
  if ! output="$("$API_DIR/venv/bin/python" import_device_ips.py --dry-run "$REAL_CSV" 2>&1)"; then
    assert_no_raw_ip_output "$output" "Real Hardware IP dry-run failure"
    echo "$output" >&2
    exit 1
  fi
  assert_no_raw_ip_output "$output" "Real Hardware IP dry-run"
  echo "$output"
else
  echo "No real api/hardware_ips.csv present; sample validation only."
fi
