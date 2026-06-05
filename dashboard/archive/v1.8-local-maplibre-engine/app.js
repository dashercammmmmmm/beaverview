const data = window.dashboardData;

const state = {
  campusId: data.campuses[0].id,
  selectedBuildingCode: null,
  selectedRoomId: null,
  activeTab: "overview",
  search: "",
  filters: new Set(),
  log: [],
  compact: false,
  backendOnline: false,
  connectorOverrides: {},  // campus_id -> connector health object from /api
  lastSynced: null          // ISO timestamp of last successful connector fetch
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
  resetMap: document.querySelector("#resetMap")
};

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
      fusion: "mock",
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
    supportRoomsForBuilding(building, campus).map((room) => ({
      ...room,
      id: `${campus.id}-${building.code}-${room.number}`.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
      building
    }))
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

function buildingMatches(building) {
  const term = state.search.trim().toLowerCase();
  const rooms = allRooms().filter((room) => room.building.id === building.id);
  const hasFilters = state.filters.size > 0;
  const passesFilter = hasFilters ? rooms.some(roomMatchesFilters) : true;
  if (!passesFilter) return false;
  if (!term) return true;
  return (
    (building.code || "").toLowerCase().includes(term) ||
    building.name.toLowerCase().includes(term) ||
    rooms.some((room) => `${building.code || building.name} ${room.number}`.toLowerCase().includes(term))
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

function buildingGeoJSON(buildings) {
  return {
    type: "FeatureCollection",
    features: buildings.map((building) => {
      const summary = buildingSummary(building);
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
          selected: state.selectedBuildingCode === building.id
        }
      };
    })
  };
}

function campusBoundsLngLat(buildings) {
  const coords = buildings.flatMap((building) => (
    building.polygon && building.polygon.length ? building.polygon : [[building.lng, building.lat]]
  ));
  const lngs = coords.map((coord) => coord[0]);
  const lats = coords.map((coord) => coord[1]);
  return [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]];
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
          ["==", ["get", "selected"], true], "#d73f09",
          ["==", ["get", "status"], "issue"], "#7a2f26",
          ["==", ["get", "status"], "offline"], "#7a2f26",
          ["==", ["get", "status"], "in-use"], "#24485d",
          ["==", ["get", "status"], "available"], "#274536",
          "#2e2b2a"
        ],
        "fill-opacity": [
          "case",
          ["==", ["get", "selected"], true], 0.78,
          [">", ["get", "supportRooms"], 0], 0.74,
          0.58
        ]
      }
    });

    map.addLayer({
      id: "building-outline",
      type: "line",
      source: "osu-buildings",
      paint: {
        "line-color": ["case", ["==", ["get", "selected"], true], "#80220a", "#ffffff"],
        "line-width": ["case", ["==", ["get", "selected"], true], 2.5, 0.8],
        "line-opacity": 0.88
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
        "text-color": "#1b1d21",
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.5
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
  const buildings = campusBuildings().filter(buildingMatches);
  const source = map.getSource("osu-buildings");
  if (source) source.setData(buildingGeoJSON(buildings));
  if (options.fit && buildings.length) {
    map.fitBounds(campusBoundsLngLat(buildings), { padding: 42, duration: 0, maxZoom: campusViewDefaults[state.campusId].zoom });
  }
}

function resetMapView() {
  ensureMap();
  if (!mapReady) return;
  const buildings = campusBuildings().filter(buildingMatches);
  if ((state.search || state.filters.size > 0) && buildings.length) {
    map.fitBounds(campusBoundsLngLat(buildings), { padding: 42, duration: 350, maxZoom: campusViewDefaults[state.campusId].zoom });
  } else {
    map.easeTo({ center: campusViewDefaults[state.campusId].center, zoom: campusViewDefaults[state.campusId].zoom, duration: 350 });
  }
}

function selectBuilding(buildingId) {
  state.selectedBuildingCode = buildingId;
  const firstRoom = allRooms().find((room) => room.building.id === state.selectedBuildingCode && roomMatchesFilters(room));
  state.selectedRoomId = firstRoom ? firstRoom.id : null;
  state.activeTab = "overview";
  renderSelectedBuilding();
  renderRoom();
  updateMapData();
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
    fusion: "Fusion",
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
    ${room.generated ? `<div class="assistant-callout inventory-warning"><strong>Placeholder room</strong><span>This room was generated so every mapped building is clickable. Replace it with the secure Hardware IP List / room inventory import before production review.</span></div>` : ""}
  `;

  els.roomTabs.querySelectorAll("button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === state.activeTab);
  });

  const renderers = {
    overview: renderOverview,
    tools: renderTools,
    incidents: renderIncidents,
    log: renderLog
  };
  els.roomBody.innerHTML = renderers[state.activeTab](room);
}

function renderOverview(room) {
  return `
    <div class="metric-grid">
      <div><span>Fusion</span><strong>${room.fusion}</strong></div>
      <div><span>Display</span><strong>${room.display}</strong></div>
      <div><span>Remote</span><strong>${room.screenconnect ? "available" : "not listed"}</strong></div>
      <div><span>Schedule</span><strong>${room.activeEvent}</strong></div>
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
  const tools = [
    ["Launch XPanel", "xpanel_launched", "Open the room control interface"],
    ["Open device web UI", "device_web_ui_opened", "Use sanitized device links from inventory"],
    ["Start ScreenConnect", "screenconnect_launched", room.screenconnect ? "Remote access available" : "No matching machine in mock data"],
    ["Check WattBox", "wattbox_status_checked", room.wattbox ? "View outlet labels and power status" : "No WattBox mapped"],
    ["Power cycle device", "wattbox_power_cycle_requested", "Last-resort action; requires confirmation"],
    ["Open SharePoint guide", "sharepoint_document_opened", "Training PDF placeholder"],
    ["Draft ServiceNow ticket", "servicenow_ticket_draft_created", "Create an editable draft from room context"]
  ];

  return `
    <div class="tool-list">
      ${tools.map(([label, action, description]) => `
        <button type="button" class="tool-action ${action.includes("power") ? "danger" : ""}" data-action="${action}">
          <strong>${label}</strong>
          <span>${description}</span>
        </button>
      `).join("")}
    </div>
  `;
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
  const room = selectedRoom();
  const events = state.log.filter((event) => event.roomId === room.id);
  return `
    <div class="audit-list">
      ${events.map((event) => `
        <div class="audit-row">
          <strong>${event.action}</strong>
          <span>${event.time}</span>
          <em>${event.outcome}</em>
        </div>
      `).join("") || `<div class="audit-row"><strong>No mock actions yet</strong><span>Use the Tools tab to create audit events.</span></div>`}
    </div>
  `;
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
  // Persist to backend audit log when API is reachable
  if (state.backendOnline) {
    fetch(`/api/rooms/${room.id}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_type: action, outcome })
    }).catch(() => {});
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
  els.campusFrame.classList.remove("fold");
  void els.campusFrame.offsetWidth;
  els.campusFrame.classList.add("fold");
  
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
    await refreshConnectors();
  } else {
    renderConnectorList();
  }
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

renderAll();
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
  renderAll();
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
  addAudit("room_viewed");
  renderAll();
});

els.roomTabs.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (!button) return;
  state.activeTab = button.dataset.tab;
  renderRoom();
});

els.roomBody.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  if (action.includes("power") && !confirm("Mock confirmation: power cycling should be a last-resort action. Log this request?")) return;
  addAudit(action, action.includes("power") ? "confirmation logged" : "success");
  state.activeTab = "log";
  renderRoom();
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

renderAll();
checkBackend();
