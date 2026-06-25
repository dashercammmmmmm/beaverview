#!/usr/bin/env python3
"""Render a sanitized OSU pilot-input intake packet from readiness JSON."""

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
READINESS_SCRIPT = ROOT / "scripts" / "check_pilot_readiness.py"


CATEGORY_ORDER = (
    "Secure Room And Device Data",
    "Deployment Origin And Identity",
    "Connector Credentials",
    "Launch URLs And External Services",
)

INPUT_REQUIREMENTS = {
    "api/.env is not present; copy api/.env.example and fill deployment values": {
        "target": "ignored `api/.env`",
        "values": ("PROXY_SECRET", "SESSION_SECRET_KEY", "deployment-only values below"),
    },
    "PROXY_SECRET is not set": {
        "target": "ignored `api/.env`",
        "values": ("PROXY_SECRET",),
    },
    "SESSION_SECRET_KEY is not set": {
        "target": "ignored `api/.env`",
        "values": ("SESSION_SECRET_KEY",),
    },
    "CORS allowed origins are not restricted": {
        "target": "ignored `api/.env`",
        "values": ("BEAVERVIEW_CORS_ORIGINS",),
    },
    "hardware IP records are not loaded yet": {
        "target": "ignored `api/hardware_ips.csv`",
        "values": ("room_id", "device_type", "ip_address", "notes"),
    },
    "Azure redirect URI is not configured": {
        "target": "ignored `api/.env`",
        "values": ("AZURE_REDIRECT_URI",),
    },
    "Azure app credentials are not complete": {
        "target": "ignored `api/.env`",
        "values": ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_REDIRECT_URI"),
    },
    "Azure technician/admin group object IDs are not complete": {
        "target": "ignored `api/.env`",
        "values": ("AZURE_GROUP_TECHNICIAN", "AZURE_GROUP_ADMIN"),
    },
    "Crestron poll credentials are not complete": {
        "target": "ignored `api/.env`",
        "values": ("CRESTRON_POLL_USERNAME", "CRESTRON_POLL_PASSWORD"),
    },
    "XPanel proxy credentials are not complete": {
        "target": "ignored `api/.env`",
        "values": ("CRESTRON_PROXY_USERNAME", "CRESTRON_PROXY_PASSWORD", "CRESTRON_PROXY_SCHEME"),
    },
    "WattBox direct proxy credentials are not complete": {
        "target": "ignored `api/.env`",
        "values": ("WATTBOX_DIRECT_USERNAME", "WATTBOX_DIRECT_PASSWORD", "WATTBOX_PROXY_SCHEME"),
    },
    "PTZ proxy credentials are not complete": {
        "target": "ignored `api/.env`",
        "values": ("PTZ_PROXY_USERNAME", "PTZ_PROXY_PASSWORD", "PTZ_PROXY_SCHEME"),
    },
    "25Live credentials are not complete": {
        "target": "ignored `api/.env`",
        "values": ("LIVE25_BASE_URL", "LIVE25_USERNAME", "LIVE25_PASSWORD"),
    },
    "ScreenConnect base URL is not configured": {
        "target": "ignored `api/.env`",
        "values": ("SC_BASE_URL",),
    },
    "SharePoint base URL is not configured": {
        "target": "ignored `api/.env`",
        "values": ("SHAREPOINT_BASE_URL",),
    },
    "Hermes chat base URL is not configured": {
        "target": "ignored `api/.env`",
        "values": ("CHAT_BASE_URL",),
    },
    "ServiceNow credentials are not complete": {
        "target": "ignored `api/.env`",
        "values": ("SN_INSTANCE", "SN_CLIENT_ID + SN_CLIENT_SECRET or SN_USERNAME + SN_PASSWORD"),
    },
    "first live-room target and connector are not selected": {
        "target": "ignored `api/.env`",
        "values": ("FIRST_LIVE_ROOM_ID", "FIRST_LIVE_CONNECTOR"),
    },
}


def safe_text(value: Any, fallback: str = "not provided") -> str:
    if value is None:
        return fallback
    text = redact_line(str(value).strip())
    return text if text else fallback


def load_readiness(path: str) -> dict[str, Any]:
    if path:
        payload = json.loads(Path(path).read_text())
        if not isinstance(payload, dict):
            raise ValueError("readiness JSON must be an object")
        return payload

    result = subprocess.run(
        [sys.executable, str(READINESS_SCRIPT), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        stderr = redact_line(result.stderr.strip())
        raise ValueError(f"could not parse readiness JSON: {exc}; stderr={stderr}") from exc
    if not isinstance(payload, dict):
        raise ValueError("readiness JSON must be an object")
    return payload


def category_for(pending: str) -> str:
    lowered = pending.lower()
    if "hardware ip" in lowered or "first live-room" in lowered:
        return "Secure Room And Device Data"
    if "cors" in lowered or "azure" in lowered:
        return "Deployment Origin And Identity"
    if "crestron" in lowered or "xpanel" in lowered or "wattbox" in lowered or "ptz" in lowered or "25live" in lowered:
        return "Connector Credentials"
    return "Launch URLs And External Services"


def grouped_pending_actions(readiness: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {category: [] for category in CATEGORY_ORDER}
    actions = readiness.get("pending_actions")
    if not isinstance(actions, list):
        actions = []

    for item in actions:
        if not isinstance(item, dict):
            continue
        pending = safe_text(item.get("pending"), "unknown pending input")
        action = safe_text(item.get("action"), "review the pilot inputs checklist")
        reference = safe_text(item.get("reference"), "docs/examples/pilot-inputs-checklist.md")
        grouped.setdefault(category_for(pending), []).append(
            {
                "pending": pending,
                "action": action,
                "reference": reference,
            }
        )
    return grouped


def pending_input_requirements(readiness: dict[str, Any]) -> list[dict[str, str]]:
    actions = readiness.get("pending_actions")
    if not isinstance(actions, list):
        actions = []

    requirements: list[dict[str, str]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        pending = safe_text(item.get("pending"), "unknown pending input")
        requirement = INPUT_REQUIREMENTS.get(pending)
        if not requirement:
            continue
        values = ", ".join(safe_text(value) for value in requirement["values"])
        requirements.append(
            {
                "pending": pending,
                "target": safe_text(requirement["target"]),
                "values": values,
            }
        )
    return requirements


def render_packet(readiness: dict[str, Any]) -> str:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    grouped = grouped_pending_actions(readiness)
    requirements = pending_input_requirements(readiness)

    lines = [
        "# BeaverView Pilot Intake Packet",
        "",
        "Use this packet to collect the remaining external inputs for the first OSU pilot. Do not put completed secrets, raw device IPs, screenshots, ticket contents, or private URLs into Git.",
        "",
        "## Readiness Snapshot",
        "",
        f"- Generated at: `{safe_text(generated_at)}`",
        f"- Status: `{safe_text(readiness.get('status'), 'unknown')}`",
        f"- Passed checks: `{safe_text(readiness.get('passed_count'), 'unknown')}`",
        f"- Local failures: `{safe_text(readiness.get('failure_count'), 'unknown')}`",
        f"- Pending external prerequisites: `{safe_text(readiness.get('pending_count'), 'unknown')}`",
        "",
        "## Local Failures To Resolve First",
        "",
    ]

    failures = readiness.get("failures")
    if isinstance(failures, list) and failures:
        lines.extend(f"- {safe_text(item, 'unknown local failure')}" for item in failures)
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Secure Handling",
        "",
        "- Send secrets through the approved OSU secret channel, not chat, Git, screenshots, or shared notes.",
        "- Put deployment values only in ignored `api/.env` on the target host.",
        "- Put the secure Hardware IP export only at ignored `api/hardware_ips.csv`.",
        "- Share room selection and connector choice in plain text only after confirming the room is non-critical.",
        "",
        "## Requested Inputs",
        "",
    ])

    any_actions = False
    for category in CATEGORY_ORDER:
        items = grouped.get(category, [])
        lines.extend([f"### {category}", ""])
        if not items:
            lines.extend(["- None currently pending.", ""])
            continue
        any_actions = True
        for item in items:
            lines.append(f"- [ ] **{item['pending']}**")
            lines.append(f"  - Action: {item['action']}")
            lines.append(f"  - Reference: `{item['reference']}`")
        lines.append("")

    if not any_actions:
        lines.extend(["No external inputs are currently pending.", ""])

    lines.extend(["## Input Targets", ""])
    if requirements:
        lines.extend(
            [
                "| Pending prerequisite | Target | Values to provide |",
                "| --- | --- | --- |",
            ]
        )
        for item in requirements:
            lines.append(f"| {item['pending']} | {item['target']} | `{item['values']}` |")
        lines.append("")
    else:
        lines.extend(["No env or file inputs are currently pending.", ""])

    lines.extend(
        [
            "## Verification After Inputs Arrive",
            "",
            "```bash",
            "python3 scripts/check_pilot_readiness.py --markdown",
            "python3 scripts/check_pilot_readiness.py --json > /tmp/beaverview-readiness.json",
            "scripts/check_first_live_room_preflight.py --list-candidates --json > /tmp/beaverview-candidates.json",
            "scripts/render_first_live_room_report.py --readiness-json /tmp/beaverview-readiness.json --candidates-json /tmp/beaverview-candidates.json",
            "```",
            "",
            "Expected result: local failures remain zero, pending count drops as inputs are supplied, and first live-room preflight stays pending or pass until the selected connector is ready.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a sanitized BeaverView pilot-input intake packet.")
    parser.add_argument("--readiness-json", help="optional path to output from python3 scripts/check_pilot_readiness.py --json")
    args = parser.parse_args()

    try:
        readiness = load_readiness(args.readiness_json or "")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL {redact_line(str(exc))}", file=sys.stderr)
        return 1
    print(render_packet(readiness), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
