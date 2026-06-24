const LIMIT = 50;
let offset = 0, total = 0;

window.onAdminReady(() => {
  document.getElementById('main').style.display = '';
  loadLogs();
});

function getFilters() {
  return {
    campus:      document.getElementById('f-campus').value || null,
    room_id:     document.getElementById('f-room').value.trim() || null,
    user:        document.getElementById('f-user').value.trim() || null,
    action_type: document.getElementById('f-action').value.trim() || null,
    date_from:   document.getElementById('f-from').value || null,
    date_to:     document.getElementById('f-to').value || null,
  };
}

function buildQS(extra = {}) {
  const f = {...getFilters(), limit: LIMIT, offset, ...extra};
  return Object.entries(f)
    .filter(([,v]) => v !== null && v !== undefined)
    .map(([k,v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');
}

async function loadLogs() {
  try {
    const d = await adminGet('/api/admin/logs?' + buildQS());
    total = d.total;
    renderTable(d.rows);
    renderPagination();
  } catch(e) {
    toast('Failed to load logs: ' + e.message, 'error');
  }
}

function renderTable(rows) {
  const tbody = document.getElementById('log-body');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#888;padding:1.5rem">No entries match the current filters.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const campus = r.room_id ? r.room_id.split('-')[0] : '';
    return `<tr>
      <td style="white-space:nowrap">${r.ts ? r.ts.slice(0,16).replace('T',' ') : ''}</td>
      <td>${r.user || ''}</td>
      <td>${campus}</td>
      <td><code style="font-size:.8rem">${r.room_id || ''}</code></td>
      <td><code style="font-size:.8rem">${r.action_type || ''}</code></td>
      <td style="font-size:.8rem">${r.target || ''}</td>
      <td><span class="badge ${r.outcome === 'success' ? 'badge--live' : 'badge--degraded'}">${r.outcome || ''}</span></td>
    </tr>`;
  }).join('');
}

function renderPagination() {
  document.getElementById('page-info').textContent =
    total ? `${offset+1}–${Math.min(offset+LIMIT, total)} of ${total}` : 'No results';
  document.getElementById('btn-prev').disabled = offset === 0;
  document.getElementById('btn-next').disabled = offset + LIMIT >= total;
}

document.getElementById('btn-search').addEventListener('click', () => { offset = 0; loadLogs(); });
document.getElementById('btn-reset').addEventListener('click', () => {
  ['f-campus','f-room','f-user','f-action','f-from','f-to'].forEach(id => {
    const el = document.getElementById(id);
    if (el.tagName === 'SELECT') el.value = '';
    else el.value = '';
  });
  offset = 0; loadLogs();
});
document.getElementById('btn-prev').addEventListener('click', () => { offset = Math.max(0, offset-LIMIT); loadLogs(); });
document.getElementById('btn-next').addEventListener('click', () => { offset += LIMIT; loadLogs(); });

document.getElementById('btn-export').addEventListener('click', () => {
  const qs = buildQS({limit: undefined, offset: undefined});
  window.location = '/api/admin/logs/export?' + qs;
});

document.getElementById('btn-archive').addEventListener('click', async () => {
  const days = +document.getElementById('archive-days').value;
  if (!confirm(`Archive log entries older than ${days} days?`)) return;
  try {
    const r = await adminPost(`/api/admin/logs/archive?older_than_days=${days}`, {});
    document.getElementById('maintenance-msg').textContent =
      `Archived ${r.archived} entries (older than ${days} days). Cutoff: ${r.cutoff}`;
    toast(`Archived ${r.archived} entries`, 'success');
    loadLogs();
  } catch(e) {
    toast('Archive failed: ' + e.message, 'error');
  }
});

document.getElementById('btn-purge').addEventListener('click', async () => {
  const confirm_text = document.getElementById('purge-confirm').value.trim();
  if (confirm_text !== 'CONFIRM') {
    toast('Type CONFIRM in the box to enable purge', 'error'); return;
  }
  const days = +document.getElementById('purge-days').value;
  try {
    // Get a one-time token first
    const t = await adminGet('/api/admin/logs/purge-token');
    const r = await adminDelete(`/api/admin/logs/purge?token=${t.token}&older_than_days=${days}`);
    document.getElementById('maintenance-msg').textContent =
      `Purged ${r.purged} archived entries older than ${days} days.`;
    toast(`Purged ${r.purged} archived entries`, 'warning');
    document.getElementById('purge-confirm').value = '';
  } catch(e) {
    toast('Purge failed: ' + e.message, 'error');
  }
});
