"""Shared no-secrets output sanitizers for local readiness and pilot handoff tools."""

from __future__ import annotations

import re


AUTH_HEADER_RE = re.compile(r"(?i)\b(authorization:\s*(?:bearer|basic)\s+)[A-Za-z0-9._~+/=-]+")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b([A-Z0-9_-]*(?:PASSWORD|SECRET|TOKEN|API[_-]?KEY|CLIENT[_-]?SECRET|PRIVATE[_-]?KEY|SESSION[_-]?KEY)[A-Z0-9_-]*)"
    r"(\s*[=:]\s*)"
    r"([^\s,;]+)"
)
GENERIC_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|client[_-]?secret)"
    r"(\s*[=:]\s*)"
    r"([^\s,;]+)"
)
IPV4_RE = re.compile(r"\b(?P<ip>(?:\d{1,3}\.){3}\d{1,3})(?P<port>:\d+)?\b")


def redact_line(line: str) -> str:
    """Redact secret-like values and non-local IPv4 addresses from one output line."""

    def redact_ip(match: re.Match[str]) -> str:
        ip = match.group("ip")
        port = match.group("port") or ""
        if ip.startswith("127.") or ip == "0.0.0.0":
            return f"{ip}{port}"
        return f"<redacted-ip>{port}"

    line = AUTH_HEADER_RE.sub(r"\1<redacted>", line)
    line = SECRET_ASSIGNMENT_RE.sub(r"\1\2<redacted>", line)
    line = GENERIC_SECRET_RE.sub(r"\1\2<redacted>", line)
    return IPV4_RE.sub(redact_ip, line)
