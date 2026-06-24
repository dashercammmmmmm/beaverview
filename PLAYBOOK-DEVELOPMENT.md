# BeaverView — Development Playbook
**Audience:** Developers adding features, fixing bugs, understanding the architecture.
**Purpose:** Architecture map, code conventions, how to extend safely.

---

## Architecture overview

```
Browser
  ├── dashboard/index.html      page skeleton + IDs
  ├── dashboard/styles.css      all visual design (design tokens → component styles)
  ├── dashboard/data.js         mock room inventory (window.dashboardData)
  ├── dashboard/app.js          all interactivity (no framework, vanilla JS)
  └── dashboard/vendor/         MapLibre GL (local copy — no CDN)

Backend (FastAPI, port 8000)
  ├── api/main.py               all API endpoints + connector registry
  ├── api/data_mock.py          mock data for backend endpoints
  ├── api/.env                  credentials (never committed)
  └── api/beaverview.db         SQLite — audit_log table
```

**No build step.** No npm, webpack, or transpilation. Edit → save → browser reloads.

---

## State model (app.js)

A single `state` object at the top of `app.js` is the source of truth:

```js
const state = {
  campusId:             "corvallis",  // active campus
  selectedBuildingCode: null,         // MapLibre building ID (string)
  selectedRoomId:       null,         // e.g. "corvallis-kad-101"
  activeTab:            "overview",   // "overview" | "tools" | "incidents" | "log"
  search:               "",           // search field value
  filters:              new Set(),    // active filter IDs
  log:                  [],           // in-memory audit entries
  compact:              false,        // compact/comfortable density toggle
  backendOnline:        false,        // true when /api/health responds
  connectorOverrides:   {},           // campus_id → connector health from API
  lastSynced:           null          // ISO timestamp of last connector fetch
};
```

**Never update state directly in an event handler without re-rendering.**
Pattern: `state.x = value; renderRoom();` (or `renderAll()` for campus-wide changes).

---

## Room ID format

All room IDs follow: `{campus}-{building-code}-{room-number}`, lowercased, hyphens only.

Examples: `corvallis-kad-101`, `cascades-tykeson-201`, `hatfield-hmsc-110`

Generated in `allRooms()`:
```js
id: `${campus.id}-${building.code}-${room.number}`.toLowerCase().replace(/[^a-z0-9]+/g, "-")
```

---

## Function reference (app.js)

### Data functions
| Function | What it does |
|---|---|
| `currentCampus()` | Returns the active campus object from `data.js` |
| `campusBuildings(campus)` | All OSU map buildings for a campus (from `osu-map-buildings.js`) |
| `supportBuildingFor(b, campus)` | Finds the matching data.js building for an OSU map building |
| `supportRoomsForBuilding(b, campus)` | Returns rooms from data.js, or generated placeholders |
| `generatedRoomsForBuilding(b)` | Makes 1–3 placeholder rooms for un-inventoried buildings |
| `allRooms(campus)` | Flat list of all rooms with `id` and `building` attached |
| `selectedRoom()` | The currently selected room, or null |
| `buildingSummary(b)` | `{ status, rooms, issues }` — used for map coloring |
| `roomMatchesFilters(room)` | Returns false if room doesn't match active search + filters |

### Render functions
| Function | Renders into |
|---|---|
| `renderAll()` | Everything — calls all render functions below |
| `renderCampusTabs()` | `#campusTabs` |
| `renderFilters()` | `#filters` |
| `renderConnectorList()` | `#connectorList` |
| `renderMap()` | Initializes or updates MapLibre |
| `renderSelectedBuilding()` | `#selectedBuilding` (room shelf below map) |
| `renderRoom()` | `#roomHeader` + `#roomTabs` + `#roomBody` |
| `renderOverview(room)` | Returns HTML string — devices, metrics |
| `renderTools(room)` | Returns HTML string — dynamic tool buttons |
| `renderIncidents(room)` | Returns HTML string — open + closed incidents |
| `renderLog()` | Returns HTML string — audit trail |

### Tool panel renderers (called from the Actions tab)
| Function | Panel shown |
|---|---|
| `renderXPanelTool(room)` | Crestron source select + display + volume |
| `renderScreenConnectTool(room)` | Machine card + session launch |
| `renderPTZTool(room)` | Camera viewport + d-pad + presets |
| `renderWattBoxTool(room)` | Per-outlet status + cycle buttons |
| `renderDeviceWebTool(room)` | Device inventory + launch buttons |
| `renderSharePointTool(room)` | Documentation links |
| `renderServiceNowTool(room)` | Pre-filled incident form |

### Map functions
| Function | What it does |
|---|---|
| `ensureMap()` | Creates the MapLibre map (runs once) |
| `updateMapData(options)` | Refreshes building GeoJSON + selected state |
| `resetMapView()` | Flies to campus center/zoom |
| `selectBuilding(buildingId)` | Sets state + renders shelf + updates map |

### Backend functions
| Function | What it does |
|---|---|
| `checkBackend()` | Pings `/api/health`, sets `state.backendOnline` |
| `refreshConnectors()` | Fetches `/api/campus/{id}/connectors`, updates sidebar |
| `addAudit(action, outcome)` | Adds to local log + POSTs to `/api/rooms/{id}/action` |

---

## How to add a new tool panel

**1. Add the button to `renderTools()`**

Find the `tools` array in `renderTools()`. Add:
```js
{
  label: "My New Tool",
  action: "my_tool_opened",   // logged in audit trail — use snake_case verbs
  tool: "my_tool",            // key used to find the renderer below
  desc: "One-line description shown under the button label"
}
```
Conditional buttons: wrap in `condition && { ... }` and add `.filter(Boolean)` is already there.

**2. Write the renderer function**

Place it after `renderServiceNowTool`. Use `toolPanelWrap(content, note)`:
```js
function renderMyToolTool(room) {
  return toolPanelWrap(`
    <div class="my-tool">
      <!-- your HTML here; room object has all room data -->
      <p>${room.building.code} ${room.number}</p>
    </div>
  `, "Requests route through the BeaverView backend. Without live prerequisites, show a clear pending message.");
}
```
The `toolPanelWrap` helper automatically injects the `← Actions` back button.

**3. Register it in the PANELS map**

Search for `const PANELS =` in the click handler and add:
```js
my_tool: renderMyToolTool,
```

**4. Add CSS if needed**

Add a new class in `styles.css` Section 13 (DEVICE TOOL PANELS).
Use existing variables (`var(--osu-orange)`, `var(--bg-page)`, etc.) — no hardcoded hex.

---

## How to add a new API endpoint

In `api/main.py`:
```python
@app.get("/api/rooms/{room_id}/my-endpoint")
def my_endpoint(room_id: str):
    # validate room_id format if needed
    return {"room_id": room_id, "data": "..."}
```

**Always:**
- Validate `campus_id` against `CONNECTOR_REGISTRY` keys
- Return a `ts` field for timestamps using `_now()`
- Log state-changing actions to `audit_log`
- Return `HTTPException(404)` for missing resources, `501` for unimplemented stubs

---

## How to add a new connector

**1. Add env var detection to the connector registry section in `main.py`:**
```python
_MY_API_KEY = os.getenv("MY_SERVICE_API_KEY", "")
if _MY_API_KEY:
    for campus in CONNECTOR_REGISTRY.values():
        campus["my_service"]["mode"] = "live"
```

**2. Add the connector to all three campus entries in `CONNECTOR_REGISTRY`:**
```python
"my_service": {"status": "mock", "mode": "mock", "last_synced": None},
```

**3. Add it to `data.js` in the `connectors` object of each campus:**
```js
my_service: "mock"
```

**4. Add it to `.env.example` with a comment explaining what credentials are needed.**

**5. Update `renderConnectorList()` in `app.js` if you want a custom display label.**

---

## CSS conventions

- All colors via `var(--token-name)` — never hardcode hex outside of `:root`
- Sections separated by `/* ═══ N. NAME ═══ */` dividers
- Section 7 "APP.JS COMPONENTS" = classes injected via `innerHTML` — don't rename these
- Use `var(--radius-sm/md/lg)` for border-radius, `var(--shadow-*)` for box-shadow
- Design tokens are in Section 1 (lines 1–80) of `styles.css`

### CSS sections reference
| # | Section | What's in it |
|---|---|---|
| 1 | DESIGN TOKENS | All CSS variables |
| 2 | RESET | Box model, typography baseline |
| 3 | LAYOUT | Page grid, three-column structure |
| 4 | HEADER | `.site-header` and its children |
| 5 | SIDEBAR | `.sidebar`, campus tabs, filter chips, connector list |
| 6 | MAP | Map viewport, controls, building shelf |
| 7 | APP.JS COMPONENTS | Classes injected by innerHTML (must not be renamed) |
| 8 | STATUS STYLES | Room pill border colors |
| 9 | HELP / TOUR DIALOG | `.tour-backdrop`, `.tour-card` |
| 10 | COMPACT MODE | Body density toggle |
| 11 | DETAIL PANEL | `.detail-panel`, `.detail-header`, `.room-tabs` |
| 12 | ACCESSIBILITY | Skip nav, focus rings, reduced motion |
| 13 | DEVICE TOOL PANELS | XPanel, SC, PTZ, WattBox, ServiceNow styles |

---

## HTML conventions

- All structural IDs must match what `app.js` queries in the `els` object (top of `app.js`)
- `class` attributes on structural elements can be renamed freely
- `class` attributes on dynamically injected elements (Section 7 in CSS) must not be renamed
- `aria-*` and `role` attributes must be preserved for accessibility
- Adding new sections: duplicate an existing `<div class="sidebar-block">` structure

---

## Backend conventions (main.py)

- All routes return JSON
- Timestamps: always use `_now()` — UTC ISO 8601
- User identity: read from `X-User` request header (placeholder until Entra SSO)
- Connector mode: check `CONNECTOR_REGISTRY[campus_id]["connector"]["mode"]` before deciding mock vs live
- Mock functions: prefix with `_mock` or suffix with `_mock`
- Live implementations: use guarded backend routes, keep mock/offline functions as explicit fallbacks, and surface missing prerequisites as `pending` or clear error responses without exposing secrets or raw device IPs

---

## Database schema

```sql
-- audit_log: every state-changing action
CREATE TABLE audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT    NOT NULL,   -- ISO 8601 UTC
    user         TEXT    NOT NULL DEFAULT 'technician',
    room_id      TEXT    NOT NULL,   -- "campus-building-room"
    action_type  TEXT    NOT NULL,   -- snake_case verb, e.g. "xpanel_launched"
    target       TEXT,               -- optional — device name, outlet number, etc.
    outcome      TEXT    NOT NULL DEFAULT 'success',
    notes        TEXT                -- optional freeform detail
);
```

Query via: `GET /api/audit?campus=corvallis&action_type=wattbox_power_cycle_requested`

---

## Live reload (how it works)

`index.html` contains a polling script at the bottom:
```js
// Polls Last-Modified headers of app.js, styles.css, data.js, index.html every 1.5s
// Only active on localhost — automatically silent in production
```

When you save a file, Python's http.server updates the `Last-Modified` header.
The polling script detects the change and calls `location.reload()`.

**Cache busting:** Script and style tags have `?v=N` suffixes in `index.html`.
When you add a new JS or CSS file, bump the version number on its tag after the first save.

---

## Version history (archive folder)

The `dashboard/archive/` folder contains snapshots of earlier versions:
- `v1-static-clickable-mock` — first static HTML with CSS map
- `v1.1` through `v1.4` — iterative improvements before MapLibre
- `v1.4-maplibre-real-map-engine` — first version with real OSU building footprints

These are read-only reference snapshots. Don't edit them.
