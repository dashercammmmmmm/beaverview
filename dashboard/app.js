const data = window.dashboardData;

const state = {
  campusId: data.campuses[0].id,
  selectedBuildingCode: null,
  selectedRoomId: null,
  activeTab: "overview",
  search: "",
  filters: new Set(),
  log: [],
  history: [],   // last 5 building+room combos visited
  compact: false,
  backendOnline: false,
  connectorOverrides: {},  // campus_id -> connector health object from /api
  scheduleOverrides: {},   // campus_id -> {mode, ts, eventsByRoomId} from /api/campus/{id}/schedule
  lastSynced: null,         // ISO timestamp of last successful connector fetch
  chatHistory: {}           // room_id -> [{role, content}, ...]
};

const els = {
  campusTabs: document.querySelector("#campusTabs"),
  filters: document.querySelector("#filters"),
  connectorList: document.querySelector("#connectorList"),
  mapHeading: document.querySelector("#mapHeading"),
  campusFrame: document.querySelector("#campusFrame"),
  campusGrid: document.querySelector("#campusGrid"),
  selectedBuilding: document.querySelector("#selectedBuilding"),
  roomHeader: document.querySelector("#roomHeader"),
  roomTabs: document.querySelector("#roomTabs"),
  roomBody: document.querySelector("#roomBody"),
  statusSummary: document.querySelector("#statusSummary"),
  search: document.querySelector("#globalSearch"),
  tourButton: document.querySelector("#tourButton"),
  tourOverlay: document.querySelector("#tourOverlay"),
  closeTour: document.querySelector("#closeTour"),
  closeTourX: document.querySelector("#closeTourX"),
  densityToggle: document.querySelector("#densityToggle"),
  zoomIn: document.querySelector("#zoomIn"),
  zoomOut: document.querySelector("#zoomOut"),
  resetMap: document.querySelector("#resetMap"),
  adminLink: document.querySelector("#adminLink")
};

// Debug: check for null elements
const nullEls = Object.entries(els).filter(([_, el]) => el === null).map(([name]) => name);
if (nullEls.length > 0) {
  console.error('❌ Missing DOM elements:', nullEls);
}

function currentCampus() {
  return data.campuses.find((campus) => campus.id === state.campusId);
}

function campusBuildings(campus = currentCampus()) {
  return (window.osuMapBuildings || []).filter((building) => building.campus === campus.id);
}

function supportBuildingFor(realBuilding, campus = currentCampus()) {
  const code = (realBuilding.code || "").toLowerCase();
  return campus.buildings.find((building) => {
    const mockCode = (building.code || "").toLowerCase();
    return mockCode && code && mockCode === code;
  });
}

function supportRoomsForBuilding(realBuilding, campus = currentCampus()) {
  const supportBuilding = supportBuildingFor(realBuilding, campus);
  return supportBuilding ? supportBuilding.rooms : generatedRoomsForBuilding(realBuilding);
}

function generatedRoomsForBuilding(building) {
  const seed = Number(building.id) || 1;
  const roomCount = seed % 4 + 2;
  const statusCycle = ["available", "available", "in-use", "issue"];
  return Array.from({ length: roomCount }, (_, index) => {
    const floor = Math.floor(index / 3) + 1;
    const number = `${floor}${String((index % 3) * 10 + 10).padStart(2, "0")}`;
    const status = statusCycle[(seed + index) % statusCycle.length];
    const hasOpenIncident = status === "issue";
    return {
      number,
      type: "Inventory placeholder",
      generated: true,
      status,
      health: status === "issue" ? 74 : status === "in-use" ? 88 : 96,
      activeEvent: status === "in-use" ? "Mock class/event in progress" : "Available",
      processor: "mock",
      display: status === "issue" ? "needs review" : "mock",
      screenconnect: seed % 2 === 0,
      wattbox: seed % 3 === 0,
      hybrid: seed % 5 === 0,
      stale: false,
      incidents: {
        open: hasOpenIncident ? [`MOCK-${building.id}-${number} - Placeholder issue`] : [],
        closed: []
      },
      devices: [
        ["Room inventory", "Pending import", "Hardware IP List", "No real device data loaded"],
        ["Display/control", "Mock", "Placeholder", "Will be replaced by secure .xlsx import"]
      ]
    };
  });
}

function allRooms(campus = currentCampus()) {
  return campusBuildings(campus).flatMap((building) =>
    supportRoomsForBuilding(building, campus).map((room) => {
      const id = `${campus.id}-${building.code}-${room.number}`.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      const scheduleSource = state.scheduleOverrides[campus.id];
      const scheduleEvent = scheduleSource?.eventsByRoomId?.[id];
      return {
        ...room,
        id,
        building,
        activeEvent: scheduleEvent?.active_event || room.activeEvent,
        scheduleMode: scheduleEvent ? scheduleSource.mode : null,
        scheduleSynced: scheduleEvent ? scheduleSource.ts : null
      };
    })
  );
}

function selectedRoom() {
  return allRooms().find((room) => room.id === state.selectedRoomId) || null;
}

function statusLabel(status) {
  return {
    available: "Available",
    "in-use": "In use",
    issue: "Issue",
    offline: "Offline"
  }[status] || status;
}

function roomMatchesFilters(room) {
  if (state.filters.has("active") && room.activeEvent === "Available") return false;
  if (state.filters.has("openIncident") && room.incidents.open.length === 0) return false;
  if (state.filters.has("offline") && room.status !== "offline") return false;
  if (state.filters.has("issue") && !["issue", "offline"].includes(room.status)) return false;
  if (state.filters.has("wattbox") && !room.wattbox) return false;
  if (state.filters.has("screenconnect") && !room.screenconnect) return false;
  if (state.filters.has("hybrid") && !room.hybrid) return false;
  if (state.filters.has("stale") && !room.stale) return false;
  return true;
}

function normalizeSearch(s) {
  return s.toLowerCase()
    .replace(/['’‘`]/g, "")   // strip apostrophes
    .replace(/[-–—]/g, " ")             // dashes → space
    .replace(/&/g, "and")
    .replace(/[.,()]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function buildingMatches(building) {
  const term = normalizeSearch(state.search.trim());
  const rooms = allRooms().filter((room) => room.building.id === building.id);
  const hasFilters = state.filters.size > 0;
  const passesFilter = hasFilters ? rooms.some(roomMatchesFilters) : true;
  if (!passesFilter) return false;
  if (!term) return true;
  const normCode = normalizeSearch(building.code || "");
  const normName = normalizeSearch(building.name);
  return (
    normCode.includes(term) ||
    normName.includes(term) ||
    rooms.some((room) =>
      normalizeSearch(`${building.code || building.name} ${room.number}`).includes(term)
    )
  );
}

function buildingSummary(building) {
  const rooms = allRooms().filter((room) => room.building.id === building.id);
  const issues = rooms.filter((room) => ["issue", "offline"].includes(room.status)).length;
  const inUse = rooms.filter((room) => room.status === "in-use").length;
  const available = rooms.filter((room) => room.status === "available").length;
  const status = !rooms.length ? "map-only" : issues ? "issue" : inUse ? "in-use" : "available";
  return { rooms, issues, inUse, available, status };
}

const campusViewDefaults = {
  corvallis: { center: [-123.27977726027, 44.563696347448], zoom: 15.25 },
  cascades: { center: [-121.334198, 44.043224], zoom: 16 },
  hatfield: { center: [-124.0453, 44.6222], zoom: 16 }
};

let map = null;
let mapReady = false;

function buildingDisplayName(building) {
  return building.sourceName === "Building" || building.name.startsWith("Building ")
    ? `Unnamed OSU map building ${building.id}`
    : building.name;
}

function buildingLabel(building) {
  return building.code || "";
}

function buildingGeoJSON(buildings, matchedIds = null) {
  return {
    type: "FeatureCollection",
    features: buildings.map((building) => {
      const summary = buildingSummary(building);
      const matches = matchedIds === null || matchedIds.has(building.id);
      return {
        type: "Feature",
        id: building.id,
        geometry: building.polygon && building.polygon.length
          ? { type: "Polygon", coordinates: [building.polygon] }
          : { type: "Point", coordinates: [building.lng, building.lat] },
        properties: {
          id: building.id,
          campus: building.campus,
          name: buildingDisplayName(building),
          officialName: building.name,
          code: buildingLabel(building),
          sourceName: building.sourceName,
          status: summary.status,
          supportRooms: summary.rooms.length,
          issues: summary.issues,
          selected: state.selectedBuildingCode === building.id,
          matches
        }
      };
    })
  };
}

function campusBoundsLngLat(buildings) {
  if (!buildings.length) return null;
  const coords = buildings.flatMap((building) => (
    building.polygon && building.polygon.length ? building.polygon : [[building.lng, building.lat]]
  ));
  const lngs = coords.map((coord) => coord[0]);
  const lats = coords.map((coord) => coord[1]);
  return [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]];
}

function buildingCenter(building) {
  // Returns [lng, lat] centroid of a building (from polygon average or point)
  if (building.polygon && building.polygon.length) {
    let sumLng = 0, sumLat = 0;
    for (const [lng, lat] of building.polygon) { sumLng += lng; sumLat += lat; }
    return [sumLng / building.polygon.length, sumLat / building.polygon.length];
  }
  if (building.lng && building.lat) return [building.lng, building.lat];
  return null;
}

function ensureMap() {
  if (map || !window.maplibregl) return;

  map = new maplibregl.Map({
    container: "mapCanvas",
    style: {
      version: 8,
      glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
      sources: {
        osm: {
          type: "raster",
          tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
          attribution: "© OpenStreetMap contributors"
        }
      },
      layers: [
        { id: "osm", type: "raster", source: "osm" }
      ]
    },
    center: campusViewDefaults[state.campusId].center,
    zoom: campusViewDefaults[state.campusId].zoom,
    minZoom: 13,
    maxZoom: 20,
    pitch: 0,
    bearing: 0,
    attributionControl: false
  });

  map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");

  map.on("load", () => {
    mapReady = true;
    map.addSource("osu-buildings", {
      type: "geojson",
      data: buildingGeoJSON(campusBuildings())
    });

    map.addLayer({
      id: "building-fill",
      type: "fill",
      source: "osu-buildings",
      paint: {
        "fill-color": [
          "case",
          ["==", ["get", "selected"], true], "#d73f09",        /* OSU orange — selected */
          ["==", ["get", "status"], "issue"], "#f59e0b",       /* Amber — accessible issue indicator */
          ["==", ["get", "status"], "offline"], "#9ca3af",     /* Gray — offline/unknown */
          ["==", ["get", "status"], "in-use"], "#3b82f6",      /* Blue — in use */
          ["==", ["get", "status"], "available"], "#10b981",   /* Green — available */
          "#6b7280"                                              /* Dark gray — default */
        ],
        "fill-opacity": [
          "case",
          ["==", ["get", "selected"], true], 0.85,
          ["==", ["get", "matches"], false], 0.15,
          [">", ["get", "supportRooms"], 0], 0.72,
          0.55
        ]
      }
    });

    map.addLayer({
      id: "building-outline",
      type: "line",
      source: "osu-buildings",
      paint: {
        "line-color": ["case", ["==", ["get", "selected"], true], "#1F2937", "#d1d5db"],
        "line-width": ["case", ["==", ["get", "selected"], true], 3, 1.2],
        "line-opacity": ["case", ["==", ["get", "matches"], false], 0.15, 0.7]
      }
    });

    map.addLayer({
      id: "building-labels",
      type: "symbol",
      source: "osu-buildings",
      minzoom: 15,
      filter: ["!=", ["get", "code"], ""],
      layout: {
        "text-field": ["get", "code"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 15, 10, 17, 13, 19, 16],
        "text-font": ["Noto Sans Regular"],
        "text-allow-overlap": false,
        "text-ignore-placement": false
      },
      paint: {
        "text-color": "#111827",
        "text-halo-color": "#f3f4f6",
        "text-halo-width": 1.8
      }
    });

    map.on("click", "building-fill", (event) => {
      const feature = event.features && event.features[0];
      if (!feature) return;
      selectBuilding(feature.properties.id);
    });

    map.on("mouseenter", "building-fill", () => {
      map.getCanvas().style.cursor = "pointer";
    });

    map.on("mouseleave", "building-fill", () => {
      map.getCanvas().style.cursor = "";
    });

    updateMapData();
  });
}

function updateMapData(options = {}) {
  ensureMap();
  if (!mapReady) return;
  const all = campusBuildings();
  const matched = all.filter(buildingMatches);
  const matchedIds = (state.search.trim() || state.filters.size > 0)
    ? new Set(matched.map((b) => b.id))
    : null;  // null = all match (no dimming)
  const source = map.getSource("osu-buildings");
  if (source) source.setData(buildingGeoJSON(all, matchedIds));
  if (options.fit && matched.length) {
    const bounds = campusBoundsLngLat(matched);
    if (bounds) map.fitBounds(bounds, { padding: 42, duration: 0, maxZoom: campusViewDefaults[state.campusId].zoom });
  }
}

function resetMapView() {
  ensureMap();
  if (!mapReady) return;
  const buildings = campusBuildings().filter(buildingMatches);
  if ((state.search || state.filters.size > 0) && buildings.length) {
    const bounds = campusBoundsLngLat(buildings);
    if (bounds) map.fitBounds(bounds, { padding: 42, duration: 350, maxZoom: campusViewDefaults[state.campusId].zoom });
  } else {
    map.easeTo({ center: campusViewDefaults[state.campusId].center, zoom: campusViewDefaults[state.campusId].zoom, duration: 350 });
  }
}

function selectBuilding(buildingId) {
  state.selectedBuildingCode = buildingId;
  const firstRoom = allRooms().find((room) => room.building.id === state.selectedBuildingCode && roomMatchesFilters(room));
  state.selectedRoomId = firstRoom ? firstRoom.id : null;
  state.activeTab = "overview";
  if (firstRoom) addToHistory(firstRoom);  // track the auto-selected first room
  renderSelectedBuilding();
  renderRoom();
  updateMapData();

  // Zoom to the selected building with smooth animation
  if (mapReady) {
    const building = campusBuildings().find((b) => b.id === buildingId);
    if (building) {
      const bounds = campusBoundsLngLat([building]);
      if (bounds) map.fitBounds(bounds, { padding: 60, duration: 500, maxZoom: 19 });
    }
  }
}

function renderCampusTabs() {
  els.campusTabs.innerHTML = data.campuses.map((campus) => `
    <button
      type="button"
      role="tab"
      aria-selected="${campus.id === state.campusId}"
      class="${campus.id === state.campusId ? "active" : ""}"
      data-campus="${campus.id}">
      ${campus.name}
    </button>
  `).join("");
}

function renderFilters() {
  els.filters.innerHTML = data.filters.map((filter) => `
    <label class="filter-chip ${state.filters.has(filter.id) ? "active" : ""}">
      <input type="checkbox" value="${filter.id}" ${state.filters.has(filter.id) ? "checked" : ""}>
      <span>${filter.label}</span>
    </label>
  `).join("");
}

function renderConnectorList() {
  const campus = currentCampus();
  const overrides = state.connectorOverrides[campus.id];
  const labels = {
    crestron: "Crestron (Direct)",
    live25: "25Live",
    screenconnect: "ScreenConnect",
    wattbox: "WattBox/OvrC",
    servicenow: "ServiceNow"
  };
  // Use live data from API if available, otherwise fall back to mock data
  const connectors = overrides
    ? Object.fromEntries(Object.entries(overrides).map(([k, v]) => [k, v.status || v]))
    : campus.connectors;
  const syncNote = state.backendOnline
    ? (state.lastSynced ? `Synced ${new Date(state.lastSynced).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}` : "Backend connected")
    : "Showing mock data";
  els.connectorList.innerHTML = Object.entries(connectors).map(([key, value]) => `
    <div class="connector-row">
      <span>${labels[key] || key}</span>
      <strong class="connector-state ${value}">${value}</strong>
    </div>
  `).join("") + `<p class="connector-sync">${syncNote}</p>`;
}

function renderMap() {
  const campus = currentCampus();
  const buildings = campusBuildings(campus);
  els.mapHeading.textContent = `${campus.name} Campus`;
  els.campusFrame.dataset.campus = campus.id;

  const rooms = allRooms(campus);
  const visibleBuildings = buildings.filter(buildingMatches);
  const summary = {
    buildings: visibleBuildings.length,
    rooms: rooms.length,
    issues: rooms.filter((room) => ["issue", "offline"].includes(room.status)).length,
    active: rooms.filter((room) => room.activeEvent !== "Available").length
  };
  els.statusSummary.innerHTML = `
    <span><strong>${summary.buildings}</strong> buildings</span>
    <span><strong>${summary.rooms}</strong> mock rooms</span>
    <span><strong>${summary.active}</strong> active</span>
    <span><strong>${summary.issues}</strong> needs attention</span>
  `;

  if (!window.maplibregl) {
    els.campusGrid.innerHTML = `<div class="empty-map">Map engine did not load. Confirm local MapLibre files exist in dashboard/vendor/maplibre.</div>`;
    return;
  }

  ensureMap();
  updateMapData({ fit: Boolean(state.search || state.filters.size > 0) });
  if (mapReady && !state.search && state.filters.size === 0) {
    map.easeTo({ center: campusViewDefaults[state.campusId].center, zoom: campusViewDefaults[state.campusId].zoom, duration: 250 });
  }
}

function renderSelectedBuilding() {
  const campus = currentCampus();
  const building = campusBuildings(campus).find((item) => item.id === state.selectedBuildingCode);
  if (!building) {
    els.selectedBuilding.innerHTML = `<p>Select a building footprint on the map to see room inventory and support actions.</p>`;
    return;
  }
  state.selectedBuildingCode = building.id;
  const rooms = allRooms().filter((room) => room.building.id === building.id && roomMatchesFilters(room));
  els.selectedBuilding.innerHTML = `
    <div class="building-detail">
      <div>
        <p class="eyebrow">Building</p>
        <h3>${building.code || "Map record"} <span>${buildingDisplayName(building)}</span></h3>
      </div>
      <div class="room-list">
        ${rooms.map((room) => `
          <button type="button" class="room-pill ${room.status} ${room.generated ? "generated" : ""} ${room.id === state.selectedRoomId ? "active" : ""}" data-room="${room.id}">
            <strong>${building.code || building.name} ${room.number}</strong>
            <span>${room.generated ? "Placeholder" : statusLabel(room.status)} · ${room.health}%</span>
          </button>
        `).join("") || "<p>This building is from the public OSU map. Presentation Support room inventory is pending for this mock.</p>"}
      </div>
    </div>
  `;
}

function renderRoom() {
  const room = selectedRoom();
  if (!room) {
    els.roomTabs.hidden = true;
    els.roomHeader.innerHTML = `
      <p class="eyebrow">Selected Room</p>
      <h2>No room selected</h2>
      <p>Choose a building and room to load the support toolkit.</p>
    `;
    els.roomBody.innerHTML = "";
    return;
  }

  els.roomTabs.hidden = false;
  els.roomHeader.innerHTML = `
    <p class="eyebrow">${room.building.name}</p>
    <h2>${room.building.code || room.building.name} ${room.number}</h2>
    <p>${room.type}${room.generated ? " - generated until real inventory import" : ""}</p>
    <div class="room-status-line">
      <span class="status-dot ${room.status}"></span>
      <strong>${statusLabel(room.status)}</strong>
      <span>${room.health}% health</span>
    </div>
    ${room.placeholder ? `<div class="assistant-callout inventory-warning"><strong>Upcoming building — HCIC</strong><span>This building is not yet in service. Room data and device configuration will be added when the building opens. Map pin location is approximate.</span></div>` : ""}
    ${room.generated ? `<div class="assistant-callout inventory-warning"><strong>Placeholder room</strong><span>This room was generated so every mapped building is clickable. Replace it with the secure Hardware IP List / room inventory import before production review.</span></div>` : ""}
  `;

  els.roomTabs.querySelectorAll("button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === state.activeTab);
  });

  const renderers = {
    overview: renderOverview,
    tools: renderTools,
    incidents: renderIncidents,
    log: renderLog,
    chat: renderChat
  };
  els.roomBody.innerHTML = renderers[state.activeTab](room);
}

function renderOverview(room) {
  const scheduleSource = room.scheduleMode === "live"
    ? "25Live"
    : room.scheduleMode === "mock"
      ? "backend mock fallback"
      : "static inventory";
  return `
    <div class="metric-grid">
      <div><span>Processor</span><strong>${room.processor}</strong></div>
      <div><span>Display</span><strong>${room.display}</strong></div>
      <div><span>Remote</span><strong>${room.screenconnect ? "available" : "not listed"}</strong></div>
      <div><span>Schedule</span><strong>${room.activeEvent}</strong><em>${scheduleSource}</em></div>
    </div>
    <h3>Devices</h3>
    <div class="device-list">
      ${room.devices.map((device) => `
        <div class="device-row">
          <strong>${device[0]}</strong>
          <span>${device[1]} ${device[2]}</span>
          <em>${device[3]}</em>
        </div>
      `).join("")}
    </div>
    <div class="assistant-callout">
      <strong>AI assistant placeholder</strong>
      <span>Future phase: load this room context, guide verification steps, and draft ServiceNow documentation.</span>
    </div>
  `;
}

function renderTools(room) {
  const hasCP    = (room.devices || []).some(d => d[0] === "Control Processor" || d[0] === "Processor");
  const hasPTZ   = (room.devices || []).some(d => d[0] === "Camera");
  const openCount = (room.incidents?.open || []).length;

  // Build the list dynamically — only show tools that apply to this room's equipment
  const tools = [
    // XPanel: shown whenever a control processor is present or reporting online
    (hasCP || room.processor === "online") && {
      label: "Launch XPanel",
      action: "xpanel_launched",
      tool: "xpanel",
      desc: "Source select · display · volume control"
    },
    // ScreenConnect: only when this room has an agent registered
    room.screenconnect && {
      label: "Start ScreenConnect",
      action: "screenconnect_launched",
      tool: "screenconnect",
      desc: (room.devices || []).find(d => d[0] === "Lectern PC")
        ? "Lectern PC — remote session available"
        : "Remote access — machine lookup required"
    },
    // PTZ camera: only when a camera is in the device list
    hasPTZ && {
      label: "Control PTZ Camera",
      action: "ptz_accessed",
      tool: "ptz",
      desc: (() => { const cam = (room.devices || []).find(d => d[0] === "Camera"); return cam ? `${cam[1]} ${cam[2]}` : "Pan · tilt · zoom · presets"; })()
    },
    // WattBox tools: only when room has one mapped
    room.wattbox && {
      label: "Check WattBox",
      action: "wattbox_status_checked",
      tool: "wattbox",
      desc: `${(room.devices || []).length} outlet${(room.devices || []).length !== 1 ? "s" : ""} mapped`
    },
    room.wattbox && {
      label: "Power cycle device",
      action: "wattbox_power_cycle_requested",
      tool: "wattbox",
      danger: true,
      desc: "Last-resort — logged and requires confirmation"
    },
    // Device web UI inventory: launch remains gated until Hardware IP import and
    // a type-specific backend proxy route are available for the device.
    {
      label: "Device web UIs",
      action: "device_web_ui_opened",
      tool: "device_web",
      desc: `${(room.devices || []).length} device${(room.devices || []).length !== 1 ? "s" : ""} in inventory`
    },
    // Documentation
    {
      label: "SharePoint guide",
      action: "sharepoint_document_opened",
      tool: "sharepoint",
      desc: `${room.type} documentation`
    },
    // ServiceNow: pre-filled from room context
    {
      label: "Draft ServiceNow ticket",
      action: "servicenow_ticket_draft_created",
      tool: "servicenow",
      desc: openCount ? `${openCount} open incident — pre-filled` : "Pre-fill from room context"
    }
  ].filter(Boolean);  // drop the falsy entries from conditional includes

  const tooltips = {
    xpanel: "Open Crestron room control panel for this room in a new tab",
    screenconnect: "Launch remote desktop session to the AV control PC",
    ptz: "View and control the PTZ camera in this room",
    wattbox: "Check WattBox outlet status or power-cycle AV devices",
    device_web: "Review device inventory and web UI proxy readiness",
    sharepoint: "Open room documentation and knowledge base on SharePoint",
    servicenow: "Create or view support tickets for this room"
  };

  return `
    <div class="tool-list">
      ${tools.map(t => `
        <button type="button" class="tool-action${t.danger ? " danger" : ""}"
                data-action="${t.action}" data-tool="${t.tool}"
                aria-label="${t.label}" aria-describedby="tooltip-${t.tool}">
          <strong>${t.label}</strong>
          <span>${t.desc}</span>
          <div class="tool-tooltip">${tooltips[t.tool] || t.desc}</div>
        </button>
      `).join("")}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Device tool panel renderers
// Each returns an HTML string injected into els.roomBody.
// A "← Back to Actions" button at the top restores the tools tab.
// ---------------------------------------------------------------------------

function toolPanelWrap(content, note) {
  return `
    <button class="tool-panel-back" type="button" data-back="tools">← Actions</button>
    ${content}
    <p class="tool-mock-note">${note}</p>
  `;
}

// XPanel — Crestron-style room control mockup
function renderXPanelTool(room) {
  const cp  = (room.devices || []).find(d => d[0] === "Control Processor" || d[0] === "Processor");
  const hasPC  = (room.devices || []).some(d => d[0] === "Lectern PC");
  const hasCam = (room.devices || []).some(d => d[0] === "Camera");
  const sources = ["HDMI 1", "HDMI 2", hasPC && "Lectern PC", "USB-C / Laptop", hasCam && "Camera"].filter(Boolean);
  const disp = room.display;

  return toolPanelWrap(`
    <div class="xpanel">
      <div class="xpanel-row">
        <p class="eyebrow">Source Select</p>
        <div class="xpanel-btns">
          ${sources.map((s, i) => `<button class="xp-btn${i === 0 ? " active" : ""}" type="button">${s}</button>`).join("")}
        </div>
      </div>
      <div class="xpanel-row">
        <p class="eyebrow">Display</p>
        <div class="xpanel-btns">
          <button class="xp-btn${disp === "on"      ? " active" : ""}" type="button">On</button>
          <button class="xp-btn${disp === "standby" ? " active" : ""}" type="button">Standby</button>
          <button class="xp-btn${disp === "off"     ? " active" : ""}" type="button">Off</button>
        </div>
      </div>
      <div class="xpanel-row">
        <p class="eyebrow">Volume</p>
        <div class="xp-volume">
          <button class="xp-btn" type="button">−</button>
          <div class="xp-volume-track"><div class="xp-volume-fill" id="xpVol" style="width:62%"></div></div>
          <button class="xp-btn" type="button">+</button>
          <button class="xp-btn" type="button">Mute</button>
        </div>
      </div>
      <div class="xpanel-row">
        <div class="xp-status-row">
          <span class="status-dot ${room.processor}"></span>
          <strong>Processor:</strong>&nbsp;${room.processor}&nbsp;&nbsp;
          <strong>Display:</strong>&nbsp;${room.display}
          ${cp ? `&nbsp;&nbsp;<strong>CP:</strong>&nbsp;${cp[1]} ${cp[2]}` : ""}
        </div>
      </div>
      <button class="dev-launch" type="button" data-action="launch_tool" data-launch-tool="xpanel">Open Proxied XPanel →</button>
      <div class="tool-status" data-tool-status aria-live="polite"></div>
    </div>
  `, `Launch requests route through the BeaverView backend. XPanel credentials and Hardware IP records must be loaded before the proxied panel opens.`);
}

// ScreenConnect — remote session launcher
function renderScreenConnectTool(room) {
  const machineName = `${(room.building.code || room.building.name).toUpperCase()}-${room.number}-PC`;
  const pc = (room.devices || []).find(d => d[0] === "Lectern PC");
  const online = room.screenconnect && room.status !== "offline";

  return toolPanelWrap(`
    <div class="sc-panel">
      <div class="sc-machine">
        <div class="sc-icon">🖥</div>
        <div class="sc-machine-info">
          <strong>${machineName}</strong>
          <span>${pc ? `${pc[1]} ${pc[2]}` : "Lectern PC"}</span>
          <span>Last seen: ${online ? "Just now" : "—"}</span>
        </div>
        <span class="connector-state ${online ? "ok" : "offline"}">${online ? "Online" : "Offline"}</span>
      </div>
      ${online
        ? `<button class="sc-launch" type="button" data-action="launch_tool" data-launch-tool="screenconnect">Launch Remote Session →</button>
           <p class="sc-sessions">Session proxied through ScreenConnect · filtered by room tag</p>`
        : `<p class="sc-sessions" style="color:var(--status-offline);padding:8px 0">
             No active connection — machine offline or SC agent not responding
           </p>`}
      <div class="tool-status" data-tool-status aria-live="polite"></div>
      <div class="dev-inventory">
        ${(room.devices || []).map(d => `
          <div class="dev-card">
            <span class="dev-card-type">${d[0]}</span>
            <div class="dev-card-info">
              <strong>${d[1]} ${d[2]}</strong>
              <span>${d[3]}</span>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `, `Launch requests route through the BeaverView backend. ScreenConnect base URL must be configured before a live session opens.`);
}

// PTZ Camera — pan/tilt/zoom controls + preset recall
function renderPTZTool(room) {
  const cam = (room.devices || []).find(d => d[0] === "Camera");
  const presets = ["1 — Instructor Wide", "2 — Instructor Close", "3 — Whiteboard", "4 — Full Screen"];

  return toolPanelWrap(`
    <div class="ptz-panel">
      <div class="ptz-feed">
        <div class="ptz-feed-inner">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
          </svg>
          Live feed — available when connected to ${cam ? `${cam[1]} ${cam[2]}` : "camera"}
        </div>
      </div>
      <div class="ptz-controls">
        <div class="ptz-dpad">
          <span></span>
          <button class="ptz-btn" type="button" title="Tilt up" data-action="ptz_command" data-command="up">▲</button>
          <span></span>
          <button class="ptz-btn" type="button" title="Pan left" data-action="ptz_command" data-command="left">◄</button>
          <button class="ptz-btn ptz-btn-home" type="button" title="Go to home" data-action="ptz_command" data-command="home">HOME</button>
          <button class="ptz-btn" type="button" title="Pan right" data-action="ptz_command" data-command="right">►</button>
          <span></span>
          <button class="ptz-btn" type="button" title="Tilt down" data-action="ptz_command" data-command="down">▼</button>
          <span></span>
        </div>
        <div class="ptz-zoom">
          <button class="ptz-btn" type="button" title="Zoom in"  style="width:48px" data-action="ptz_command" data-command="zoom_in">Z +</button>
          <button class="ptz-btn" type="button" title="Zoom out" style="width:48px" data-action="ptz_command" data-command="zoom_out">Z −</button>
        </div>
        <div class="ptz-presets">
          <p class="eyebrow">Presets</p>
          ${presets.map((p, i) => `<button class="ptz-preset" type="button" data-action="ptz_command" data-command="preset_${i + 1}">${p}</button>`).join("")}
        </div>
      </div>
      <div class="tool-status" data-tool-status aria-live="polite"></div>
    </div>
  `, `Commands route through the BeaverView backend. PTZ credentials and Hardware IP records must be loaded before live camera movement works.`);
}

// WattBox — outlet status + per-outlet cycle button
function renderWattBoxTool(room) {
  const outlets = (room.devices || []).map((d, i) => ({
    num: i + 1,
    label: `${d[1]} ${d[2]}`,
    type: d[0],
    on: room.status !== "offline"
  }));
  outlets.push({ num: outlets.length + 1, label: "(spare)", type: "—", on: false });

  return toolPanelWrap(`
    <div class="wb-panel">
      <p class="eyebrow" style="margin-bottom:6px">
        ${room.building.code} ${room.number} — ${outlets.length - 1} device outlet${outlets.length - 1 !== 1 ? "s" : ""}
      </p>
      <div class="tool-status" data-tool-status aria-live="polite">Checking backend WattBox status...</div>
      ${outlets.map(o => `
        <div class="wb-outlet" data-outlet-row="${o.num}">
          <span class="wb-outlet-num">${o.num}</span>
          <div class="wb-outlet-name">
            <strong>${o.label}</strong>
            <span>${o.type}</span>
          </div>
          <span class="wb-status ${o.on ? "on" : "off"}">${o.on ? "On" : "Off"}</span>
          <button class="wb-cycle" type="button" data-action="wattbox_outlet_cycle" data-outlet="${o.num}" ${!o.on && o.label === "(spare)" ? "disabled" : ""}>Cycle</button>
        </div>
      `).join("")}
    </div>
  `, "Status and cycle requests route through the BeaverView backend. Without OvrC credentials, the local outlet list remains a mock fallback.");
}

// Device Web UI — inventory list with guarded launch readiness
function renderDeviceWebTool(room) {
  const devices = room.devices || [];
  return toolPanelWrap(`
    <div class="tool-status" data-tool-status aria-live="polite">
      Device web UI launch is pending Hardware IP records and backend proxy mapping.
    </div>
    <div class="dev-inventory">
      ${devices.length
        ? devices.map(d => `
            <div class="dev-card">
              <span class="dev-card-type">${d[0]}</span>
              <div class="dev-card-info">
                <strong>${d[1]} ${d[2]}</strong>
                <span>${d[3]}</span>
              </div>
              <button class="dev-launch dev-launch--pending" type="button" disabled>Proxy pending</button>
            </div>
          `).join("")
        : `<p style="color:var(--text-muted);font-size:13px;padding:8px 0">No device inventory recorded for this room.</p>`
      }
    </div>
  `, "Device browser access will stay disabled until secure Hardware IP records are imported and each supported device type has an approved backend proxy route.");
}

// SharePoint — room-type documentation links
function renderSharePointTool(room) {
  const guides = {
    "Presentation Classroom": { title: "Classroom AV Quick Guide",   pages: "8 pp",  updated: "Mar 2025" },
    "Conference Room":        { title: "Conference Room Setup",       pages: "5 pp",  updated: "Jan 2025" },
    "Lecture Hall":           { title: "Lecture Hall Operations",     pages: "12 pp", updated: "Feb 2025" },
    "Active Learning Room":   { title: "Active Learning AV Guide",    pages: "10 pp", updated: "Apr 2025" },
    "Event Space":            { title: "Event AV Setup Checklist",    pages: "6 pp",  updated: "Dec 2024" }
  };
  const g = guides[room.type] || { title: `${room.type} AV Guide`, pages: "—", updated: "—" };

  return toolPanelWrap(`
    <div class="dev-inventory">
      <div class="dev-card">
        <span class="dev-card-type" style="font-size:22px;width:36px">📄</span>
        <div class="dev-card-info">
          <strong>${g.title}</strong>
          <span>${g.pages} · Updated ${g.updated}</span>
        </div>
        <button class="dev-launch" type="button" data-action="launch_tool" data-launch-tool="sharepoint">Open PDF →</button>
      </div>
      <div class="dev-card">
        <span class="dev-card-type" style="font-size:22px;width:36px">🔧</span>
        <div class="dev-card-info">
          <strong>Troubleshooting Runbook</strong>
          <span>Common issues · Escalation paths</span>
        </div>
        <button class="dev-launch" type="button" data-action="launch_tool" data-launch-tool="sharepoint">Open →</button>
      </div>
      <div class="dev-card">
        <span class="dev-card-type" style="font-size:22px;width:36px">📋</span>
        <div class="dev-card-info">
          <strong>Room Inventory Record</strong>
          <span>Hardware list · warranty · install date</span>
        </div>
        <button class="dev-launch" type="button" data-action="launch_tool" data-launch-tool="sharepoint">Open →</button>
      </div>
      <div class="tool-status" data-tool-status aria-live="polite"></div>
    </div>
  `, "Launch requests route through the BeaverView backend. SharePoint base URL must be configured before live documentation opens.");
}

// ServiceNow — pre-filled incident draft form
function renderServiceNowTool(room) {
  const roomLabel  = `${room.building.code || room.building.name} ${room.number}`;
  const openInc    = (room.incidents?.open || []);
  const shortDesc  = openInc[0] || `AV issue in ${roomLabel}`;
  const priority   = room.status === "offline" ? "2" : room.status === "issue" ? "3" : "4";
  const bodyText   = [
    `Building: ${room.building.name}`,
    `Room: ${roomLabel}  (${room.type})`,
    `Health: ${room.health}%   Processor: ${room.processor}   Display: ${room.display}`,
    openInc.length ? `\nOpen incidents:\n${openInc.map(i => "  • " + i).join("\n")}` : "",
    "\n\nAdditional detail:"
  ].filter(Boolean).join("\n");

  return toolPanelWrap(`
    <div class="sn-panel">
      <div class="sn-field">
        <label>Room (auto-filled)</label>
        <input type="text" readonly value="${roomLabel}">
      </div>
      <div class="sn-field">
        <label>Short Description</label>
        <input type="text" data-sn-field="short_description" value="${shortDesc}">
      </div>
      <div class="sn-field">
        <label>Category</label>
        <select data-sn-field="category">
          <option value="AV Equipment" selected>AV Equipment</option>
          <option value="Network Connectivity">Network Connectivity</option>
          <option value="Software / Control System">Software / Control System</option>
          <option value="Physical / Facilities">Physical / Facilities</option>
        </select>
      </div>
      <div class="sn-field">
        <label>Priority</label>
        <select data-sn-field="priority">
          <option value="2" ${priority === "2" ? "selected" : ""}>2 — High (room down)</option>
          <option value="3" ${priority === "3" ? "selected" : ""}>3 — Moderate (partial issue)</option>
          <option value="4" ${priority === "4" ? "selected" : ""}>4 — Low (cosmetic / informational)</option>
        </select>
      </div>
      <div class="sn-field">
        <label>Description</label>
        <textarea rows="5" data-sn-field="description">${bodyText}</textarea>
      </div>
      <div class="sn-status" data-sn-status aria-live="polite"></div>
      <button class="sn-submit" type="button" data-action="servicenow_ticket_submitted" data-tool="sn_submit">
        Create Draft Ticket
      </button>
    </div>
  `, "Submits to the BeaverView backend. Without ServiceNow credentials, the backend returns and logs a mock draft.");
}

function renderIncidents(room) {
  const closed = room.incidents.closed.slice(0, 5);
  return `
    <h3>Open Incidents</h3>
    <div class="incident-list">
      ${room.incidents.open.map((incident) => `<div class="incident open">${incident}</div>`).join("") || `<div class="incident">No open incidents in mock data.</div>`}
    </div>
    <h3>Recent Closed</h3>
    <div class="incident-list">
      ${closed.map((incident) => `<div class="incident closed">${incident}</div>`).join("") || `<div class="incident">No recent closed incidents in mock data.</div>`}
    </div>
  `;
}

function renderLog() {
  // Shows recent local actions and the last 5 building + room combinations visited.
  if (!state.log.length && !state.history.length) {
    return `
      <div class="audit-list">
        <div class="audit-row">
          <strong>No rooms visited yet</strong>
          <span>Select a building on the map, then click a room. Recent actions and visits appear here.</span>
        </div>
      </div>`;
  }
  return `
    <div class="audit-list">
      ${state.log.length ? `
        <div class="audit-row" style="opacity:.55;font-size:.8em;border-bottom:none;padding-bottom:0">
          <strong>Recent actions</strong>
          <span>Backend-backed actions are also written to the admin audit log when the API is reachable.</span>
        </div>
        ${state.log.slice(0, 5).map((entry) => `
          <div class="audit-row">
            <strong>${entry.action.replaceAll("_", " ")}</strong>
            <span>${entry.outcome}</span>
            <em>${entry.time}</em>
          </div>
        `).join("")}
      ` : ""}
      ${state.history.length ? `
        <div class="audit-row" style="opacity:.55;font-size:.8em;border-bottom:none;padding-bottom:0">
          <strong>Recently visited</strong>
          <span>Click any row to return</span>
        </div>
        ${state.history.map((entry, i) => `
        <div class="audit-row history-row" data-history-idx="${i}"
             style="cursor:pointer" title="Return to ${entry.buildingCode} ${entry.roomNumber}">
          <strong>${entry.buildingCode} · ${entry.roomNumber}</strong>
          <span>${entry.buildingName}${entry.typeLabel ? " · " + entry.typeLabel : ""}</span>
          <em>${entry.ts}</em>
        </div>
      `).join("")}
      ` : ""}
    </div>`;
}

function renderChat(room) {
  // Hermes AI assistant chat interface. Stateless on backend.
  // Session stored in browser — backend never persists conversation.
  return `
    <div class="chat-panel">
      <div class="chat-intro">
        <strong>Hi, I'm Hermes!</strong> I can help troubleshoot
        <strong>${room.building.code || room.building.name} ${room.number}</strong>,
        explain incidents, and find documentation for this room.
      </div>

      <div class="chat-messages" id="chatMessages" role="log" aria-live="polite"
           aria-label="Conversation with Hermes">
        <div class="chat-message assistant">
          <strong>How can I help you today?</strong>
        </div>
      </div>

      <div class="chat-input-area">
        <textarea id="chatInput" class="chat-input"
                  placeholder="Ask about this room, its devices, or past incidents..."
                  rows="1"></textarea>
        <button type="button" id="chatSendBtn" class="chat-send-btn"
                aria-label="Send message">Send</button>
      </div>

      <div class="chat-disclaimer">
        Hermes uses only room context — no personal information is shared.
        Powered by local AI on DGX Spark.
      </div>
    </div>
  `;
}

function addToHistory(room) {
  // Track a room visit in state.history (max 5, deduplicated by roomId).
  if (!room) return;
  const entry = {
    buildingCode: room.building.code || room.building.name,
    buildingName: room.building.name,
    roomId:       room.id,
    roomNumber:   room.number,
    typeLabel:    room.type || "",
    ts:           new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
  };
  state.history = state.history.filter((h) => h.roomId !== room.id); // dedup
  state.history.unshift(entry);
  if (state.history.length > 5) state.history = state.history.slice(0, 5);
}

function addAudit(action, outcome = "success") {
  const room = selectedRoom();
  if (!room) return;
  state.log.unshift({
    roomId: room.id,
    action,
    outcome,
    time: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
  });
  // Persist to backend admin audit log when API is reachable
  if (state.backendOnline) {
    fetch(`/api/rooms/${room.id}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_type: action, outcome })
    }).catch(() => {});
  }
}

function apiDetail(data, fallback) {
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg || String(item)).join("; ");
  return fallback;
}

async function launchBackendTool(button) {
  const room = selectedRoom();
  const launchTool = button.dataset.launchTool;
  const panel = button.closest(".xpanel, .sc-panel, .dev-inventory");
  const statusEl = panel?.querySelector("[data-tool-status]");
  if (!room || !launchTool) return;

  button.disabled = true;
  if (statusEl) statusEl.textContent = `Checking ${launchTool} launch target.`;

  try {
    const response = await fetch(`/api/rooms/${encodeURIComponent(room.id)}/launch/${encodeURIComponent(launchTool)}`, {
      signal: AbortSignal.timeout(5000)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(apiDetail(data, `HTTP ${response.status}`));
    }

    if (data.mode === "live" && data.url) {
      window.open(data.url, "_blank", "noopener,noreferrer");
      addAudit(`${launchTool}_launched`, "backend launch opened");
      if (statusEl) statusEl.textContent = `${launchTool} launch opened in a new tab.`;
      return;
    }

    const message = data.note || `${launchTool} launch is not configured yet.`;
    addAudit(`${launchTool}_launch_pending`, data.mode || "mock");
    if (statusEl) statusEl.textContent = `${message} Configure the connector before live launch.`;
  } catch (error) {
    const message = error instanceof Error ? error.message : "request failed";
    addAudit(`${launchTool}_launch_failed`, message);
    if (statusEl) statusEl.textContent = `${launchTool} launch unavailable: ${message}`;
  } finally {
    button.disabled = false;
  }
}

async function refreshWattBoxOutlets(room) {
  const panel = document.querySelector(".wb-panel");
  const statusEl = panel?.querySelector("[data-tool-status]");
  if (!room || !panel || !statusEl) return;

  try {
    const response = await fetch(`/api/rooms/${encodeURIComponent(room.id)}/wattbox/outlets`, {
      signal: AbortSignal.timeout(5000)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(apiDetail(data, `HTTP ${response.status}`));
    }

    const outlets = Array.isArray(data.outlets) ? data.outlets : [];
    statusEl.textContent = outlets.length
      ? `Backend reported ${outlets.length} WattBox outlet${outlets.length === 1 ? "" : "s"} from ${data.source || "OvrC"}.`
      : "Backend reached OvrC, but no outlet rows were returned.";
    addAudit("wattbox_status_checked", "backend status loaded");
  } catch (error) {
    const message = error instanceof Error ? error.message : "request failed";
    statusEl.textContent = `Using mock outlet list: ${message}`;
    addAudit("wattbox_status_unavailable", message);
  }
}

async function submitPTZCommand(button) {
  const room = selectedRoom();
  const command = button.dataset.command;
  const panel = button.closest(".ptz-panel");
  const statusEl = panel?.querySelector("[data-tool-status]");
  if (!room || !command) return;

  button.disabled = true;
  if (statusEl) statusEl.textContent = `Sending PTZ command: ${command.replaceAll("_", " ")}.`;
  try {
    const response = await fetch(`/api/rooms/${encodeURIComponent(room.id)}/ptz/${encodeURIComponent(command)}`, {
      method: "POST"
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(apiDetail(data, `HTTP ${response.status}`));
    }
    const outcome = data.http_status ? `HTTP ${data.http_status}` : "sent";
    addAudit("ptz_command", `${command}: ${outcome}`);
    if (statusEl) statusEl.textContent = `PTZ command sent: ${command.replaceAll("_", " ")}.`;
  } catch (error) {
    const message = error instanceof Error ? error.message : "request failed";
    addAudit("ptz_command_failed", `${command}: ${message}`);
    if (statusEl) statusEl.textContent = `PTZ command unavailable: ${message}`;
  } finally {
    button.disabled = false;
  }
}

async function cycleWattBoxOutlet(button) {
  const room = selectedRoom();
  const outlet = button.dataset.outlet;
  const panel = button.closest(".wb-panel");
  const statusEl = panel?.querySelector("[data-tool-status]");
  if (!room || !outlet) return;

  if (!confirm(`Cycle WattBox outlet ${outlet}? This is a last-resort action and will be logged.`)) return;

  button.disabled = true;
  if (statusEl) statusEl.textContent = `Requesting WattBox outlet ${outlet} cycle.`;
  try {
    const response = await fetch(`/api/rooms/${encodeURIComponent(room.id)}/wattbox/outlets/${encodeURIComponent(outlet)}/cycle`, {
      method: "POST"
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(apiDetail(data, `HTTP ${response.status}`));
    }
    const outcome = data.http_status ? `outlet ${outlet}: HTTP ${data.http_status}` : `outlet ${outlet}: requested`;
    addAudit("wattbox_outlet_cycle", outcome);
    if (statusEl) statusEl.textContent = `WattBox outlet ${outlet} cycle requested.`;
  } catch (error) {
    const message = error instanceof Error ? error.message : "request failed";
    addAudit("wattbox_outlet_cycle_failed", `outlet ${outlet}: ${message}`);
    if (statusEl) statusEl.textContent = `WattBox cycle unavailable: ${message}`;
  } finally {
    button.disabled = false;
  }
}

async function submitServiceNowIncident(button) {
  const room = selectedRoom();
  const panel = button.closest(".sn-panel");
  const statusEl = panel?.querySelector("[data-sn-status]");
  if (!room || !panel) return;

  const valueFor = (name) => (panel.querySelector(`[data-sn-field="${name}"]`)?.value || "").trim();
  const priority = valueFor("priority") || "3";
  const payload = {
    short_description: valueFor("short_description"),
    description: valueFor("description"),
    category: valueFor("category") || "AV Equipment",
    urgency: priority,
    impact: priority
  };

  button.disabled = true;
  button.textContent = "Submitting...";
  if (statusEl) statusEl.textContent = "Sending draft to BeaverView backend.";

  try {
    const response = await fetch(`/api/rooms/${encodeURIComponent(room.id)}/servicenow/incident`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    const incidentNumber = data.incident?.number;
    const outcome = data.status === "live" && incidentNumber
      ? `created ${incidentNumber}`
      : "mock draft returned";
    addAudit("servicenow_ticket_submitted", outcome);
    if (statusEl) {
      statusEl.textContent = data.status === "live" && incidentNumber
        ? `Created ServiceNow incident ${incidentNumber}.`
        : "ServiceNow credentials are not configured; backend logged a mock draft.";
    }
    button.textContent = data.status === "live" ? "Incident Created" : "Draft Captured";
  } catch (error) {
    const message = error instanceof Error ? error.message : "request failed";
    addAudit("servicenow_ticket_failed", message);
    if (statusEl) statusEl.textContent = `Could not create draft: ${message}`;
    button.textContent = "Retry Draft";
  } finally {
    button.disabled = false;
  }
}

async function sendChatMessage() {
  const room = selectedRoom();
  if (!room) return;

  const input = document.querySelector("#chatInput");
  const message = (input?.value || "").trim();
  if (!message) return;

  const messagesDiv = document.querySelector("#chatMessages");
  if (!messagesDiv) return;

  // Initialize chat history for this room if needed
  if (!state.chatHistory[room.id]) {
    state.chatHistory[room.id] = [];
  }

  // Add user message to UI
  const userMsg = document.createElement("div");
  userMsg.className = "chat-message user";
  userMsg.textContent = message;
  messagesDiv.appendChild(userMsg);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;

  // Add to state history
  state.chatHistory[room.id].push({ role: "user", content: message });

  // Clear input
  if (input) input.value = "";

  // Show typing indicator
  const typingDiv = document.createElement("div");
  typingDiv.className = "chat-message typing";
  typingDiv.innerHTML = '<div class="chat-typing-indicator"><span></span><span></span><span></span></div>';
  messagesDiv.appendChild(typingDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;

  // Send to Hermes
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        room_id: room.id,
        history: state.chatHistory[room.id].slice(0, -1)  // exclude latest user message
      })
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    // Remove typing indicator
    if (typingDiv.parentNode) typingDiv.remove();

    // Add assistant response
    const assistantMsg = document.createElement("div");
    assistantMsg.className = "chat-message assistant";
    assistantMsg.textContent = data.reply || "(No response)";
    messagesDiv.appendChild(assistantMsg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Add to state history
    state.chatHistory[room.id].push({ role: "assistant", content: data.reply });

  } catch (error) {
    // Remove typing indicator
    if (typingDiv.parentNode) typingDiv.remove();

    // Show error
    const errorMsg = document.createElement("div");
    errorMsg.className = "chat-message assistant";
    errorMsg.textContent = `Error: ${error.message}. Check that CHAT_BASE_URL is configured.`;
    messagesDiv.appendChild(errorMsg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }
}

function renderAll() {
  renderCampusTabs();
  renderFilters();
  renderConnectorList();
  renderMap();
  renderSelectedBuilding();
  renderRoom();
}

els.campusTabs.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-campus]");
  if (!button) return;
  state.campusId = button.dataset.campus;
  state.selectedBuildingCode = null;
  state.selectedRoomId = null;
  resetMapView();
  els.campusFrame.classList.remove("fold");
  void els.campusFrame.offsetWidth;
  els.campusFrame.classList.add("fold");
  renderAll();
  if (state.backendOnline) refreshBackendCampusData();
});

els.filters.addEventListener("change", (event) => {
  const input = event.target.closest("input");
  if (!input) return;
  if (input.checked) state.filters.add(input.value);
  else state.filters.delete(input.value);
  renderAll();
});

els.search.addEventListener("input", (event) => {
  state.search = event.target.value;
  renderAll();  // updates map source + fitBounds via updateMapData({fit:true})

  if (!mapReady || !map) return;
  const term = state.search.trim();
  if (!term) return;

  const matches = campusBuildings().filter(buildingMatches);

  if (matches.length === 1) {
    // Single match → auto-select building (highlights it orange, loads right panel)
    selectBuilding(matches[0].id);
    // Fly in tight — overrides the campus-level fitBounds from renderAll()
    const center = buildingCenter(matches[0]);
    if (center) {
      requestAnimationFrame(() => {
        map.flyTo({ center, zoom: 18.5, duration: 500, essential: true });
      });
    }
  } else if (matches.length >= 2 && matches.length <= 6) {
    // A few matches → zoom closer than campus default
    const bounds = campusBoundsLngLat(matches);
    if (bounds) map.fitBounds(bounds, { padding: 80, duration: 400, maxZoom: 17.5 });
  }
});

els.zoomIn.addEventListener("click", () => {
  if (map) map.zoomIn({ duration: 180 });
});

els.zoomOut.addEventListener("click", () => {
  if (map) map.zoomOut({ duration: 180 });
});

els.resetMap.addEventListener("click", resetMapView);

els.selectedBuilding.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-room]");
  if (!button) return;
  state.selectedRoomId = button.dataset.room;
  state.activeTab = "overview";
  addToHistory(selectedRoom());  // track visit in history (not admin log)
  renderAll();
});

els.roomTabs.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (!button) return;
  state.activeTab = button.dataset.tab;
  renderRoom();
});

els.roomBody.addEventListener("click", async (event) => {
  // History row — click to return to that building + room
  const historyRow = event.target.closest("[data-history-idx]");
  if (historyRow) {
    const idx = +historyRow.dataset.historyIdx;
    const entry = state.history[idx];
    if (entry) {
      // Find the building by code (case-insensitive)
      const building = campusBuildings().find((b) =>
        (b.code || "").toLowerCase() === entry.buildingCode.toLowerCase()
      );
      if (building) {
        state.selectedBuildingCode = building.id;
        renderSelectedBuilding();
        updateMapData();
        // Fly map to the building
        const center = buildingCenter(building);
        if (center && mapReady) map.flyTo({ center, zoom: 18.5, duration: 400 });
      }
      state.selectedRoomId = entry.roomId;
      state.activeTab = "overview";
      renderRoom();
    }
    return;
  }

  // "← Actions" back button inside any tool panel
  if (event.target.closest("[data-back='tools']")) {
    state.activeTab = "tools";
    renderRoom();
    return;
  }

  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  const tool   = button.dataset.tool || "";

  if (action === "servicenow_ticket_submitted") {
    await submitServiceNowIncident(button);
    return;
  }
  if (action === "ptz_command") {
    await submitPTZCommand(button);
    return;
  }
  if (action === "wattbox_outlet_cycle") {
    await cycleWattBoxOutlet(button);
    return;
  }
  if (action === "launch_tool") {
    await launchBackendTool(button);
    return;
  }

  // Power cycle needs an explicit confirmation before proceeding
  if (action.includes("power") && !confirm("Power cycling is a last-resort action. Confirm? This will be logged.")) return;

  // Log the action
  addAudit(action, action.includes("power") ? "confirmation logged" : "success");

  // Map tool key → renderer function
  const PANELS = {
    xpanel:       renderXPanelTool,
    screenconnect: renderScreenConnectTool,
    ptz:          renderPTZTool,
    wattbox:      renderWattBoxTool,
    device_web:   renderDeviceWebTool,
    sharepoint:   renderSharePointTool,
    servicenow:   renderServiceNowTool
  };

  const room = selectedRoom();
  if (PANELS[tool] && room) {
    // Replace room body with the tool panel (back button is inside the panel)
    els.roomBody.innerHTML = PANELS[tool](room);
    if (tool === "wattbox") refreshWattBoxOutlets(room);
  } else {
    // Fallback: go to log tab
    state.activeTab = "log";
    renderRoom();
  }
});

// Chat input handlers (delegated from roomBody)
els.roomBody.addEventListener("keydown", (event) => {
  if (event.target.id === "chatInput") {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendChatMessage();
    }
  }
});

els.roomBody.addEventListener("click", (event) => {
  if (event.target.id === "chatSendBtn") {
    sendChatMessage();
  }
});

els.tourButton.addEventListener("click", () => {
  els.tourOverlay.hidden = false;
  els.closeTour.focus();
});

function closeTour() {
  els.tourOverlay.hidden = true;
  els.tourButton.focus();
}

els.closeTour.addEventListener("click", closeTour);
els.closeTourX.addEventListener("click", closeTour);

els.tourOverlay.addEventListener("click", (event) => {
  if (event.target === els.tourOverlay) {
    closeTour();
  }
});

els.densityToggle.addEventListener("click", () => {
  state.compact = !state.compact;
  document.body.classList.toggle("compact", state.compact);
  els.densityToggle.textContent = state.compact ? "Comfortable" : "Compact";
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.tourOverlay.hidden) {
    closeTour();
  }
});


// ---------------------------------------------------------------------------
// Backend API integration (Phase 4)
// ---------------------------------------------------------------------------

async function checkBackend() {
  try {
    const res = await fetch("/api/health", { signal: AbortSignal.timeout(2000) });
    state.backendOnline = res.ok;
  } catch {
    state.backendOnline = false;
  }
  if (state.backendOnline) {
    await refreshBackendCampusData();
  } else {
    renderConnectorList();
  }
}

async function refreshBackendCampusData() {
  await Promise.all([
    refreshConnectors(),
    refreshSchedule()
  ]);
}

async function refreshConnectors() {
  try {
    const res = await fetch(`/api/campus/${state.campusId}/connectors`, {
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) return;
    const body = await res.json();
    state.connectorOverrides[state.campusId] = body.connectors;
    state.lastSynced = body.ts;
    renderConnectorList();
  } catch {
    // backend unreachable; keep showing mock data
  }
}

async function refreshSchedule() {
  try {
    const res = await fetch(`/api/campus/${state.campusId}/schedule`, {
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) return;
    const body = await res.json();
    if (!Array.isArray(body.events)) return;

    state.scheduleOverrides[state.campusId] = {
      mode: body.mode || "unknown",
      ts: body.ts || null,
      eventsByRoomId: Object.fromEntries(
        body.events
          .filter((event) => event && event.room_id && event.active_event)
          .map((event) => [event.room_id, event])
      )
    };
    renderAll();
  } catch {
    // backend unreachable or 25Live unavailable; keep static schedule text
  }
}

async function checkRole() {
  try {
    const res = await fetch("/api/me", { signal: AbortSignal.timeout(2000) });
    if (!res.ok) return;
    const { role } = await res.json();
    if (role === "admin") {
      els.adminLink.hidden = false;
    }
  } catch {
    // backend unreachable or no session — leave link hidden
  }
}

try {
  console.log('🔧 Starting app initialization...');

  // Check critical dependencies
  const checks = {
    'maplibregl': typeof window.maplibregl !== 'undefined',
    'osuMapBuildings': typeof window.osuMapBuildings !== 'undefined',
    'data': typeof data !== 'undefined',
    'state': typeof state !== 'undefined'
  };

  Object.entries(checks).forEach(([key, ok]) => {
    console.log(`  ${key}: ${ok ? '✓' : '✗'}`);
  });

  if (!checks.data) throw new Error('data.js not loaded');
  if (!checks.osuMapBuildings) throw new Error('osu-map-buildings.js not loaded');
  if (!checks.maplibregl) throw new Error('maplibre-gl.js not loaded');

  console.log(`  data.campuses: ${data.campuses.length} campuses`);
  console.log(`  osuMapBuildings: ${window.osuMapBuildings.length} buildings`);

  renderAll();
  console.log('✓ renderAll() completed');

  checkBackend();
  checkRole();
  console.log('✓ App initialized successfully');
} catch (err) {
  console.error('❌ App initialization error:', err.message);
  console.error('Stack:', err.stack);
  document.body.innerHTML = `<div style="padding: 20px; color: red; font-family: monospace;"><h1>🔴 App Error</h1><pre>${err.message}\n\n${err.stack}</pre></div>`;
}

// Dev helper — exposes selectBuilding() to the browser console for testing
// Usage: _dev.selectBuilding("1027537")  (building ID from osuMapBuildings)
window._dev = { selectBuilding };
