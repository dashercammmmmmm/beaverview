#!/usr/bin/env python3
"""Validate selected first live-room prerequisites without printing secrets or raw IPs."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
DB_PATH = Path(os.environ.get("BEAVERVIEW_DB_PATH", API_DIR / "beaverview.db"))
ENV_PATH = API_DIR / ".env"
VENV_PYTHON = API_DIR / "venv" / "bin" / "python"

if (
    VENV_PYTHON.exists()
    and Path(sys.executable).resolve() != VENV_PYTHON.resolve()
    and os.environ.get("BEAVERVIEW_FIRST_ROOM_PREFLIGHT_REEXEC") != "1"
):
    env = os.environ.copy()
    env["BEAVERVIEW_FIRST_ROOM_PREFLIGHT_REEXEC"] = "1"
    os.execve(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], env)


CONNECTORS: dict[str, dict[str, Any]] = {
    "xpanel": {
        "label": "XPanel proxy",
        "device_type": "xpanel",
        "env_any": [("CRESTRON_PROXY_USERNAME", "CRESTRON_PROXY_PASSWORD")],
    },
    "crestron_poll": {
        "label": "Crestron processor polling",
        "device_type": "xpanel",
        "env_any": [("CRESTRON_POLL_USERNAME", "CRESTRON_POLL_PASSWORD")],
    },
    "wattbox": {
        "label": "WattBox direct proxy",
        "device_type": "wattbox",
        "env_any": [("WATTBOX_DIRECT_USERNAME", "WATTBOX_DIRECT_PASSWORD")],
    },
    "ptz": {
        "label": "PTZ proxy",
        "device_type": "ptz",
        "env_any": [("PTZ_PROXY_USERNAME", "PTZ_PROXY_PASSWORD")],
    },
    "25live": {
        "label": "25Live schedule",
        "env_any": [("LIVE25_BASE_URL", "LIVE25_USERNAME", "LIVE25_PASSWORD")],
    },
    "screenconnect": {
        "label": "ScreenConnect launch",
        "room_flag": "screenconnect",
        "env_any": [("SC_BASE_URL",)],
    },
    "sharepoint": {
        "label": "SharePoint launch",
        "env_any": [("SHAREPOINT_BASE_URL",)],
    },
    "servicenow": {
        "label": "ServiceNow incident create",
        "env_any": [
            ("SN_INSTANCE", "SN_CLIENT_ID", "SN_CLIENT_SECRET"),
            ("SN_INSTANCE", "SN_USERNAME", "SN_PASSWORD"),
        ],
    },
}


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    for key, value in os.environ.items():
        if key.isupper():
            values[key] = value
    return values


def is_configured(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.strip().lower()
    if not lowered:
        return False
    placeholder_markers = (
        "your-",
        "your_",
        "<",
        ">",
        "object-id",
        "tenant-id",
        "client-id",
        "client-secret",
        "change-me",
    )
    return not any(marker in lowered for marker in placeholder_markers)


def has_key_set(env: dict[str, str], keys: tuple[str, ...]) -> bool:
    return all(is_configured(env.get(key)) for key in keys)


def emit(status: str, message: str, *, details: dict[str, Any] | None = None, as_json: bool = False) -> int:
    code = 0 if status == "pass" else 2 if status == "pending" else 1
    if as_json:
        print(json.dumps({"status": status, "message": message, "details": details or {}}, indent=2, sort_keys=True))
    else:
        print(f"{status.upper()} {message}")
    return code


def normalize_connector(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    aliases = {
        "live25": "25live",
        "25_live": "25live",
        "crestron": "crestron_poll",
        "crestron_polling": "crestron_poll",
        "service_now": "servicenow",
    }
    return aliases.get(normalized, normalized)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check first live-room connector prerequisites.")
    parser.add_argument("--room-id", help="selected BeaverView room ID, e.g. corvallis-kad-101")
    parser.add_argument("--connector", help="first connector to validate, e.g. xpanel, ptz, 25live")
    parser.add_argument("--json", action="store_true", help="print machine-readable result")
    args = parser.parse_args()

    env = parse_env(ENV_PATH)
    room_id = (args.room_id or env.get("FIRST_LIVE_ROOM_ID", "")).strip().lower()
    connector = normalize_connector(args.connector or env.get("FIRST_LIVE_CONNECTOR", ""))

    if not room_id or not connector:
        return emit(
            "pending",
            "first live-room target is not selected; set FIRST_LIVE_ROOM_ID and FIRST_LIVE_CONNECTOR in api/.env",
            as_json=args.json,
        )
    if connector not in CONNECTORS:
        return emit(
            "fail",
            f"unknown FIRST_LIVE_CONNECTOR '{connector}'",
            details={"allowed_connectors": sorted(CONNECTORS)},
            as_json=args.json,
        )
    if not DB_PATH.exists():
        return emit("fail", "api/beaverview.db is missing; run scripts/check_data_migration.sh", as_json=args.json)

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        room = con.execute(
            "SELECT id, screenconnect FROM rooms WHERE id=?",
            (room_id,),
        ).fetchone()
        if not room:
            return emit("fail", f"selected first live-room ID is not in SQLite inventory: {room_id}", as_json=args.json)

        config = CONNECTORS[connector]
        device_type = config.get("device_type")
        if device_type:
            count = con.execute(
                "SELECT COUNT(*) FROM device_ips WHERE room_id=? AND device_type=?",
                (room_id, device_type),
            ).fetchone()[0]
            if count == 0:
                return emit(
                    "pending",
                    f"selected room has no {device_type} Hardware IP record loaded",
                    details={"room_id": room_id, "connector": connector, "device_type": device_type},
                    as_json=args.json,
                )
            if count > 1:
                return emit(
                    "fail",
                    f"selected room has multiple {device_type} Hardware IP records; re-run import validation",
                    details={"room_id": room_id, "connector": connector, "device_type": device_type},
                    as_json=args.json,
                )

        room_flag = config.get("room_flag")
        if room_flag and not bool(room[room_flag]):
            return emit(
                "pending",
                f"selected room is not marked for {config['label']}",
                details={"room_id": room_id, "connector": connector},
                as_json=args.json,
            )
    finally:
        con.close()

    if not any(has_key_set(env, keys) for keys in CONNECTORS[connector]["env_any"]):
        return emit(
            "pending",
            f"{CONNECTORS[connector]['label']} prerequisites are not configured in api/.env",
            details={"room_id": room_id, "connector": connector},
            as_json=args.json,
        )

    return emit(
        "pass",
        f"first live-room preflight passed for {room_id} using {CONNECTORS[connector]['label']}",
        details={"room_id": room_id, "connector": connector},
        as_json=args.json,
    )


if __name__ == "__main__":
    sys.exit(main())
