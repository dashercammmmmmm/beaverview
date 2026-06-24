#!/usr/bin/env python3
"""Browser smoke check for the BeaverView admin panel.

Requires Python Playwright. Use scripts/check_admin_browser.sh so the
repository can discover a Python interpreter with Playwright installed.
"""
from __future__ import annotations

import re
import sys

from playwright.sync_api import expect, sync_playwright


def goto_admin(page, base_url: str, path: str) -> None:
    page.goto(f"{base_url}{path}", wait_until="domcontentloaded", timeout=15_000)
    expect(page.locator("#main")).to_be_visible(timeout=8_000)
    expect(page.locator("body")).not_to_contain_text("Access Denied", timeout=2_000)


def text_content(page, selector: str) -> str:
    return page.locator(selector).text_content(timeout=5_000) or ""


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            goto_admin(page, base_url, "/admin/")
            expect(page.get_by_role("heading", name=re.compile("Summary Dashboard", re.I))).to_be_visible()
            expect(page.locator("#stat-rooms")).to_have_text(re.compile(r"[1-9]\d*"), timeout=8_000)
            expect(page.locator("#connector-health")).to_contain_text("servicenow", timeout=8_000)

            goto_admin(page, base_url, "/admin/rooms.html")
            expect(page.get_by_role("heading", name=re.compile("Select a building", re.I))).to_be_visible()
            page.locator("#building-list a", has_text=re.compile("KAd", re.I)).first.click()
            expect(page.locator("#rooms-table")).to_be_visible(timeout=8_000)
            expect(page.locator("#rooms-body")).to_contain_text("101", timeout=8_000)
            page.get_by_role("button", name=re.compile("Edit", re.I)).first.click()
            expect(page.locator("#room-drawer")).to_have_class(re.compile(r"\bopen\b"), timeout=5_000)
            page.locator("#drawer-close").click()
            expect(page.locator("#room-drawer")).not_to_have_class(re.compile(r"\bopen\b"), timeout=5_000)

            goto_admin(page, base_url, "/admin/connectors.html")
            expect(page.get_by_role("heading", name=re.compile("Connector Management", re.I))).to_be_visible()
            connector_text = text_content(page, "#connector-grid").lower()
            for name in ("crestron", "live25", "screenconnect", "servicenow", "wattbox"):
                if name not in connector_text:
                    raise AssertionError(f"Admin connectors page missing {name}")
            expect(page.locator("#connector-grid button", has_text=re.compile("Test", re.I)).first).to_be_visible()

            goto_admin(page, base_url, "/admin/logs.html")
            expect(page.get_by_role("heading", name=re.compile("Audit Logs", re.I))).to_be_visible()
            expect(page.locator("#page-info")).to_have_text(re.compile(r"No results|\d+.*of.*\d+"), timeout=8_000)
            page.locator("#f-room").fill("corvallis-kad-101")
            page.get_by_role("button", name=re.compile("Search", re.I)).click()
            expect(page.locator("#page-info")).to_have_text(re.compile(r"No results|\d+.*of.*\d+"), timeout=8_000)

            goto_admin(page, base_url, "/admin/users.html")
            expect(page.get_by_role("heading", name=re.compile("User Roles", re.I))).to_be_visible()
            page.wait_for_function(
                """() => {
                    const text = document.querySelector("#users-body")?.textContent || "";
                    return text && !text.includes("Loading");
                }""",
                timeout=8_000,
            )
            expect(page.locator("#users-body")).to_contain_text(
                re.compile("No manual role overrides|Manual override", re.I),
                timeout=5_000,
            )
        finally:
            browser.close()

    print(f"Admin browser smoke checks passed at {base_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
