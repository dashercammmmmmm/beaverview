#!/usr/bin/env python3
"""Render a sanitized first live-room validation report template."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sanitize_output import redact_line


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SCRIPT = ROOT / "scripts" / "check_first_live_room_preflight.py"


def safe_text(value: Any, fallback: str = "not selected") -> str:
    text = redact_line(str(value or "").strip())
    return text if text else fallback


def code(value: Any, fallback: str = "not selected") -> str:
    text = safe_text(value, fallback).replace("`", "'")
    return f"`{text}`"


def run_preflight(room_id: str, connector: str) -> tuple[int, dict[str, Any]]:
    cmd = [sys.executable, str(PREFLIGHT_SCRIPT), "--json"]
    if room_id:
        cmd.extend(["--room-id", room_id])
    if connector:
        cmd.extend(["--connector", connector])

    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {
            "status": "fail",
            "message": "first live-room preflight did not return JSON",
            "details": {"stderr": redact_line(result.stderr.strip())},
        }
    return result.returncode, payload


def render_report(room_id: str, connector: str) -> str:
    preflight_exit, preflight = run_preflight(room_id, connector)
    details = preflight.get("details") if isinstance(preflight.get("details"), dict) else {}
    selected_room = room_id or details.get("room_id") or "not selected"
    selected_connector = connector or details.get("connector") or "not selected"
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    lines = [
        "# BeaverView First Live-Room Validation Report",
        "",
        "Use this as a private deployment note. Do not commit completed reports if they contain operational details, screenshots, ticket data, raw device IPs, or secrets.",
        "",
        "## Selection",
        "",
        f"- Generated at: {code(generated_at)}",
        f"- Room ID: {code(selected_room)}",
        f"- First connector: {code(selected_connector)}",
        "",
        "## Preflight Result",
        "",
        f"- Preflight status: {code(preflight.get('status'), 'unknown')}",
        f"- Preflight exit code: {code(preflight_exit, 'unknown')}",
        f"- Message: {safe_text(preflight.get('message'), 'no message returned')}",
        "",
        "## Required Commands",
        "",
        "```bash",
        "python3 scripts/check_pilot_readiness.py --markdown",
        "scripts/check_hardware_ip_import.sh",
        "scripts/check_first_live_room_preflight.py",
        "scripts/render_first_live_room_report.py",
        "```",
        "",
        "## Required Private Evidence",
        "",
        "- readiness report",
        "- first connector test result",
        "- admin audit log row",
        "- technician notes",
        "- screenshots with private details redacted",
        "",
        "## Go / No-Go",
        "",
        "- Go only if pilot readiness has zero local failures and the selected first connector preflight is `pass`.",
        "- Keep unselected connectors guarded or pending.",
        "- Do not expose raw device IPs in browser URLs, page text, network responses, committed files, or shared notes.",
        "- Roll back by setting connector mode back to `mock`, removing imported Hardware IP rows if needed, and restarting BeaverView.",
        "",
        "## Sanitized Project Log Summary",
        "",
        "After validation, update `PROJECT-LOG.md` with connector name, non-critical room class, and pass/fail outcome only.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a sanitized first live-room validation report template.")
    parser.add_argument("--room-id", help="selected BeaverView room ID; defaults to FIRST_LIVE_ROOM_ID in api/.env")
    parser.add_argument("--connector", help="selected first connector; defaults to FIRST_LIVE_CONNECTOR in api/.env")
    args = parser.parse_args()

    if not PREFLIGHT_SCRIPT.exists():
        print("FAIL first live-room preflight script is missing", file=sys.stderr)
        return 1

    print(render_report(args.room_id or "", args.connector or ""), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
