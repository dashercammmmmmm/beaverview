#!/bin/bash
# BeaverView API server startup script
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create venv if it doesn't exist
if [ ! -d "$SCRIPT_DIR/venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$SCRIPT_DIR/venv"
  "$SCRIPT_DIR/venv/bin/pip" install -q fastapi "uvicorn[standard]" python-dotenv
fi

echo "Starting BeaverView API on http://localhost:8000/"
echo "Dashboard: http://localhost:8000/"
echo "API docs:  http://localhost:8000/docs"
echo ""

cd "$SCRIPT_DIR"
exec venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --reload
