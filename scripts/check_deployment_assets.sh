#!/usr/bin/env bash
# Validate reusable deployment templates without requiring nginx/systemd locally.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE="$ROOT/deploy/systemd/beaverview.service"
NGINX="$ROOT/deploy/nginx/beaverview.conf.template"

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

echo "Deployment assets verified"
