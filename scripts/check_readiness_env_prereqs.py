#!/usr/bin/env python3
"""Validate readiness classification for env prerequisite placeholder values."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "scripts" / "check_pilot_readiness.py"


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_readiness_module():
    os.environ["BEAVERVIEW_PILOT_READINESS_REEXEC"] = "1"
    spec = importlib.util.spec_from_file_location("check_pilot_readiness", READINESS)
    if spec is None or spec.loader is None:
        fail("could not load scripts/check_pilot_readiness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def env_text(*, technician_group: str, admin_group: str) -> str:
    return "\n".join(
        [
            "PROXY_SECRET=local-generated-proxy-secret",
            "SESSION_SECRET_KEY=local-generated-session-secret",
            "BEAVERVIEW_CORS_ORIGINS=https://beaverview",
            "AZURE_TENANT_ID=00000000-0000-0000-0000-000000000001",
            "AZURE_CLIENT_ID=00000000-0000-0000-0000-000000000002",
            "AZURE_CLIENT_SECRET=local-client-secret",
            "AZURE_REDIRECT_URI=https://beaverview/auth/callback",
            f"AZURE_GROUP_TECHNICIAN={technician_group}",
            f"AZURE_GROUP_ADMIN={admin_group}",
            "CRESTRON_POLL_USERNAME=svc-crestron",
            "CRESTRON_POLL_PASSWORD=local-crestron-password",
            "CRESTRON_PROXY_USERNAME=svc-xpanel",
            "CRESTRON_PROXY_PASSWORD=local-xpanel-password",
            "WATTBOX_DIRECT_USERNAME=svc-wattbox",
            "WATTBOX_DIRECT_PASSWORD=local-wattbox-password",
            "PTZ_PROXY_USERNAME=svc-ptz",
            "PTZ_PROXY_PASSWORD=local-ptz-password",
            "LIVE25_BASE_URL=https://25live.example.edu",
            "LIVE25_USERNAME=svc-25live",
            "LIVE25_PASSWORD=local-25live-password",
            "SC_BASE_URL=https://screenconnect.example.edu",
            "SHAREPOINT_BASE_URL=https://sharepoint.example.edu/sites/AVSupport",
            "CHAT_BASE_URL=http://localhost:8080",
            "SN_INSTANCE=example.service-now.com",
            "SN_CLIENT_ID=00000000-0000-0000-0000-000000000003",
            "SN_CLIENT_SECRET=local-servicenow-secret",
            "",
        ]
    )


def run_env_case(readiness, env_path: Path) -> tuple[list[str], list[str], list[str]]:
    readiness.LOCAL_FAILURES.clear()
    readiness.PENDING.clear()
    readiness.PASSED.clear()
    readiness.ENV_PATH = env_path
    readiness.check_env_prereqs()
    return readiness.PASSED[:], readiness.PENDING[:], readiness.LOCAL_FAILURES[:]


def main() -> int:
    readiness = load_readiness_module()
    pending_message = "Azure technician/admin group object IDs are not complete"
    pass_message = "Azure group object IDs are present"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        placeholder_env = tmp_path / "placeholder.env"
        placeholder_env.write_text(
            env_text(
                technician_group="object-id-of-technician-group",
                admin_group="object-id-of-admin-group",
            )
        )
        passed, pending, failures = run_env_case(readiness, placeholder_env)
        expect(not failures, "placeholder group env case produced local failures: " + ", ".join(failures))
        expect(pending_message in pending, "placeholder Azure group values should remain pending")
        expect(pass_message not in passed, "placeholder Azure group values should not pass readiness")

        configured_env = tmp_path / "configured.env"
        configured_env.write_text(
            env_text(
                technician_group="00000000-0000-0000-0000-000000000004",
                admin_group="00000000-0000-0000-0000-000000000005",
            )
        )
        passed, pending, failures = run_env_case(readiness, configured_env)
        expect(not failures, "configured group env case produced local failures: " + ", ".join(failures))
        expect(pass_message in passed, "configured Azure group values should pass readiness")
        expect(pending_message not in pending, "configured Azure group values should not remain pending")

    print("Readiness env prerequisite classification verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
