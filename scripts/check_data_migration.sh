#!/usr/bin/env bash
# Rebuild local SQLite inventory from dashboard/data.js and verify row counts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT/api"
DB_PATH="$API_DIR/beaverview.db"

if [ ! -x "$API_DIR/venv/bin/python" ]; then
  echo "Missing api/venv. Create it with: cd api && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

cd "$API_DIR"
"$API_DIR/venv/bin/python" migrate_data.py

campuses="$(sqlite3 "$DB_PATH" "select count(*) from campuses;")"
buildings="$(sqlite3 "$DB_PATH" "select count(*) from buildings;")"
rooms="$(sqlite3 "$DB_PATH" "select count(*) from rooms;")"
devices="$(sqlite3 "$DB_PATH" "select count(*) from devices;")"
bad_modes="$(sqlite3 "$DB_PATH" "select count(*) from connector_config where mode not in ('mock','live');")"

if [ "$campuses" -lt 1 ] || [ "$buildings" -lt 1 ] || [ "$rooms" -lt 1 ] || [ "$devices" -lt 1 ]; then
  echo "Migration produced incomplete inventory: campuses=$campuses buildings=$buildings rooms=$rooms devices=$devices" >&2
  exit 1
fi

if [ "$bad_modes" -ne 0 ]; then
  echo "Migration produced invalid connector modes: $bad_modes" >&2
  exit 1
fi

echo "Data migration verified: campuses=$campuses buildings=$buildings rooms=$rooms devices=$devices"
