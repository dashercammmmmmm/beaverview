#!/usr/bin/env python3
"""Validate that the first live-room validation runbook covers pilot gates."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "examples" / "first-live-room-validation.md"

REQUIRED_TERMS = (
    "non-critical room",
    "api/.env",
    "FIRST_LIVE_ROOM_ID",
    "FIRST_LIVE_CONNECTOR",
    "api/hardware_ips.csv",
    "VLAN route",
    "python3 scripts/check_pilot_readiness.py",
    "scripts/check_hardware_ip_import.sh",
    "scripts/check_first_live_room_preflight.py",
    "scripts/render_first_live_room_report.py",
    "--candidates-json",
    "--readiness-json",
    "--list-candidates",
    "--connector",
    "--hardware-csv",
    "import_device_ips.py",
    "XPanel",
    "25Live",
    "ServiceNow",
    "ScreenConnect",
    "SharePoint",
    "PTZ",
    "WattBox/OvrC",
    "raw device IP",
    "admin audit log",
    "sanitized first live-room validation report",
    "connector mode back to `mock`",
    "No secret",
    "PROJECT-LOG.md",
)


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect_order(text: str, first: str, second: str) -> None:
    first_index = text.find(first)
    second_index = text.find(second)
    if first_index == -1 or second_index == -1:
        missing = first if first_index == -1 else second
        fail(f"first live-room validation runbook is missing ordered term: {missing}")
    if first_index > second_index:
        fail(f"first live-room validation runbook must list {first!r} before {second!r}")


def main() -> int:
    if not RUNBOOK.exists():
        fail("first live-room validation runbook is missing")

    text = RUNBOOK.read_text()
    missing = [term for term in REQUIRED_TERMS if term not in text]
    if missing:
        fail("first live-room validation runbook is missing terms: " + ", ".join(missing))
    expect_order(
        text,
        "scripts/check_hardware_ip_import.sh",
        "(cd api && venv/bin/python import_device_ips.py hardware_ips.csv)",
    )
    expect_order(
        text,
        "(cd api && venv/bin/python import_device_ips.py hardware_ips.csv)",
        "\nscripts/check_first_live_room_preflight.py\n",
    )
    expect_order(
        text,
        "\nscripts/check_first_live_room_preflight.py\n",
        "scripts/render_first_live_room_report.py --readiness-json",
    )

    print(f"First live-room validation runbook verified: {len(REQUIRED_TERMS)} terms covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
