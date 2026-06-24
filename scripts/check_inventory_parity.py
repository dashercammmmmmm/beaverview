#!/usr/bin/env python3
"""Verify dashboard static inventory matches the sanitized SQLite inventory API."""

from __future__ import annotations

import os
import re
import sys
import warnings
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
VENV_PYTHON = API_DIR / "venv" / "bin" / "python"
DATA_PATH = ROOT / "dashboard" / "data.js"

if (
    VENV_PYTHON.exists()
    and Path(sys.executable).resolve() != VENV_PYTHON.resolve()
    and os.environ.get("BEAVERVIEW_INVENTORY_PARITY_REEXEC") != "1"
):
    env = os.environ.copy()
    env["BEAVERVIEW_INVENTORY_PARITY_REEXEC"] = "1"
    os.execve(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], env)


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def room_id(campus_id: str, building_code: str, room_number: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", f"{campus_id}-{building_code}-{room_number}".lower()).strip("-")


def static_room(campus_id: str, building: dict[str, Any], room: dict[str, Any]) -> dict[str, Any]:
    incidents = room.get("incidents", {})
    return {
        "id": room_id(campus_id, building["code"], room["number"]),
        "building_code": building["code"],
        "building_name": building["name"],
        "number": room["number"],
        "type": room.get("type", ""),
        "status": room.get("status", "offline"),
        "health": room.get("health", 0),
        "active_event": room.get("activeEvent", ""),
        "processor": room.get("processor", room.get("crestron", "mock")),
        "display": room.get("display", "unknown"),
        "screenconnect": bool(room.get("screenconnect", False)),
        "wattbox": bool(room.get("wattbox", False)),
        "hybrid": bool(room.get("hybrid", False)),
        "stale": bool(room.get("stale", False)),
        "devices": [tuple(device[:4]) for device in room.get("devices", [])],
        "open_incidents": incidents.get("open", []),
        "closed_incidents": incidents.get("closed", []),
    }


def api_room(room: dict[str, Any]) -> dict[str, Any]:
    incidents = room.get("incidents", [])
    return {
        "id": room["id"],
        "building_code": room["building_code"],
        "building_name": room["building_name"],
        "number": room["number"],
        "type": room.get("type", ""),
        "status": room.get("status", "offline"),
        "health": room.get("health", 0),
        "active_event": room.get("active_event", ""),
        "processor": room.get("processor", "mock"),
        "display": room.get("display", "unknown"),
        "screenconnect": bool(room.get("screenconnect", False)),
        "wattbox": bool(room.get("wattbox", False)),
        "hybrid": bool(room.get("hybrid", False)),
        "stale": bool(room.get("stale", False)),
        "devices": [
            (
                device.get("device_type", ""),
                device.get("manufacturer", ""),
                device.get("model", ""),
                device.get("connection", ""),
            )
            for device in room.get("devices", [])
        ],
        "open_incidents": [item.get("ticket", "") for item in incidents if item.get("status") == "open"],
        "closed_incidents": [item.get("ticket", "") for item in incidents if item.get("status") == "closed"],
    }


def main() -> int:
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.chdir(API_DIR)
    sys.path.insert(0, str(API_DIR))
    warnings.filterwarnings("ignore")

    try:
        from fastapi.testclient import TestClient
        from migrate_data import extract_json
        import main as api
    except Exception as exc:
        fail(f"could not import parity dependencies: {exc}")

    static_data = extract_json(DATA_PATH.read_text())
    client = TestClient(api.app, client=("127.0.0.1", 50001))
    try:
        for campus in static_data["campuses"]:
            campus_id = campus["id"]
            response = client.get(f"/api/campus/{campus_id}/inventory")
            expect(response.status_code == 200, f"{campus_id} inventory returned {response.status_code}")
            payload = response.json()
            expect(payload.get("source") == "sqlite", f"{campus_id} inventory source is not sqlite")

            static_buildings = {building["code"].lower(): building for building in campus.get("buildings", [])}
            api_buildings = {building["code"].lower(): building for building in payload.get("buildings", [])}
            expect(
                set(static_buildings) == set(api_buildings),
                f"{campus_id} building codes differ: static={sorted(static_buildings)} api={sorted(api_buildings)}",
            )
            for code, building in static_buildings.items():
                expect(
                    building["name"] == api_buildings[code]["name"],
                    f"{campus_id}/{building['code']} building name differs",
                )

            static_rooms = {
                room_data["id"]: room_data
                for building in campus.get("buildings", [])
                for room_data in [static_room(campus_id, building, room) for room in building.get("rooms", [])]
            }
            api_rooms = {room["id"]: api_room(room) for room in payload.get("rooms", [])}
            expect(
                set(static_rooms) == set(api_rooms),
                f"{campus_id} room IDs differ: static={sorted(static_rooms)} api={sorted(api_rooms)}",
            )
            for rid, expected in static_rooms.items():
                actual = api_rooms[rid]
                for key, expected_value in expected.items():
                    expect(
                        actual[key] == expected_value,
                        f"{rid} field {key} differs: static={expected_value!r} api={actual[key]!r}",
                    )

            expect(payload.get("counts", {}).get("rooms") == len(static_rooms), f"{campus_id} room count differs")
    finally:
        client.close()

    print("Inventory parity verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
