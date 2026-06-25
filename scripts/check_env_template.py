#!/usr/bin/env python3
"""Validate that api/.env.example documents BeaverView runtime env vars."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / "api" / ".env.example"
SCAN_PATHS = [
    ROOT / "api" / "main.py",
    ROOT / "api" / "migrate_data.py",
    ROOT / "api" / "connectors" / "chat.py",
    ROOT / "api" / "connectors" / "servicenow.py",
    ROOT / "scripts" / "check_first_live_room_preflight.py",
    ROOT / "scripts" / "check_pilot_readiness.py",
]

ENV_LOOKUP_RE = re.compile(
    r"(?:os\.getenv|os\.environ\.get|env\.get)\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]"
)
ENV_ASSIGNMENT_RE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)\s*=")

# Backward-compatible aliases accepted by code but intentionally omitted from
# the canonical template so new deployments use the current SN_* names.
ALLOWED_CODE_ONLY = {
    "BEAVERVIEW_PILOT_READINESS_REEXEC",
    "BEAVERVIEW_FIRST_ROOM_PREFLIGHT_REEXEC",
    "BEAVERVIEW_DB_PATH",
    "SERVICENOW_INSTANCE",
    "SERVICENOW_CLIENT_ID",
    "SERVICENOW_CLIENT_SECRET",
}

ALLOWED_DOCUMENTATION_ONLY: set[str] = set()


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def keys_used_by_code() -> set[str]:
    used: set[str] = set()
    for path in SCAN_PATHS:
        if not path.exists():
            fail(f"expected scan target is missing: {path.relative_to(ROOT)}")
        used.update(ENV_LOOKUP_RE.findall(path.read_text()))
    return used


def keys_documented_in_template() -> tuple[set[str], list[str]]:
    if not ENV_EXAMPLE.exists():
        fail("api/.env.example is missing")

    keys: set[str] = set()
    duplicates: list[str] = []
    for line in ENV_EXAMPLE.read_text().splitlines():
        match = ENV_ASSIGNMENT_RE.match(line)
        if not match:
            continue
        key = match.group(1)
        if key in keys:
            duplicates.append(key)
        keys.add(key)
    return keys, duplicates


def main() -> int:
    used = keys_used_by_code()
    documented, duplicates = keys_documented_in_template()

    missing = sorted(used - documented - ALLOWED_CODE_ONLY)
    stale = sorted(documented - used - ALLOWED_DOCUMENTATION_ONLY)

    if duplicates:
        fail("duplicate keys in api/.env.example: " + ", ".join(sorted(set(duplicates))))
    if missing:
        fail("env vars used by code but missing from api/.env.example: " + ", ".join(missing))
    if stale:
        fail("env vars documented but not used by code/readiness: " + ", ".join(stale))

    print(f"Environment template verified: {len(documented)} keys documented")
    return 0


if __name__ == "__main__":
    sys.exit(main())
