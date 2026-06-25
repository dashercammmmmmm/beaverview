#!/usr/bin/env python3
"""Validate human-facing readiness output stays sanitized."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "scripts" / "check_pilot_readiness.py"
RAW_IP_SENTINEL = "10.77.1.25"
SECRET_SENTINEL = "super-secret-value"
TOKEN_SENTINEL = "abc.def.ghi"


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


def render_output(readiness, mode: str, result: dict) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        if mode == "text":
            readiness.print_text_result(result)
        elif mode == "markdown":
            readiness.print_markdown_result(result)
        else:
            fail(f"unsupported render mode: {mode}")
    return buffer.getvalue()


def main() -> int:
    readiness = load_readiness_module()
    result = {
        "status": "pass",
        "passed_count": 1,
        "pending_count": 1,
        "failure_count": 1,
        "passed": [
            "local health at http://127.0.0.1:8027/api/health passed",
            f"device probe reached {RAW_IP_SENTINEL}",
        ],
        "pending": [
            f"waiting on CLIENT_SECRET={SECRET_SENTINEL}",
        ],
        "pending_actions": [
            {
                "pending": f"hardware IP includes {RAW_IP_SENTINEL}",
                "action": f"Set Authorization: Bearer {TOKEN_SENTINEL} and PASSWORD={SECRET_SENTINEL}",
                "reference": f"docs/examples/pilot-inputs-checklist.md#device-{RAW_IP_SENTINEL}",
            }
        ],
        "failures": [
            f"backend returned password: {SECRET_SENTINEL}",
        ],
    }

    output = render_output(readiness, "text", result) + render_output(readiness, "markdown", result)
    for forbidden in (RAW_IP_SENTINEL, SECRET_SENTINEL, TOKEN_SENTINEL):
        expect(forbidden not in output, f"readiness human output leaked {forbidden!r}: {output}")
    expect("<redacted-ip>" in output, "readiness human output should redact non-local IPs")
    expect("<redacted>" in output, "readiness human output should redact secret-like values")
    expect("127.0.0.1:8027" in output, "readiness human output should preserve localhost diagnostics")

    print("Readiness human output redaction verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
