#!/usr/bin/env python3
"""Validate shared first live-room connector aliases."""

from __future__ import annotations

import sys

from first_live_connectors import normalize_connector


CASES = {
    "crestron": "crestron_poll",
    "crestron-polling": "crestron_poll",
    "service-now": "servicenow",
    "live25": "25live",
    "25-live": "25live",
    "xpanel": "xpanel",
    "": "",
}


def main() -> int:
    for raw, expected in CASES.items():
        actual = normalize_connector(raw)
        if actual != expected:
            print(f"FAIL connector alias {raw!r} normalized to {actual!r}, expected {expected!r}", file=sys.stderr)
            return 1
    print("First live-room connector aliases verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
