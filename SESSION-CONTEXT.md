# BeaverView — Session Context & Handoff
**Purpose:** Reference for the next Claude session. Read this before doing anything.
**Last updated:** After search/history/admin-bypass fixes + complete build playbook generated.

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
├── api/
│   ├── main.py              ← FastAPI app (1360+ lines) — ALL backend code
│   ├── data_mock.py         ← 19 mock rooms for dev/test
│   ├── requirements.txt     ← fastapi, uvicorn, python-dotenv, httpx, msal, starlette-sessions, itsdangerous
│   ├── .env                 ← YOUR credentials (NEVER commit — in .gitignore)
│   ├── migrate_data.py      ← one-time: data.js → SQLite
│   ├── import_device_ips.py ← one-time: hardware_ips.csv → SQLite
│   └── beaverview.db        ← SQLite database (auto-created on first run)
└── dashboard/
    ├── index.html           ← main dashboard page
    ├── app.js               ← all interactivity (~1150 lines)
    ├── styles.css           ← all visual design (~1400 lines)
    ├── data.js              ← room inventory + campus data (472 lines)
    ├── osu-map-buildings.js ← 278 OSU building footprints (DO NOT EDIT)
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
```
cd "/Users/cam/Documents/New project/api" && uvicorn main:app --reload --port 8000
```

### Step 3 — Open the site
Open **Chrome** or **Safari** and go to: `http://localhost:8000`

### Step 4 — Open the admin panel (dev mode — no login needed)
Go to: `http://localhost:8000/admin/`

### To stop the server:
Click in the Terminal window and press **Control + C** (hold Control, tap C).

### If uvicorn is not found:
```
cd "/Users/cam/Documents/New project/api" && pip3 install -r requirements.txt && uvicorn main:app --reload --port 8000
```

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

## What was just changed (latest session)

### Search bar — 3 fixes
1. **Single match → zooms in** to zoom 18.5 (street level) using `map.flyTo()`
2. **Single match → building turns orange** (auto-selects building, which triggers the selected color)
3. **Single match → right panel updates** with rooms for that building
4. **2–6 matches** zoom closer than campus default (maxZoom 17.5 vs 15.25)

### History tab (was "Log")
- Tab renamed from "Log" → **"History"**
- Shows **last 5 building + room combos** visited, most recent first
- Click any history row to fly back to that location
- Individual tool actions still go to backend audit log (admin console only)
- New functions: `addToHistory(room)`, updated `renderLog()`, history-row click handler

### Admin panel dev bypass
- `/api/me` now returns `{role: 'admin'}` automatically when:
  - Running on localhost (127.0.0.1)
  - AND `AZURE_CLIENT_ID` is not set in `.env`
- Auto-disables in production when Azure creds are added

### Comprehensive build playbook generated
- `BeaverView-Complete-Build-Playbook.pdf` — 167 pages, every file copy-paste ready
- Generated by `generate_complete_playbook.py`

---

## What is NOT done (priority order)

### 🔴 Blocking — must fix before production
| Item | Notes |
|---|---|
| **Git repository** | Files are local only. Need to `git init` and push to GitHub or Azure DevOps |
| **Azure App Registration** | IT team needs to do this. See playbook Part 7, Steps 1–3. They need Application Administrator role in Azure Portal |
| **.env credentials** | AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, group IDs — not filled in yet |
| **Ubuntu VM** | Not yet created. See playbook Part 2 |
| **Data migration** | `python3 migrate_data.py` not yet run — rooms table is empty (dev works on mock data) |

### 🟠 Important — needed soon
| Item | Notes |
|---|---|
| Add "Admin" link to main dashboard header | Show only when role === 'admin'. Small app.js + styles.css change |
| Windows hosts file entries | `192.168.x.x beaverview` on each Windows PC |
| nginx + SSL + systemd setup | Part 7–8 of playbook |
| VLAN routing on Ubuntu VM | AV devices on separate subnet need static route |

### 🟡 Nice to have
| Item | Notes |
|---|---|
| Chart.js in vendor/ | For admin summary bar charts (currently shows tables, not charts) |
| Rate limiting (slowapi) | On admin log export endpoint |
| Mobile responsive design | Currently desktop-only |
| 3-Series processor TCP fallback | Port 41794 ping instead of REST API |

---

## Next session prompt

```
I'm continuing work on the BeaverView OSU Presentation Support Dashboard.
Read SESSION-CONTEXT.md at /Users/cam/Documents/New project/SESSION-CONTEXT.md first —
it has the full project state.

Here is what I need help with next:
1. Set up a git repository so I can keep the project organized and push it to GitHub
2. Add an "Admin" link to the main dashboard header that only shows when the user's
   role is 'admin' (the /api/me endpoint returns the role)
3. I want to test the admin panel — the dev bypass is in place so it should work on
   localhost. Walk me through what to expect and how to verify each admin page works.

Key files: api/main.py, dashboard/app.js, dashboard/index.html, dashboard/styles.css
Project root: /Users/cam/Documents/New project/
Dev server command: cd "/Users/cam/Documents/New project/api" && uvicorn main:app --reload --port 8000
```
