let campuses = [], buildings = [], currentBldg = null, deviceRows = [];

function encodePayload(value) {
  return encodeURIComponent(JSON.stringify(value));
}

window.onAdminReady(async () => {
  document.getElementById('main').style.display = '';
  await loadCampuses();
});

// ── Load campuses + buildings ───────────────────────────────────────────────
async function loadCampuses() {
  try {
    campuses  = await adminGet('/api/admin/campuses');
    buildings = await adminGet('/api/admin/buildings');
    renderSidebar();
    // Pre-populate campus select in building dialog
    const sel = document.getElementById('b-campus');
    sel.innerHTML = campuses.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  } catch(e) {
    toast('Could not load building list: ' + e.message, 'error');
  }
}

function renderSidebar() {
  const ul = document.getElementById('building-list');
  if (!buildings.length) {
    ul.innerHTML = '<li style="padding:.75rem 1.25rem;color:#888">No buildings yet.</li>';
    return;
  }
  // Group by campus
  const byCampus = {};
  for (const b of buildings) {
    (byCampus[b.campus_id] = byCampus[b.campus_id] || []).push(b);
  }
  ul.innerHTML = Object.entries(byCampus).map(([cid, bldgs]) => `
    <li class="sidebar-list__section">${cid}</li>
    ${bldgs.map(b => `
      <li class="sidebar-list__item">
        <a href="#" data-bldg="${b.id}" data-bldg-name="${b.name}"
           class="${currentBldg === b.id ? 'active' : ''}">
          ${b.code} — ${b.name}
          <small style="color:#999;font-weight:400">(${b.room_count ?? 0})</small>
        </a>
      </li>`).join('')}
  `).join('');
  ul.querySelectorAll('[data-bldg]').forEach(a => {
    a.addEventListener('click', e => { e.preventDefault(); selectBuilding(+a.dataset.bldg, a.dataset.bldgName); });
  });
}

// ── Select building → load rooms ────────────────────────────────────────────
async function selectBuilding(id, name) {
  currentBldg = id;
  renderSidebar();
  document.getElementById('room-list-title').textContent = name;
  document.getElementById('btn-add-room').style.display = '';
  try {
    const rooms = await adminGet(`/api/admin/rooms?building_id=${id}`);
    renderRoomsTable(rooms);
  } catch(e) {
    toast('Could not load rooms: ' + e.message, 'error');
  }
}

function renderRoomsTable(rooms) {
  const tbody = document.getElementById('rooms-body');
  const table = document.getElementById('rooms-table');
  const empty = document.getElementById('rooms-empty');
  if (!rooms.length) { table.style.display = 'none'; empty.style.display = ''; return; }
  empty.style.display = 'none'; table.style.display = '';
  tbody.innerHTML = rooms.map(r => `
    <tr>
      <td><strong>${r.number}</strong></td>
      <td>${r.type || '—'}</td>
      <td><span class="badge badge--${r.status}">${r.status}</span></td>
      <td>${r.health ?? 0}%</td>
      <td>${r.processor || 'mock'}</td>
      <td>${(r.devices || []).length}</td>
      <td>
        <button class="btn btn--secondary btn--sm" data-room-edit="${encodePayload(r)}">Edit</button>
      </td>
    </tr>`).join('');
}

// ── Room drawer ──────────────────────────────────────────────────────────────
function openDrawer(isNew) {
  document.getElementById('drawer-overlay').classList.add('open');
  document.getElementById('room-drawer').classList.add('open');
  document.getElementById('drawer-title').textContent = isNew ? 'Add Room' : 'Edit Room';
  document.getElementById('btn-delete-room').style.display = isNew ? 'none' : '';
}
function closeDrawer() {
  document.getElementById('drawer-overlay').classList.remove('open');
  document.getElementById('room-drawer').classList.remove('open');
}

document.getElementById('drawer-close').addEventListener('click', closeDrawer);
document.getElementById('drawer-overlay').addEventListener('click', closeDrawer);
document.getElementById('btn-cancel').addEventListener('click', closeDrawer);

document.getElementById('btn-add-room').addEventListener('click', () => {
  document.getElementById('room-form').reset();
  document.getElementById('f-room-id').value = '';
  document.getElementById('f-building-id').value = currentBldg;
  deviceRows = [];
  renderDevicesTable();
  openDrawer(true);
});

document.getElementById('rooms-body').addEventListener('click', event => {
  const btn = event.target.closest('[data-room-edit]');
  if (!btn) return;
  openEditRoom(decodeURIComponent(btn.dataset.roomEdit));
});

window.openEditRoom = function(jsonStr) {
  const r = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
  document.getElementById('f-room-id').value       = r.id || '';
  document.getElementById('f-building-id').value   = r.building_id || currentBldg;
  document.getElementById('f-number').value         = r.number || '';
  document.getElementById('f-type').value           = r.type || '';
  document.getElementById('f-status').value         = r.status || 'offline';
  document.getElementById('f-health').value         = r.health ?? 0;
  document.getElementById('f-active-event').value  = r.active_event || '';
  document.getElementById('f-processor').value     = r.processor || 'mock';
  document.getElementById('f-display').value       = r.display || 'unknown';
  document.getElementById('f-notes').value          = r.notes || '';
  document.getElementById('f-screenconnect').checked = !!r.screenconnect;
  document.getElementById('f-wattbox').checked      = !!r.wattbox;
  document.getElementById('f-hybrid').checked       = !!r.hybrid;
  document.getElementById('f-stale').checked        = !!r.stale;
  deviceRows = (r.devices || []).map(d => ({...d}));
  renderDevicesTable();
  openDrawer(false);
};

// ── Devices sub-table ────────────────────────────────────────────────────────
function renderDevicesTable() {
  const tbody = document.getElementById('devices-body');
  tbody.innerHTML = deviceRows.map((d, i) => `
    <tr>
      <td><input class="form-control" style="min-width:90px" value="${d.device_type||''}" data-device-index="${i}" data-device-field="device_type"></td>
      <td><input class="form-control" style="min-width:90px" value="${d.manufacturer||''}" data-device-index="${i}" data-device-field="manufacturer"></td>
      <td><input class="form-control" style="min-width:90px" value="${d.model||''}" data-device-index="${i}" data-device-field="model"></td>
      <td><input class="form-control" style="min-width:80px" value="${d.connection||''}" data-device-index="${i}" data-device-field="connection"></td>
      <td><button type="button" class="btn btn--danger btn--sm" data-device-remove="${i}">✕</button></td>
    </tr>`).join('');
}
document.getElementById('devices-body').addEventListener('input', event => {
  const input = event.target.closest('[data-device-field]');
  if (!input) return;
  const row = deviceRows[Number(input.dataset.deviceIndex)];
  if (row) row[input.dataset.deviceField] = input.value;
});
document.getElementById('devices-body').addEventListener('click', event => {
  const button = event.target.closest('[data-device-remove]');
  if (!button) return;
  deviceRows.splice(Number(button.dataset.deviceRemove), 1);
  renderDevicesTable();
});
document.getElementById('btn-add-device').addEventListener('click', () => {
  deviceRows.push({device_type:'',manufacturer:'',model:'',connection:''});
  renderDevicesTable();
});

// ── Save room ────────────────────────────────────────────────────────────────
document.getElementById('btn-save').addEventListener('click', async () => {
  const rid  = document.getElementById('f-room-id').value;
  const bldg = document.getElementById('f-building-id').value;
  const body = {
    number:        document.getElementById('f-number').value.trim(),
    type:          document.getElementById('f-type').value.trim(),
    status:        document.getElementById('f-status').value,
    health:        +document.getElementById('f-health').value,
    active_event:  document.getElementById('f-active-event').value.trim(),
    processor:     document.getElementById('f-processor').value,
    display:       document.getElementById('f-display').value,
    notes:         document.getElementById('f-notes').value.trim(),
    screenconnect: document.getElementById('f-screenconnect').checked,
    wattbox:       document.getElementById('f-wattbox').checked,
    hybrid:        document.getElementById('f-hybrid').checked,
    stale:         document.getElementById('f-stale').checked,
    devices:       deviceRows.filter(d => d.device_type),
  };
  if (!body.number) { toast('Room number is required', 'error'); return; }
  try {
    if (rid) {
      await adminPut(`/api/admin/rooms/${rid}`, body);
      toast('Room updated');
    } else {
      await adminPost(`/api/admin/rooms?building_id=${bldg}`, body);
      toast('Room created');
    }
    closeDrawer();
    await selectBuilding(currentBldg, document.getElementById('room-list-title').textContent);
  } catch(e) {
    toast('Save failed: ' + e.message, 'error');
  }
});

// ── Delete room ──────────────────────────────────────────────────────────────
document.getElementById('btn-delete-room').addEventListener('click', async () => {
  const rid = document.getElementById('f-room-id').value;
  if (!rid || !confirm(`Delete room ${rid}? This cannot be undone.`)) return;
  try {
    await adminDelete(`/api/admin/rooms/${rid}`);
    toast('Room deleted', 'warning');
    closeDrawer();
    await selectBuilding(currentBldg, document.getElementById('room-list-title').textContent);
  } catch(e) {
    toast('Delete failed: ' + e.message, 'error');
  }
});

// ── Building drawer ──────────────────────────────────────────────────────────
function openBldgDrawer(isNew) {
  document.getElementById('bldg-overlay').classList.add('open');
  document.getElementById('bldg-drawer').classList.add('open');
  document.getElementById('bldg-drawer-title').textContent = isNew ? 'Add Building' : 'Edit Building';
  document.getElementById('btn-delete-building').style.display = isNew ? 'none' : '';
}
function closeBldgDrawer() {
  document.getElementById('bldg-overlay').classList.remove('open');
  document.getElementById('bldg-drawer').classList.remove('open');
}
document.getElementById('bldg-close').addEventListener('click', closeBldgDrawer);
document.getElementById('bldg-overlay').addEventListener('click', closeBldgDrawer);
document.getElementById('btn-bldg-cancel').addEventListener('click', closeBldgDrawer);
document.getElementById('btn-add-building').addEventListener('click', () => {
  document.getElementById('b-id').value   = '';
  document.getElementById('b-code').value = '';
  document.getElementById('b-name').value = '';
  openBldgDrawer(true);
});
document.getElementById('btn-bldg-save').addEventListener('click', async () => {
  const bid  = document.getElementById('b-id').value;
  const body = {
    campus_id: document.getElementById('b-campus').value,
    code:      document.getElementById('b-code').value.trim(),
    name:      document.getElementById('b-name').value.trim(),
  };
  if (!body.code || !body.name) { toast('Code and name are required', 'error'); return; }
  try {
    if (bid) {
      await adminPut(`/api/admin/buildings/${bid}`, body);
      toast('Building updated');
    } else {
      await adminPost('/api/admin/buildings', body);
      toast('Building created');
    }
    closeBldgDrawer();
    await loadCampuses();
  } catch(e) {
    toast('Save failed: ' + e.message, 'error');
  }
});
document.getElementById('btn-delete-building').addEventListener('click', async () => {
  const bid = document.getElementById('b-id').value;
  if (!bid || !confirm('Delete this building and ALL its rooms? This cannot be undone.')) return;
  try {
    await adminDelete(`/api/admin/buildings/${bid}`);
    toast('Building deleted', 'warning');
    closeBldgDrawer();
    currentBldg = null;
    await loadCampuses();
    document.getElementById('room-list-title').textContent = 'Select a building';
    document.getElementById('btn-add-room').style.display = 'none';
    document.getElementById('rooms-table').style.display = 'none';
    document.getElementById('rooms-empty').style.display = 'none';
  } catch(e) {
    toast('Delete failed: ' + e.message, 'error');
  }
});
