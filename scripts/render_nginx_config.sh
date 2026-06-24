#!/usr/bin/env bash
# Render the nginx template with a validated IPv4 VM IP.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$ROOT/deploy/nginx/beaverview.conf.template"

usage() {
  echo "Usage: $0 <vm-ip> [output-path]" >&2
}

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage
  exit 2
fi

VM_IP="$1"
OUTPUT="${2:-}"

if [ ! -f "$TEMPLATE" ]; then
  echo "Missing nginx template: $TEMPLATE" >&2
  exit 1
fi

python3 - "$VM_IP" <<'PY'
import ipaddress
import sys

try:
    ipaddress.IPv4Address(sys.argv[1])
except ValueError:
    print(f"Invalid IPv4 VM IP address: {sys.argv[1]}", file=sys.stderr)
    raise SystemExit(1)
PY

if [ -n "$OUTPUT" ]; then
  sed "s/__VM_IP__/$VM_IP/g" "$TEMPLATE" > "$OUTPUT"
  if grep -q "__VM_IP__" "$OUTPUT"; then
    echo "Rendered nginx config still contains __VM_IP__" >&2
    exit 1
  fi
  echo "Rendered nginx config: $OUTPUT"
else
  sed "s/__VM_IP__/$VM_IP/g" "$TEMPLATE"
fi
