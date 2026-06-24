window.onAdminReady(() => {
  document.getElementById('main').style.display = '';
  loadConnectors();
});
document.getElementById('btn-refresh').addEventListener('click', loadConnectors);

async function loadConnectors() {
  try {
    const rows = await adminGet('/api/admin/connectors');
    renderGrid(rows);
  } catch(e) {
    toast('Failed to load connectors: ' + e.message, 'error');
  }
}

function renderGrid(rows) {
  const el = document.getElementById('connector-grid');
  if (!rows.length) {
    el.innerHTML = '<p style="color:#888">No connector records. Run the data migration first.</p>';
    return;
  }

  // Group by connector name (show one row per connector, columns per campus)
  const campuses = [...new Set(rows.map(r => r.campus_id))].sort();
  const connectors = [...new Set(rows.map(r => r.connector_name))].sort();

  el.innerHTML = connectors.map(cn => {
    const campusCells = campuses.map(cid => {
      const r = rows.find(x => x.campus_id === cid && x.connector_name === cn);
      if (!r) return `<div style="min-width:200px"></div>`;
      return `
        <div style="min-width:200px;background:#fafafa;border:1px solid var(--border);border-radius:4px;padding:.65rem .75rem">
          <div style="font-size:.78rem;color:#888;margin-bottom:.35rem">${cid}</div>
          <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem">
            <span class="badge badge--${r.mode}">${r.mode}</span>
            <span class="connector-row__cred ${r.credentials_present ? 'connector-row__cred--ok' : 'connector-row__cred--miss'}">
              creds: ${r.credentials_present ? '✓' : '✗'}
            </span>
          </div>
          ${r.last_synced ? `<div style="font-size:.72rem;color:#999;margin-bottom:.4rem">synced ${r.last_synced.slice(0,16).replace('T',' ')}</div>` : ''}
          <div style="display:flex;gap:.3rem;flex-wrap:wrap">
            <button class="btn btn--secondary btn--sm"
              data-action="toggle-connector" data-campus="${cid}" data-connector="${cn}" data-mode="${r.mode === 'live' ? 'mock' : 'live'}">
              → ${r.mode === 'live' ? 'mock' : 'live'}
            </button>
            <button class="btn btn--secondary btn--sm"
              data-action="test-connector" data-campus="${cid}" data-connector="${cn}">Test</button>
          </div>
        </div>`;
    }).join('');

    return `
      <div class="connector-row" style="align-items:flex-start;gap:.75rem;flex-wrap:wrap">
        <div class="connector-row__name" style="min-width:120px;padding-top:.35rem">${cn}</div>
        <div style="display:flex;gap:.5rem;flex-wrap:wrap">${campusCells}</div>
      </div>`;
  }).join('');
}

document.getElementById('connector-grid').addEventListener('click', event => {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const { action, campus, connector, mode } = button.dataset;
  if (action === 'toggle-connector') {
    toggleMode(campus, connector, mode);
  } else if (action === 'test-connector') {
    testConnector(campus, connector);
  }
});

async function toggleMode(campus, name, newMode) {
  // Clear any previous warning
  document.getElementById('warning-banner').style.display = 'none';
  try {
    const r = await adminPut(
      `/api/admin/connectors/${campus}/${name}/mode?mode=${newMode}`, {}
    );
    if (r.status === 'warning') {
      document.getElementById('warning-msg').textContent = r.message;
      document.getElementById('warning-banner').style.display = 'flex';
    } else {
      toast(`${name} on ${campus} → ${newMode}`);
    }
    await loadConnectors();
  } catch(e) {
    toast('Toggle failed: ' + e.message, 'error');
  }
}

async function testConnector(campus, name) {
  try {
    const r = await adminPost(`/api/admin/connectors/${campus}/${name}/test`, {});
    const msg = r.message || (r.reachable ? 'Reachable ✓' : 'Unreachable ✗');
    toast(`${name} (${campus}): ${msg}`, r.reachable === false ? 'error' : 'success');
  } catch(e) {
    toast('Test failed: ' + e.message, 'error');
  }
}
