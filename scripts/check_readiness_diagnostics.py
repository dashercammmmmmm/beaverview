#!/usr/bin/env python3
"""Validate pilot-readiness failure diagnostics stay sanitized."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
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


def main() -> int:
    readiness = load_readiness_module()
    redacted_line = readiness.redact_line("CLIENT_SECRET=super-secret 10.42.7.9")
    expect("super-secret" not in redacted_line, "readiness should import the shared sanitizer")
    expect("10.42.7.9" not in redacted_line, "readiness should redact IPs through the shared sanitizer")

    result = subprocess.CompletedProcess(
        args=["example-validator"],
        returncode=7,
        stdout="\n".join(
            [
                "Connecting to 10.42.7.9",
                "CLIENT_SECRET=super-secret-value",
                "authorization: Bearer abc.def.ghi",
                "http://127.0.0.1:8027/api/health ok",
            ]
        ),
        stderr="password = letmein\n",
    )

    detail = readiness.subprocess_failure_detail(result)
    expect("exit 7" in detail, "diagnostic detail should include exit code")
    expect("127.0.0.1:8027" in detail, "localhost diagnostics should remain visible")
    for forbidden in ("10.42.7.9", "super-secret-value", "abc.def.ghi", "letmein"):
        expect(forbidden not in detail, f"diagnostic detail leaked {forbidden!r}: {detail}")
    expect("<redacted-ip>" in detail, "non-local IPv4 addresses should be redacted")
    expect("<redacted>" in detail, "secret-like values should be redacted")

    print("Readiness diagnostic redaction verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
