#!/usr/bin/env python3
"""Validate readiness pending-action references without running readiness."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "scripts" / "check_pilot_readiness.py"


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def markdown_anchor(text: str) -> str:
    value = text.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"\s+", "-", value)
    return value


def markdown_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    for line in path.read_text().splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            anchors.add(markdown_anchor(match.group(1)))
    return anchors


def literal_pending_actions() -> dict[str, dict[str, str]]:
    if not READINESS.exists():
        fail("scripts/check_pilot_readiness.py is missing")

    module = ast.parse(READINESS.read_text())
    for node in module.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "PENDING_ACTIONS" for target in node.targets):
                value: Any = ast.literal_eval(node.value)
                if not isinstance(value, dict):
                    fail("PENDING_ACTIONS is not a dict literal")
                return value
    fail("PENDING_ACTIONS mapping is missing")


def main() -> int:
    actions = literal_pending_actions()
    expect(actions, "PENDING_ACTIONS is empty")

    for pending, item in actions.items():
        expect(isinstance(pending, str) and pending.strip(), "pending action key is empty")
        expect(isinstance(item, dict), f"pending action for {pending!r} is not an object")
        action = item.get("action", "")
        reference = item.get("reference", "")
        expect(isinstance(action, str) and action.strip(), f"pending action for {pending!r} has no action")
        expect(isinstance(reference, str) and reference.strip(), f"pending action for {pending!r} has no reference")
        expect("your-" not in action.lower(), f"pending action for {pending!r} contains placeholder wording")

        ref_path, _, anchor = reference.partition("#")
        path = ROOT / ref_path
        expect(path.exists(), f"pending action reference does not exist for {pending!r}: {reference}")
        if anchor:
            expect(path.suffix.lower() == ".md", f"anchor reference is not a Markdown file for {pending!r}: {reference}")
            anchors = markdown_anchors(path)
            expect(anchor in anchors, f"anchor #{anchor} not found in {ref_path} for {pending!r}")

    print(f"Readiness pending actions verified: {len(actions)} mappings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
