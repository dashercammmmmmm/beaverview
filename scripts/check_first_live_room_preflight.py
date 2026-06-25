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

from first_live_connectors import normalize_connector
from sanitize_output import redact_line

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
DB_PATH = Path(os.environ.get("BEAVERVIEW_DB_PATH", API_DIR / "beaverview.db"))
ENV_PATH = API_DIR / ".env"
VENV_PYTHON = API_DIR / "venv" / "bin" / "python"

sys.path.insert(0, str(API_DIR))
from hardware_ip_csv import HardwareCsvError, load_hardware_rows, room_device_counts  # noqa: E402

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


def safe_text(value: Any) -> str:
    return redact_line(str(value))


def sanitized_json(value: Any) -> Any:
    if isinstance(value, str):
        return safe_text(value)
    if isinstance(value, list):
        return [sanitized_json(item) for item in value]
    if isinstance(value, dict):
        return {safe_text(key): sanitized_json(item) for key, item in value.items()}
    return value


def emit(status: str, message: str, *, details: dict[str, Any] | None = None, as_json: bool = False) -> int:
    code = 0 if status == "pass" else 2 if status == "pending" else 1
    payload = {
        "status": status,
        "message": safe_text(message),
        "details": sanitized_json(details or {}),
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{status.upper()} {payload['message']}")
    return code


def table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def device_ip_counts(con: sqlite3.Connection) -> dict[str, dict[str, int]]:
    if not table_exists(con, "device_ips"):
        return {}
    rows = con.execute(
        "SELECT room_id, device_type, COUNT(*) AS count FROM device_ips GROUP BY room_id, device_type"
    ).fetchall()
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        counts.setdefault(row["room_id"], {})[row["device_type"]] = int(row["count"])
    return counts


def hardware_csv_device_counts(path: Path) -> dict[str, dict[str, int]]:
    try:
        return room_device_counts(load_hardware_rows(path))
    except HardwareCsvError as exc:
        raise ValueError(f"hardware CSV {exc}") from exc


def connector_hints(room: sqlite3.Row, counts: dict[str, int]) -> list[str]:
    connectors = ["25live", "servicenow", "sharepoint"]
    if bool(room["screenconnect"]):
        connectors.append("screenconnect")
    if counts.get("xpanel") == 1:
        connectors.extend(["xpanel", "crestron_poll"])
    if counts.get("wattbox") == 1 and bool(room["wattbox"]):
        connectors.append("wattbox")
    if counts.get("ptz") == 1:
        connectors.append("ptz")
    return connectors


def is_non_critical_candidate(room: sqlite3.Row) -> bool:
    return non_critical_blocker(room) is None


def non_critical_blocker(room: sqlite3.Row) -> str | None:
    status = str(room["status"] or "").lower()
    room_type = str(room["type"] or "").lower()
    room_id = str(room["id"] or "").lower()
    health = int(room["health"] or 0)
    if status in {"in-use", "offline"}:
        return f"selected room is not a non-critical candidate: status is {status}"
    if health <= 0:
        return "selected room is not a non-critical candidate: health is not positive"
    if "placeholder" in room_type or room_id.endswith("-tbd"):
        return "selected room is not a non-critical candidate: placeholder inventory"
    return None


def list_candidates(
    *,
    as_json: bool = False,
    limit: int = 12,
    connector: str = "",
    hardware_csv: str = "",
) -> int:
    if not DB_PATH.exists():
        return emit("fail", "api/beaverview.db is missing; run scripts/check_data_migration.sh", as_json=as_json)
    connector_filter = normalize_connector(connector) if connector else ""
    if connector_filter and connector_filter not in CONNECTORS:
        return emit(
            "fail",
            f"unknown FIRST_LIVE_CONNECTOR '{connector_filter}'",
            details={"allowed_connectors": sorted(CONNECTORS)},
            as_json=as_json,
        )

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        if hardware_csv:
            try:
                counts_by_room = hardware_csv_device_counts(Path(hardware_csv))
            except ValueError as exc:
                return emit("fail", str(exc), as_json=as_json)
            hardware_source = "csv"
        else:
            counts_by_room = device_ip_counts(con)
            hardware_source = "sqlite"
        rows = con.execute(
            """
            SELECT
                rooms.id,
                rooms.number,
                rooms.type,
                rooms.status,
                rooms.health,
                rooms.screenconnect,
                rooms.wattbox,
                buildings.code AS building_code,
                buildings.name AS building_name
            FROM rooms
            JOIN buildings ON rooms.building_id = buildings.id
            ORDER BY rooms.id
            """
        ).fetchall()
    finally:
        con.close()

    room_ids = {row["id"] for row in rows}
    unknown_csv_rooms = sorted(set(counts_by_room) - room_ids)
    if unknown_csv_rooms:
        preview = ", ".join(unknown_csv_rooms[:8])
        if len(unknown_csv_rooms) > 8:
            preview += f", ... ({len(unknown_csv_rooms)} total)"
        return emit("fail", f"hardware CSV references unknown room_id values: {preview}", as_json=as_json)

    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not is_non_critical_candidate(row):
            continue
        room_counts = counts_by_room.get(row["id"], {})
        connectors = connector_hints(row, room_counts)
        if connector_filter and connector_filter not in connectors:
            continue
        candidates.append(
            {
                "room_id": row["id"],
                "building_code": row["building_code"],
                "room_number": row["number"],
                "room_type": row["type"],
                "status": row["status"],
                "health": row["health"],
                "eligible_connectors": connectors,
                "hardware_ip_device_types": sorted(device_type for device_type, count in room_counts.items() if count == 1),
            }
        )

    candidates.sort(key=lambda item: (-int(item["health"] or 0), item["room_id"]))
    candidates = candidates[:limit]
    payload = {
        "status": "pass",
        "message": "first live-room candidates listed",
        "connector_filter": connector_filter or None,
        "hardware_source": hardware_source,
        "count": len(candidates),
        "candidates": candidates,
    }
    if as_json:
        print(json.dumps(sanitized_json(payload), indent=2, sort_keys=True))
    else:
        print("PASS first live-room candidates listed")
        if not candidates:
            print("No non-critical candidate rooms found in the current SQLite inventory.")
        for item in candidates:
            scope = f" for {connector_filter}" if connector_filter else ""
            print(
                f"- {safe_text(item['room_id'])} ({safe_text(item['building_code'])} {safe_text(item['room_number'])}): "
                f"{safe_text(item['status'])}, health {safe_text(item['health'])}, "
                f"connectors{scope}: {safe_text(', '.join(item['eligible_connectors']))}"
            )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check first live-room connector prerequisites.")
    parser.add_argument("--room-id", help="selected BeaverView room ID, e.g. corvallis-kad-101")
    parser.add_argument("--connector", help="first connector to validate, e.g. xpanel, ptz, 25live")
    parser.add_argument("--list-candidates", action="store_true", help="list non-critical candidate rooms without printing raw IPs")
    parser.add_argument("--limit", type=int, default=12, help="maximum candidates to list with --list-candidates")
    parser.add_argument("--hardware-csv", help="preview candidate device-type matches from a Hardware IP CSV without printing raw IPs")
    parser.add_argument("--json", action="store_true", help="print machine-readable result")
    args = parser.parse_args()

    if args.list_candidates:
        return list_candidates(
            as_json=args.json,
            limit=max(args.limit, 1),
            connector=args.connector or "",
            hardware_csv=args.hardware_csv or "",
        )

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
            "SELECT id, type, status, health, screenconnect FROM rooms WHERE id=?",
            (room_id,),
        ).fetchone()
        if not room:
            return emit("fail", f"selected first live-room ID is not in SQLite inventory: {room_id}", as_json=args.json)

        blocker = non_critical_blocker(room)
        if blocker:
            return emit(
                "pending",
                blocker,
                details={"room_id": room_id, "connector": connector},
                as_json=args.json,
            )

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
