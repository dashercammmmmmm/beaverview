# BeaverView — Session Context & Handoff
**Purpose:** Reference for the next Claude session. Read this before doing anything.
**Last updated:** After git init, admin link, search fixes, HCIC placeholder, CLAUDE.md.

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
- Project root: `/Users/cam/Documents/New project/`
- API folder:   `/Users/cam/Documents/New project/api/`
- Dashboard:    `/Users/cam/Documents/New project/dashboard/`
- **To run locally:** Open Terminal → paste the dev server command in the "How to start the server" section below
- **Local URL:** `http://localhost:8000`
- **Admin panel (dev):** `http://localhost:8000/admin/` — works without login when AZURE_CLIENT_ID is NOT set in .env

---

## Repository layout (active files only)
```
New project/
├── .gitignore               ← excludes .env, beaverview.db, hardware_ips.csv, *.pdf
├── .env.example             ← credential template (safe to commit)
├── CLAUDE.md                ← AI assistant guidance (architecture, dev commands)
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
cd "/Users/cam/Documents/New project/api" && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
```

**Every time after that** (venv already exists):
```
cd "/Users/cam/Documents/New project/api" && source venv/bin/activate && uvicorn main:app --reload --port 8000
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

---

## What was just changed (latest sessions)

### Git repository initialized
- `git init` + initial commit (ec60a6f) — all project files committed
- Remaining step: create repo on GitHub and `git remote add origin …` + `git push -u origin main`

### Python venv required (macOS)
- macOS Homebrew Python blocks system-wide `pip install` (PEP 668)
- Fixed: `api/venv/` created, `starlette-sessions` version corrected to `>=0.3.0` in `requirements.txt`

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
| **Push to GitHub** | `git init` done locally (commit ec60a6f). Create repo on GitHub, then `git remote add origin …` + `git push -u origin main` |
| **Azure App Registration** | IT team registers BeaverView in Azure Portal. See `PLAYBOOK-DEPLOYMENT.md` Part 7, Steps 1–3. Requires Application Administrator role. |
| **.env credentials** | Fill in `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, group object IDs |
| **Ubuntu VM** | Not yet created. See `PLAYBOOK-DEPLOYMENT.md` Part 2 |
| **Data migration** | `python3 migrate_data.py` not yet run — SQLite rooms table is empty (dev uses `data.js` mock) |

### 🟠 Important — needed soon
| Item | Notes |
|---|---|
| Windows hosts file entries | `192.168.x.x beaverview` on each Windows PC |
| nginx + SSL + systemd setup | `PLAYBOOK-DEPLOYMENT.md` Parts 7–8 |
| VLAN routing on Ubuntu VM | AV devices on separate subnet need static route |
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
Read SESSION-CONTEXT.md at /Users/cam/Documents/New project/SESSION-CONTEXT.md first —
it has the full project state.

Key files: api/main.py, dashboard/app.js, dashboard/index.html, dashboard/styles.css
Project root: /Users/cam/Documents/New project/
Dev server: cd "/Users/cam/Documents/New project/api" && source venv/bin/activate && uvicorn main:app --reload --port 8000
```
