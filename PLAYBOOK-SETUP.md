# BeaverView — Setup Playbook
**Audience:** Anyone running this project for the first time.
**Time:** ~15 minutes.

---

## What you'll have at the end
- The dashboard running at `http://localhost:8000/`
- A working map of OSU Corvallis, Cascades, and Hatfield Marine campuses
- All tool panels functional (mock data — no real API connections yet)
- Live reload active so the browser refreshes automatically when you save files

---

## Prerequisites

| Requirement | Check | Install |
|---|---|---|
| macOS 12+ or Linux | `sw_vers` | — |
| Python 3.11+ | `python3 --version` | [python.org](https://python.org) |
| A text editor | — | VS Code recommended |
| A web browser | — | Chrome or Firefox |

You do **not** need Node.js, npm, Docker, or any build tools.

---

## Step 1 — Get the project files

If you received a zip file:
1. Unzip it anywhere (e.g. `~/Documents/New project/`)
2. Open Terminal and run: `cd ~/Documents/New\ project`

If you're cloning from Git:
```bash
git clone <repo-url> ~/Documents/New\ project
cd ~/Documents/New\ project
```

Verify the folder structure:
```
New project/
├── api/
│   ├── main.py          ← backend
│   ├── start.sh         ← startup script
│   ├── .env.example     ← credential template
│   └── requirements.txt
└── dashboard/
    ├── index.html       ← the page
    ├── app.js           ← all interactivity
    ├── styles.css       ← all visual design
    ├── data.js          ← mock room inventory
    └── vendor/maplibre/ ← map library (local, no CDN)
```

---

## Step 2 — Start the backend

```bash
cd ~/Documents/New\ project/api
./start.sh
```

The first run takes ~30 seconds to create a Python virtual environment and install packages.
You'll see:

```
Starting BeaverView API on http://localhost:8000/
Dashboard: http://localhost:8000/
API docs:  http://localhost:8000/docs
```

**Leave this terminal window open.** The server runs in the foreground.

> **Troubleshooting:**
> - `permission denied: ./start.sh` → run `chmod +x start.sh` first
> - `python3: command not found` → install Python 3.11+ from python.org
> - `port 8000 already in use` → another process owns port 8000. Run `lsof -ti:8000 | xargs kill` to free it.

---

## Step 3 — Open the dashboard

Open your browser and go to: **http://localhost:8000/**

You should see:
- A dark header: **BeaverView · OSU Presentation Support**
- A sidebar with Campus tabs, filters, and Connector Health badges
- The OSU Corvallis campus map with colored building footprints
- Status bar: "278 buildings · 954 mock rooms"

If the map is blank/grey, wait 3–5 seconds for the map tiles to load (requires internet for street map tiles; building footprints are local).

---

## Step 4 — Verify the tool panels work

1. Click any colored building on the map (e.g., **KAd** — Kerr Administration)
2. A room shelf appears below the map. Click **KAd 101**.
3. The detail panel on the right shows the Overview tab.
4. Click the **Actions** tab.
5. Click **Launch XPanel** → you should see a control panel with an **Open Proxied XPanel** launch button. With no live credentials, the panel reports the connector prerequisite instead of opening a raw device URL.
6. Click **← Actions** to go back.
7. Click **Draft ServiceNow ticket** → a pre-filled incident form appears. Submitting it calls the backend and returns a mock draft until ServiceNow credentials are configured.

These workflows are guarded: no credentials are needed for local review, and live actions stay pending until the required `.env` values and Hardware IP records are loaded.

---

## Step 5 — Confirm live reload is active

1. Open `dashboard/styles.css` in a text editor.
2. Find `--osu-orange: #D73F09;` near the top and change it to `--osu-orange: #FF0000;`.
3. Save the file.
4. Within ~2 seconds, the browser should reload automatically and the header stripe turns bright red.
5. Undo the change (restore `#D73F09`) and save again.

Live reload only works on `localhost`. It polls `app.js`, `styles.css`, `data.js`, and `index.html`.

---

## Step 6 — (Optional) Run both servers during development

The backend at port 8000 serves both the API and the static frontend.
During active development you may want the static file server at port 8001 for faster reloads:

```bash
# Terminal 1 — backend (API + audit log)
cd api && ./start.sh

# Terminal 2 — static file server (faster CSS/JS reload)
cd dashboard && python3 -m http.server 8001
# open http://localhost:8001/
```

The static server doesn't have the API, so `/api/health` will 404 — the dashboard gracefully
falls back to mock data and shows "Showing mock data" in the Connector Health section.

---

## What's running

| Port | Process | What it serves |
|---|---|---|
| 8000 | FastAPI (uvicorn) | Dashboard + all `/api/...` endpoints |
| 8001 | Python http.server | Static files only (development convenience) |

The database is at `api/beaverview.db` (SQLite). It's created automatically on first start.
Every tool action you click is logged there.

---

## Next steps

- **Add rooms or buildings** → see `PLAYBOOK-CONTENT.md`
- **Connect a real API** → see `PLAYBOOK-CONNECTORS.md`
- **Change the look** → see `PLAYBOOK-CONTENT.md` → Changing colors section
- **Add a new feature** → see `PLAYBOOK-DEVELOPMENT.md`
- **Deploy to a server** → see `PLAYBOOK-PRODUCTION.md`
