window.onAdminReady(() => {
  document.getElementById('main').style.display = '';
  loadUsers();
});
document.getElementById('btn-refresh').addEventListener('click', loadUsers);

function encodePayload(value) {
  return encodeURIComponent(JSON.stringify(value));
}

async function loadUsers() {
  try {
    const rows = await adminGet('/api/admin/users');
    renderTable(rows);
  } catch(e) {
    toast('Failed to load users: ' + e.message, 'error');
  }
}

function renderTable(rows) {
  const tbody = document.getElementById('users-body');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#888;padding:1.5rem">No manual role overrides. Users with AD-group roles do not appear here.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.display_name || '—'}</td>
      <td>${r.email || r.entra_id}</td>
      <td><span class="badge badge--${r.role}">${r.role}</span></td>
      <td>Manual override</td>
      <td style="font-size:.8rem;color:#888">${r.updated_at ? r.updated_at.slice(0,16).replace('T',' ') : ''}</td>
      <td style="font-size:.8rem">${r.notes || ''}</td>
      <td>
        <button class="btn btn--secondary btn--sm"
          data-user-edit="${encodePayload(r)}">Edit</button>
      </td>
    </tr>`).join('');
}

function openDrawer() {
  document.getElementById('drawer-overlay').classList.add('open');
  document.getElementById('role-drawer').classList.add('open');
}
function closeDrawer() {
  document.getElementById('drawer-overlay').classList.remove('open');
  document.getElementById('role-drawer').classList.remove('open');
}
document.getElementById('drawer-close').addEventListener('click', closeDrawer);
document.getElementById('drawer-overlay').addEventListener('click', closeDrawer);
document.getElementById('btn-cancel').addEventListener('click', closeDrawer);

document.getElementById('users-body').addEventListener('click', event => {
  const btn = event.target.closest('[data-user-edit]');
  if (!btn) return;
  openEdit(decodeURIComponent(btn.dataset.userEdit));
});

window.openEdit = function(jsonStr) {
  const r = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
  document.getElementById('f-entra-id').value = r.entra_id;
  document.getElementById('f-role').value    = r.role || 'technician';
  document.getElementById('f-notes').value   = r.notes || '';
  document.getElementById('drawer-user-name').textContent =
    r.display_name || r.email || r.entra_id;
  openDrawer();
};

document.getElementById('btn-save').addEventListener('click', async () => {
  const id = document.getElementById('f-entra-id').value;
  const body = {
    role:  document.getElementById('f-role').value,
    notes: document.getElementById('f-notes').value.trim(),
  };
  try {
    await adminPut(`/api/admin/users/${id}`, body);
    toast('Role override saved');
    closeDrawer();
    loadUsers();
  } catch(e) {
    toast('Save failed: ' + e.message, 'error');
  }
});

document.getElementById('btn-remove-override').addEventListener('click', async () => {
  const id = document.getElementById('f-entra-id').value;
  if (!confirm('Remove override? This user will fall back to their Azure AD group role.')) return;
  try {
    await adminDelete(`/api/admin/users/${id}`);
    toast('Override removed', 'warning');
    closeDrawer();
    loadUsers();
  } catch(e) {
    toast('Remove failed: ' + e.message, 'error');
  }
});
