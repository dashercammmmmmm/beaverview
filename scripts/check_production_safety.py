#!/usr/bin/env python3
"""Validate production-safety guardrails that should not drift before pilot."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_MAIN = ROOT / "api" / "main.py"
ENV_EXAMPLE = ROOT / "api" / ".env.example"
APP_JS = ROOT / "dashboard" / "app.js"
INDEX_HTML = ROOT / "dashboard" / "index.html"
PLAYBOOK = ROOT / "PLAYBOOK-DEPLOYMENT.md"


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"expected file is missing: {path.relative_to(ROOT)}")
    return path.read_text()


def main() -> int:
    api_main = read(API_MAIN)
    env_example = read(ENV_EXAMPLE)
    app_js = read(APP_JS)
    index_html = read(INDEX_HTML)
    playbook = read(PLAYBOOK)

    expect(
        'os.getenv("BEAVERVIEW_CORS_ORIGINS", "*")' in api_main,
        "api/main.py must source CORS origins from BEAVERVIEW_CORS_ORIGINS",
    )
    expect(
        "allow_origins=_CORS_ORIGINS" in api_main,
        "api/main.py must not hardcode CORSMiddleware allow_origins",
    )
    expect(
        'allow_origins=["*"]' not in api_main,
        "api/main.py still hardcodes wildcard CORS origins",
    )
    expect(
        "BEAVERVIEW_DB_PATH" not in env_example,
        "api/.env.example must not document the test-only BEAVERVIEW_DB_PATH override",
    )
    expect(
        "BEAVERVIEW_DB_PATH" not in playbook,
        "deployment playbook must not use the test-only BEAVERVIEW_DB_PATH override",
    )

    dev_helper_guard = re.search(
        r"function isLocalDevHost\(\).*?if \(isLocalDevHost\(\)\) \{\s*window\._dev =",
        app_js,
        re.DOTALL,
    )
    expect(dev_helper_guard is not None, "dashboard/app.js must guard window._dev behind isLocalDevHost()")
    expect(
        '"localhost", "127.0.0.1", "::1"' in app_js,
        "dashboard/app.js local dev host allowlist changed unexpectedly",
    )

    expect(
        "location.hostname !== 'localhost' && location.hostname !== '127.0.0.1'" in index_html,
        "dashboard/index.html live reload must stay localhost-only",
    )

    expect(
        "BEAVERVIEW_CORS_ORIGINS=https://beaverview" in playbook,
        "deployment playbook must tell operators to set the production CORS origin",
    )
    forbidden_playbook_text = (
        'change `allow_origins=["*"]`',
        "delete the `window._dev",
        "delete the `<!-- Live reload -->`",
    )
    for text in forbidden_playbook_text:
        expect(text not in playbook, f"deployment playbook still asks for a manual source edit: {text}")

    print("Production safety guardrails verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
