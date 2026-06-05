# BeaverView — Content Playbook
**Audience:** Non-developers. No coding experience required.
**Purpose:** Add rooms, change colors, update labels, adjust the layout.

> **Before you start:** The project must be running. See `PLAYBOOK-SETUP.md`.
> Open the files below in VS Code or any plain-text editor (not Word).

---

## The two files you'll edit most

| File | Location | What it controls |
|---|---|---|
| `data.js` | `dashboard/data.js` | Room inventory — names, statuses, devices |
| `styles.css` | `dashboard/styles.css` | All colors, sizes, fonts |

Save either file and the browser reloads automatically within ~2 seconds.

---

## Changing colors

Open `dashboard/styles.css`. The very first section (lines 1–80) is labeled **DESIGN TOKENS**.
Every color used anywhere in the dashboard comes from a variable here. Change it once and it
updates everywhere.

```css
:root {
  --osu-orange:        #D73F09;   /* active tabs, selected rooms, action buttons */
  --osu-orange-dark:   #A83205;   /* orange hover states */
  --osu-orange-faint:  #FFF0EB;   /* light orange backgrounds */

  --status-ok:         #15803D;   /* available rooms (green) */
  --status-active:     #1D6A9F;   /* in-use rooms (blue) */
  --status-warn:       #B45309;   /* rooms with issues (amber) */
  --status-offline:    #6B7280;   /* offline rooms (gray) */

  --bg-page:           #EEF2F7;   /* overall page background */
  --bg-panel:          #FFFFFF;   /* card and panel background */
  --text-strong:       #111827;   /* headings and important values */
  --text-muted:        #6B7280;   /* labels and secondary text */
}
```

**Example — make the header a different color:**
Search for `.site-header` in `styles.css` (around line 100):
```css
.site-header {
  background: #111827;             /* ← change this hex value */
  border-bottom: 3px solid var(--osu-orange);  /* ← and this stripe */
}
```

**Example — change "available" rooms from green to teal:**
```css
--status-ok: #0D9488;
```

---

## Adding a room to an existing building

Open `dashboard/data.js`. Search for the building code (e.g., `"KAd"`) and find its `rooms` array.
Add a new object following this exact template:

```js
{
  number: "210",               // room number as a string
  type: "Seminar Room",        // room type label shown in the UI
  status: "available",         // "available" | "in-use" | "issue" | "offline"
  health: 94,                  // 0–100 (shown as a percentage)
  activeEvent: "Available",    // or e.g. "CS 101 until 2:00 PM"
  processor: "online",         // "online" | "offline" | "mock" — set by direct device poller
  display: "on",               // "on" | "off" | "standby" | "unknown"
  screenconnect: true,         // true if this room has a ScreenConnect machine
  wattbox: false,              // true if this room has a WattBox
  hybrid: true,                // true if hybrid-capable
  stale: false,                // true if data hasn't updated recently
  incidents: {
    open: [],                  // e.g. ["INC0012500 - Projector lamp warning"]
    closed: []
  },
  devices: [
    // Format: ["Device type", "Manufacturer", "Model", "Connection note"]
    ["Display",   "NEC",      "P-series",  "Sanitized host"],
    ["Control Processor", "Crestron", "CP4", "Sanitized host"]
  ]
}
```

**Tip:** Copy an existing room object and edit the values rather than typing from scratch.

### Which tool panels appear?
The Actions tab shows only the tools that match the room's equipment:
- `screenconnect: true` → Start ScreenConnect button appears
- `wattbox: true` → Check WattBox + Power cycle buttons appear
- A device with type `"Camera"` → Control PTZ Camera button appears
- A device with type `"Control Processor"` or `"Processor"` → Launch XPanel button appears

---

## Adding a new building

In `data.js`, find the campus you want (search for `id: "corvallis"`) and add an object to
its `buildings` array:

```js
{
  code: "Graf",           // MUST match a code in osu-map-buildings.js for map highlighting
  name: "Graf Hall",      // full building name
  x: 55, y: 40,          // ignored (MapLibre uses real coordinates from osu-map-buildings.js)
  rooms: [ /* ... */ ]
}
```

**How to find the right building code:**
Open `dashboard/osu-map-buildings.js` and search for the building name. The `code` field
next to it is what you need. Examples: `KAd`, `LINC`, `MU`, `ALS`, `KEC`.

If the code doesn't match, the building footprint won't highlight on the map — but the rooms
will still appear when the building is clicked (as a generated placeholder).

---

## Adding a new campus

In `data.js`, add an entry to the `campuses` array:

```js
{
  id: "newport",              // lowercase, no spaces — used in URLs and code
  name: "Newport",            // displayed in the Campus tab
  subtitle: "Hatfield extension site",
  connectors: {               // initial mock statuses
    crestron: "mock",
    live25: "mock",
    screenconnect: "mock",
    wattbox: "mock",
    servicenow: "mock"
  },
  buildings: [ /* ... */ ]
}
```

Also add a map center/zoom in `app.js` (search for `campusViewDefaults`):
```js
newport: { center: [-124.065, 44.625], zoom: 16 }
```

And add a filter in `osu-map-buildings.js` — or just tag buildings with `campus: "newport"`.

---

## Adding a quick filter (Show Only checkboxes)

Filters live at the bottom of `data.js` in the `filters` array:

```js
{ id: "dsp", label: "Has DSP" }
```

Then add the matching condition in `app.js` inside `roomMatchesFilters()` (search for that
function name):

```js
if (state.filters.has("dsp") && !room.devices?.some(d => d[1] === "Q-SYS")) return false;
```

---

## Changing layout column widths

In `styles.css`, find the `DESIGN TOKENS` section (top of file):

```css
--sidebar-w:  264px;   /* left panel width */
--detail-w:   368px;   /* right panel width */
--gutter:      14px;   /* gap between all panels */
```

The map fills whatever space is left between the two panels.

---

## Changing the text in the help dialog

Open `dashboard/index.html`. Search for `tour-card`. You'll find the help dialog content:

```html
<h2 class="tour-card__title" id="tour-title">Using BeaverView</h2>
<ol class="tour-card__steps">
  <li>Use the <strong>Campus</strong> tabs to switch between ...</li>
  <li>Click any colored building on the map ...</li>
  ...
</ol>
```

Edit the `<li>` items freely. Keep the `id="tour-title"` attribute — don't remove it.

---

## Changing the page title in the browser tab

Open `dashboard/index.html`, line 20:
```html
<title>BeaverView — OSU AV Support</title>
```

---

## Changing the header name and department

Open `dashboard/index.html`, find `.site-header__brand`:
```html
<span class="site-header__name">BeaverView</span>
<span class="site-header__dept">OSU Presentation Support</span>
```

---

## What NOT to change (will break things)

| Don't touch | Why |
|---|---|
| Any `id="..."` attribute in `index.html` | `app.js` uses these to find elements |
| Class names listed in Section 7 of `styles.css` ("APP.JS COMPONENTS") | `app.js` injects HTML with these class names |
| `osu-map-buildings.js` | Generated from OSU's public map API — regenerate, don't edit |
| `dashboard/vendor/` folder | Local copy of MapLibre GL — don't modify |
| `api/beaverview.db` | SQLite audit database — edit via the `/api/audit` endpoint |
| The `?v=2` cache-buster on script tags in `index.html` | Browser cache control — see Development Playbook if you need to bump it |

---

## Room status reference

| Status value | Color | Meaning |
|---|---|---|
| `"available"` | Green | Room is free, system healthy |
| `"in-use"` | Blue | Class or event in progress |
| `"issue"` | Amber | Device problem or open incident |
| `"offline"` | Gray | Processor not reporting / no data |
