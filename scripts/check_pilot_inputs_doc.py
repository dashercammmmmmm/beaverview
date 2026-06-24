#!/usr/bin/env python3
"""Validate the pilot input checklist covers readiness prerequisites."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs" / "examples" / "pilot-inputs-checklist.md"

REQUIRED_TERMS = (
    "api/.env",
    "api/hardware_ips.csv",
    "python3 scripts/check_pilot_readiness.py",
    "bash scripts/init_local_env.sh",
    "PROXY_SECRET",
    "SESSION_SECRET_KEY",
    "BEAVERVIEW_CORS_ORIGINS",
    "room_id",
    "device_type",
    "ip_address",
    "xpanel",
    "wattbox",
    "ptz",
    "FIRST_LIVE_ROOM_ID",
    "FIRST_LIVE_CONNECTOR",
    "scripts/check_first_live_room_preflight.py",
    "--list-candidates",
    "scripts/check_first_live_room_preflight_cases.py",
    "scripts/check_readiness_actions.py",
    "crestron_poll",
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_REDIRECT_URI",
    "https://beaverview/auth/callback",
    "AZURE_GROUP_TECHNICIAN",
    "AZURE_GROUP_ADMIN",
    "CRESTRON_POLL_USERNAME",
    "CRESTRON_POLL_PASSWORD",
    "CRESTRON_PROXY_USERNAME",
    "CRESTRON_PROXY_PASSWORD",
    "SC_BASE_URL",
    "WATTBOX_DIRECT_USERNAME",
    "WATTBOX_DIRECT_PASSWORD",
    "PTZ_PROXY_USERNAME",
    "PTZ_PROXY_PASSWORD",
    "LIVE25_BASE_URL",
    "LIVE25_USERNAME",
    "LIVE25_PASSWORD",
    "SHAREPOINT_BASE_URL",
    "CHAT_BASE_URL",
    "SN_INSTANCE",
    "SN_CLIENT_ID",
    "SN_CLIENT_SECRET",
    "SN_USERNAME",
    "SN_PASSWORD",
    "docs/examples/first-live-room-validation.md",
    "python3 scripts/check_live_validation_doc.py",
)


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    if not CHECKLIST.exists():
        fail("pilot input checklist is missing")

    text = CHECKLIST.read_text()
    missing = [term for term in REQUIRED_TERMS if term not in text]
    if missing:
        fail("pilot input checklist is missing terms: " + ", ".join(missing))

    print(f"Pilot input checklist verified: {len(REQUIRED_TERMS)} terms covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
