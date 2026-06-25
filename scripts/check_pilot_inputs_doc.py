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
    "api/hardware_ip_csv.py",
    "python3 scripts/check_pilot_readiness.py",
    "bash scripts/init_local_env.sh",
    "scripts/render_pilot_intake_packet.py",
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
    "scripts/check_hardware_ip_csv.py",
    "scripts/check_first_live_room_preflight.py",
    "scripts/render_first_live_room_report.py",
    "--candidates-json",
    "--readiness-json",
    "--list-candidates",
    "--connector",
    "--hardware-csv",
    "--list-candidates --connector xpanel --json > /tmp/beaverview-candidates.json",
    "Replace `xpanel` in the candidate JSON command with the selected `FIRST_LIVE_CONNECTOR`",
    "omit `--connector` only when intentionally comparing several possible first connectors",
    "import_device_ips.py",
    "For device-backed connectors",
    "Blank required fields",
    "Unknown room IDs",
    "valid IPv4",
    "Invalid, non-proxyable, or unreviewed public IP rows",
    "raw IP values",
    "scripts/check_first_live_room_preflight_cases.py",
    "scripts/check_first_live_room_report.py",
    "scripts/check_readiness_actions.py",
    "scripts/check_deployment_playbook.py",
    "scripts/check_inventory_parity.py",
    "scripts/check_dashboard_browser.sh",
    "scripts/check_admin_browser.sh",
    "scripts/check_init_local_env.py",
    "scripts/check_pilot_inputs_doc.py",
    "scripts/check_pilot_intake_packet.py",
    "scripts/check_playbook_html.py",
    "scripts/check_project_log.py",
    "scripts/check_sanitize_output.py",
    "scripts/check_readiness_env_prereqs.py",
    "scripts/check_readiness_output.py",
    "scripts/check_readiness_diagnostics.py",
    "scripts/check_production_safety.py",
    "scripts/check_first_live_connectors.py",
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
    "Must start with `https://`",
    "WATTBOX_DIRECT_USERNAME",
    "WATTBOX_DIRECT_PASSWORD",
    "PTZ_PROXY_USERNAME",
    "PTZ_PROXY_PASSWORD",
    "LIVE25_BASE_URL",
    "`LIVE25_BASE_URL` must start with `https://`",
    "LIVE25_USERNAME",
    "LIVE25_PASSWORD",
    "SHAREPOINT_BASE_URL",
    "CHAT_BASE_URL",
    "Must start with `http://` or `https://`",
    "Must include a host name",
    "SN_INSTANCE",
    "Host name only",
    "Do not include `https://` or a path",
    "SN_CLIENT_ID",
    "SN_CLIENT_SECRET",
    "SN_USERNAME",
    "SN_PASSWORD",
    "docs/examples/first-live-room-validation.md",
    "python3 scripts/check_live_validation_doc.py",
)

FINAL_VERIFICATION_COMMANDS = (
    "scripts/smoke_check.sh",
    "scripts/check_data_migration.sh",
    "scripts/check_hardware_ip_csv.py",
    "scripts/check_hardware_ip_import.sh",
    "scripts/check_deployment_assets.sh",
    "python3 scripts/check_deployment_playbook.py",
    "scripts/check_api_contracts.py",
    "python3 scripts/check_inventory_parity.py",
    "scripts/check_dashboard_browser.sh",
    "scripts/check_admin_browser.sh",
    "python3 scripts/check_env_template.py",
    "python3 scripts/check_init_local_env.py",
    "python3 scripts/check_pilot_inputs_doc.py",
    "python3 scripts/check_pilot_intake_packet.py",
    "python3 scripts/check_playbook_html.py",
    "python3 scripts/check_project_log.py",
    "python3 scripts/check_readiness_actions.py",
    "python3 scripts/check_readiness_env_prereqs.py",
    "python3 scripts/check_sanitize_output.py",
    "python3 scripts/check_readiness_output.py",
    "python3 scripts/check_readiness_diagnostics.py",
    "python3 scripts/check_production_safety.py",
    "python3 scripts/check_live_validation_doc.py",
    "python3 scripts/check_first_live_connectors.py",
    "scripts/check_first_live_room_preflight_cases.py",
    "scripts/check_first_live_room_report.py",
    "python3 scripts/check_pilot_readiness.py",
)


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect_order(text: str, first: str, second: str) -> None:
    first_index = text.find(first)
    second_index = text.find(second)
    if first_index == -1 or second_index == -1:
        missing = first if first_index == -1 else second
        fail(f"pilot input checklist is missing ordered term: {missing}")
    if first_index > second_index:
        fail(f"pilot input checklist must list {first!r} before {second!r}")


def section_between(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index == -1:
        fail(f"pilot input checklist is missing section: {start}")
    end_index = text.find(end, start_index + len(start))
    if end_index == -1:
        fail(f"pilot input checklist is missing section after {start}: {end}")
    return text[start_index:end_index]


def main() -> int:
    if not CHECKLIST.exists():
        fail("pilot input checklist is missing")

    text = CHECKLIST.read_text()
    missing = [term for term in REQUIRED_TERMS if term not in text]
    if missing:
        fail("pilot input checklist is missing terms: " + ", ".join(missing))
    hardware_section = section_between(text, "## Hardware IP Records", "## First Live-Room Target")
    first_live_section = section_between(text, "## First Live-Room Target", "## Azure / Entra App")
    final_section = section_between(text, "## Final Verification", "Expected result before external inputs are available:")
    expect_order(
        first_live_section,
        "scripts/check_hardware_ip_csv.py",
        "scripts/check_first_live_room_preflight.py --list-candidates --connector xpanel --hardware-csv api/hardware_ips.csv",
    )
    expect_order(
        first_live_section,
        "scripts/check_first_live_room_preflight.py",
        "scripts/check_first_live_room_preflight.py --list-candidates --connector xpanel --json > /tmp/beaverview-candidates.json",
    )
    expect_order(
        first_live_section,
        "scripts/check_first_live_room_preflight.py --list-candidates --connector xpanel --json > /tmp/beaverview-candidates.json",
        "scripts/render_first_live_room_report.py --readiness-json",
    )
    expect_order(
        hardware_section,
        "scripts/check_hardware_ip_csv.py",
        "scripts/check_hardware_ip_import.sh",
    )
    for previous, current in zip(FINAL_VERIFICATION_COMMANDS, FINAL_VERIFICATION_COMMANDS[1:]):
        expect_order(final_section, previous, current)

    print(f"Pilot input checklist verified: {len(REQUIRED_TERMS)} terms covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
