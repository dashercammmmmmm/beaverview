#!/usr/bin/env python3
"""Validate the VM deployment playbook against committed BeaverView assets."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "PLAYBOOK-DEPLOYMENT.md"
REQUIREMENTS = ROOT / "api" / "requirements.txt"

REQUIRED_TEXT = (
    "Ubuntu 22.04 or 24.04 VM",
    "sudo apt install python3 python3-venv python3-pip sqlite3 nginx -y",
    "sudo -u beaverview python3 -m venv venv",
    "sudo -u beaverview venv/bin/pip install -r requirements.txt",
    "sudo -u beaverview bash scripts/init_local_env.sh",
    "BEAVERVIEW_CORS_ORIGINS=https://beaverview",
    "sudo cp /home/beaverview/app/deploy/systemd/beaverview.service /etc/systemd/system/beaverview.service",
    "sudo systemctl daemon-reload",
    "sudo systemctl enable beaverview",
    "sudo systemctl start beaverview",
    "sudo scripts/generate_self_signed_cert.sh 192.168.1.50",
    "scripts/render_nginx_config.sh 192.168.1.50 /tmp/beaverview.nginx",
    "sudo nginx -t",
    "curl -k https://localhost/api/health",
    "AZURE_REDIRECT_URI=https://beaverview/auth/callback",
    "sudo -u beaverview /home/beaverview/app/api/venv/bin/python -c",
    "python3 scripts/check_pilot_readiness.py",
)

FORBIDDEN_TEXT = (
    "pip install msal",
    "tee -a /home/beaverview/app/api/requirements.txt",
    'allow_origins=["*"]',
    "delete the `window._dev",
    "delete the `<!-- Live reload -->`",
)


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> int:
    if not PLAYBOOK.exists():
        fail("PLAYBOOK-DEPLOYMENT.md is missing")
    if not REQUIREMENTS.exists():
        fail("api/requirements.txt is missing")

    playbook = PLAYBOOK.read_text()
    requirements = REQUIREMENTS.read_text()

    missing = [text for text in REQUIRED_TEXT if text not in playbook]
    expect(not missing, "deployment playbook is missing required text: " + ", ".join(missing))

    forbidden = [text for text in FORBIDDEN_TEXT if text in playbook]
    expect(not forbidden, "deployment playbook contains stale or unsafe text: " + ", ".join(forbidden))

    expect("msal>=1.28.0" in requirements, "api/requirements.txt must own the MSAL dependency")
    expect(
        re.search(r"^### Step 6 .+Verify Python dependencies", playbook, re.MULTILINE) is not None,
        "deployment playbook Part 6 Step 6 must verify dependencies, not install ad hoc packages",
    )
    expect(
        re.search(r"^### Step 7 .+Run pilot readiness", playbook, re.MULTILINE) is not None,
        "deployment playbook Part 6 Step 7 must run pilot readiness before login testing",
    )

    print(f"Deployment playbook verified: {len(REQUIRED_TEXT)} required terms covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
