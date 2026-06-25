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

from first_live_connectors import normalize_connector
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


def load_json_snapshot(path: str, label: str) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        payload = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "unavailable",
            "error": f"could not read {label} JSON: {exc}",
        }
    return payload if isinstance(payload, dict) else {"status": "unavailable", "error": f"{label} JSON is not an object"}


def load_readiness_snapshot(path: str) -> dict[str, Any] | None:
    return load_json_snapshot(path, "readiness")


def load_candidates_snapshot(path: str) -> dict[str, Any] | None:
    return load_json_snapshot(path, "candidate")


def readiness_lines(snapshot: dict[str, Any] | None) -> list[str]:
    if snapshot is None:
        return [
            "## Readiness Snapshot",
            "",
            "- Readiness JSON: `not attached`",
            "- Attach one with `python3 scripts/check_pilot_readiness.py --json > /tmp/beaverview-readiness.json` and `scripts/render_first_live_room_report.py --readiness-json /tmp/beaverview-readiness.json`.",
        ]

    lines = [
        "## Readiness Snapshot",
        "",
        f"- Status: {code(snapshot.get('status'), 'unknown')}",
        f"- Passed checks: {code(snapshot.get('passed_count'), 'unknown')}",
        f"- Local failures: {code(snapshot.get('failure_count'), 'unknown')}",
        f"- Pending external prerequisites: {code(snapshot.get('pending_count'), 'unknown')}",
    ]
    if snapshot.get("error"):
        lines.append(f"- Readiness JSON error: {safe_text(snapshot.get('error'), 'unknown error')}")

    pending_items = snapshot.get("pending")
    if isinstance(pending_items, list):
        lines.extend(["", "Pending external prerequisites:"])
        if pending_items:
            lines.extend(f"- {safe_text(item, 'unknown pending item')}" for item in pending_items)
        else:
            lines.append("- None")

    pending_actions = snapshot.get("pending_actions")
    if isinstance(pending_actions, list):
        lines.extend(["", "Pending next actions:"])
        if not pending_actions:
            lines.append("- None")
        for item in pending_actions:
            if not isinstance(item, dict):
                continue
            pending = safe_text(item.get("pending"), "unknown pending item")
            action = safe_text(item.get("action"), "review the pilot input checklist")
            reference = safe_text(item.get("reference"), "docs/examples/pilot-inputs-checklist.md")
            lines.append(f"- {pending}: {action} See `{reference}`.")
    return lines


def candidate_lines(snapshot: dict[str, Any] | None) -> list[str]:
    if snapshot is None:
        return [
            "## Candidate Snapshot",
            "",
            "- Candidate JSON: `not attached`",
            "- Attach one with `scripts/check_first_live_room_preflight.py --list-candidates --json > /tmp/beaverview-candidates.json` and `scripts/render_first_live_room_report.py --candidates-json /tmp/beaverview-candidates.json`.",
        ]

    lines = [
        "## Candidate Snapshot",
        "",
        f"- Status: {code(snapshot.get('status'), 'unknown')}",
        f"- Connector filter: {code(snapshot.get('connector_filter'), 'none')}",
        f"- Hardware source: {code(snapshot.get('hardware_source'), 'unknown')}",
        f"- Candidate count: {code(snapshot.get('count'), 'unknown')}",
    ]
    if snapshot.get("error"):
        lines.append(f"- Candidate JSON error: {safe_text(snapshot.get('error'), 'unknown error')}")

    candidates = snapshot.get("candidates")
    if isinstance(candidates, list):
        lines.extend(["", "Candidates:"])
        if not candidates:
            lines.append("- None")
        for item in candidates[:8]:
            if not isinstance(item, dict):
                continue
            connectors = item.get("eligible_connectors") if isinstance(item.get("eligible_connectors"), list) else []
            device_types = item.get("hardware_ip_device_types") if isinstance(item.get("hardware_ip_device_types"), list) else []
            lines.append(
                "- "
                f"{safe_text(item.get('room_id'), 'unknown room')} "
                f"({safe_text(item.get('building_code'), 'unknown building')} "
                f"{safe_text(item.get('room_number'), 'unknown room number')}): "
                f"{safe_text(item.get('status'), 'unknown status')}, "
                f"health {safe_text(item.get('health'), 'unknown')}, "
                f"connectors {safe_text(', '.join(str(value) for value in connectors), 'none')}, "
                f"device types {safe_text(', '.join(str(value) for value in device_types), 'none')}"
            )
    return lines


def readiness_is_pass(snapshot: dict[str, Any] | None) -> bool:
    if snapshot is None:
        return False
    if snapshot.get("status") != "pass":
        return False
    try:
        return int(snapshot.get("failure_count", 1)) == 0
    except (TypeError, ValueError):
        return False


def candidate_matches_selection(snapshot: dict[str, Any] | None, selected_room: str, selected_connector: str) -> bool:
    if snapshot is None:
        return False
    if snapshot.get("status") != "pass":
        return False
    candidates = snapshot.get("candidates")
    if not isinstance(candidates, list):
        return False

    normalized_room = selected_room.strip().lower()
    normalized_connector = normalize_connector(selected_connector)
    for item in candidates:
        if not isinstance(item, dict):
            continue
        if str(item.get("room_id", "")).strip().lower() != normalized_room:
            continue
        connectors = item.get("eligible_connectors")
        if normalized_connector and isinstance(connectors, list):
            return normalized_connector in {str(value).strip().lower() for value in connectors}
        return True
    return False


def candidate_filter_matches_selection(snapshot: dict[str, Any] | None, selected_connector: str) -> bool:
    if snapshot is None:
        return False
    connector_filter = normalize_connector(snapshot.get("connector_filter"))
    if not connector_filter:
        return True
    selected = normalize_connector(selected_connector)
    return bool(selected) and connector_filter == selected


def decision_lines(
    preflight: dict[str, Any],
    readiness_snapshot: dict[str, Any] | None,
    candidates_snapshot: dict[str, Any] | None,
    selected_room: str,
    selected_connector: str,
) -> list[str]:
    reasons: list[str] = []
    if preflight.get("status") != "pass":
        reasons.append(f"selected-room preflight is {safe_text(preflight.get('status'), 'unknown')}")
    if readiness_snapshot is None:
        reasons.append("readiness JSON snapshot is not attached")
    elif not readiness_is_pass(readiness_snapshot):
        reasons.append(
            "pilot readiness is "
            f"{safe_text(readiness_snapshot.get('status'), 'unknown')} with "
            f"{safe_text(readiness_snapshot.get('failure_count'), 'unknown')} local failure(s)"
        )
    if candidates_snapshot is None:
        reasons.append("candidate JSON snapshot is not attached")
    elif not candidate_filter_matches_selection(candidates_snapshot, selected_connector):
        reasons.append("candidate snapshot connector filter does not match the selected connector")
    elif not candidate_matches_selection(candidates_snapshot, selected_room, selected_connector):
        reasons.append("selected room and connector are not present in the candidate snapshot")

    if reasons:
        return [
            "## Decision",
            "",
            "- Go/no-go: `NO-GO`",
            *[f"- Reason: {reason}" for reason in reasons],
        ]
    return [
        "## Decision",
        "",
        "- Go/no-go: `GO FOR FIRST CONNECTOR VALIDATION`",
        "- Reason: selected-room preflight is `pass`, pilot readiness has zero local failures, and the selected room/connector appears in the candidate snapshot.",
    ]


def render_report(room_id: str, connector: str, readiness_json: str = "", candidates_json: str = "") -> str:
    preflight_exit, preflight = run_preflight(room_id, connector)
    readiness_snapshot = load_readiness_snapshot(readiness_json)
    candidates_snapshot = load_candidates_snapshot(candidates_json)
    details = preflight.get("details") if isinstance(preflight.get("details"), dict) else {}
    selected_room = room_id or details.get("room_id") or "not selected"
    selected_connector = normalize_connector(connector or details.get("connector")) or "not selected"
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
        *candidate_lines(candidates_snapshot),
        "",
        "## Preflight Result",
        "",
        f"- Preflight status: {code(preflight.get('status'), 'unknown')}",
        f"- Preflight exit code: {code(preflight_exit, 'unknown')}",
        f"- Message: {safe_text(preflight.get('message'), 'no message returned')}",
        "",
        *readiness_lines(readiness_snapshot),
        "",
        *decision_lines(preflight, readiness_snapshot, candidates_snapshot, str(selected_room), str(selected_connector)),
        "",
        "## Required Commands",
        "",
        "```bash",
        "python3 scripts/check_pilot_readiness.py --markdown",
        "python3 scripts/check_pilot_readiness.py --json > /tmp/beaverview-readiness.json",
        "scripts/check_hardware_ip_csv.py",
        "scripts/check_hardware_ip_import.sh",
        "(cd api && venv/bin/python import_device_ips.py hardware_ips.csv)",
        "scripts/check_first_live_room_preflight.py",
        "scripts/check_first_live_room_preflight.py --list-candidates --json > /tmp/beaverview-candidates.json",
        "scripts/render_first_live_room_report.py --readiness-json /tmp/beaverview-readiness.json --candidates-json /tmp/beaverview-candidates.json",
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
        "## Guardrails",
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
    parser.add_argument("--readiness-json", help="optional path to output from python3 scripts/check_pilot_readiness.py --json")
    parser.add_argument(
        "--candidates-json",
        help="optional path to output from scripts/check_first_live_room_preflight.py --list-candidates --json",
    )
    args = parser.parse_args()

    if not PREFLIGHT_SCRIPT.exists():
        print("FAIL first live-room preflight script is missing", file=sys.stderr)
        return 1

    print(render_report(args.room_id or "", args.connector or "", args.readiness_json or "", args.candidates_json or ""), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
