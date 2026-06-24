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

It compiles active Python modules, verifies required imports, starts uvicorn on `127.0.0.1:8017`, then checks `/api/health`, `/api/me`, ServiceNow mock fallback, and chat mock fallback.

Run this after changing `dashboard/data.js`, `api/migrate_data.py`, or DB schema:

```bash
scripts/check_data_migration.sh
```

It rebuilds the ignored local SQLite inventory from `dashboard/data.js` and verifies non-empty campus, building, room, and device counts plus valid connector modes.

The device web proxy at `/api/rooms/{room_id}/proxy/{tool}/{path}` performs server-side `device_ips` lookup for `xpanel`, `wattbox`, and `ptz`, injects backend-only credentials, and only proxies private/link-local IPs unless `DEVICE_PROXY_ALLOW_PUBLIC=true` is explicitly set after review. It supports GET only.

Run this for a broader local readiness snapshot before deployment work:

```bash
scripts/check_pilot_readiness.py
```

It verifies repo sync, ignored local secrets/data, Python imports, seeded SQLite inventory, and reports pending external prerequisites without printing secret values.

There is no build step, bundler, or test suite. Frontend changes are visible immediately — `index.html` has a built-in live-reload poller (HEAD requests every 1.5s, localhost only).

## Architecture

### Backend — `api/main.py` (single file, ~1400 lines)

FastAPI app. All routes, DB schema, auth logic, and connector stubs live here. Key sections:

- `init_db()` — creates all 9 SQLite tables on startup (`audit_log`, `campuses`, `buildings`, `rooms`, `devices`, `incidents`, `connector_config`, `user_roles`, `device_ips`). DB auto-created at `api/beaverview.db`.
- `resolve_role()` / `require_admin()` — maps Entra group membership to `admin` / `technician` / `viewer`. Dev bypass in `GET /api/me` returns `role: admin` when `AZURE_CLIENT_ID` is unset and request is from localhost.
- Connector mode (mock vs live) is stored per-campus in `connector_config` table and toggled via `PUT /api/admin/connectors/{campus_id}/{connector_name}/mode`.

### Frontend — `dashboard/`

No framework. Three files own everything:
- `app.js` — all state, rendering, map control, and API calls
- `styles.css` — all visual design
- `index.html` — static shell; do not rename element IDs (app.js selects by ID)

**State object** (`state` in app.js) holds the single source of truth: selected campus, building, room, active tab, search string, filters, history, connector overrides.

**Map data flow:** `window.osuMapBuildings` (278 footprints from `osu-map-buildings.js`) drives the MapLibre map. When a building is clicked, `supportBuildingFor()` matches it to a `data.js` entry by `code` field. If no match, `generatedRoomsForBuilding()` auto-generates placeholder rooms so every building is clickable. The `data.js` mock remains active until `migrate_data.py` seeds the SQLite DB and the backend API is used instead.

**Search:** `normalizeSearch()` strips apostrophes, dashes, and `&`→`and` before matching, so "womens" finds "Women's Building". Non-matching buildings are dimmed (18% opacity) rather than removed, so map clicks always work.

**Admin panel** (`dashboard/admin/`): five standalone HTML pages (index, rooms, logs, connectors, users). Each includes `admin.js` which calls `GET /api/me` on load; if `role !== 'admin'`, it replaces the page body with an access-denied message. All API calls go through `adminFetch()` helper which handles 401 → redirect.

### Two parallel data sources

| Source | Used when | How to populate |
|---|---|---|
| `dashboard/data.js` | Always (frontend mock) | Edit by hand |
| `api/beaverview.db` | When backend connectors are in live mode | `python3 migrate_data.py` (rooms from data.js), `python3 import_device_ips.py` (from `hardware_ips.csv`) |

The DB is empty until migration runs. Dev mode works entirely off `data.js` mock data.

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
