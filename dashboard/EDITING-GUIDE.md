# BeaverView — Editing Guide

> **This file is a quick-reference index.**
> For full step-by-step instructions, open the playbook that matches your task (all in the project root folder, one level up).

---

## Which playbook do I need?

| I want to… | Open this file |
|---|---|
| **Run it for the first time (Mac/localhost)** | `../PLAYBOOK-SETUP.md` |
| **Add rooms, change colors, edit labels** | `../PLAYBOOK-CONTENT.md` |
| **Connect a real API (Fusion, ScreenConnect, etc.)** | `../PLAYBOOK-CONNECTORS.md` |
| **Add a feature or understand the code** | `../PLAYBOOK-DEVELOPMENT.md` |
| **Deploy to a server (generic Linux)** | `../PLAYBOOK-PRODUCTION.md` |
| **Deploy to a VMware VM for Windows clients** | `../PLAYBOOK-DEPLOYMENT.md` |
| **Build the admin panel (room editor, log management)** | `../PLAYBOOK-ADMIN.md` |

---

## File map (quick reference)

| File | What it does | Edit when… |
|---|---|---|
| `index.html` | Page structure — labels, headings, skeleton | Changing static text |
| `styles.css` | All visual design — colors, sizes, fonts | Changing the look |
| `data.js` | Mock room and building inventory | Adding/editing rooms |
| `app.js` | All interactivity — map, tabs, tool panels, API calls | Adding features |
| `osu-map-buildings.js` | 278+ OSU building footprints | Almost never (regenerate, don't edit) |
| `../api/main.py` | FastAPI backend — endpoints, connector registry, audit log | Wiring real APIs |
| `../api/.env` | Live credentials (never committed to Git) | Connecting live systems |

---

## Most common edits

### Change a color
Open `styles.css` → find the `DESIGN TOKENS` section at the very top → change the variable value. One change updates everywhere that color is used.

Key variables: `--osu-orange`, `--status-ok` (green), `--status-active` (blue), `--status-warn` (amber), `--status-offline` (gray), `--bg-page`, `--bg-panel`.

Full guide: `../PLAYBOOK-CONTENT.md` → Changing colors

---

### Add a room
Open `data.js` → find the building (search for its code, e.g. `"KAd"`) → add an object to its `rooms` array.

Minimum required fields:
```js
{
  number: "210",
  type: "Seminar Room",
  status: "available",     // "available" | "in-use" | "issue" | "offline"
  health: 94,
  activeEvent: "Available",
  processor: "online",  // "online" | "offline" | "mock" — set by Crestron poller
  display: "on",
  screenconnect: true,
  wattbox: false,
  hybrid: true,
  stale: false,
  incidents: { open: [], closed: [] },
  devices: [
    ["Display", "NEC", "P-series", "Sanitized host"],
    ["Control Processor", "Crestron", "CP4", "Sanitized host"]
  ]
}
```

Full guide: `../PLAYBOOK-CONTENT.md` → Adding a room to an existing building

---

### Connect a live API
```bash
cd api
cp .env.example .env    # first time only
nano .env               # fill in credentials for the connector you want
./start.sh              # restart — badge in sidebar turns green automatically
```

Full guide per connector: `../PLAYBOOK-CONNECTORS.md`

---

### Add a new tool panel (developer)
1. Add an entry to the `tools` array in `renderTools()` in `app.js`
2. Write a renderer function — use `toolPanelWrap(html, note)` as the wrapper
3. Register it in the `PANELS` map inside the click handler

Full guide: `../PLAYBOOK-DEVELOPMENT.md` → How to add a new tool panel

---

## Room status reference

| Value | Color | Meaning |
|---|---|---|
| `"available"` | Green | Room free, system healthy |
| `"in-use"` | Blue | Class or event in progress |
| `"issue"` | Amber | Device problem or open incident |
| `"offline"` | Gray | Processor not reporting / no data |

---

## What NOT to change

| Don't touch | Why |
|---|---|
| Any `id="..."` attribute in `index.html` | `app.js` uses these to find elements |
| Class names in the `APP.JS COMPONENTS` section of `styles.css` | `app.js` injects HTML with these class names |
| `osu-map-buildings.js` | Generated from OSU's public map API — regenerate, don't edit |
| `../api/beaverview.db` | SQLite audit database — query via `/api/audit`, don't edit directly |
| `dashboard/vendor/` | Local MapLibre GL copy — do not modify |
