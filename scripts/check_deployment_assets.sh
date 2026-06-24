#!/usr/bin/env bash
# Validate reusable deployment templates without requiring nginx/systemd locally.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE="$ROOT/deploy/systemd/beaverview.service"
NGINX="$ROOT/deploy/nginx/beaverview.conf.template"
RENDER="$ROOT/scripts/render_nginx_config.sh"
CERT="$ROOT/scripts/generate_self_signed_cert.sh"

fail() {
  echo "FAIL $*" >&2
  exit 1
}

require_file() {
  [ -f "$1" ] || fail "missing file: $1"
}

require_text() {
  local file="$1"
  local text="$2"
  grep -Fq "$text" "$file" || fail "missing '$text' in $file"
}

require_file "$SERVICE"
require_file "$NGINX"
require_file "$RENDER"
require_file "$CERT"

require_text "$SERVICE" "User=beaverview"
require_text "$SERVICE" "WorkingDirectory=/home/beaverview/app/api"
require_text "$SERVICE" "ExecStart=/home/beaverview/app/api/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000"
require_text "$SERVICE" "Restart=on-failure"
require_text "$SERVICE" "WantedBy=multi-user.target"

require_text "$NGINX" "server_name beaverview __VM_IP__;"
require_text "$NGINX" "listen 443 ssl;"
require_text "$NGINX" "ssl_certificate     /etc/ssl/beaverview/beaverview.crt;"
require_text "$NGINX" "ssl_certificate_key /etc/ssl/beaverview/beaverview.key;"
require_text "$NGINX" "add_header Strict-Transport-Security"
require_text "$NGINX" "add_header X-Frame-Options DENY always;"
require_text "$NGINX" "add_header X-Content-Type-Options nosniff always;"
require_text "$NGINX" "proxy_pass         http://127.0.0.1:8000;"
require_text "$NGINX" 'proxy_set_header   X-Forwarded-Proto $scheme;'

rendered="$(mktemp)"
cert_dir="$(mktemp -d)"
trap 'rm -f "$rendered"; rm -rf "$cert_dir"' EXIT
"$RENDER" "192.0.2.50" "$rendered" >/dev/null
require_text "$rendered" "server_name beaverview 192.0.2.50;"
if grep -Fq "__VM_IP__" "$rendered"; then
  fail "rendered nginx config still contains __VM_IP__"
fi

"$CERT" "192.0.2.50" "$cert_dir" >/dev/null
require_file "$cert_dir/beaverview.key"
require_file "$cert_dir/beaverview.crt"
cert_text="$(openssl x509 -in "$cert_dir/beaverview.crt" -noout -text)"
printf '%s\n' "$cert_text" | grep -Fq "DNS:beaverview" || fail "certificate missing DNS SAN"
printf '%s\n' "$cert_text" | grep -Fq "IP Address:192.0.2.50" || fail "certificate missing IP SAN"

echo "Deployment assets verified"
