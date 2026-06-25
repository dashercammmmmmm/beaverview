#!/usr/bin/env python3
"""Validate shared readiness/report output sanitizers."""

from __future__ import annotations

import sys

from sanitize_output import redact_line


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> int:
    raw = (
        "Authorization: Bearer abc.def.ghi "
        "CLIENT_SECRET=super-secret "
        "password: letmein "
        "device=10.77.1.25 "
        "health=http://127.0.0.1:8027/api/health"
    )
    redacted = redact_line(raw)
    for forbidden in ("abc.def.ghi", "super-secret", "letmein", "10.77.1.25"):
        expect(forbidden not in redacted, f"sanitizer leaked {forbidden!r}: {redacted}")
    expect("Authorization: Bearer <redacted>" in redacted, "authorization header was not redacted")
    expect("CLIENT_SECRET=<redacted>" in redacted, "secret assignment was not redacted")
    expect("password: <redacted>" in redacted, "generic secret was not redacted")
    expect("<redacted-ip>" in redacted, "non-local IPv4 address was not redacted")
    expect("127.0.0.1:8027" in redacted, "localhost diagnostic context should remain visible")

    print("Shared output sanitizer verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
