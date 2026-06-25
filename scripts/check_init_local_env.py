#!/usr/bin/env python3
"""Validate local api/.env bootstrap behavior without touching real api/.env."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "init_local_env.sh"
ENV_EXAMPLE = ROOT / "api" / ".env.example"
SECRET_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def run_bootstrap(temp_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(temp_root / "scripts" / "init_local_env.sh")],
        cwd=temp_root,
        text=True,
        capture_output=True,
    )


def assert_no_secret_output(result: subprocess.CompletedProcess[str], secrets: tuple[str, ...]) -> None:
    output = f"{result.stdout}\n{result.stderr}"
    for secret in secrets:
        expect(secret not in output, "init_local_env.sh printed a generated secret value")


def main() -> int:
    expect(SCRIPT.exists(), "scripts/init_local_env.sh is missing")
    expect(ENV_EXAMPLE.exists(), "api/.env.example is missing")

    with tempfile.TemporaryDirectory() as tmp:
        temp_root = Path(tmp)
        (temp_root / "scripts").mkdir()
        (temp_root / "api").mkdir()
        shutil.copy2(SCRIPT, temp_root / "scripts" / "init_local_env.sh")
        shutil.copy2(ENV_EXAMPLE, temp_root / "api" / ".env.example")

        first = run_bootstrap(temp_root)
        expect(first.returncode == 0, f"init_local_env.sh first run failed: {first.stderr or first.stdout}")
        env_path = temp_root / "api" / ".env"
        expect(env_path.exists(), "init_local_env.sh did not create api/.env")
        mode = stat.S_IMODE(env_path.stat().st_mode)
        expect(mode == 0o600, f"api/.env mode should be 600, got {oct(mode)}")

        values = parse_env(env_path)
        proxy_secret = values.get("PROXY_SECRET", "")
        session_secret = values.get("SESSION_SECRET_KEY", "")
        expect(SECRET_RE.match(proxy_secret) is not None, "PROXY_SECRET was not generated as 64 hex characters")
        expect(SECRET_RE.match(session_secret) is not None, "SESSION_SECRET_KEY was not generated as 64 hex characters")
        expect(proxy_secret != session_secret, "generated local secrets should be distinct")
        assert_no_secret_output(first, (proxy_secret, session_secret))

        before = env_path.read_text()
        second = run_bootstrap(temp_root)
        expect(second.returncode == 0, f"init_local_env.sh second run failed: {second.stderr or second.stdout}")
        expect(env_path.read_text() == before, "init_local_env.sh should not rewrite existing local secrets")
        assert_no_secret_output(second, (proxy_secret, session_secret))

    print("Local env bootstrap verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
