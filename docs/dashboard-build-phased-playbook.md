# Phased Build Playbook: OSU Presentation Support Dashboard

## Purpose

This playbook defines how to build the Dashboard collaboratively in phases. The goal is to avoid a one-shot build and instead create useful, reviewable increments that can be tested with technicians, adjusted, and then expanded.

This document is separate from the leadership and technical architecture playbooks. It is the working build plan.

## Build Philosophy

- Build in small reviewable phases.
- Start with a clickable mock dashboard using realistic anonymized data.
- Keep API connectors mocked until the team is ready to insert credentials.
- Preserve technician feedback after each phase.
- Do not add real Hardware IP data to public demos or external tools.
- Treat accessibility, speed, and clarity as acceptance requirements, not polish.

## Phase Overview

| Phase | Name | Primary Outcome |
| --- | --- | --- |
| 0 | Project setup and source docs | Living docs, version archive, build decisions, and source structure. |
| 1 | Static clickable dashboard mock | Leadership-friendly UI with mock campus/building/room flow. |
| 2 | Data model and mock JSON | Realistic room/device/status data shape for roughly 500 rooms. |
| 3 | Room detail and action logging mock | Tool panels, mock actions, and local audit trail behavior. |
| 4 | Backend scaffold | Local API shell with mock connectors and connector health. |
| 5 | Secure Hardware IP import | Local `.xlsx` import process with validation and sanitized outputs. |
| 6 | First real connector | One production integration connected end-to-end. |
| 7 | Entra SSO and security hardening | Required Phase 2 auth, roles, and audit controls. |
| 8 | Technician pilot and training | First-run tour, feedback, training flow, and pilot readiness. |

## Phase 0: Project Setup And Source Docs

Goal: establish the working project structure and living documentation.

Deliverables:

- Markdown source playbooks.
- HTML versions generated from Markdown.
- Version archive folder.
- Dashboard build playbook.
- Decision log for project name, stack, hosting, and security assumptions.

Acceptance criteria:

- All current docs are in the project folder.
- HTML versions open locally.
- Previous versions are archived before major updates.
- The team agrees that future work proceeds phase by phase.

Current status: complete for initial documentation package.

## Phase 1: Static Clickable Dashboard Mock

Goal: create the first leadership- and technician-reviewable dashboard experience without real APIs.

User-facing scope:

- One desktop page.
- Campus selector for Corvallis, OSU-Cascades, and Hatfield.
- Smooth campus fold-over or slide transition.
- Prominent building acronym markers.
- Hover state that enlarges building acronym and shows status summary.
- Building detail panel with supported rooms.
- Room detail view with tabs or sections for overview, schedule, tools, devices, incidents, action log, and AI placeholder.
- Quick filters visible but powered by mock data.
- First-run guided tour placeholder.

Data scope:

- Small curated mock set first, not all 500 rooms.
- Include at least:
  - 8-12 Corvallis buildings.
  - 2-4 OSU-Cascades buildings.
  - 2-4 Hatfield locations.
  - 15-30 sample rooms.
  - Mixed statuses, incidents, schedules, and device types.

Acceptance criteria:

- A technician can find a mock room by search.
- A technician can switch campuses without losing search/filter context.
- Hover and focus states are accessible.
- Room view clearly shows all future tool placeholders.
- No production credentials or real IP addresses are used.

Current status: first static clickable mock created in `dashboard/`.

Included in this build:

- Desktop-first static HTML/CSS/JavaScript app.
- Corvallis, OSU-Cascades, and Hatfield campus selector.
- Mock building map with large building acronyms.
- Hover/focus enlargement for building nodes.
- Room drill-down and room support tabs.
- Quick filters and connector health.
- Mock tool actions and audit log.
- First-run tour.

Latest fixes:

- Guided tour can be dismissed with Got it, X, Escape, or clicking outside the panel.
- Building names/codes corrected in the mock data where sources were available.
- Schematic building grid replaced with public OSU building footprint data from `map.oregonstate.edu`.
- Current public map data includes 303 building/location records: 278 Corvallis, 8 OSU-Cascades, and 17 Hatfield/Newport-area records.
- Building polygons use OSU map-style dark footprints with orange hover emphasis.
- Map interaction rebuilt as a functional tool with drag-to-pan, wheel zoom, zoom buttons, reset, clickable buildings, and map-layer labels that move with the building footprints.
- Custom SVG projection replaced with a MapLibre map engine, OpenStreetMap base tiles, and OSU building footprints placed by real latitude/longitude.
- Generic unnamed public map records remain visible as footprints but are not treated as authoritative building names.
- After review feedback, active dashboard returned to the preferred v1.3 pan/zoom map baseline and now generates placeholder room entries for every mapped building.
- Generated rooms are clearly labeled as placeholders and must be replaced by the secure Hardware IP List / room inventory import before production use.
- After additional review feedback, active dashboard was rolled back to the exact v1.3 pan/zoom functional map baseline. Future room coverage work should be added carefully on top of this baseline only after preserving the map behavior.
- Current preferred baseline is v1.4 MapLibre real-map engine with generated placeholder rooms for every mapped building.
- MapLibre is now vendored locally under the dashboard package so the map engine can load without external CDN access; OpenStreetMap base tiles still require network access until a local tile service is introduced.
- Current mock uses sanitized room/device data and should still be treated as non-authoritative until internal room inventory is imported.

Current guarded implementation state:

- Static `dashboard/data.js` remains the visible room inventory until the secure Hardware IP / room inventory import is loaded.
- Public OSU map data provides building/location records, not Presentation Support room inventory.
- FastAPI backend endpoints now exist for health, auth/session checks, admin inventory, audit logging, connector tests, 25Live schedule fallback, ServiceNow draft/create, XPanel launch/proxy, ScreenConnect launch, SharePoint launch, WattBox status/cycle, and PTZ commands.
- Dashboard tool panels call guarded backend routes and show pending/prerequisite messages when credentials or Hardware IP records are missing.
- Real external systems still require ignored `api/.env` values and ignored `api/hardware_ips.csv`.
- Entra SSO is scaffolded but still requires real Azure app and group configuration.

## Phase 2: Data Model And Mock JSON

Goal: make the prototype data-shaped like the production system.

Deliverables:

- Campus JSON.
- Building JSON.
- Room JSON.
- Device JSON.
- Mock status JSON.
- Mock ServiceNow incident JSON.
- Mock action log JSON.

Acceptance criteria:

- Data model supports roughly 500 rooms without redesign.
- Every room has stable IDs.
- Building acronyms and room numbers are searchable.
- Device records support manufacturer, model, IP/hostname placeholder, VLAN/network zone, and web UI URL placeholder.
- Mock data can represent stale data, connector outages, and conflicting source status.

## Phase 3: Room Detail And Action Logging Mock

Goal: demonstrate the "dial into room" workflow and required audit behavior.

Deliverables:

- Room overview.
- XPanel launch through the backend proxy contract.
- Device web UI inventory fallback until Hardware IP records are loaded.
- ScreenConnect launch through the backend URL contract.
- WattBox status and cycle requests through guarded backend endpoints.
- SharePoint training links through the backend URL contract.
- ServiceNow incident list and draft/create workflows through guarded backend endpoints.
- Action log that records local UI actions and backend-audited sensitive actions.

Acceptance criteria:

- Every placeholder action writes a mock audit event.
- Power-cycle placeholder requires confirmation.
- Action log includes timestamp, user, room, action type, target, and outcome.
- The UI differentiates safe view actions from disruptive actions.

## Phase 4: Backend Scaffold

Goal: add the local backend foundation while keeping connectors in mock mode.

Deliverables:

- Local API service.
- Room/status endpoints.
- Mock connector modules.
- Connector health endpoint.
- Audit log endpoint.
- Config file for mock vs real connector mode.

Acceptance criteria:

- Frontend can load data from backend instead of static files.
- Each connector has a mock response and health status.
- Backend never exposes secrets to the browser.
- Connector failure states can be simulated.

## Phase 5: Secure Hardware IP Import

Goal: safely ingest the real `.xlsx` inventory locally without exposing it to external systems.

Deliverables:

- Local import workflow.
- Required column validation.
- Duplicate and missing-field report.
- Normalized room/device output.
- Sanitized demo export option.

Acceptance criteria:

- Real `.xlsx` remains on-prem.
- Invalid rows are flagged before import.
- Import can update existing rooms/devices without destroying unrelated records.
- Sanitized export contains no real IP addresses or sensitive network details.

## Phase 6: First Real Connector

Goal: connect one production integration end-to-end.

Recommended first connector options:

1. Hardware IP import - best if inventory quality is the biggest risk.
2. Crestron Fusion - best if live room status is the biggest demo value.
3. ServiceNow read-only incidents - best if leadership wants support-process value first.

Acceptance criteria:

- Connector credentials stay server-side.
- API results normalize into the internal room model.
- Connector health and last sync time are visible.
- Failures show cached/stale states instead of breaking the dashboard.
- All user actions are audited.

## Phase 7: Entra SSO And Security Hardening

Goal: move from prototype access to OSU-ready authenticated access.

Deliverables:

- Microsoft Entra OIDC app registration.
- Technician/admin role mapping.
- Session timeout and logout behavior.
- Auth audit events.
- Security review checklist.

Acceptance criteria:

- Only approved users can access the dashboard.
- All users can access all campuses and rooms unless policy changes.
- Admin-only functions are separated from technician use.
- Audit logs identify the authenticated user.

## Phase 8: Technician Pilot And Training

Goal: validate the dashboard with real support workflows.

Deliverables:

- First-run tour.
- Quick-start training page.
- Pilot feedback form or feedback capture.
- Common workflow examples.
- Updated screenshots in leadership and technical docs.

Acceptance criteria:

- Student workers can complete guided room lookup and ticket-context tasks.
- Technicians can identify missing or confusing fields.
- Feedback is reviewed and prioritized.
- Leadership receives updated screenshots and pilot findings.

## Versioning And Archive Practice

For each major documentation or prototype milestone:

1. Archive the current Markdown and HTML files.
2. Update Markdown source.
3. Regenerate HTML.
4. Create a versioned archive folder with the updated files.
5. Record what changed in the README or decision log.

Current archives:

- `v1-initial-package`
- `v2-dgx-spark-orin-and-dashboard-build-plan`

## Immediate Next Build Step

The next implementation phase should be **first live-room validation**.

Before enabling pilot use, confirm:

- Which non-critical room should be used for the first live connector test.
- The real secure `api/hardware_ips.csv` export and room ID mapping.
- Which connector should be validated first after Hardware IP import: XPanel, WattBox/OvrC, PTZ, 25Live, ServiceNow, ScreenConnect, or SharePoint.
- The required ignored `api/.env` values for that first connector.
- Whether the static dashboard room list should be replaced by a backend room API response before broader pilot review.

Use `docs/examples/first-live-room-validation.md` as the no-secrets runbook for that first room. It defines the preflight commands, connector order, evidence rules, rollback path, and raw-IP/secret handling requirements.

Recommended default if no further input is available:

- Keep the current Phase 1 mock as-is for quick review.
- Move the mock data into separate JSON-shaped files in Phase 2.
- Preserve the current anonymized/sanitized device host labels.
- Add validation notes that map each mock field to the future secure `.xlsx` import.

## Open Questions

- Which pilot buildings should be included in Phase 1?
- Should the first mock be pure HTML/CSS/JS or a lightweight app structure?
- Should the dashboard run from static files first or start with the backend scaffold immediately?
- What is the preferred visual tone: darker command center, light OSU-branded interface, or both with a toggle?
