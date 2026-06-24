# BeaverView — Session Context & Handoff
**Purpose:** Reference for the next Claude session. Read this before doing anything.
**Last updated:** 2026-06-24 after source-of-truth stabilization on the Mac Mini v2 checkout.

---

## Project in one sentence
BeaverView is an OSU Presentation Support dashboard — a FastAPI backend + vanilla JS frontend showing all campus AV rooms on a MapLibre map, letting technicians control devices, view logs, and file tickets from a single browser tab.

---

## Deployment target (locked in)
| Item | Value |
|---|---|
| Server | Ubuntu 22.04/24.04 VM in **VMware** (bridged network adapter) |
| Clients | Windows PCs on the same LAN — type `https://beaverview` in browser |
| SSL | Self-signed cert (`/etc/ssl/beaverview/`) — hosts file on each Windows PC |
| Login | OSU **Entra SSO** (Azure AD) — MSAL, starlette-sessions (wired but not yet tested with real Azure creds) |
| Service | systemd: `beaverview.service`, runs uvicorn on `127.0.0.1:8000` |
| Reverse proxy | nginx on port 443, forwards to uvicorn |

---

## Local dev environment (Mac)
- Project root: `/Users/benjaminfranklinautomation/projects/beaverview/`
- API folder:   `/Users/benjaminfranklinautomation/projects/beaverview/api/`
- Dashboard:    `/Users/benjaminfranklinautomation/projects/beaverview/dashboard/`
- **To run locally:** Open Terminal → paste the dev server command in the "How to start the server" section below
- **Local URL:** `http://localhost:8000`
- **Admin panel (dev):** `http://localhost:8000/admin/` — works without login when AZURE_CLIENT_ID is NOT set in .env

## Source-of-truth status
- Canonical local repo: `/Users/benjaminfranklinautomation/projects/beaverview`
- GitHub remote: `https://github.com/dashercammmmmmm/beaverview`
- Branch: `main`
- Current sync state: local `main`, `origin/main`, and `origin/HEAD` are synced.
- GitHub push verified: 2026-06-24T02:30:07Z
- `/Users/benjaminfranklinautomation/Documents/Beaverview` is not the active v2 repo; it has no commits and no remote.
- Durable work log: update `PROJECT-LOG.md` for material changes.

---

## Repository layout (active files only)
```
beaverview/
├── .gitignore               ← excludes .env, beaverview.db, hardware_ips.csv, *.pdf
├── CLAUDE.md                ← AI assistant guidance (architecture, dev commands)
├── PROJECT-LOG.md           ← durable local work log
├── SESSION-CONTEXT.md       ← this file
├── api/
│   ├── main.py              ← FastAPI app (~1400 lines) — ALL backend code
│   ├── data_mock.py         ← 19 mock rooms for dev/test
│   ├── requirements.txt     ← fastapi, uvicorn, python-dotenv, httpx, msal, starlette-sessions>=0.3.0, itsdangerous
│   ├── venv/                ← Python virtual environment (auto-created, not committed)
│   ├── .env                 ← YOUR credentials (NEVER commit — in .gitignore)
│   ├── migrate_data.py      ← one-time: data.js → SQLite
│   ├── import_device_ips.py ← one-time: hardware_ips.csv → SQLite
│   └── beaverview.db        ← SQLite database (auto-created on first run, not committed)
└── dashboard/
    ├── index.html           ← main dashboard page
    ├── app.js               ← all interactivity (~1230 lines)
    ├── styles.css           ← all visual design (~1400 lines)
    ├── data.js              ← room inventory + campus data (includes HCIC placeholder)
    ├── osu-map-buildings.js ← 278 OSU building footprints + HCIC manual entry
    ├── vendor/maplibre/     ← local MapLibre GL (DO NOT EDIT)
    └── admin/
        ├── admin.js         ← shared auth check + API helpers
        ├── admin.css        ← admin panel styles
        ├── index.html       ← admin summary dashboard
        ├── rooms.html       ← room + building editor
        ├── logs.html        ← audit log viewer + export
        ├── connectors.html  ← connector toggle management
        └── users.html       ← user role management
```

---

## How to start the dev server (Mac — Terminal)

### Step 1 — Open Terminal
Press **Command + Space**, type **Terminal**, press **Enter**.

### Step 2 — Paste this exact command and press Enter:

**First time only** (creates the virtual environment and installs packages):
```
cd "/Users/benjaminfranklinautomation/projects/beaverview/api" && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
```

**Every time after that** (venv already exists):
```
cd "/Users/benjaminfranklinautomation/projects/beaverview/api" && source venv/bin/activate && uvicorn main:app --reload --port 8000
```

**Convenience startup script** (also refreshes dependencies from `requirements.txt`):
```
cd "/Users/benjaminfranklinautomation/projects/beaverview" && api/start.sh
```

**Smoke check before pushes or connector/auth changes:**
```
cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/smoke_check.sh
```

**Data migration check after data/schema changes:**
```
cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/check_data_migration.sh
```

**Pilot readiness preflight before deployment work:**
```
cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/check_pilot_readiness.py
```

**Offline API contract check after route/auth/connector changes:**
```
cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/check_api_contracts.py
```

**Initialize local `.env` with generated `PROXY_SECRET`:**
```
cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/init_local_env.sh
```

**Hardware IP CSV dry-run before real import:**
```
cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/check_hardware_ip_import.sh
```

**Deployment template validation:**
```
cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/check_deployment_assets.sh
```

### Step 3 — Open the site
Open **Chrome** or **Safari** and go to: `http://localhost:8000`

### Step 4 — Open the admin panel (dev mode — no login needed)
Go to: `http://localhost:8000/admin/`

### To stop the server:
Click in the Terminal window and press **Control + C** (hold Control, tap C).

### If you see "externally-managed-environment" from pip:
macOS Homebrew Python blocks system-wide pip installs. The venv command above is the correct fix — it creates an isolated environment. Never use `pip3 install` without a venv active on macOS.

---

## Key architectural decisions (do not relitigate)
1. **No Crestron Fusion** — removed. BeaverView polls each processor directly via HTTP.
2. **Room data field rename** — `fusion:` → `processor:` everywhere.
3. **Admin panel at `/admin`** — same FastAPI app, Admins-group-only.
4. **Data migration** — room data moves from `data.js` → SQLite via `migrate_data.py`.
5. **Self-signed SSL** — cert at `/etc/ssl/beaverview/beaverview.crt`.
6. **No CDN** — MapLibre is local in `dashboard/vendor/`.

---

## Current API endpoints (main.py)
| Method | Path | Status |
|---|---|---|
| GET | `/api/health` | ✅ Live |
| GET | `/api/campus/{id}/connectors` | ✅ Live (mock) |
| GET | `/api/campus/{id}/crestron/rooms` | ✅ Live (mock/live) |
| GET | `/api/rooms/{room_id}/launch/{tool}` | ✅ Stub |
| GET | `/api/rooms/{room_id}/proxy/{tool}/{path}` | ⚠️ 501 stub |
| POST | `/api/rooms/{room_id}/action` | ✅ Live |
| GET | `/api/rooms/{room_id}/log` | ✅ Live |
| GET | `/api/audit` | ✅ Live |
| GET | `/api/me` | ✅ Live (+ localhost dev bypass) |
| GET | `/auth/login` | ✅ Live (needs Azure creds in .env) |
| GET | `/auth/callback` | ✅ Live (needs Azure creds in .env) |
| GET | `/auth/logout` | ✅ Live |
| GET/POST/PUT/DELETE | `/api/admin/*` | ✅ Live (all admin endpoints) |

---

## Database — current state
All 9 tables defined in `init_db()` and auto-created on startup:
```
audit_log, campuses, buildings, rooms, devices,
incidents, connector_config, user_roles, device_ips
```
Migration script (`migrate_data.py`) seeds campuses/buildings/rooms from `data.js`.
Device IPs go in via `import_device_ips.py` with a `hardware_ips.csv` file.

2026-06-24 verification: `scripts/check_data_migration.sh` seeds the local ignored DB successfully from `dashboard/data.js`:
- campuses: 3
- buildings: 18
- rooms: 20
- devices: 22
- connector modes: all normalized to `mock`/`live`

---

## What was just changed (latest sessions)

### Git repository initialized
- `git init` + initial commit (ec60a6f) — all project files committed
- GitHub remote exists at `https://github.com/dashercammmmmmm/beaverview`
- Local BeaverView v2 and stabilization commits were pushed to GitHub on 2026-06-24.
- `git status --short --branch` should show `## main...origin/main` when the repo is clean and synced.

### Python venv required (macOS)
- macOS Homebrew Python blocks system-wide `pip install` (PEP 668)
- Fixed: `api/venv/` created, `starlette-sessions` version corrected to `>=0.3.0` in `requirements.txt`
- 2026-06-24 finding: local venv was missing `httpx`, disabling Crestron polling and connector modules. `api/start.sh` now installs from `requirements.txt`; run it or `pip install -r requirements.txt` to repair the venv.

### BeaverView v2 commits now on GitHub
- `a4b259e` BeaverView v2 — Phase 1 & 2 visual redesign, ServiceNow, map UX improvements
- `b9fd9fe` Phase 4 — Hermes chat agent integration
- `a51006e` Map crash fix when search/filters match zero buildings
- `c1f98ea` `/api/me` unsafe session access fix
- `9a4cb4f` Relaxed CSP for MapLibre and OSM tiles
- `82fbfa3` Source-of-truth handoff and smoke checks
- Data migration repair: `fix: repair dashboard data migration`
- Device proxy foundation: `feat: add device proxy foundation`
- GitHub sync status docs: `docs: record github sync status`

### Data migration repaired
- `migrate_data.py` now handles the JavaScript object literal shape in `dashboard/data.js` instead of assuming strict JSON.
- It calls `init_db()` before seeding, so it works against a fresh local DB.
- It preserves either `processor` or legacy `crestron` room fields into `rooms.processor`.
- It normalizes connector config values to valid admin modes: `mock` or `live`.
- `scripts/check_data_migration.sh` reruns the migration and verifies inventory counts.

### First live-connector gap: device proxy foundation
- `/api/rooms/{room_id}/proxy/{tool}/{path}` is no longer a 501 stub.
- Supported proxy tools: `xpanel`, `wattbox`, `ptz`.
- Device IPs are looked up server-side from `device_ips`; browser responses never include the raw IP.
- Credentials are read from `.env`: `CRESTRON_PROXY_*`, `WATTBOX_DIRECT_*`, `PTZ_PROXY_*`.
- Proxy defaults to private/link-local IPs only; `DEVICE_PROXY_ALLOW_PUBLIC=true` is available only for reviewed deployments.
- `import_device_ips.py` now initializes the DB schema and validates IP addresses before import.
- `import_device_ips.py --dry-run <csv>` validates Hardware IP CSV data without replacing the `device_ips` table.
- Safe sample CSV: `docs/examples/hardware_ips.sample.csv`.
- `scripts/check_hardware_ip_import.sh` validates the sample and dry-runs the real ignored `api/hardware_ips.csv` when present.
- Still requires the real secure `hardware_ips.csv` and actual device credentials before live device access can be tested.

### Pilot readiness preflight
- `scripts/check_pilot_readiness.py` verifies local repo sync, ignored local-only files, Python dependency imports, SQLite seed state, offline API contracts, and deployment prerequisite status.
- It does not print secret values.
- It exits nonzero only for local failures; missing Azure/connector credentials and missing hardware IPs are reported as pending external prerequisites.
- It also validates reusable deployment templates under `deploy/`.
- `scripts/init_local_env.sh` creates ignored `api/.env` and sets `PROXY_SECRET` without printing it.
- Azure/Entra setup checklist: `docs/examples/azure-entra-app-registration.md`.
- The preflight validates the Azure redirect URI shape when configured.

### Offline API contracts
- `scripts/check_api_contracts.py` uses FastAPI `TestClient` with deterministic mock connector settings.
- It validates health, localhost dev auth, admin inventory access, xpanel launch/proxy behavior, ServiceNow/chat fallback health, `/api/chat`, and room incidents without requiring live credentials.

### Deployment templates
- `deploy/systemd/beaverview.service` is the checked-in systemd unit for the Ubuntu VM.
- `deploy/nginx/beaverview.conf.template` is the checked-in nginx reverse-proxy template. Replace `__VM_IP__` with the VM IP before installing.
- `scripts/check_deployment_assets.sh` validates these templates locally.

### Admin link in dashboard header
- Orange-tinted "Admin" button appears in the top-right header
- Shown only when `GET /api/me` returns `role: 'admin'`
- Hidden (`hidden` attribute) by default; revealed by `checkRole()` in `app.js`
- `dashboard/index.html`, `dashboard/app.js`, `dashboard/styles.css` all updated

### Search improvements
- **Fuzzy/normalized search**: `normalizeSearch()` strips apostrophes, dashes, `&`→"and" before matching — "womens" now finds "Women's Building"
- **Building clicks work while search is active**: all buildings stay on the map; non-matching ones fade to 18% opacity instead of disappearing — you can click any building at any time

### HCIC placeholder
- Added to `osu-map-buildings.js` (approximate coordinates — update when building is officially placed)
- Added to `data.js` with one placeholder room; clicking it shows a "Upcoming building" banner
- Search for "HCIC" or "Health and Collaborative" will find it

### CLAUDE.md created
- `CLAUDE.md` at project root — guides AI assistants on architecture, dev commands, and key file rules

---

## What is NOT done (priority order)

### 🔴 Blocking — must do before production
| Item | Notes |
|---|---|
| **Azure App Registration** | IT team registers BeaverView in Azure Portal. See `PLAYBOOK-DEPLOYMENT.md` Part 7, Steps 1–3. Requires Application Administrator role. |
| **.env credentials** | Fill in `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_REDIRECT_URI`, group object IDs |
| **Ubuntu VM** | Not yet created. See `PLAYBOOK-DEPLOYMENT.md` Part 2 |
| **Real inventory import** | `dashboard/data.js` now migrates cleanly into SQLite. Secure Hardware IP import from `hardware_ips.csv` still requires the real spreadsheet. |

### 🟠 Important — needed soon
| Item | Notes |
|---|---|
| Windows hosts file entries | `192.168.x.x beaverview` on each Windows PC |
| nginx + SSL + systemd setup | `PLAYBOOK-DEPLOYMENT.md` Parts 7–8 |
| VLAN routing on Ubuntu VM | AV devices on separate subnet need static route |
| Real Hardware IP import | Place secure `hardware_ips.csv` under `api/`, run `python3 import_device_ips.py hardware_ips.csv`, then verify proxy lookup with a real room/device. |
| Device issue diagnostics card | In room Overview tab: show which device is failing, probable cause, "Auto-Fix" button (WattBox reboot). Auto-fix only when room is empty. Recommended but not yet built. |

### 🟡 Nice to have
| Item | Notes |
|---|---|
| HCIC map coordinates | Current pin is approximate — update `osu-map-buildings.js` entry when building is officially on OSU's map |
| Chart.js in vendor/ | Admin summary page shows tables; charts would be better |
| Rate limiting (slowapi) | On admin log export endpoint |
| Mobile responsive design | Currently desktop-only |
| 3-Series processor TCP fallback | Port 41794 ping instead of REST API |

---

## Next session prompt

```
I'm continuing work on the BeaverView OSU Presentation Support Dashboard.
Read SESSION-CONTEXT.md at /Users/benjaminfranklinautomation/projects/beaverview/SESSION-CONTEXT.md first —
it has the full project state.

Key files: api/main.py, dashboard/app.js, dashboard/index.html, dashboard/styles.css
Project root: /Users/benjaminfranklinautomation/projects/beaverview/
Dev server: cd "/Users/benjaminfranklinautomation/projects/beaverview/api" && source venv/bin/activate && uvicorn main:app --reload --port 8000
Initialize env: cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/init_local_env.sh
Smoke check: cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/smoke_check.sh
Data migration check: cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/check_data_migration.sh
Hardware IP CSV check: cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/check_hardware_ip_import.sh
Deployment asset check: cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/check_deployment_assets.sh
Pilot readiness: cd "/Users/benjaminfranklinautomation/projects/beaverview" && scripts/check_pilot_readiness.py
```
