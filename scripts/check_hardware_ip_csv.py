#!/usr/bin/env python3
"""Validate shared Hardware IP CSV parsing rules without printing raw IPs."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
RAW_IP_SENTINEL = "10.77.1.25"
PUBLIC_IP_SENTINEL = "8.8.8.8"

sys.path.insert(0, str(API_DIR))
from hardware_ip_csv import HardwareCsvError, load_hardware_rows, room_device_counts  # noqa: E402


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def expect_error(path: Path, expected: str, *, allow_public: bool = False, raw_value: str = RAW_IP_SENTINEL) -> None:
    try:
        load_hardware_rows(path, allow_public=allow_public)
    except HardwareCsvError as exc:
        message = str(exc)
        expect(expected in message, f"expected {expected!r} in error {message!r}")
        expect(raw_value not in message, f"Hardware CSV error leaked raw value {raw_value!r}: {message}")
        return
    fail(f"expected Hardware CSV validation to fail for {path.name}")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        valid = tmp_dir / "hardware_ips.valid.csv"
        valid.write_text(
            "room_id,device_type,ip_address,notes\n"
            f"corvallis-kad-101,xpanel,{RAW_IP_SENTINEL},processor\n"
            "corvallis-kad-101,wattbox,10.77.1.26,power\n"
        )
        rows = load_hardware_rows(valid)
        expect(rows == [("corvallis-kad-101", "xpanel", RAW_IP_SENTINEL), ("corvallis-kad-101", "wattbox", "10.77.1.26")], "valid Hardware CSV rows changed")
        counts = room_device_counts(rows)
        expect(counts == {"corvallis-kad-101": {"xpanel": 1, "wattbox": 1}}, f"room/device counts changed: {json.dumps(counts, sort_keys=True)}")

        public = tmp_dir / "hardware_ips.public.csv"
        public.write_text(
            "room_id,device_type,ip_address,notes\n"
            f"corvallis-kad-101,xpanel,{PUBLIC_IP_SENTINEL},public\n"
        )
        expect_error(public, "public IP address", raw_value=PUBLIC_IP_SENTINEL)
        public_rows = load_hardware_rows(public, allow_public=True)
        expect(public_rows == [("corvallis-kad-101", "xpanel", PUBLIC_IP_SENTINEL)], "allow_public path changed")

        duplicate = tmp_dir / "hardware_ips.duplicate.csv"
        duplicate.write_text(
            "room_id,device_type,ip_address,notes\n"
            f"corvallis-kad-101,xpanel,{RAW_IP_SENTINEL},first\n"
            "corvallis-kad-101,xpanel,10.77.1.26,duplicate\n"
        )
        expect_error(duplicate, "duplicate room/device mapping")

        blank = tmp_dir / "hardware_ips.blank.csv"
        blank.write_text(
            "room_id,device_type,ip_address,notes\n"
            f"corvallis-kad-101,,{RAW_IP_SENTINEL},blank device type\n"
        )
        expect_error(blank, "missing required field")

        missing_column = tmp_dir / "hardware_ips.missing-column.csv"
        missing_column.write_text(
            "room_id,device_type,notes\n"
            "corvallis-kad-101,xpanel,no IP column\n"
        )
        expect_error(missing_column, "missing required columns")

        invalid = tmp_dir / "hardware_ips.invalid.csv"
        invalid.write_text(
            "room_id,device_type,ip_address,notes\n"
            "corvallis-kad-101,xpanel,not-an-ip,invalid\n"
        )
        expect_error(invalid, "invalid IP address", raw_value="not-an-ip")

        loopback = tmp_dir / "hardware_ips.loopback.csv"
        loopback.write_text(
            "room_id,device_type,ip_address,notes\n"
            "corvallis-kad-101,xpanel,127.0.0.1,loopback\n"
        )
        expect_error(loopback, "non-proxyable IP address", raw_value="127.0.0.1")

    print("Shared Hardware IP CSV validation verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
