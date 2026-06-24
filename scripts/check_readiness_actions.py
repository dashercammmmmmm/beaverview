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
ALLOWED_DYNAMIC_PENDING = {
    'pending(f"{label} credentials are not complete")',
    'pending(f"{label} is not configured")',
    "pending(message)",
}


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


def readiness_source() -> tuple[str, ast.Module]:
    if not READINESS.exists():
        fail("scripts/check_pilot_readiness.py is missing")

    source = READINESS.read_text()
    return source, ast.parse(source)


def literal_pending_actions(module: ast.Module) -> dict[str, dict[str, str]]:
    for node in module.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "PENDING_ACTIONS" for target in node.targets):
                value: Any = ast.literal_eval(node.value)
                if not isinstance(value, dict):
                    fail("PENDING_ACTIONS is not a dict literal")
                return value
    fail("PENDING_ACTIONS mapping is missing")


def dict_literal_named(module: ast.Module, name: str) -> dict[str, Any]:
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            value: Any = ast.literal_eval(node.value)
            if not isinstance(value, dict):
                fail(f"{name} is not a dict literal")
            return value
    fail(f"{name} mapping is missing")


def pending_calls(source: str, module: ast.Module) -> tuple[set[str], set[str], list[str]]:
    literals: set[str] = set()
    dynamic_source: set[str] = set()
    unsupported: list[str] = []

    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "pending":
            continue
        if not node.args:
            unsupported.append(f"line {node.lineno}: pending call has no message")
            continue

        message = node.args[0]
        if isinstance(message, ast.Constant) and isinstance(message.value, str):
            literals.add(message.value)
            continue

        call_source = ast.get_source_segment(source, node) or f"line {node.lineno}"
        dynamic_source.add(call_source)
        if call_source not in ALLOWED_DYNAMIC_PENDING:
            unsupported.append(f"line {node.lineno}: unsupported dynamic pending message: {call_source}")

    return literals, dynamic_source, unsupported


def expected_dynamic_pending_messages(module: ast.Module) -> set[str]:
    connector_sets = dict_literal_named(module, "connector_sets")
    launch_urls = dict_literal_named(module, "launch_urls")
    messages: set[str] = set()
    messages.update(f"{label} credentials are not complete" for label in connector_sets)
    messages.update(f"{label} is not configured" for label in launch_urls)
    return messages


def main() -> int:
    source, module = readiness_source()
    actions = literal_pending_actions(module)
    expect(actions, "PENDING_ACTIONS is empty")

    literal_messages, dynamic_messages, unsupported_dynamic = pending_calls(source, module)
    expect(not unsupported_dynamic, "\n".join(unsupported_dynamic))
    missing_literal_actions = sorted(literal_messages - set(actions))
    expect(
        not missing_literal_actions,
        "literal pending messages missing PENDING_ACTIONS entries: "
        + ", ".join(repr(item) for item in missing_literal_actions),
    )

    expected_dynamic_actions = expected_dynamic_pending_messages(module)
    missing_dynamic_actions = sorted(expected_dynamic_actions - set(actions))
    expect(
        not missing_dynamic_actions,
        "dynamic pending messages missing PENDING_ACTIONS entries: "
        + ", ".join(repr(item) for item in missing_dynamic_actions),
    )
    expect(
        dynamic_messages <= ALLOWED_DYNAMIC_PENDING,
        "dynamic pending calls must be added to ALLOWED_DYNAMIC_PENDING before use",
    )

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

    print(
        "Readiness pending actions verified: "
        f"{len(actions)} mappings, {len(literal_messages)} literal pending messages, "
        f"{len(expected_dynamic_actions)} loop-generated pending messages"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
