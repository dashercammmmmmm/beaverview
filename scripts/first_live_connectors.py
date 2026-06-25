"""Shared first live-room connector naming helpers."""

from __future__ import annotations

from typing import Any


CONNECTOR_ALIASES = {
    "live25": "25live",
    "25_live": "25live",
    "crestron": "crestron_poll",
    "crestron_polling": "crestron_poll",
    "service_now": "servicenow",
}


def normalize_connector(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    return CONNECTOR_ALIASES.get(normalized, normalized)
