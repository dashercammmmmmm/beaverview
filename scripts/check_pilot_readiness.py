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

from sanitize_output import redact_line


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
DEPLOYMENT_PLAYBOOK_SCRIPT = ROOT / "scripts" / "check_deployment_playbook.py"
ENV_TEMPLATE_SCRIPT = ROOT / "scripts" / "check_env_template.py"
FIRST_LIVE_CONNECTORS_SCRIPT = ROOT / "scripts" / "check_first_live_connectors.py"
FIRST_LIVE_ROOM_CASES_SCRIPT = ROOT / "scripts" / "check_first_live_room_preflight_cases.py"
FIRST_LIVE_ROOM_PREFLIGHT_SCRIPT = ROOT / "scripts" / "check_first_live_room_preflight.py"
FIRST_LIVE_ROOM_REPORT_SCRIPT = ROOT / "scripts" / "check_first_live_room_report.py"
HARDWARE_IP_IMPORT_SCRIPT = ROOT / "scripts" / "check_hardware_ip_import.sh"
HARDWARE_IP_CSV_SCRIPT = ROOT / "scripts" / "check_hardware_ip_csv.py"
INIT_LOCAL_ENV_SCRIPT = ROOT / "scripts" / "check_init_local_env.py"
INVENTORY_PARITY_SCRIPT = ROOT / "scripts" / "check_inventory_parity.py"
LIVE_VALIDATION_SCRIPT = ROOT / "scripts" / "check_live_validation_doc.py"
PILOT_INPUTS_SCRIPT = ROOT / "scripts" / "check_pilot_inputs_doc.py"
PILOT_INTAKE_PACKET_SCRIPT = ROOT / "scripts" / "check_pilot_intake_packet.py"
PLAYBOOK_HTML_SCRIPT = ROOT / "scripts" / "check_playbook_html.py"
PRODUCTION_SAFETY_SCRIPT = ROOT / "scripts" / "check_production_safety.py"
PROJECT_LOG_SCRIPT = ROOT / "scripts" / "check_project_log.py"
READINESS_ACTIONS_SCRIPT = ROOT / "scripts" / "check_readiness_actions.py"
READINESS_ENV_PREREQS_SCRIPT = ROOT / "scripts" / "check_readiness_env_prereqs.py"
READINESS_DIAGNOSTICS_SCRIPT = ROOT / "scripts" / "check_readiness_diagnostics.py"
READINESS_OUTPUT_SCRIPT = ROOT / "scripts" / "check_readiness_output.py"
SANITIZE_OUTPUT_SCRIPT = ROOT / "scripts" / "check_sanitize_output.py"

LOCAL_FAILURES: list[str] = []
PENDING: list[str] = []
PASSED: list[str] = []

PENDING_ACTIONS = {
    "api/.env is not present; copy api/.env.example and fill deployment values": {
        "action": "Run bash scripts/init_local_env.sh, then fill deployment-only values in ignored api/.env.",
        "reference": "docs/examples/pilot-inputs-checklist.md#local-secret-baseline",
    },
    "PROXY_SECRET is not set": {
        "action": "Run bash scripts/init_local_env.sh to generate PROXY_SECRET in ignored api/.env.",
        "reference": "docs/examples/pilot-inputs-checklist.md#local-secret-baseline",
    },
    "SESSION_SECRET_KEY is not set": {
        "action": "Run bash scripts/init_local_env.sh to generate SESSION_SECRET_KEY in ignored api/.env.",
        "reference": "docs/examples/pilot-inputs-checklist.md#local-secret-baseline",
    },
    "CORS allowed origins are not restricted": {
        "action": "Set BEAVERVIEW_CORS_ORIGINS=https://beaverview in ignored api/.env before VM pilot use.",
        "reference": "docs/examples/pilot-inputs-checklist.md#production-http-origin",
    },
    "hardware IP records are not loaded yet": {
        "action": "Place the secure export at ignored api/hardware_ips.csv, run scripts/check_hardware_ip_csv.py and scripts/check_hardware_ip_import.sh, then import it from the api directory.",
        "reference": "docs/examples/pilot-inputs-checklist.md#hardware-ip-records",
    },
    "Azure redirect URI is not configured": {
        "action": "Set AZURE_REDIRECT_URI=https://beaverview/auth/callback in ignored api/.env.",
        "reference": "docs/examples/azure-entra-app-registration.md#app-registration",
    },
    "Azure app credentials are not complete": {
        "action": "Fill AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_REDIRECT_URI in ignored api/.env.",
        "reference": "docs/examples/azure-entra-app-registration.md",
    },
    "Azure technician/admin group object IDs are not complete": {
        "action": "Fill AZURE_GROUP_TECHNICIAN and AZURE_GROUP_ADMIN in ignored api/.env after assigning the Entra app groups.",
        "reference": "docs/examples/azure-entra-app-registration.md",
    },
    "Crestron poll credentials are not complete": {
        "action": "Fill CRESTRON_POLL_USERNAME and CRESTRON_POLL_PASSWORD in ignored api/.env for direct processor polling.",
        "reference": "docs/examples/pilot-inputs-checklist.md#crestron-poll-credentials",
    },
    "XPanel proxy credentials are not complete": {
        "action": "Fill CRESTRON_PROXY_USERNAME and CRESTRON_PROXY_PASSWORD in ignored api/.env for XPanel proxy testing.",
        "reference": "docs/examples/pilot-inputs-checklist.md#xpanel-proxy-credentials",
    },
    "WattBox direct proxy credentials are not complete": {
        "action": "Fill WATTBOX_DIRECT_USERNAME and WATTBOX_DIRECT_PASSWORD in ignored api/.env for direct WattBox access.",
        "reference": "docs/examples/pilot-inputs-checklist.md#wattbox-direct-proxy-credentials",
    },
    "PTZ proxy credentials are not complete": {
        "action": "Fill PTZ_PROXY_USERNAME and PTZ_PROXY_PASSWORD in ignored api/.env before live PTZ command testing.",
        "reference": "docs/examples/pilot-inputs-checklist.md#ptz-proxy-credentials",
    },
    "25Live credentials are not complete": {
        "action": "Fill LIVE25_BASE_URL, LIVE25_USERNAME, and LIVE25_PASSWORD in ignored api/.env for schedule validation.",
        "reference": "docs/examples/pilot-inputs-checklist.md#25live-credentials",
    },
    "ScreenConnect base URL is not configured": {
        "action": "Fill SC_BASE_URL in ignored api/.env; no ScreenConnect service password is stored.",
        "reference": "docs/examples/pilot-inputs-checklist.md#screenconnect-launch-url",
    },
    "SharePoint base URL is not configured": {
        "action": "Fill SHAREPOINT_BASE_URL in ignored api/.env; user auth stays in the browser session.",
        "reference": "docs/examples/pilot-inputs-checklist.md#sharepoint-launch-url",
    },
    "Hermes chat base URL is not configured": {
        "action": "Fill CHAT_BASE_URL in ignored api/.env only after the approved local Hermes endpoint is available.",
        "reference": "docs/examples/pilot-inputs-checklist.md#hermes-chat-endpoint",
    },
    "ServiceNow credentials are not complete": {
        "action": "Fill SN_INSTANCE plus either OAuth keys or service-account Basic Auth keys in ignored api/.env.",
        "reference": "docs/examples/pilot-inputs-checklist.md#servicenow-credentials",
    },
    "first live-room target and connector are not selected": {
        "action": "After OSU selects the non-critical room and first connector, set FIRST_LIVE_ROOM_ID and FIRST_LIVE_CONNECTOR in ignored api/.env.",
        "reference": "docs/examples/pilot-inputs-checklist.md#first-live-room-target",
    },
}


def run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def pass_(message: str) -> None:
    PASSED.append(message)


def fail(message: str) -> None:
    LOCAL_FAILURES.append(message)


def subprocess_failure_detail(result: subprocess.CompletedProcess[str], max_lines: int = 8, max_chars: int = 900) -> str:
    lines: list[str] = []
    for label, text in (("stdout", result.stdout), ("stderr", result.stderr)):
        for raw_line in (text or "").splitlines():
            line = redact_line(raw_line.strip())
            if line:
                lines.append(f"{label}: {line}")

    detail = f"exit {result.returncode}"
    if lines:
        detail += "; last output: " + " | ".join(lines[-max_lines:])
    if len(detail) > max_chars:
        detail = detail[: max_chars - 3].rstrip() + "..."
    return detail


def fail_with_result(message: str, result: subprocess.CompletedProcess[str]) -> None:
    fail(f"{message} ({subprocess_failure_detail(result)})")


def pending(message: str) -> None:
    PENDING.append(message)


def safe_output(value: object) -> str:
    return redact_line(str(value))


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
        fail_with_result("Python venv cannot import required backend dependencies", result)


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
        fail_with_result("data migration failed validation", result)


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
        fail_with_result("hardware IP import validation failed", result)


def check_hardware_ip_csv() -> None:
    if not HARDWARE_IP_CSV_SCRIPT.exists():
        fail("shared Hardware IP CSV validator is missing")
        return

    result = run([sys.executable, str(HARDWARE_IP_CSV_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("shared Hardware IP CSV validation rules pass")
    else:
        fail_with_result("shared Hardware IP CSV validation failed", result)


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
        fail_with_result("deployment templates failed validation", result)


def check_deployment_playbook() -> None:
    if not DEPLOYMENT_PLAYBOOK_SCRIPT.exists():
        fail("deployment playbook validator is missing")
        return

    result = run([sys.executable, str(DEPLOYMENT_PLAYBOOK_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("deployment playbook validates")
    else:
        fail_with_result("deployment playbook validation failed", result)


def check_api_contracts() -> None:
    if not API_CONTRACTS_SCRIPT.exists():
        fail("API contract validator is missing")
        return

    result = run([sys.executable, str(API_CONTRACTS_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("offline API contracts validate")
    else:
        fail_with_result("offline API contracts failed validation", result)


def check_inventory_parity() -> None:
    if not INVENTORY_PARITY_SCRIPT.exists():
        fail("inventory parity validator is missing")
        return

    result = run([sys.executable, str(INVENTORY_PARITY_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("dashboard data matches sanitized SQLite inventory")
    else:
        fail_with_result("dashboard data and sanitized SQLite inventory differ", result)


def check_dashboard_browser() -> None:
    if not BROWSER_SMOKE_SCRIPT.exists():
        fail("dashboard browser smoke validator is missing")
        return

    result = run([str(BROWSER_SMOKE_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("dashboard browser smoke validates guarded workflows")
    else:
        fail_with_result("dashboard browser smoke failed validation", result)


def check_admin_browser() -> None:
    if not ADMIN_BROWSER_SMOKE_SCRIPT.exists():
        fail("admin browser smoke validator is missing")
        return

    result = run([str(ADMIN_BROWSER_SMOKE_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("admin browser smoke validates management pages")
    else:
        fail_with_result("admin browser smoke failed validation", result)


def check_env_template() -> None:
    if not ENV_TEMPLATE_SCRIPT.exists():
        fail("environment template validator is missing")
        return

    result = run([sys.executable, str(ENV_TEMPLATE_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("environment template matches runtime env usage")
    else:
        fail_with_result("environment template validation failed", result)


def check_init_local_env() -> None:
    if not INIT_LOCAL_ENV_SCRIPT.exists():
        fail("local env bootstrap validator is missing")
        return

    result = run([sys.executable, str(INIT_LOCAL_ENV_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("local env bootstrap generates required secrets safely")
    else:
        fail_with_result("local env bootstrap validation failed", result)


def check_pilot_inputs_doc() -> None:
    if not PILOT_INPUTS_SCRIPT.exists():
        fail("pilot input checklist validator is missing")
        return

    result = run([sys.executable, str(PILOT_INPUTS_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("pilot input checklist covers external prerequisites")
    else:
        fail_with_result("pilot input checklist validation failed", result)


def check_pilot_intake_packet() -> None:
    if not PILOT_INTAKE_PACKET_SCRIPT.exists():
        fail("pilot intake packet validator is missing")
        return

    result = run([sys.executable, str(PILOT_INTAKE_PACKET_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("pilot intake packet covers readiness handoff actions")
    else:
        fail_with_result("pilot intake packet validation failed", result)


def check_playbook_html() -> None:
    if not PLAYBOOK_HTML_SCRIPT.exists():
        fail("playbook HTML validator is missing")
        return

    result = run([sys.executable, str(PLAYBOOK_HTML_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("playbook HTML matches Markdown sources")
    else:
        fail_with_result("playbook HTML validation failed", result)


def check_project_log() -> None:
    if not PROJECT_LOG_SCRIPT.exists():
        fail("project log validator is missing")
        return

    result = run([sys.executable, str(PROJECT_LOG_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("project log structure and redaction validate")
    else:
        fail_with_result("project log validation failed", result)


def check_readiness_actions() -> None:
    if not READINESS_ACTIONS_SCRIPT.exists():
        fail("readiness pending-action validator is missing")
        return

    result = run([sys.executable, str(READINESS_ACTIONS_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("readiness pending-action references validate")
    else:
        fail_with_result("readiness pending-action reference validation failed", result)


def check_readiness_env_prereqs() -> None:
    if not READINESS_ENV_PREREQS_SCRIPT.exists():
        fail("readiness env-prerequisite validator is missing")
        return

    result = run([sys.executable, str(READINESS_ENV_PREREQS_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("readiness env prerequisite classification validates")
    else:
        fail_with_result("readiness env prerequisite classification failed", result)


def check_readiness_diagnostics() -> None:
    if not READINESS_DIAGNOSTICS_SCRIPT.exists():
        fail("readiness diagnostic redaction validator is missing")
        return

    result = run([sys.executable, str(READINESS_DIAGNOSTICS_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("readiness failure diagnostics redact sensitive output")
    else:
        fail_with_result("readiness diagnostic redaction validation failed", result)


def check_readiness_output() -> None:
    if not READINESS_OUTPUT_SCRIPT.exists():
        fail("readiness output redaction validator is missing")
        return

    result = run([sys.executable, str(READINESS_OUTPUT_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("readiness human output redaction validates")
    else:
        fail_with_result("readiness human output redaction validation failed", result)


def check_sanitize_output() -> None:
    if not SANITIZE_OUTPUT_SCRIPT.exists():
        fail("shared output sanitizer validator is missing")
        return

    result = run([sys.executable, str(SANITIZE_OUTPUT_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("shared output sanitizer validates no-secrets redaction")
    else:
        fail_with_result("shared output sanitizer validation failed", result)


def check_production_safety() -> None:
    if not PRODUCTION_SAFETY_SCRIPT.exists():
        fail("production safety validator is missing")
        return

    result = run([sys.executable, str(PRODUCTION_SAFETY_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("production safety guardrails validate")
    else:
        fail_with_result("production safety guardrail validation failed", result)


def check_live_validation_doc() -> None:
    if not LIVE_VALIDATION_SCRIPT.exists():
        fail("first live-room validation doc validator is missing")
        return

    result = run([sys.executable, str(LIVE_VALIDATION_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("first live-room validation runbook covers pilot gates")
    else:
        fail_with_result("first live-room validation runbook validation failed", result)


def check_first_live_connectors() -> None:
    if not FIRST_LIVE_CONNECTORS_SCRIPT.exists():
        fail("first live-room connector alias validator is missing")
        return

    result = run([sys.executable, str(FIRST_LIVE_CONNECTORS_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("first live-room connector aliases validate")
    else:
        fail_with_result("first live-room connector alias validation failed", result)


def check_first_live_room_preflight(env: dict[str, str]) -> None:
    if not FIRST_LIVE_ROOM_PREFLIGHT_SCRIPT.exists():
        fail("first live-room preflight validator is missing")
        return

    room_id = env.get("FIRST_LIVE_ROOM_ID", "")
    connector = env.get("FIRST_LIVE_CONNECTOR", "")
    if not is_configured(room_id) or not is_configured(connector):
        pending("first live-room target and connector are not selected")
        return

    result = run([
        sys.executable,
        str(FIRST_LIVE_ROOM_PREFLIGHT_SCRIPT),
        "--room-id",
        room_id,
        "--connector",
        connector,
        "--json",
    ], cwd=ROOT)
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}

    message = payload.get("message") or "first live-room preflight did not return a message"
    if result.returncode == 0:
        pass_("first live-room preflight validates selected room and connector")
    elif result.returncode == 2:
        pending(message)
    else:
        fail(message)


def check_first_live_room_preflight_cases() -> None:
    if not FIRST_LIVE_ROOM_CASES_SCRIPT.exists():
        fail("first live-room preflight case validator is missing")
        return

    result = run([sys.executable, str(FIRST_LIVE_ROOM_CASES_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("first live-room preflight pass/pending/fail cases validate")
    else:
        fail_with_result("first live-room preflight case validation failed", result)


def check_first_live_room_report() -> None:
    if not FIRST_LIVE_ROOM_REPORT_SCRIPT.exists():
        fail("first live-room report validator is missing")
        return

    result = run([sys.executable, str(FIRST_LIVE_ROOM_REPORT_SCRIPT)], cwd=ROOT)
    if result.returncode == 0:
        pass_("first live-room report renderer validates no-secrets handoff output")
    else:
        fail_with_result("first live-room report renderer validation failed", result)


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


def cors_origins_are_restricted(value: str | None) -> bool:
    if not is_configured(value):
        return False
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    if not origins or "*" in origins:
        return False
    return all(origin.startswith("https://") for origin in origins)


def is_https_url(value: str | None) -> bool:
    return is_configured(value) and value.strip().lower().startswith("https://")


def servicenow_instance_is_host(value: str | None) -> bool:
    if not is_configured(value):
        return False
    cleaned = value.strip()
    return "://" not in cleaned and "/" not in cleaned and "." in cleaned


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

    if cors_origins_are_restricted(env.get("BEAVERVIEW_CORS_ORIGINS")):
        pass_("CORS allowed origins are restricted")
    else:
        pending("CORS allowed origins are not restricted")

    if has_all(env, ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")):
        pass_("Azure app credentials are present")
    else:
        pending("Azure app credentials are not complete")

    if has_all(env, ("AZURE_GROUP_TECHNICIAN", "AZURE_GROUP_ADMIN")):
        pass_("Azure group object IDs are present")
    else:
        pending("Azure technician/admin group object IDs are not complete")

    connector_sets = {
        "Crestron poll": ("CRESTRON_POLL_USERNAME", "CRESTRON_POLL_PASSWORD"),
        "XPanel proxy": ("CRESTRON_PROXY_USERNAME", "CRESTRON_PROXY_PASSWORD"),
        "WattBox direct proxy": ("WATTBOX_DIRECT_USERNAME", "WATTBOX_DIRECT_PASSWORD"),
        "PTZ proxy": ("PTZ_PROXY_USERNAME", "PTZ_PROXY_PASSWORD"),
    }
    for label, keys in connector_sets.items():
        if has_all(env, keys):
            pass_(f"{label} credentials are present")
        else:
            pending(f"{label} credentials are not complete")

    if has_all(env, ("LIVE25_BASE_URL", "LIVE25_USERNAME", "LIVE25_PASSWORD")):
        if is_https_url(env.get("LIVE25_BASE_URL")):
            pass_("25Live credentials are present")
        else:
            fail("25Live base URL must use https")
    elif is_configured(env.get("LIVE25_BASE_URL")) and not is_https_url(env.get("LIVE25_BASE_URL")):
        fail("25Live base URL must use https")
    else:
        pending("25Live credentials are not complete")

    launch_urls = {
        "ScreenConnect base URL": "SC_BASE_URL",
        "SharePoint base URL": "SHAREPOINT_BASE_URL",
        "Hermes chat base URL": "CHAT_BASE_URL",
    }
    for label, key in launch_urls.items():
        if key == "CHAT_BASE_URL":
            continue
        if is_configured(env.get(key)):
            if is_https_url(env.get(key)):
                pass_(f"{label} is configured")
            else:
                fail(f"{label} must use https")
        else:
            pending(f"{label} is not configured")

    if is_configured(env.get("CHAT_BASE_URL")):
        pass_("Hermes chat base URL is configured")
    else:
        pending("Hermes chat base URL is not configured")

    servicenow_oauth = has_all(env, ("SN_INSTANCE", "SN_CLIENT_ID", "SN_CLIENT_SECRET"))
    servicenow_basic = has_all(env, ("SN_INSTANCE", "SN_USERNAME", "SN_PASSWORD"))
    if servicenow_oauth or servicenow_basic:
        if servicenow_instance_is_host(env.get("SN_INSTANCE")):
            pass_("ServiceNow credentials are present")
        else:
            fail("ServiceNow instance must be a host name without scheme or path")
    else:
        pending("ServiceNow credentials are not complete")

    check_first_live_room_preflight(env)


def run_checks() -> None:
    check_git()
    check_sensitive_paths()
    check_python_env()
    check_data_migration()
    check_db()
    check_hardware_ip_csv()
    check_hardware_ip_import()
    check_deployment_assets()
    check_deployment_playbook()
    check_api_contracts()
    check_inventory_parity()
    check_dashboard_browser()
    check_admin_browser()
    check_env_template()
    check_init_local_env()
    check_pilot_inputs_doc()
    check_pilot_intake_packet()
    check_playbook_html()
    check_project_log()
    check_readiness_actions()
    check_readiness_env_prereqs()
    check_sanitize_output()
    check_readiness_output()
    check_readiness_diagnostics()
    check_production_safety()
    check_live_validation_doc()
    check_first_live_connectors()
    check_first_live_room_preflight_cases()
    check_first_live_room_report()
    check_env_prereqs()


def readiness_result() -> dict:
    pending_actions = [
        {
            "pending": item,
            **PENDING_ACTIONS.get(
                item,
                {
                    "action": "Review docs/examples/pilot-inputs-checklist.md and update ignored local deployment inputs.",
                    "reference": "docs/examples/pilot-inputs-checklist.md",
                },
            ),
        }
        for item in PENDING
    ]
    return {
        "status": "fail" if LOCAL_FAILURES else "pass",
        "passed": PASSED,
        "pending": PENDING,
        "pending_actions": pending_actions,
        "failures": LOCAL_FAILURES,
        "passed_count": len(PASSED),
        "pending_count": len(PENDING),
        "failure_count": len(LOCAL_FAILURES),
    }


def print_text_result(result: dict) -> None:
    print("BeaverView pilot-readiness preflight")
    print()
    for item in result["passed"]:
        print(f"PASS    {safe_output(item)}")
    for item in result["pending"]:
        print(f"PENDING {safe_output(item)}")
    for item in result["failures"]:
        print(f"FAIL    {safe_output(item)}")

    if result["pending_actions"]:
        print()
        print("Next actions")
        for item in result["pending_actions"]:
            pending_text = safe_output(item["pending"])
            action = safe_output(item["action"])
            reference = safe_output(item["reference"])
            print(f"- {pending_text}: {action} See {reference}.")

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
        print(f"- {safe_output(item)}")
    if not result["passed"]:
        print("- None")
    print()

    print("## Pending External Prerequisites")
    print()
    for item in result["pending"]:
        print(f"- {safe_output(item)}")
    if not result["pending"]:
        print("- None")
    print()

    print("## Pending Next Actions")
    print()
    for item in result["pending_actions"]:
        pending_text = safe_output(item["pending"])
        action = safe_output(item["action"])
        reference = safe_output(item["reference"])
        print(f"- **{pending_text}**: {action} See `{reference}`.")
    if not result["pending_actions"]:
        print("- None")
    print()

    print("## Local Failures")
    print()
    for item in result["failures"]:
        print(f"- {safe_output(item)}")
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
