#!/usr/bin/env python3
"""Offline API contract checks for BeaverView.

These checks exercise the FastAPI app in-process with deterministic mock
connector settings. They do not print or require secrets.
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
VENV_PYTHON = API_DIR / "venv" / "bin" / "python"

if (
    VENV_PYTHON.exists()
    and Path(sys.executable).resolve() != VENV_PYTHON.resolve()
    and os.environ.get("BEAVERVIEW_API_CONTRACTS_REEXEC") != "1"
):
    env = os.environ.copy()
    env["BEAVERVIEW_API_CONTRACTS_REEXEC"] = "1"
    os.execve(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], env)

MOCK_ENV_KEYS = (
    "AZURE_CLIENT_ID",
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_SECRET",
    "SN_INSTANCE",
    "SN_CLIENT_ID",
    "SN_CLIENT_SECRET",
    "CHAT_BASE_URL",
    "CRESTRON_PROXY_USERNAME",
    "CRESTRON_PROXY_PASSWORD",
    "WATTBOX_DIRECT_USERNAME",
    "WATTBOX_DIRECT_PASSWORD",
    "PTZ_PROXY_USERNAME",
    "PTZ_PROXY_PASSWORD",
)


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


def main() -> int:
    if not (API_DIR / "beaverview.db").exists():
        fail("api/beaverview.db is missing; run scripts/check_data_migration.sh")

    for key in MOCK_ENV_KEYS:
        os.environ[key] = ""

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

    try:
        with TestClient(api.app, client=("127.0.0.1", 50000)) as client:
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
        api.app.dependency_overrides.clear()

    print("API contracts verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
