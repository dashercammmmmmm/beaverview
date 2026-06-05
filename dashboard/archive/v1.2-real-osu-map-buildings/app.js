const data = window.dashboardData;

const state = {
  campusId: data.campuses[0].id,
  selectedBuildingCode: null,
  selectedRoomId: null,
  activeTab: "overview",
  search: "",
  filters: new Set(),
  log: [],
  compact: false
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
  densityToggle: document.querySelector("#densityToggle")
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
  return supportBuilding ? supportBuilding.rooms : [];
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

function campusBounds(buildings) {
  const points = buildings.flatMap((building) => (
    building.polygon && building.polygon.length ? building.polygon : [[building.lng, building.lat]]
  ));
  const lngs = points.map((point) => point[0]);
  const lats = points.map((point) => point[1]);
  return {
    minLng: Math.min(...lngs),
    maxLng: Math.max(...lngs),
    minLat: Math.min(...lats),
    maxLat: Math.max(...lats)
  };
}

function makeProjector(buildings) {
  const bounds = campusBounds(buildings);
  const width = 1000;
  const height = 650;
  const pad = 48;
  const lngSpan = bounds.maxLng - bounds.minLng || 0.01;
  const latSpan = bounds.maxLat - bounds.minLat || 0.01;
  return ([lng, lat]) => {
    const x = pad + ((lng - bounds.minLng) / lngSpan) * (width - pad * 2);
    const y = pad + ((bounds.maxLat - lat) / latSpan) * (height - pad * 2);
    return [x, y];
  };
}

function polygonPath(building, project) {
  const polygon = building.polygon && building.polygon.length
    ? building.polygon
    : [
      [building.lng - 0.00005, building.lat - 0.00005],
      [building.lng + 0.00005, building.lat - 0.00005],
      [building.lng + 0.00005, building.lat + 0.00005],
      [building.lng - 0.00005, building.lat + 0.00005],
      [building.lng - 0.00005, building.lat - 0.00005]
    ];
  return polygon.map((point, index) => {
    const [x, y] = project(point);
    return `${index ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ") + " Z";
}

function labelPoint(building, project) {
  const polygon = building.polygon && building.polygon.length ? building.polygon : [[building.lng, building.lat]];
  const projected = polygon.map(project);
  const x = projected.reduce((sum, point) => sum + point[0], 0) / projected.length;
  const y = projected.reduce((sum, point) => sum + point[1], 0) / projected.length;
  return [x, y];
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
  const labels = {
    fusion: "Fusion",
    live25: "25Live",
    screenconnect: "ScreenConnect",
    wattbox: "WattBox/OvrC",
    servicenow: "ServiceNow"
  };
  els.connectorList.innerHTML = Object.entries(campus.connectors).map(([key, value]) => `
    <div class="connector-row">
      <span>${labels[key]}</span>
      <strong class="connector-state ${value}">${value}</strong>
    </div>
  `).join("");
}

function renderMap() {
  const campus = currentCampus();
  const buildings = campusBuildings(campus);
  els.mapHeading.textContent = `${campus.name} Campus`;
  els.campusFrame.dataset.campus = campus.id;

  const rooms = allRooms(campus);
  const summary = {
    buildings: buildings.length,
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

  const visibleBuildings = buildings.filter(buildingMatches);
  if (!visibleBuildings.length) {
    els.campusGrid.innerHTML = `<div class="empty-map">No buildings match the current search and filters.</div>`;
    return;
  }
  const project = makeProjector(visibleBuildings);
  const paths = visibleBuildings.map((building) => {
    const summary = buildingSummary(building);
    const [labelX, labelY] = labelPoint(building, project);
    const label = building.code || "Bldg";
    return `
      <button
        type="button"
        class="building-hotspot"
        style="left:${(labelX / 10).toFixed(2)}%; top:${(labelY / 6.5).toFixed(2)}%;"
        data-building="${building.id}"
        aria-label="${label}, ${building.name}, ${summary.rooms.length} mock support rooms, ${summary.issues} issues">
        <span class="building-code">${label}</span>
        <span class="building-meta">${summary.rooms.length ? `${summary.rooms.length} rooms · ${summary.issues} issues` : "inventory pending"}</span>
      </button>
    `;
  }).join("");

  const polygons = visibleBuildings.map((building) => {
    const summary = buildingSummary(building);
    return `
      <path
        class="building-shape ${summary.status} ${state.selectedBuildingCode === building.id ? "selected" : ""}"
        d="${polygonPath(building, project)}"
        data-building="${building.id}">
        <title>${building.name}</title>
      </path>
    `;
  }).join("");

  els.campusGrid.innerHTML = `
    <svg class="real-map-svg" viewBox="0 0 1000 650" role="img" aria-label="${campus.name} buildings from map.oregonstate.edu">
      <rect class="map-ground" x="0" y="0" width="1000" height="650"></rect>
      <path class="map-path primary" d="M40 340 C190 298 330 372 500 326 S790 258 960 292"></path>
      <path class="map-path secondary" d="M480 40 C520 180 488 294 548 432 S620 564 594 620"></path>
      <g>${polygons}</g>
    </svg>
    ${paths}
  `;
}

function renderSelectedBuilding() {
  const campus = currentCampus();
  const building = campusBuildings(campus).find((item) => item.id === state.selectedBuildingCode) || campusBuildings(campus).find(buildingMatches);
  if (!building) {
    els.selectedBuilding.innerHTML = `<p>No building selected.</p>`;
    return;
  }
  state.selectedBuildingCode = building.id;
  const rooms = allRooms().filter((room) => room.building.id === building.id && roomMatchesFilters(room));
  els.selectedBuilding.innerHTML = `
    <div class="building-detail">
      <div>
        <p class="eyebrow">Building</p>
        <h3>${building.code || "Building"} <span>${building.name}</span></h3>
      </div>
      <div class="room-list">
        ${rooms.map((room) => `
          <button type="button" class="room-pill ${room.status} ${room.id === state.selectedRoomId ? "active" : ""}" data-room="${room.id}">
            <strong>${building.code || building.name} ${room.number}</strong>
            <span>${statusLabel(room.status)} · ${room.health}%</span>
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
    <p>${room.type}</p>
    <div class="room-status-line">
      <span class="status-dot ${room.status}"></span>
      <strong>${statusLabel(room.status)}</strong>
      <span>${room.health}% health</span>
    </div>
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

els.campusGrid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-building]");
  if (!button) return;
  state.selectedBuildingCode = button.dataset.building;
  const firstRoom = allRooms().find((room) => room.building.id === state.selectedBuildingCode && roomMatchesFilters(room));
  state.selectedRoomId = firstRoom ? firstRoom.id : null;
  state.activeTab = "overview";
  renderAll();
});

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
