#!/usr/bin/env python3
"""Validate the pilot intake packet renderer stays aligned and sanitized."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from render_pilot_intake_packet import CATEGORY_ORDER, render_packet


ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "scripts" / "check_pilot_readiness.py"
RAW_IP_SENTINEL = "10.77.1.25"
SECRET_SENTINEL = "super-secret-value"
TOKEN_SENTINEL = "abc.def.ghi"


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_readiness_module():
    os.environ["BEAVERVIEW_PILOT_READINESS_REEXEC"] = "1"
    spec = importlib.util.spec_from_file_location("check_pilot_readiness", READINESS)
    if spec is None or spec.loader is None:
        fail("could not load scripts/check_pilot_readiness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    readiness = load_readiness_module()
    actions = readiness.PENDING_ACTIONS
    expect(isinstance(actions, dict) and actions, "PENDING_ACTIONS must be a non-empty dict")

    pending_actions = []
    for pending, item in actions.items():
        pending_actions.append(
            {
                "pending": pending,
                "action": item["action"],
                "reference": item["reference"],
            }
        )
    pending_actions.append(
        {
            "pending": f"device at {RAW_IP_SENTINEL} needs CLIENT_SECRET={SECRET_SENTINEL}",
            "action": f"Use Authorization: Bearer {TOKEN_SENTINEL} with PASSWORD={SECRET_SENTINEL}",
            "reference": f"docs/examples/pilot-inputs-checklist.md#device-{RAW_IP_SENTINEL}",
        }
    )

    packet = render_packet(
        {
            "status": "pass",
            "passed_count": 34,
            "failure_count": 0,
            "pending_count": len(pending_actions),
            "pending_actions": pending_actions,
        }
    )

    required_terms = (
        "# BeaverView Pilot Intake Packet",
        "## Secure Handling",
        "## Requested Inputs",
        "## Verification After Inputs Arrive",
        "python3 scripts/check_pilot_readiness.py --markdown",
        "scripts/render_first_live_room_report.py --readiness-json /tmp/beaverview-readiness.json --candidates-json /tmp/beaverview-candidates.json",
    )
    for term in required_terms:
        expect(term in packet, f"pilot intake packet is missing term: {term}")
    for category in CATEGORY_ORDER:
        expect(f"### {category}" in packet, f"pilot intake packet is missing category: {category}")
    for pending in actions:
        expect(pending in packet, f"pilot intake packet is missing pending action: {pending}")
    for forbidden in (RAW_IP_SENTINEL, SECRET_SENTINEL, TOKEN_SENTINEL):
        expect(forbidden not in packet, f"pilot intake packet leaked {forbidden!r}: {packet}")
    expect("<redacted-ip>" in packet, "pilot intake packet should redact non-local IPs")
    expect("<redacted>" in packet, "pilot intake packet should redact secret-like values")

    print(f"Pilot intake packet verified: {len(actions)} readiness actions covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
