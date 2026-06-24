window.onAdminReady(async () => {
  document.getElementById('main').style.display = '';
  await loadAll();
  setInterval(loadFeed, 60000);
});

async function loadAll() {
  await Promise.all([loadSummary(), loadFeed(), loadConnectors()]);
  document.getElementById('last-refresh').textContent =
    'Last refreshed: ' + new Date().toLocaleTimeString();
}

async function loadSummary() {
  try {
    const d = await adminGet('/api/admin/logs/summary?days=7');
    document.getElementById('stat-rooms').textContent     = d.stats.total_rooms;
    document.getElementById('stat-active').textContent    = d.stats.active_rooms;
    document.getElementById('stat-incidents').textContent = d.stats.open_incidents;
    const total7 = d.daily.reduce((s, r) => s + r.n, 0);
    document.getElementById('stat-actions7').textContent  = total7;

    document.getElementById('top-rooms').innerHTML = d.top_rooms.length
      ? d.top_rooms.map(r => `<tr><td>${r.room_id}</td><td>${r.n}</td></tr>`).join('')
      : '<tr><td colspan="2" style="color:#888">No data yet</td></tr>';

    document.getElementById('top-actions').innerHTML = d.top_actions.length
      ? d.top_actions.map(r => `<tr><td><code>${r.action}</code></td><td>${r.n}</td></tr>`).join('')
      : '<tr><td colspan="2" style="color:#888">No data yet</td></tr>';
  } catch(e) {
    console.warn('Summary load failed:', e);
  }
}

async function loadFeed() {
  try {
    const d = await adminGet('/api/admin/logs?limit=20');
    const feed = document.getElementById('activity-feed');
    if (!d.rows.length) {
      feed.innerHTML = '<li style="color:#888;padding:.5rem 0">No activity recorded yet.</li>';
      return;
    }
    feed.innerHTML = d.rows.map(r => `
      <li class="feed__item">
        <span class="feed__ts">${r.ts ? r.ts.slice(0,16).replace('T',' ') : ''}</span>
        <span class="feed__user">${r.user || ''}</span>
        <span class="feed__action"><code>${r.action_type}</code>${r.room_id ? ' · ' + r.room_id : ''}${r.outcome === 'failure' ? ' <span style="color:#c62828">✗</span>' : ''}</span>
      </li>`).join('');
  } catch(e) {
    console.warn('Feed load failed:', e);
  }
}

async function loadConnectors() {
  try {
    const rows = await adminGet('/api/admin/connectors');
    const el = document.getElementById('connector-health');
    if (!rows.length) {
      el.innerHTML = '<p style="color:#888">No connector data. Run the data migration first.</p>';
      return;
    }
    el.innerHTML = rows.map(r => `
      <div class="connector-row">
        <span class="connector-row__name">${r.connector_name}</span>
        <span class="connector-row__campus">${r.campus_id}</span>
        <span class="badge badge--${r.mode}">${r.mode}</span>
        <span class="connector-row__cred ${r.credentials_present ? 'connector-row__cred--ok' : 'connector-row__cred--miss'}">
          credentials: ${r.credentials_present ? '✓' : '✗ missing'}
        </span>
        ${r.last_synced ? `<span style="font-size:.78rem;color:#999">synced ${r.last_synced.slice(0,16).replace('T',' ')}</span>` : ''}
      </div>`).join('');
  } catch(e) {
    console.warn('Connector health load failed:', e);
  }
}
