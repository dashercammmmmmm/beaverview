#!/usr/bin/env python3
"""Validate committed playbook HTML is current with Markdown sources."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import build_playbook_html


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
COMMITTED_HTML = DOCS / "html"


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def compare_file(generated: Path, committed: Path) -> None:
    expect(committed.exists(), f"committed HTML is missing: {committed.relative_to(ROOT)}")
    expect(
        generated.read_text(encoding="utf-8") == committed.read_text(encoding="utf-8"),
        f"committed HTML is stale: {committed.relative_to(ROOT)}; run python3 scripts/build_playbook_html.py",
    )


def main() -> int:
    expect(COMMITTED_HTML.exists(), "docs/html directory is missing")
    for filename in build_playbook_html.FILES:
        expect((DOCS / filename).exists(), f"Markdown playbook is missing: docs/{filename}")

    with tempfile.TemporaryDirectory() as tmp:
        generated_html = Path(tmp) / "html"
        original_html_dir = build_playbook_html.HTML_DIR
        try:
            build_playbook_html.HTML_DIR = generated_html
            build_playbook_html.main()
        finally:
            build_playbook_html.HTML_DIR = original_html_dir

        for filename in build_playbook_html.FILES:
            html_name = Path(filename).with_suffix(".html").name
            compare_file(generated_html / html_name, COMMITTED_HTML / html_name)
        compare_file(generated_html / "index.html", COMMITTED_HTML / "index.html")

    print(f"Playbook HTML verified: {len(build_playbook_html.FILES) + 1} files current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
