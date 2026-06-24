#!/usr/bin/env python3
"""Browser smoke check for the active BeaverView dashboard.

Requires Python Playwright. Use scripts/check_dashboard_browser.sh so the
repository can discover a Python interpreter with Playwright installed.
"""
from __future__ import annotations

import re
import sys

from playwright.sync_api import expect, sync_playwright


def select_room(page, building_code: str, room_id: str) -> None:
    page.evaluate(
        """(code) => {
            const building = campusBuildings().find((item) =>
                (item.code || "").toLowerCase() === code.toLowerCase()
            );
            if (!building) throw new Error(`Building not found: ${code}`);
            selectBuilding(building.id);
            renderSelectedBuilding();
            updateMapData();
        }""",
        building_code,
    )
    page.locator(f"button[data-room='{room_id}']").click()
    expect(page.locator("#roomHeader")).to_contain_text(re.compile(building_code, re.I), timeout=5_000)


def open_actions(page) -> None:
    page.locator("#roomTabs button[data-tab='tools']").click()
    expect(page.locator("#roomBody")).to_contain_text("Draft ServiceNow ticket", timeout=5_000)


def click_tool(page, label: str) -> None:
    page.get_by_role("button", name=re.compile(label, re.I)).click()


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(base_url, wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_function(
                "typeof selectBuilding === 'function' && typeof campusBuildings === 'function'",
                timeout=10_000,
            )
            expect(page.locator("#roomHeader")).to_contain_text("No room selected", timeout=5_000)

            select_room(page, "KAd", "corvallis-kad-101")
            open_actions(page)

            click_tool(page, "Draft ServiceNow ticket")
            page.get_by_role("button", name=re.compile("Create Draft Ticket", re.I)).click()
            expect(page.locator("[data-sn-status]")).to_contain_text("mock draft", timeout=8_000)
            page.locator("[data-back='tools']").click()

            click_tool(page, "Launch XPanel")
            page.get_by_role("button", name=re.compile("Open Proxied XPanel", re.I)).click()
            expect(page.locator("[data-tool-status]")).to_contain_text("Configure the connector", timeout=5_000)
            page.locator("[data-back='tools']").click()

            click_tool(page, "Start ScreenConnect")
            page.get_by_role("button", name=re.compile("Launch Remote Session", re.I)).click()
            expect(page.locator("[data-tool-status]")).to_contain_text("Configure the connector", timeout=5_000)
            page.locator("[data-back='tools']").click()

            click_tool(page, "SharePoint guide")
            page.get_by_role("button", name=re.compile("Open PDF", re.I)).click()
            expect(page.locator("[data-tool-status]")).to_contain_text("Configure the connector", timeout=5_000)
            page.locator("[data-back='tools']").click()

            click_tool(page, "Check WattBox")
            expect(page.locator("[data-tool-status]")).to_contain_text("Using mock outlet list", timeout=8_000)
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("button[data-action='wattbox_outlet_cycle']").first.click()
            expect(page.locator("[data-tool-status]")).to_contain_text("WattBox cycle unavailable", timeout=8_000)

            select_room(page, "LINC", "corvallis-linc-100")
            open_actions(page)
            click_tool(page, "Control PTZ Camera")
            page.locator("button[data-command='home']").click()
            expect(page.locator("[data-tool-status]")).to_contain_text("PTZ command unavailable", timeout=8_000)

            page.locator("#roomTabs button[data-tab='chat']").click()
            page.locator("#chatInput").fill("What should I check first?")
            page.locator("#chatSendBtn").click()
            expect(page.locator("#chatMessages")).to_contain_text("Chat agent not configured", timeout=8_000)
        finally:
            browser.close()

    print(f"Dashboard browser smoke checks passed at {base_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
