# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

BeaverView — OSU Presentation Support Dashboard. FastAPI backend + vanilla JS frontend showing all OSU campus AV rooms on a MapLibre map. Technicians control devices, view audit logs, and file tickets from one browser tab. Admin panel at `/admin/` for room/user/connector management.

## Dev server

**First time** (creates Python venv and installs deps):
```bash
cd api && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
```

**Every time after** (venv already exists):
```bash
cd api && source venv/bin/activate && uvicorn main:app --reload --port 8000
```

- Dashboard: `http://localhost:8000`
- Admin panel (no login needed on localhost when `AZURE_CLIENT_ID` is unset): `http://localhost:8000/admin/`

You can also run `api/start.sh`; it installs/updates dependencies from `api/requirements.txt` before starting uvicorn.

## Source of truth and logging

The canonical BeaverView v2 checkout on this Mac Mini is `/Users/benjaminfranklinautomation/projects/beaverview`. Keep `PROJECT-LOG.md` updated with dated entries for material code, environment, deployment, and documentation changes. The GitHub remote is `https://github.com/dashercammmmmmm/beaverview`; as of 2026-06-24, local `main` is synced with `origin/main`.

## Smoke checks

Run this before pushing or after changing backend/auth/connector behavior:

```bash
scripts/smoke_check.sh
```

It compiles active Python modules, verifies required imports, checks `dashboard/app.js` syntax, starts uvicorn on `127.0.0.1:8017`, then checks `/api/health`, `/api/me`, 25Live mock fallback, ServiceNow/chat mock fallbacks, ScreenConnect/SharePoint launch guardrails, and PTZ/WattBox offline guardrails.

Run this after changing dashboard workflows or backend-wired tool panels:

```bash
scripts/check_dashboard_browser.sh
```

It starts uvicorn on `127.0.0.1:8027`, opens the active dashboard in headless Chromium through Playwright, selects seeded rooms, and verifies guarded UI feedback for ServiceNow, XPanel, ScreenConnect, SharePoint, WattBox, PTZ, and Hermes chat fallback. It is also part of `scripts/check_pilot_readiness.py`.

Run this after changing admin pages, auth, or admin API behavior:

```bash
scripts/check_admin_browser.sh
```

It starts uvicorn on `127.0.0.1:8028`, opens the admin panel in headless Chromium through Playwright, and verifies the summary, rooms, connectors, logs, and users pages. It is also part of `scripts/check_pilot_readiness.py`.

Admin page behavior lives in external `dashboard/admin/*-page.js` files. Do not add inline `<script>` blocks or inline event handlers; the app CSP uses `script-src 'self' blob:`.

Run this after changing `dashboard/data.js`, `api/migrate_data.py`, or DB schema:

```bash
scripts/check_data_migration.sh
```

It rebuilds the ignored local SQLite inventory from `dashboard/data.js` and verifies non-empty campus, building, room, and device counts plus valid connector modes.

The device web proxy at `/api/rooms/{room_id}/proxy/{tool}/{path}` performs server-side `device_ips` lookup for `xpanel`, `wattbox`, and `ptz`, injects backend-only credentials, and only proxies private/link-local IPs unless `DEVICE_PROXY_ALLOW_PUBLIC=true` is explicitly set after review. It supports GET only.
WattBox OvrC outlet status/cycle endpoints live at `/api/rooms/{room_id}/wattbox/outlets` and `/api/rooms/{room_id}/wattbox/outlets/{outlet_num}/cycle`; they inject the OvrC API key server-side and log cycle attempts.
PTZ camera commands also have an allowlisted backend endpoint at `/api/rooms/{room_id}/ptz/{command}`; it uses the same backend-only IP/credential path and logs each attempted command.

Run this after changing `api/import_device_ips.py`, `docs/examples/hardware_ips.sample.csv`, or the secure local `api/hardware_ips.csv`:

```bash
scripts/check_hardware_ip_import.sh
```

It dry-runs the committed sample and dry-runs the real ignored CSV if present, without replacing `device_ips`.

Run this for a broader local readiness snapshot before deployment work:

```bash
python3 scripts/check_pilot_readiness.py
```

It verifies repo sync, ignored local secrets/data, Python imports, data migration, hardware IP import validation, seeded SQLite inventory, offline API contracts, browser smoke coverage, env-template consistency, the pilot input checklist, and reports pending external prerequisites without printing secret values.

For automation or reports, use:

```bash
python3 scripts/check_pilot_readiness.py --json
python3 scripts/check_pilot_readiness.py --markdown
```

Run this after changing API route, auth, connector fallback, or proxy behavior:

```bash
scripts/check_api_contracts.py
```

It exercises the FastAPI app in-process with deterministic mock connector settings: health, localhost dev auth, admin inventory, all seeded admin connector tests, live-mode pending behavior without credentials, 25Live schedule mock fallback, xpanel launch/proxy behavior, WattBox outlet failure contracts, PTZ command failure contracts, ServiceNow incident read/create fallbacks, chat fallback, `/api/chat`, and room incidents.

Run this after changing `dashboard/data.js`, `api/migrate_data.py`, the campus inventory endpoint, or the dashboard inventory read path:

```bash
scripts/check_inventory_parity.py
```

It verifies that every seeded static room still matches `GET /api/campus/{campus_id}/inventory` before the browser uses SQLite inventory.

Run this after changing runtime environment variables in `api/main.py`, connector modules, or readiness checks:

```bash
python3 scripts/check_env_template.py
```

It verifies `api/.env.example` documents the runtime env vars used by code/readiness, has no duplicate keys, and has no stale documented keys.

Run this once on a local checkout or VM to create/update ignored `api/.env` with generated `PROXY_SECRET` and `SESSION_SECRET_KEY` values:

```bash
bash scripts/init_local_env.sh
```

It does not print generated secret values.

Azure/Entra setup has a committed checklist at `docs/examples/azure-entra-app-registration.md`. The preflight validates that the checklist exists and that `AZURE_REDIRECT_URI`, if configured, is an HTTPS `/auth/callback` URL.

The non-secret external input collection packet is `docs/examples/pilot-inputs-checklist.md`. It maps the remaining preflight pending items to `api/.env` keys and the ignored `api/hardware_ips.csv` file.

The first live-room validation runbook is `docs/examples/first-live-room-validation.md`. It defines the non-critical-room checklist, connector order, evidence rules, rollback path, and no-secrets/no-raw-IP requirements. `python3 scripts/check_live_validation_doc.py` validates that the runbook still covers those gates and is part of `scripts/check_pilot_readiness.py`.

Run this after changing deployment templates:

```bash
scripts/check_deployment_assets.sh
```

It validates the checked-in systemd and nginx templates under `deploy/`, including a sample nginx render with `scripts/render_nginx_config.sh` and a sample self-signed certificate with `scripts/generate_self_signed_cert.sh`.

There is no build step, bundler, or test suite. Frontend changes are visible immediately — `index.html` has a built-in live-reload poller (HEAD requests every 1.5s, localhost only).

## Architecture

### Backend — `api/main.py` (single file, ~1700 lines)

FastAPI app. All routes, DB schema, auth logic, connector scaffolding, and live connector probes live here. Key sections:

- `init_db()` — creates all 9 SQLite tables on startup (`audit_log`, `campuses`, `buildings`, `rooms`, `devices`, `incidents`, `connector_config`, `user_roles`, `device_ips`). DB auto-created at `api/beaverview.db`.
- `resolve_role()` / `require_admin()` — maps Entra group membership to `admin` / `technician` / `viewer`. Dev bypass in `GET /api/me` returns `role: admin` when `AZURE_CLIENT_ID` is unset and request is from localhost.
- Connector mode (mock vs live) is stored per-campus in `connector_config` table and toggled via `PUT /api/admin/connectors/{campus_id}/{connector_name}/mode`.

### Frontend — `dashboard/`

No framework. Three files own everything:
- `app.js` — all state, rendering, map control, and API calls
- `styles.css` — all visual design
- `index.html` — static shell; do not rename element IDs (app.js selects by ID)

**State object** (`state` in app.js) holds the single source of truth: selected campus, building, room, active tab, search string, filters, history, connector overrides.

**Map data flow:** `window.osuMapBuildings` (278 footprints from `osu-map-buildings.js`) drives the MapLibre map. When a building is clicked, `supportBuildingFor()` matches it to the current campus inventory by `code` field. If no match, `generatedRoomsForBuilding()` auto-generates placeholder rooms so every building is clickable. The dashboard starts from `data.js` so static file mode still works, then replaces campus room data with `GET /api/campus/{campus_id}/inventory` when served by FastAPI.

**Search:** `normalizeSearch()` strips apostrophes, dashes, and `&`→`and` before matching, so "womens" finds "Women's Building". Non-matching buildings are dimmed (18% opacity) rather than removed, so map clicks always work.

**Admin panel** (`dashboard/admin/`): five standalone HTML pages (index, rooms, logs, connectors, users). Each includes `admin.js` which calls `GET /api/me` on load; if `role !== 'admin'`, it replaces the page body with an access-denied message. All API calls go through `adminFetch()` helper which handles 401 → redirect.

### Two parallel data sources

| Source | Used when | How to populate |
|---|---|---|
| `dashboard/data.js` | Static/offline dashboard fallback and SQLite seed source | Edit by hand |
| `api/beaverview.db` | FastAPI dashboard inventory, admin APIs, connector state, and audit logs | `python3 migrate_data.py` (rooms from data.js), `python3 import_device_ips.py` (from `hardware_ips.csv`) |

The DB is empty until migration runs. Frontend room rendering still falls back to `data.js`; FastAPI-served dashboard inventory uses SQLite and must not expose `device_ips` or raw IP fields.

## Key files and their rules

| File | Rule |
|---|---|
| `dashboard/osu-map-buildings.js` | Generated from OSU map API. Edit only to manually add new buildings not yet in OSU's system (e.g. HCIC). |
| `api/.env` | Never commit. Copy from `.env.example`. |
| `api/beaverview.db` | Never commit. Auto-created. |
| `hardware_ips.csv` | Never commit. Device IPs. |

## Credential / connector patterns

Three patterns used throughout (documented in `api/.env.example`):
1. **REST API key** — backend calls service directly (25Live, ServiceNow server-to-server)
2. **Device web proxy** — backend reverse-proxies device UIs; browser accesses `/api/rooms/{id}/proxy/...` (Crestron XPanel, WattBox, PTZ cameras)
3. **Entra SSO passthrough** — backend builds a URL; user's existing OSU session handles auth (ScreenConnect, SharePoint, ServiceNow web UI)

## Cache busting

Frontend script/CSS tags use `?v=2` query strings. Bump the version number when deploying a breaking change to force browsers to re-fetch.

## Production deployment target

Ubuntu VM → nginx (443) → uvicorn (127.0.0.1:8000) → systemd `beaverview.service`. Self-signed SSL cert. Windows clients add a hosts-file entry for `beaverview`. See `PLAYBOOK-DEPLOYMENT.md` for full steps.
