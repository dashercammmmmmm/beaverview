#!/usr/bin/env python3
"""Exercise first live-room preflight pass/pending/fail behavior with a temp DB."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_first_live_room_preflight.py"
RAW_IP_SENTINEL = "10.77.1.25"


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def create_db(path: Path, *, duplicate: bool = False, screenconnect: bool = True) -> None:
    con = sqlite3.connect(path)
    try:
        con.executescript(
            """
            CREATE TABLE rooms (
                id TEXT PRIMARY KEY,
                building_id INTEGER NOT NULL,
                number TEXT,
                type TEXT,
                status TEXT,
                health INTEGER DEFAULT 0,
                screenconnect INTEGER DEFAULT 0,
                wattbox INTEGER DEFAULT 0
            );
            CREATE TABLE buildings (
                id INTEGER PRIMARY KEY,
                code TEXT NOT NULL,
                name TEXT NOT NULL
            );
            CREATE TABLE device_ips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                device_type TEXT NOT NULL,
                ip_address TEXT NOT NULL
            );
            """
        )
        con.execute(
            "INSERT INTO buildings(id, code, name) VALUES(?, ?, ?)",
            (1, "KAd", "Kearney Addition"),
        )
        con.execute(
            "INSERT INTO rooms(id, building_id, number, type, status, health, screenconnect, wattbox) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            ("corvallis-kad-101", 1, "101", "Presentation Classroom", "available", 91, int(screenconnect), 1),
        )
        con.execute(
            "INSERT INTO device_ips(room_id, device_type, ip_address) VALUES(?, ?, ?)",
            ("corvallis-kad-101", "xpanel", RAW_IP_SENTINEL),
        )
        if duplicate:
            con.execute(
                "INSERT INTO device_ips(room_id, device_type, ip_address) VALUES(?, ?, ?)",
                ("corvallis-kad-101", "xpanel", "10.77.1.26"),
            )
        con.commit()
    finally:
        con.close()


def run_case(db_path: Path, *args: str, env_extra: dict[str, str] | None = None) -> tuple[int, dict]:
    env = os.environ.copy()
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["BEAVERVIEW_DB_PATH"] = str(db_path)
    for key in (
        "FIRST_LIVE_ROOM_ID",
        "FIRST_LIVE_CONNECTOR",
        "CRESTRON_PROXY_USERNAME",
        "CRESTRON_PROXY_PASSWORD",
        "SC_BASE_URL",
    ):
        env.pop(key, None)
    if env_extra:
        env.update(env_extra)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--json"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    expect(RAW_IP_SENTINEL not in result.stdout, "preflight stdout leaked a raw IP address")
    expect(RAW_IP_SENTINEL not in result.stderr, "preflight stderr leaked a raw IP address")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"preflight did not return JSON: {exc}; stdout={result.stdout!r}; stderr={result.stderr!r}")
    return result.returncode, payload


def expect_case(db_path: Path, expected_code: int, expected_status: str, *args: str, env_extra: dict[str, str] | None = None) -> None:
    code, payload = run_case(db_path, *args, env_extra=env_extra)
    expect(code == expected_code, f"expected exit {expected_code}, got {code}: {payload}")
    expect(payload.get("status") == expected_status, f"expected status {expected_status}, got {payload}")
    expect(payload.get("message"), "preflight response did not include a message")


def expect_candidate_list(db_path: Path) -> None:
    code, payload = run_case(db_path, "--list-candidates")
    expect(code == 0, f"candidate list returned exit {code}: {payload}")
    expect(payload.get("status") == "pass", f"candidate list status changed: {payload}")
    candidates = payload.get("candidates")
    expect(isinstance(candidates, list) and candidates, "candidate list returned no candidates")
    first = candidates[0]
    expect(first.get("room_id") == "corvallis-kad-101", f"candidate room changed: {first}")
    expect("xpanel" in first.get("eligible_connectors", []), "candidate list did not include xpanel hint")
    expect("crestron_poll" in first.get("eligible_connectors", []), "candidate list did not include crestron_poll hint")
    expect("xpanel" in first.get("hardware_ip_device_types", []), "candidate list did not include sanitized Hardware IP device type")

    code, payload = run_case(db_path, "--list-candidates", "--connector", "xpanel")
    expect(code == 0, f"xpanel candidate filter returned exit {code}: {payload}")
    expect(payload.get("connector_filter") == "xpanel", f"xpanel filter was not echoed: {payload}")
    expect(len(payload.get("candidates", [])) == 1, f"xpanel filter returned unexpected candidates: {payload}")

    code, payload = run_case(db_path, "--list-candidates", "--connector", "crestron")
    expect(code == 0, f"crestron alias candidate filter returned exit {code}: {payload}")
    expect(payload.get("connector_filter") == "crestron_poll", f"crestron alias did not normalize: {payload}")
    expect(len(payload.get("candidates", [])) == 1, f"crestron alias filter returned unexpected candidates: {payload}")

    code, payload = run_case(db_path, "--list-candidates", "--connector", "ptz")
    expect(code == 0, f"ptz empty candidate filter returned exit {code}: {payload}")
    expect(payload.get("connector_filter") == "ptz", f"ptz filter was not echoed: {payload}")
    expect(payload.get("candidates") == [], f"ptz filter should return no candidates without a ptz Hardware IP row: {payload}")

    code, payload = run_case(db_path, "--list-candidates", "--connector", "not-a-connector")
    expect(code == 1, f"invalid connector candidate filter returned exit {code}: {payload}")
    expect(payload.get("status") == "fail", f"invalid connector candidate filter should fail: {payload}")


def expect_hardware_csv_preview(db_path: Path, csv_path: Path) -> None:
    csv_path.write_text(
        "room_id,device_type,ip_address,notes\n"
        f"corvallis-kad-101,ptz,{RAW_IP_SENTINEL},preview PTZ\n"
    )
    code, payload = run_case(db_path, "--list-candidates", "--connector", "ptz", "--hardware-csv", str(csv_path))
    expect(code == 0, f"hardware CSV candidate preview returned exit {code}: {payload}")
    expect(payload.get("hardware_source") == "csv", f"hardware CSV preview did not identify CSV source: {payload}")
    candidates = payload.get("candidates")
    expect(isinstance(candidates, list) and len(candidates) == 1, f"hardware CSV preview returned unexpected candidates: {payload}")
    first = candidates[0]
    expect(first.get("room_id") == "corvallis-kad-101", f"hardware CSV preview returned wrong room: {first}")
    expect("ptz" in first.get("eligible_connectors", []), "hardware CSV preview did not include ptz hint")
    expect("ptz" in first.get("hardware_ip_device_types", []), "hardware CSV preview did not include sanitized ptz device type")

    duplicate_csv = csv_path.with_name("hardware_ips.duplicate-preview.csv")
    duplicate_csv.write_text(
        "room_id,device_type,ip_address,notes\n"
        f"corvallis-kad-101,ptz,{RAW_IP_SENTINEL},preview PTZ\n"
        "corvallis-kad-101,ptz,10.77.1.26,duplicate PTZ\n"
    )
    code, payload = run_case(db_path, "--list-candidates", "--connector", "ptz", "--hardware-csv", str(duplicate_csv))
    expect(code == 1, f"duplicate hardware CSV preview returned exit {code}: {payload}")
    expect(payload.get("status") == "fail", f"duplicate hardware CSV preview should fail: {payload}")
    expect("duplicate room/device mappings" in payload.get("message", ""), f"duplicate preview message changed: {payload}")
    expect(RAW_IP_SENTINEL not in json.dumps(payload), "duplicate hardware CSV preview leaked a raw IP address")

    unknown_room_csv = csv_path.with_name("hardware_ips.unknown-room-preview.csv")
    unknown_room_csv.write_text(
        "room_id,device_type,ip_address,notes\n"
        f"corvallis-missing-101,ptz,{RAW_IP_SENTINEL},unknown room\n"
    )
    code, payload = run_case(db_path, "--list-candidates", "--connector", "ptz", "--hardware-csv", str(unknown_room_csv))
    expect(code == 1, f"unknown-room hardware CSV preview returned exit {code}: {payload}")
    expect(payload.get("status") == "fail", f"unknown-room hardware CSV preview should fail: {payload}")
    expect("unknown room_id values" in payload.get("message", ""), f"unknown-room preview message changed: {payload}")
    expect(RAW_IP_SENTINEL not in json.dumps(payload), "unknown-room hardware CSV preview leaked a raw IP address")

    blank_field_csv = csv_path.with_name("hardware_ips.blank-preview.csv")
    blank_field_csv.write_text(
        "room_id,device_type,ip_address,notes\n"
        f"corvallis-kad-101,,{RAW_IP_SENTINEL},blank device type\n"
    )
    code, payload = run_case(db_path, "--list-candidates", "--connector", "ptz", "--hardware-csv", str(blank_field_csv))
    expect(code == 1, f"blank-field hardware CSV preview returned exit {code}: {payload}")
    expect(payload.get("status") == "fail", f"blank-field hardware CSV preview should fail: {payload}")
    expect("missing required field" in payload.get("message", ""), f"blank-field preview message changed: {payload}")
    expect(RAW_IP_SENTINEL not in json.dumps(payload), "blank-field hardware CSV preview leaked a raw IP address")


def main() -> int:
    if not SCRIPT.exists():
        fail("first live-room preflight script is missing")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "beaverview.test.db"
        create_db(db_path)

        expect_case(db_path, 2, "pending")
        expect_case(db_path, 1, "fail", "--room-id", "corvallis-kad-101", "--connector", "not-a-connector")
        expect_case(db_path, 1, "fail", "--room-id", "corvallis-missing-101", "--connector", "xpanel")
        expect_case(db_path, 2, "pending", "--room-id", "corvallis-kad-101", "--connector", "xpanel")
        expect_case(
            db_path,
            0,
            "pass",
            "--room-id",
            "corvallis-kad-101",
            "--connector",
            "xpanel",
            env_extra={"CRESTRON_PROXY_USERNAME": "contract-user", "CRESTRON_PROXY_PASSWORD": "contract-pass"},
        )
        expect_case(
            db_path,
            0,
            "pass",
            "--room-id",
            "corvallis-kad-101",
            "--connector",
            "screenconnect",
            env_extra={"SC_BASE_URL": "https://screenconnect.example.test"},
        )
        expect_candidate_list(db_path)
        expect_hardware_csv_preview(db_path, Path(tmp) / "hardware_ips.preview.csv")

        duplicate_db = Path(tmp) / "beaverview.duplicate.db"
        create_db(duplicate_db, duplicate=True)
        expect_case(
            duplicate_db,
            1,
            "fail",
            "--room-id",
            "corvallis-kad-101",
            "--connector",
            "xpanel",
            env_extra={"CRESTRON_PROXY_USERNAME": "contract-user", "CRESTRON_PROXY_PASSWORD": "contract-pass"},
        )

        no_screenconnect_db = Path(tmp) / "beaverview.no-screenconnect.db"
        create_db(no_screenconnect_db, screenconnect=False)
        expect_case(
            no_screenconnect_db,
            2,
            "pending",
            "--room-id",
            "corvallis-kad-101",
            "--connector",
            "screenconnect",
            env_extra={"SC_BASE_URL": "https://screenconnect.example.test"},
        )

    print("First live-room preflight cases verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
