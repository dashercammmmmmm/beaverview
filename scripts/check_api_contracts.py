#!/usr/bin/env python3
"""Offline API contract checks for BeaverView.

These checks exercise the FastAPI app in-process with deterministic mock
connector settings. They do not print or require secrets.
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
import warnings
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
VENV_PYTHON = API_DIR / "venv" / "bin" / "python"
ENV_EXAMPLE = API_DIR / ".env.example"
DB_PATH = API_DIR / "beaverview.db"
EXPECTED_CONNECTORS = {
    "crestron",
    "live25",
    "ptz",
    "screenconnect",
    "servicenow",
    "sharepoint",
    "wattbox",
}

if (
    VENV_PYTHON.exists()
    and Path(sys.executable).resolve() != VENV_PYTHON.resolve()
    and os.environ.get("BEAVERVIEW_API_CONTRACTS_REEXEC") != "1"
):
    env = os.environ.copy()
    env["BEAVERVIEW_API_CONTRACTS_REEXEC"] = "1"
    os.execve(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], env)

ENV_ASSIGNMENT_RE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)\s*=")
LEGACY_ENV_KEYS = {
    "SERVICENOW_INSTANCE",
    "SERVICENOW_CLIENT_ID",
    "SERVICENOW_CLIENT_SECRET",
}


def offline_env_keys() -> set[str]:
    keys = set(LEGACY_ENV_KEYS)
    for line in ENV_EXAMPLE.read_text().splitlines():
        match = ENV_ASSIGNMENT_RE.match(line)
        if match:
            keys.add(match.group(1))
    return keys


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def json_response(response: Any, label: str) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        fail(f"{label} did not return JSON: {exc}")


def connector_mode_snapshot() -> list[tuple[str, str, str]]:
    con = sqlite3.connect(DB_PATH)
    try:
        return con.execute(
            "SELECT campus_id, connector_name, mode FROM connector_config"
        ).fetchall()
    finally:
        con.close()


def restore_connector_modes(snapshot: list[tuple[str, str, str]]) -> None:
    if not snapshot:
        return
    con = sqlite3.connect(DB_PATH)
    try:
        con.executemany(
            "UPDATE connector_config SET mode=? WHERE campus_id=? AND connector_name=?",
            [(mode, campus_id, connector_name) for campus_id, connector_name, mode in snapshot],
        )
        con.commit()
    finally:
        con.close()


def set_connector_mode(campus_id: str, connector_name: str, mode: str) -> None:
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(
            "UPDATE connector_config SET mode=? WHERE campus_id=? AND connector_name=?",
            (mode, campus_id, connector_name),
        )
        con.commit()
    finally:
        con.close()


def main() -> int:
    if not DB_PATH.exists():
        fail("api/beaverview.db is missing; run scripts/check_data_migration.sh")

    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    for key in offline_env_keys():
        os.environ.pop(key, None)

    os.chdir(API_DIR)
    sys.path.insert(0, str(API_DIR))
    warnings.filterwarnings("ignore")

    try:
        from fastapi.testclient import TestClient
        import main as api
    except Exception as exc:
        fail(f"could not import FastAPI app: {exc}")

    api.app.dependency_overrides[api.require_admin] = lambda: {
        "preferred_username": "contract@localhost",
        "groups": [],
    }

    connector_snapshot = connector_mode_snapshot()
    original_ptz_user = api._PTZ_USER
    original_ptz_pass = api._PTZ_PASS
    client = TestClient(api.app, client=("127.0.0.1", 50000))
    try:
        health = client.get("/api/health")
        expect(health.status_code == 200, f"/api/health returned {health.status_code}")
        expect(json_response(health, "/api/health").get("status") == "ok", "/api/health status is not ok")

        me = client.get("/api/me")
        expect(me.status_code == 200, f"/api/me returned {me.status_code}")
        me_data = json_response(me, "/api/me")
        expect(me_data.get("role") == "admin", "/api/me did not return localhost admin role")
        expect(me_data.get("_dev") is True, "/api/me did not use localhost dev bypass")

        rooms = client.get("/api/admin/rooms")
        expect(rooms.status_code == 200, f"/api/admin/rooms returned {rooms.status_code}")
        room_data = json_response(rooms, "/api/admin/rooms")
        expect(isinstance(room_data, list) and room_data, "/api/admin/rooms returned no seeded rooms")
        room_id = room_data[0].get("id") or "corvallis-kad-101"

        connectors = client.get("/api/admin/connectors")
        expect(connectors.status_code == 200, f"/api/admin/connectors returned {connectors.status_code}")
        connector_data = json_response(connectors, "/api/admin/connectors")
        expect(isinstance(connector_data, list) and connector_data, "/api/admin/connectors returned no rows")
        campuses = {row.get("campus_id") for row in connector_data}
        connector_names = {row.get("connector_name") for row in connector_data}
        expect("corvallis" in campuses, "/api/admin/connectors is missing Corvallis")
        expect(EXPECTED_CONNECTORS.issubset(connector_names), "/api/admin/connectors is missing expected connectors")

        corvallis_connectors = sorted(
            row["connector_name"]
            for row in connector_data
            if row.get("campus_id") == "corvallis"
        )
        expect(
            EXPECTED_CONNECTORS.issubset(set(corvallis_connectors)),
            "Corvallis connector seed set is incomplete",
        )

        for connector_name in corvallis_connectors:
            connector_test = client.post(f"/api/admin/connectors/corvallis/{connector_name}/test")
            expect(
                connector_test.status_code == 200,
                f"{connector_name} mock connector test returned {connector_test.status_code}",
            )
            connector_test_data = json_response(connector_test, f"{connector_name} mock connector test")
            expect(
                connector_test_data.get("status") == "mock",
                f"{connector_name} connector test should stay mock offline",
            )
            expect(
                connector_test_data.get("reachable") is True,
                f"{connector_name} mock connector test should be reachable",
            )

            live_toggle = client.put(f"/api/admin/connectors/corvallis/{connector_name}/mode?mode=live", json={})
            expect(
                live_toggle.status_code == 200,
                f"{connector_name} live-mode warning returned {live_toggle.status_code}",
            )
            live_toggle_data = json_response(live_toggle, f"{connector_name} live-mode warning")
            expect(
                live_toggle_data.get("status") == "warning",
                f"{connector_name} should not switch to live without offline credentials",
            )
            expect(
                live_toggle_data.get("mode_set") is False,
                f"{connector_name} live-mode warning should not change DB mode",
            )

        for connector_name in corvallis_connectors:
            set_connector_mode("corvallis", connector_name, "live")
            live_test = client.post(f"/api/admin/connectors/corvallis/{connector_name}/test")
            expect(
                live_test.status_code == 200,
                f"{connector_name} live connector test returned {live_test.status_code}",
            )
            live_test_data = json_response(live_test, f"{connector_name} live connector test")
            expect(
                live_test_data.get("status") == "pending",
                f"{connector_name} live connector test should be pending without prerequisites",
            )
            expect(
                live_test_data.get("reachable") is False,
                f"{connector_name} live connector test should not be reachable without prerequisites",
            )
            expect(
                "message" in live_test_data and live_test_data["message"],
                f"{connector_name} live connector test should explain pending state",
            )
            set_connector_mode("corvallis", connector_name, "mock")

        missing_connector = client.post("/api/admin/connectors/corvallis/__missing__/test")
        expect(missing_connector.status_code == 404, "missing connector test did not return 404")

        launch = client.get(f"/api/rooms/{room_id}/launch/xpanel")
        expect(launch.status_code == 200, f"xpanel launch returned {launch.status_code}")
        launch_data = json_response(launch, "xpanel launch")
        expect(launch_data.get("mode") == "mock", "xpanel launch should be mock with offline env")
        expect(launch_data.get("url") is None, "xpanel launch exposed a URL in offline env")

        proxy = client.get("/api/rooms/__contract-no-ip__/proxy/xpanel/")
        expect(proxy.status_code != 501, "device proxy is still the old 501 stub")
        expect(proxy.status_code == 404, f"device proxy missing-IP contract returned {proxy.status_code}")
        proxy_data = json_response(proxy, "device proxy missing-IP contract")
        expect("No xpanel IP on record" in str(proxy_data.get("detail", "")), "device proxy missing-IP detail changed")

        bad_ptz = client.post(f"/api/rooms/{room_id}/ptz/not-a-command")
        expect(bad_ptz.status_code == 400, f"bad PTZ command returned {bad_ptz.status_code}")
        expect("Unknown PTZ command" in str(json_response(bad_ptz, "bad PTZ command").get("detail", "")), "bad PTZ command detail changed")

        ptz_missing_creds = client.post(f"/api/rooms/{room_id}/ptz/home")
        expect(ptz_missing_creds.status_code == 400, f"PTZ missing-credentials contract returned {ptz_missing_creds.status_code}")
        expect(
            "ptz proxy credentials are not configured" in str(json_response(ptz_missing_creds, "PTZ missing credentials").get("detail", "")),
            "PTZ missing-credentials detail changed",
        )

        api._PTZ_USER = "contract-user"
        api._PTZ_PASS = "contract-pass"
        ptz_missing_ip = client.post("/api/rooms/__contract-no-ip__/ptz/home")
        expect(ptz_missing_ip.status_code == 404, f"PTZ missing-IP contract returned {ptz_missing_ip.status_code}")
        expect("No ptz IP on record" in str(json_response(ptz_missing_ip, "PTZ missing IP").get("detail", "")), "PTZ missing-IP detail changed")
        api._PTZ_USER = original_ptz_user
        api._PTZ_PASS = original_ptz_pass

        sn = client.get("/api/connectors/servicenow/test")
        expect(sn.status_code == 200, f"ServiceNow connector test returned {sn.status_code}")
        expect(json_response(sn, "ServiceNow connector test").get("status") == "mock", "ServiceNow test is not mock")

        chat_test = client.get("/api/connectors/chat/test")
        expect(chat_test.status_code == 200, f"chat connector test returned {chat_test.status_code}")
        expect(json_response(chat_test, "chat connector test").get("status") == "mock", "chat connector test is not mock")

        chat = client.post("/api/chat", json={"message": "ping"})
        expect(chat.status_code == 200, f"/api/chat returned {chat.status_code}")
        expect(json_response(chat, "/api/chat").get("model") == "unavailable", "/api/chat did not use offline fallback")

        incidents = client.get(f"/api/rooms/{room_id}/incidents")
        expect(incidents.status_code == 200, f"room incidents returned {incidents.status_code}")
        incidents_data = json_response(incidents, "room incidents")
        expect(isinstance(incidents_data.get("incidents"), list), "room incidents did not return a list")
    finally:
        client.close()
        api._PTZ_USER = original_ptz_user
        api._PTZ_PASS = original_ptz_pass
        restore_connector_modes(connector_snapshot)
        api.app.dependency_overrides.clear()

    print("API contracts verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
