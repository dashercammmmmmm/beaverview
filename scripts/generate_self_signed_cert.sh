#!/usr/bin/env bash
# Generate BeaverView's self-signed TLS certificate with a validated VM IP.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: scripts/generate_self_signed_cert.sh [--force] <vm-ip> [output-dir] [dns-name]

Defaults:
  output-dir  /etc/ssl/beaverview
  dns-name    beaverview
EOF
}

FORCE=0
if [ "${1:-}" = "--force" ]; then
  FORCE=1
  shift
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
  usage
  exit 2
fi

VM_IP="$1"
OUTPUT_DIR="${2:-/etc/ssl/beaverview}"
DNS_NAME="${3:-beaverview}"
KEY_PATH="$OUTPUT_DIR/beaverview.key"
CRT_PATH="$OUTPUT_DIR/beaverview.crt"

if ! command -v openssl >/dev/null 2>&1; then
  echo "Missing required command: openssl" >&2
  exit 1
fi

python3 - "$VM_IP" "$DNS_NAME" <<'PY'
import ipaddress
import re
import sys

ip = sys.argv[1]
dns = sys.argv[2]

try:
    ipaddress.IPv4Address(ip)
except ValueError:
    print(f"Invalid IPv4 VM IP address: {ip}", file=sys.stderr)
    raise SystemExit(1)

if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,251}[A-Za-z0-9]", dns):
    print(f"Invalid DNS name: {dns}", file=sys.stderr)
    raise SystemExit(1)
PY

mkdir -p "$OUTPUT_DIR"

if [ "$FORCE" -ne 1 ] && { [ -e "$KEY_PATH" ] || [ -e "$CRT_PATH" ]; }; then
  echo "Certificate files already exist in $OUTPUT_DIR; rerun with --force to replace them." >&2
  exit 1
fi

TMP_KEY="$OUTPUT_DIR/.beaverview.key.$$"
TMP_CRT="$OUTPUT_DIR/.beaverview.crt.$$"
trap 'rm -f "$TMP_KEY" "$TMP_CRT"' EXIT

openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout "$TMP_KEY" \
  -out "$TMP_CRT" \
  -subj "/CN=$DNS_NAME" \
  -addext "subjectAltName=DNS:$DNS_NAME,IP:$VM_IP" >/dev/null 2>&1

chmod 600 "$TMP_KEY"
chmod 644 "$TMP_CRT"
mv "$TMP_KEY" "$KEY_PATH"
mv "$TMP_CRT" "$CRT_PATH"
trap - EXIT

echo "Generated certificate: $CRT_PATH"
echo "Generated private key: $KEY_PATH"
