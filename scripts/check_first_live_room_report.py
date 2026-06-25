#!/usr/bin/env python3
"""Validate the sanitized first live-room report renderer."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_SCRIPT = ROOT / "scripts" / "render_first_live_room_report.py"
RAW_IP_SENTINEL = "10.77.1.25"
SECRET_SENTINEL = "contract-pass"


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def create_db(path: Path) -> None:
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
        con.execute("INSERT INTO buildings(id, code, name) VALUES(?, ?, ?)", (1, "KAd", "Kearney Addition"))
        con.execute(
            "INSERT INTO rooms(id, building_id, number, type, status, health, screenconnect, wattbox) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            ("corvallis-kad-101", 1, "101", "Presentation Classroom", "available", 91, 1, 1),
        )
        con.execute(
            "INSERT INTO device_ips(room_id, device_type, ip_address) VALUES(?, ?, ?)",
            ("corvallis-kad-101", "xpanel", RAW_IP_SENTINEL),
        )
        con.commit()
    finally:
        con.close()


def main() -> int:
    if not REPORT_SCRIPT.exists():
        fail("first live-room report renderer is missing")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "beaverview.report.db"
        create_db(db_path)
        env = os.environ.copy()
        env["PYTHON_DOTENV_DISABLED"] = "1"
        env["BEAVERVIEW_DB_PATH"] = str(db_path)
        env["CRESTRON_PROXY_USERNAME"] = "contract-user"
        env["CRESTRON_PROXY_PASSWORD"] = SECRET_SENTINEL
        readiness_json = Path(tmp) / "readiness.json"
        readiness_json.write_text(
            "{"
            '"status": "pass",'
            '"passed_count": 28,'
            '"failure_count": 0,'
            '"pending_count": 2,'
            f'"pending": ["hardware IP records are not loaded yet", "device at {RAW_IP_SENTINEL} has PASSWORD=secret"]'
            "}"
        )

        result = subprocess.run(
            [
                sys.executable,
                str(REPORT_SCRIPT),
                "--room-id",
                "corvallis-kad-101",
                "--connector",
                "xpanel",
                "--readiness-json",
                str(readiness_json),
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )

    expect(result.returncode == 0, f"report renderer exited {result.returncode}: {result.stderr}")
    output = result.stdout
    expect(RAW_IP_SENTINEL not in output, "report renderer leaked a raw IP address")
    expect(SECRET_SENTINEL not in output, "report renderer leaked a credential value")
    required_terms = (
        "# BeaverView First Live-Room Validation Report",
        "Preflight status: `pass`",
        "Readiness Snapshot",
        "Status: `pass`",
        "Pending external prerequisites: `2`",
        "scripts/check_pilot_readiness.py --markdown",
        "scripts/render_first_live_room_report.py --readiness-json /tmp/beaverview-readiness.json",
        "scripts/check_hardware_ip_import.sh",
        "Required Private Evidence",
        "admin audit log row",
        "PROJECT-LOG.md",
    )
    missing = [term for term in required_terms if term not in output]
    expect(not missing, "report renderer output is missing terms: " + ", ".join(missing))

    print("First live-room report renderer verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
