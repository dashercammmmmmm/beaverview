#!/usr/bin/env python3
"""Validate the pilot intake packet renderer stays aligned and sanitized."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from render_pilot_intake_packet import CATEGORY_ORDER, INPUT_REQUIREMENTS, render_packet


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
    expect(
        set(INPUT_REQUIREMENTS) == set(actions),
        "pilot intake input matrix must cover exactly the canonical readiness actions",
    )

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
            "failures": [],
            "pending_actions": pending_actions,
        }
    )

    required_terms = (
        "# BeaverView Pilot Intake Packet",
        "## Secure Handling",
        "## Local Failures To Resolve First",
        "## Requested Inputs",
        "## Input Targets",
        "## Verification After Inputs Arrive",
        "- Local failures: `0`",
        "- None",
        "| Pending prerequisite | Target | Values to provide |",
        "ignored `api/.env`",
        "ignored `api/hardware_ips.csv`",
        "`SN_INSTANCE, SN_CLIENT_ID + SN_CLIENT_SECRET or SN_USERNAME + SN_PASSWORD`",
        "python3 scripts/check_pilot_readiness.py --markdown",
        "scripts/render_first_live_room_report.py --readiness-json /tmp/beaverview-readiness.json --candidates-json /tmp/beaverview-candidates.json",
    )
    for term in required_terms:
        expect(term in packet, f"pilot intake packet is missing term: {term}")
    for category in CATEGORY_ORDER:
        expect(f"### {category}" in packet, f"pilot intake packet is missing category: {category}")
    for pending in actions:
        expect(pending in packet, f"pilot intake packet is missing pending action: {pending}")
        for value in INPUT_REQUIREMENTS[pending]["values"]:
            expect(value in packet, f"pilot intake packet is missing input target value: {value}")
    for forbidden in (RAW_IP_SENTINEL, SECRET_SENTINEL, TOKEN_SENTINEL):
        expect(forbidden not in packet, f"pilot intake packet leaked {forbidden!r}: {packet}")
    expect("<redacted-ip>" in packet, "pilot intake packet should redact non-local IPs")
    expect("<redacted>" in packet, "pilot intake packet should redact secret-like values")

    failure_packet = render_packet(
        {
            "status": "fail",
            "passed_count": 33,
            "failure_count": 1,
            "pending_count": 0,
            "failures": [f"validator reached {RAW_IP_SENTINEL} with PASSWORD={SECRET_SENTINEL}"],
            "pending_actions": [],
        }
    )
    expect("## Local Failures To Resolve First" in failure_packet, "local failure section is missing")
    expect("validator reached <redacted-ip> with PASSWORD=<redacted>" in failure_packet, "local failure was not redacted")
    for forbidden in (RAW_IP_SENTINEL, SECRET_SENTINEL):
        expect(forbidden not in failure_packet, f"local failure packet leaked {forbidden!r}: {failure_packet}")

    print(f"Pilot intake packet verified: {len(actions)} readiness actions covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
