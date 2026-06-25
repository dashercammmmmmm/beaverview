#!/usr/bin/env python3
"""Validate the durable BeaverView project log structure and safety."""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from sanitize_output import AUTH_HEADER_RE, IPV4_RE


ROOT = Path(__file__).resolve().parents[1]
PROJECT_LOG = ROOT / "PROJECT-LOG.md"
ENTRY_RE = re.compile(r"^## (?P<date>\d{4}-\d{2}-\d{2}) - (?P<title>.+)$")
SECRET_ASSIGNMENT_RE = re.compile(
    r"\b("
    r"[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY|APIKEY|CLIENT_SECRET|PRIVATE_KEY|SESSION_KEY)[A-Z0-9_]*"
    r"|password|passwd|token|api[_-]?key|client[_-]?secret"
    r")(\s*[=:]\s*)([^\s,;]+)"
)


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def entry_sections(lines: list[str]) -> list[tuple[int, int, re.Match[str]]]:
    headings: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = ENTRY_RE.match(line)
        if match:
            headings.append((index, match))

    sections: list[tuple[int, int, re.Match[str]]] = []
    for offset, (start, match) in enumerate(headings):
        end = headings[offset + 1][0] if offset + 1 < len(headings) else len(lines)
        sections.append((start, end, match))
    return sections


def validate_no_sensitive_output(lines: list[str]) -> None:
    for line_number, line in enumerate(lines, start=1):
        if AUTH_HEADER_RE.search(line) or SECRET_ASSIGNMENT_RE.search(line):
            fail(f"PROJECT-LOG.md line {line_number} contains unredacted sensitive-looking text")
        for match in IPV4_RE.finditer(line):
            ip = match.group("ip")
            if not (ip.startswith("127.") or ip == "0.0.0.0"):
                fail(f"PROJECT-LOG.md line {line_number} contains a raw non-local IPv4 address")


def validate_entries(lines: list[str]) -> int:
    sections = entry_sections(lines)
    expect(sections, "PROJECT-LOG.md has no dated entries")

    previous_date: date | None = None
    for start, end, match in sections:
        try:
            entry_date = date.fromisoformat(match.group("date"))
        except ValueError as exc:
            raise AssertionError("unreachable: ENTRY_RE only matches ISO dates") from exc
        title = match.group("title").strip()
        expect(title, f"PROJECT-LOG.md entry on line {start + 1} has an empty title")
        if previous_date is not None:
            expect(
                entry_date <= previous_date,
                f"PROJECT-LOG.md entries must be newest-first: line {start + 1}",
            )
        previous_date = entry_date

        body = lines[start + 1 : end]
        expect(any(line.startswith("- ") for line in body), f"PROJECT-LOG.md entry {title!r} has no summary bullet")
        expect("### Next" in body, f"PROJECT-LOG.md entry {title!r} is missing a Next section")
        next_index = body.index("### Next")
        expect(
            any(line.startswith("- ") for line in body[next_index + 1 :]),
            f"PROJECT-LOG.md entry {title!r} has no Next bullet",
        )
    return len(sections)


def main() -> int:
    if not PROJECT_LOG.exists():
        fail("PROJECT-LOG.md is missing")

    lines = PROJECT_LOG.read_text().splitlines()
    expect(lines[:1] == ["# BeaverView Project Log"], "PROJECT-LOG.md title is missing or changed")
    expect(
        any("source of truth" in line for line in lines[:6]),
        "PROJECT-LOG.md must identify the Mac Mini checkout as the source of truth",
    )
    validate_no_sensitive_output(lines)
    count = validate_entries(lines)

    print(f"Project log verified: {count} dated entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
