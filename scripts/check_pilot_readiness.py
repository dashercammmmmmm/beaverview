#!/usr/bin/env python3
"""Local pilot-readiness preflight for BeaverView.

This check separates:
- local gates that should pass before any push/deploy, and
- external prerequisites that remain pending until OSU/VM credentials and
  secure hardware data are available.

It prints no secret values.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
VENV_PYTHON = API_DIR / "venv" / "bin" / "python"

if (
    VENV_PYTHON.exists()
    and Path(sys.executable).resolve() != VENV_PYTHON.resolve()
    and os.environ.get("BEAVERVIEW_PILOT_READINESS_REEXEC") != "1"
):
    env = os.environ.copy()
    env["BEAVERVIEW_PILOT_READINESS_REEXEC"] = "1"
    os.execve(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], env)

DB_PATH = API_DIR / "beaverview.db"
ENV_PATH = API_DIR / ".env"
HARDWARE_SAMPLE_PATH = ROOT / "docs" / "examples" / "hardware_ips.sample.csv"
DEPLOY_SERVICE_PATH = ROOT / "deploy" / "systemd" / "beaverview.service"
DEPLOY_NGINX_PATH = ROOT / "deploy" / "nginx" / "beaverview.conf.template"
AZURE_CHECKLIST_PATH = ROOT / "docs" / "examples" / "azure-entra-app-registration.md"
API_CONTRACTS_SCRIPT = ROOT / "scripts" / "check_api_contracts.py"
BROWSER_SMOKE_SCRIPT = ROOT / "scripts" / "check_dashboard_browser.sh"
ADMIN_BROWSER_SMOKE_SCRIPT = ROOT / "scripts" / "check_admin_browser.sh"
DATA_MIGRATION_SCRIPT = ROOT / "scripts" / "check_data_migration.sh"
ENV_TEMPLATE_SCRIPT = ROOT / "scripts" / "check_env_template.py"
HARDWARE_IP_IMPORT_SCRIPT = ROOT / "scripts" / "check_hardware_ip_import.sh"
INVENTORY_PARITY_SCRIPT = ROOT / "scripts" / "check_inventory_parity.py"
LIVE_VALIDATION_SCRIPT = ROOT / "scripts" / "check_live_validation_doc.py"
PILOT_INPUTS_SCRIPT = ROOT / "scripts" / "check_pilot_inputs_doc.py"

LOCAL_FAILURES: list[str] = []
PENDING: list[str] = []
PASSED: list[str] = []


def run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def pass_(message: str) -> None:
    PASSED.append(message)


def fail(message: str) -> None:
    LOCAL_FAILURES.append(message)


def pending(message: str) -> None:
    PENDING.append(message)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def check_git() -> None:
    status = run(["git", "status", "--porcelain"])
    if status.returncode != 0:
        fail("git status failed")
        return
    if status.stdout.strip():
        fail("working tree has uncommitted changes")
    else:
        pass_("working tree is clean")

    branch = run(["git", "status", "--short", "--branch"])
    if branch.returncode != 0:
        fail("git branch status failed")
        return
    first_line = branch.stdout.splitlines()[0] if branch.stdout else ""
    if "ahead" in first_line or "behind" in first_line or "gone" in first_line:
        fail(f"branch is not synced: {first_line}")
    else:
        pass_(f"branch sync state is clean: {first_line}")


def check_sensitive_paths() -> None:
    sensitive = [
        API_DIR / ".env",
        API_DIR / "hardware_ips.csv",
        ROOT / "hardware_ips.csv",
        API_DIR / "beaverview.db",
    ]
    tracked = set(run(["git", "ls-files"]).stdout.splitlines())
    for path in sensitive:
        rel = str(path.relative_to(ROOT))
        if rel in tracked:
            fail(f"sensitive/local file is tracked by git: {rel}")
        elif path.exists():
            ignore = run(["git", "check-ignore", rel])
            if ignore.returncode == 0:
                pass_(f"local-only file is ignored: {rel}")
            else:
                fail(f"local-only file exists but is not ignored: {rel}")


def check_python_env() -> None:
    py = API_DIR / "venv" / "bin" / "python"
    if not py.exists():
        fail("api/venv is missing")
        return
    result = run([
        str(py),
        "-c",
        "import fastapi, httpx, msal, starlette_sessions, itsdangerous; import main",
    ], cwd=API_DIR)
    if result.returncode == 0:
        pass_("Python venv imports required backend dependencies")
    else:
        fail("Python venv cannot import required backend dependencies")


def check_db() -> None:
    if not DB_PATH.exists():
        fail("api/beaverview.db is missing; run scripts/check_data_migration.sh")
        return
    con = sqlite3.connect(DB_PATH)
    try:
        counts = {
            "campuses": con.execute("select count(*) from campuses").fetchone()[0],
            "buildings": con.execute("select count(*) from buildings").fetchone()[0],
            "rooms": con.execute("select count(*) from rooms").fetchone()[0],
            "devices": con.execute("select count(*) from devices").fetchone()[0],
            "device_ips": con.execute("select count(*) from device_ips").fetchone()[0],
        }
    except sqlite3.Error as exc:
        fail(f"SQLite readiness query failed: {exc}")
        return
    finally:
        con.close()

    inventory_ok = all(counts[name] > 0 for name in ("campuses", "buildings", "rooms", "devices"))
    if inventory_ok:
        pass_(
            "SQLite inventory is seeded: "
            f"{counts['campuses']} campuses, {counts['buildings']} buildings, "
            f"{counts['rooms']} rooms, {counts['devices']} devices"
        )
    else:
        fail(f"SQLite inventory is incomplete: {counts}")

    if counts["device_ips"] > 0:
        pass_(f"Hardware IP records loaded: {counts['device_ips']}")
    else:
        pending("hardware IP records are not loaded yet")


def check_data_migration() -> None:
    if not DATA_MIGRATION_SCRIPT.exists():
        fail("data migration validator is missing")
        return

    result = run([str(DATA_MIGRATION_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("data migration validates")
    else:
        fail("data migration failed validation")


def check_hardware_ip_import() -> None:
    if not HARDWARE_IP_IMPORT_SCRIPT.exists():
        fail("hardware IP import validator is missing")
        return

    if not HARDWARE_SAMPLE_PATH.exists():
        fail("hardware IP sample CSV is missing")
        return

    result = run([str(HARDWARE_IP_IMPORT_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("hardware IP import validation passes")
    else:
        fail("hardware IP import validation failed")


def check_deployment_assets() -> None:
    script = ROOT / "scripts" / "check_deployment_assets.sh"
    if not DEPLOY_SERVICE_PATH.exists():
        fail("systemd deployment template is missing")
        return
    if not DEPLOY_NGINX_PATH.exists():
        fail("nginx deployment template is missing")
        return
    if not script.exists():
        fail("deployment asset validator is missing")
        return

    result = run([str(script)], cwd=ROOT)
    if result.returncode == 0:
        pass_("deployment templates validate")
    else:
        fail("deployment templates failed validation")


def check_api_contracts() -> None:
    if not API_CONTRACTS_SCRIPT.exists():
        fail("API contract validator is missing")
        return

    result = run([sys.executable, str(API_CONTRACTS_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("offline API contracts validate")
    else:
        fail("offline API contracts failed validation")


def check_inventory_parity() -> None:
    if not INVENTORY_PARITY_SCRIPT.exists():
        fail("inventory parity validator is missing")
        return

    result = run([sys.executable, str(INVENTORY_PARITY_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("dashboard data matches sanitized SQLite inventory")
    else:
        fail("dashboard data and sanitized SQLite inventory differ")


def check_dashboard_browser() -> None:
    if not BROWSER_SMOKE_SCRIPT.exists():
        fail("dashboard browser smoke validator is missing")
        return

    result = run([str(BROWSER_SMOKE_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("dashboard browser smoke validates guarded workflows")
    else:
        fail("dashboard browser smoke failed validation")


def check_admin_browser() -> None:
    if not ADMIN_BROWSER_SMOKE_SCRIPT.exists():
        fail("admin browser smoke validator is missing")
        return

    result = run([str(ADMIN_BROWSER_SMOKE_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("admin browser smoke validates management pages")
    else:
        fail("admin browser smoke failed validation")


def check_env_template() -> None:
    if not ENV_TEMPLATE_SCRIPT.exists():
        fail("environment template validator is missing")
        return

    result = run([sys.executable, str(ENV_TEMPLATE_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("environment template matches runtime env usage")
    else:
        fail("environment template validation failed")


def check_pilot_inputs_doc() -> None:
    if not PILOT_INPUTS_SCRIPT.exists():
        fail("pilot input checklist validator is missing")
        return

    result = run([sys.executable, str(PILOT_INPUTS_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("pilot input checklist covers external prerequisites")
    else:
        fail("pilot input checklist validation failed")


def check_live_validation_doc() -> None:
    if not LIVE_VALIDATION_SCRIPT.exists():
        fail("first live-room validation doc validator is missing")
        return

    result = run([sys.executable, str(LIVE_VALIDATION_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("first live-room validation runbook covers pilot gates")
    else:
        fail("first live-room validation runbook validation failed")


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


def has_all(env: dict[str, str], keys: tuple[str, ...]) -> bool:
    return all(is_configured(env.get(key)) for key in keys)


def check_azure_template() -> None:
    if AZURE_CHECKLIST_PATH.exists():
        pass_("Azure/Entra app registration checklist exists")
    else:
        fail("Azure/Entra app registration checklist is missing")


def check_azure_redirect(env: dict[str, str]) -> None:
    redirect_uri = env.get("AZURE_REDIRECT_URI", "https://beaverview/auth/callback")
    if not is_configured(redirect_uri):
        pending("Azure redirect URI is not configured")
        return
    if not redirect_uri.startswith("https://"):
        fail("Azure redirect URI must use https")
        return
    if not redirect_uri.endswith("/auth/callback"):
        fail("Azure redirect URI must end with /auth/callback and must not have a trailing slash")
        return
    pass_(f"Azure redirect URI shape is valid: {redirect_uri}")


def check_env_prereqs() -> None:
    env = parse_env(ENV_PATH)
    check_azure_template()
    if not ENV_PATH.exists():
        pending("api/.env is not present; copy api/.env.example and fill deployment values")
        return

    pass_("api/.env exists")
    check_azure_redirect(env)

    if is_configured(env.get("PROXY_SECRET")):
        pass_("PROXY_SECRET is set")
    else:
        pending("PROXY_SECRET is not set")

    if is_configured(env.get("SESSION_SECRET_KEY")):
        pass_("SESSION_SECRET_KEY is set")
    else:
        pending("SESSION_SECRET_KEY is not set")

    if has_all(env, ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")):
        pass_("Azure app credentials are present")
    else:
        pending("Azure app credentials are not complete")

    if env.get("AZURE_GROUP_TECHNICIAN") and env.get("AZURE_GROUP_ADMIN"):
        pass_("Azure group object IDs are present")
    else:
        pending("Azure technician/admin group object IDs are not complete")

    connector_sets = {
        "Crestron poll": ("CRESTRON_POLL_USERNAME", "CRESTRON_POLL_PASSWORD"),
        "XPanel proxy": ("CRESTRON_PROXY_USERNAME", "CRESTRON_PROXY_PASSWORD"),
        "WattBox direct proxy": ("WATTBOX_DIRECT_USERNAME", "WATTBOX_DIRECT_PASSWORD"),
        "PTZ proxy": ("PTZ_PROXY_USERNAME", "PTZ_PROXY_PASSWORD"),
        "25Live": ("LIVE25_BASE_URL", "LIVE25_USERNAME", "LIVE25_PASSWORD"),
    }
    for label, keys in connector_sets.items():
        if has_all(env, keys):
            pass_(f"{label} credentials are present")
        else:
            pending(f"{label} credentials are not complete")

    launch_urls = {
        "ScreenConnect base URL": "SC_BASE_URL",
        "SharePoint base URL": "SHAREPOINT_BASE_URL",
        "Hermes chat base URL": "CHAT_BASE_URL",
    }
    for label, key in launch_urls.items():
        if is_configured(env.get(key)):
            pass_(f"{label} is configured")
        else:
            pending(f"{label} is not configured")

    servicenow_oauth = has_all(env, ("SN_INSTANCE", "SN_CLIENT_ID", "SN_CLIENT_SECRET"))
    servicenow_basic = has_all(env, ("SN_INSTANCE", "SN_USERNAME", "SN_PASSWORD"))
    if servicenow_oauth or servicenow_basic:
        pass_("ServiceNow credentials are present")
    else:
        pending("ServiceNow credentials are not complete")


def run_checks() -> None:
    check_git()
    check_sensitive_paths()
    check_python_env()
    check_data_migration()
    check_db()
    check_hardware_ip_import()
    check_deployment_assets()
    check_api_contracts()
    check_inventory_parity()
    check_dashboard_browser()
    check_admin_browser()
    check_env_template()
    check_pilot_inputs_doc()
    check_live_validation_doc()
    check_env_prereqs()


def readiness_result() -> dict:
    return {
        "status": "fail" if LOCAL_FAILURES else "pass",
        "passed": PASSED,
        "pending": PENDING,
        "failures": LOCAL_FAILURES,
        "passed_count": len(PASSED),
        "pending_count": len(PENDING),
        "failure_count": len(LOCAL_FAILURES),
    }


def print_text_result(result: dict) -> None:
    print("BeaverView pilot-readiness preflight")
    print()
    for item in result["passed"]:
        print(f"PASS    {item}")
    for item in result["pending"]:
        print(f"PENDING {item}")
    for item in result["failures"]:
        print(f"FAIL    {item}")

    print()
    if result["failures"]:
        print(f"Local readiness failed: {result['failure_count']} issue(s)")
        return
    print(f"Local readiness passed with {result['pending_count']} external prerequisite(s) pending")


def print_markdown_result(result: dict) -> None:
    print("# BeaverView Pilot Readiness")
    print()
    print(f"- Status: `{result['status']}`")
    print(f"- Passed checks: {result['passed_count']}")
    print(f"- Pending external prerequisites: {result['pending_count']}")
    print(f"- Local failures: {result['failure_count']}")
    print()

    print("## Passed")
    print()
    for item in result["passed"]:
        print(f"- {item}")
    if not result["passed"]:
        print("- None")
    print()

    print("## Pending External Prerequisites")
    print()
    for item in result["pending"]:
        print(f"- {item}")
    if not result["pending"]:
        print("- None")
    print()

    print("## Local Failures")
    print()
    for item in result["failures"]:
        print(f"- {item}")
    if not result["failures"]:
        print("- None")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BeaverView local pilot-readiness checks.")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--markdown", action="store_true", help="print a Markdown readiness report")
    args = parser.parse_args()

    run_checks()
    result = readiness_result()

    if args.json and args.markdown:
        parser.error("choose only one output format")

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.markdown:
        print_markdown_result(result)
    else:
        print_text_result(result)

    if result["failures"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
