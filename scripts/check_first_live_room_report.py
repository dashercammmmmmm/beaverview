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


def expect_order(text: str, first: str, second: str) -> None:
    first_index = text.find(first)
    second_index = text.find(second)
    if first_index == -1 or second_index == -1:
        missing = first if first_index == -1 else second
        fail(f"report renderer output is missing ordered term: {missing}")
    if first_index > second_index:
        fail(f"report renderer output must list {first!r} before {second!r}")


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


def write_readiness_json(path: Path) -> None:
    path.write_text(
        "{"
        '"status": "pass",'
        '"passed_count": 28,'
        '"failure_count": 0,'
        '"pending_count": 2,'
        f'"pending": ["hardware IP records are not loaded yet", "device at {RAW_IP_SENTINEL} has PASSWORD=secret"],'
        '"pending_actions": ['
        '{'
        '"pending": "hardware IP records are not loaded yet",'
        f'"action": "Place export containing {RAW_IP_SENTINEL} with PASSWORD=secret in ignored api/hardware_ips.csv",'
        '"reference": "docs/examples/pilot-inputs-checklist.md#hardware-ip-records"'
        '}'
        ']'
        "}"
    )


def write_candidates_json(path: Path, *, room_id: str = "corvallis-kad-101", connector: str = "xpanel") -> None:
    path.write_text(
        "{"
        '"status": "pass",'
        f'"connector_filter": "{connector}",'
        '"hardware_source": "csv",'
        '"count": 1,'
        '"candidates": ['
        '{'
        f'"room_id": "{room_id}",'
        '"building_code": "KAd",'
        '"room_number": "101",'
        '"status": "available",'
        '"health": 91,'
        f'"eligible_connectors": ["{connector}", "crestron_poll"],'
        f'"hardware_ip_device_types": ["{connector}"],'
        f'"ignored_raw_ip": "{RAW_IP_SENTINEL}"'
        '}'
        ']'
        "}"
    )


def run_report(db_path: Path, readiness_json: Path, candidates_json: Path, *, room_id: str = "corvallis-kad-101", connector: str = "xpanel") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["BEAVERVIEW_DB_PATH"] = str(db_path)
    env["CRESTRON_PROXY_USERNAME"] = "contract-user"
    env["CRESTRON_PROXY_PASSWORD"] = SECRET_SENTINEL
    env["CRESTRON_POLL_USERNAME"] = "contract-user"
    env["CRESTRON_POLL_PASSWORD"] = SECRET_SENTINEL
    return subprocess.run(
        [
            sys.executable,
            str(REPORT_SCRIPT),
            "--room-id",
            room_id,
            "--connector",
            connector,
            "--readiness-json",
            str(readiness_json),
            "--candidates-json",
            str(candidates_json),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


def main() -> int:
    if not REPORT_SCRIPT.exists():
        fail("first live-room report renderer is missing")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "beaverview.report.db"
        create_db(db_path)
        readiness_json = Path(tmp) / "readiness.json"
        write_readiness_json(readiness_json)

        candidates_json = Path(tmp) / "candidates.json"
        write_candidates_json(candidates_json)

        result = run_report(db_path, readiness_json, candidates_json)

        mismatch_candidates = Path(tmp) / "candidates-mismatch.json"
        write_candidates_json(mismatch_candidates, room_id="corvallis-kad-999")
        mismatch_result = run_report(db_path, readiness_json, mismatch_candidates)

        alias_candidates = Path(tmp) / "candidates-alias.json"
        write_candidates_json(alias_candidates, connector="crestron_poll")
        alias_result = run_report(db_path, readiness_json, alias_candidates, connector="crestron")

    expect(result.returncode == 0, f"report renderer exited {result.returncode}: {result.stderr}")
    output = result.stdout
    expect(RAW_IP_SENTINEL not in output, "report renderer leaked a raw IP address")
    expect(SECRET_SENTINEL not in output, "report renderer leaked a credential value")
    required_terms = (
        "# BeaverView First Live-Room Validation Report",
        "Candidate Snapshot",
        "Connector filter: `xpanel`",
        "corvallis-kad-101 (KAd 101): available, health 91, connectors xpanel, crestron_poll, device types xpanel",
        "Preflight status: `pass`",
        "Readiness Snapshot",
        "Status: `pass`",
        "Pending external prerequisites: `2`",
        "Pending next actions",
        "Place export containing <redacted-ip> with PASSWORD=<redacted> in ignored api/hardware_ips.csv",
        "Go/no-go: `GO FOR FIRST CONNECTOR VALIDATION`",
        "selected room/connector appears in the candidate snapshot",
        "scripts/check_pilot_readiness.py --markdown",
        "scripts/render_first_live_room_report.py --readiness-json /tmp/beaverview-readiness.json --candidates-json /tmp/beaverview-candidates.json",
        "scripts/check_hardware_ip_import.sh",
        "(cd api && venv/bin/python import_device_ips.py hardware_ips.csv)",
        "Required Private Evidence",
        "admin audit log row",
        "PROJECT-LOG.md",
    )
    missing = [term for term in required_terms if term not in output]
    expect(not missing, "report renderer output is missing terms: " + ", ".join(missing))
    expect_order(output, "scripts/check_hardware_ip_import.sh", "(cd api && venv/bin/python import_device_ips.py hardware_ips.csv)")
    expect_order(output, "(cd api && venv/bin/python import_device_ips.py hardware_ips.csv)", "scripts/check_first_live_room_preflight.py")
    expect_order(
        output,
        "scripts/check_first_live_room_preflight.py",
        "scripts/check_first_live_room_preflight.py --list-candidates --json > /tmp/beaverview-candidates.json",
    )
    expect_order(
        output,
        "scripts/check_first_live_room_preflight.py --list-candidates --json > /tmp/beaverview-candidates.json",
        "scripts/render_first_live_room_report.py --readiness-json /tmp/beaverview-readiness.json --candidates-json /tmp/beaverview-candidates.json",
    )

    expect(mismatch_result.returncode == 0, f"mismatch report renderer exited {mismatch_result.returncode}: {mismatch_result.stderr}")
    mismatch_output = mismatch_result.stdout
    expect("Go/no-go: `NO-GO`" in mismatch_output, "candidate mismatch should force no-go")
    expect(
        "selected room and connector are not present in the candidate snapshot" in mismatch_output,
        "candidate mismatch no-go reason is missing",
    )
    expect(RAW_IP_SENTINEL not in mismatch_output, "candidate mismatch output leaked a raw IP address")

    expect(alias_result.returncode == 0, f"alias report renderer exited {alias_result.returncode}: {alias_result.stderr}")
    alias_output = alias_result.stdout
    expect("First connector: `crestron_poll`" in alias_output, "connector alias should be normalized in report output")
    expect("Go/no-go: `GO FOR FIRST CONNECTOR VALIDATION`" in alias_output, "connector alias should match normalized candidate")
    expect(RAW_IP_SENTINEL not in alias_output, "connector alias output leaked a raw IP address")

    print("First live-room report renderer verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
