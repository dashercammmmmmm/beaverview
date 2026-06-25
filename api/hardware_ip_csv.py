"""Shared validation helpers for BeaverView Hardware IP CSV files."""

from __future__ import annotations

import csv
import ipaddress
from pathlib import Path

HardwareRow = tuple[str, str, str]
REQUIRED_COLUMNS = {"room_id", "device_type", "ip_address"}


class HardwareCsvError(ValueError):
    """Raised when Hardware IP CSV data fails validation."""


def validate_ip_address(ip_address: str, row_number: int, *, allow_public: bool = False) -> str:
    try:
        parsed = ipaddress.ip_address(ip_address)
    except ValueError as exc:
        raise HardwareCsvError(f"invalid IP address in CSV row {row_number}") from exc
    if parsed.is_loopback or parsed.is_unspecified or parsed.is_multicast:
        raise HardwareCsvError(f"non-proxyable IP address in CSV row {row_number}")
    if not allow_public and not (parsed.is_private or parsed.is_link_local):
        raise HardwareCsvError(f"public IP address in CSV row {row_number}; use --allow-public only after network review")
    return str(parsed)


def load_hardware_rows(csv_path: str | Path, *, allow_public: bool = False) -> list[HardwareRow]:
    path = Path(csv_path)
    if not path.exists():
        raise HardwareCsvError(f"file not found: {path}")

    rows: list[HardwareRow] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise HardwareCsvError("CSV missing required columns: " + ", ".join(sorted(missing)))
        for line in reader:
            row_number = reader.line_num
            room_id = (line.get("room_id") or "").strip().lower()
            device_type = (line.get("device_type") or "").strip().lower()
            ip_raw = (line.get("ip_address") or "").strip()
            missing_fields = [
                field
                for field, value in (
                    ("room_id", room_id),
                    ("device_type", device_type),
                    ("ip_address", ip_raw),
                )
                if not value
            ]
            if missing_fields:
                raise HardwareCsvError(f"CSV row {row_number} missing required field(s): {', '.join(missing_fields)}")
            ip_address = validate_ip_address(ip_raw, row_number, allow_public=allow_public)
            rows.append((room_id, device_type, ip_address))

    if not rows:
        raise HardwareCsvError("CSV contains no importable rows")

    validate_unique_device_targets(rows)
    return rows


def validate_unique_device_targets(rows: list[HardwareRow]) -> None:
    seen: set[tuple[str, str]] = set()
    duplicates: list[str] = []
    for room_id, device_type, _ in rows:
        key = (room_id, device_type)
        if key in seen:
            duplicates.append(f"{room_id}/{device_type}")
        seen.add(key)

    if duplicates:
        preview = ", ".join(sorted(set(duplicates))[:8])
        if len(set(duplicates)) > 8:
            preview += f", ... ({len(set(duplicates))} total)"
        raise HardwareCsvError(f"duplicate room/device mapping in CSV: {preview}")


def room_device_counts(rows: list[HardwareRow]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for room_id, device_type, _ in rows:
        room_counts = counts.setdefault(room_id, {})
        room_counts[device_type] = room_counts.get(device_type, 0) + 1
    return counts
