/**
 * BeaverView Admin — shared auth, API helpers, navigation
 * Include this script on every admin page (type="module").
 */

// ---------------------------------------------------------------------------
// Auth check — runs immediately on load
// ---------------------------------------------------------------------------
(async function () {
  let role;
  try {
    const res = await fetch('/api/me');
    if (!res.ok) {
      window.location = '/auth/login?next=' + encodeURIComponent(window.location.pathname);
      return;
    }
    const data = await res.json();
    role = data.role;
    window._adminUser = data;
  } catch {
    showAccessDenied('Could not contact the server. Is BeaverView running?');
    return;
  }

  if (role !== 'admin') {
    showAccessDenied('Your account does not have admin access to BeaverView.');
    return;
  }

  // Populate nav username
  const el = document.getElementById('nav-username');
  if (el) el.textContent = window._adminUser.name || window._adminUser.user || '';

  document.dispatchEvent(new Event('admin-ready'));
})();

function showAccessDenied(msg) {
  document.body.innerHTML = `
    <div style="padding:2rem;font-family:system-ui,sans-serif;max-width:480px;margin:4rem auto">
      <h2 style="color:#cc0000">Access Denied</h2>
      <p>${msg}</p>
      <a href="/">← Back to dashboard</a>
    </div>`;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
async function adminFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  if (res.status === 401) {
    window.location = '/auth/login?next=' + encodeURIComponent(window.location.pathname);
    return null;
  }
  return res;
}

async function adminGet(url) {
  const res = await adminFetch(url);
  if (!res || !res.ok) throw new Error(`GET ${url} failed: ${res?.status}`);
  return res.json();
}

async function adminPost(url, body) {
  const res = await adminFetch(url, { method: 'POST', body: JSON.stringify(body) });
  if (!res || !res.ok) {
    const err = await res?.json().catch(() => ({}));
    throw new Error(err.detail || `POST ${url} failed: ${res?.status}`);
  }
  return res.json();
}

async function adminPut(url, body) {
  const res = await adminFetch(url, { method: 'PUT', body: JSON.stringify(body) });
  if (!res || !res.ok) {
    const err = await res?.json().catch(() => ({}));
    throw new Error(err.detail || `PUT ${url} failed: ${res?.status}`);
  }
  return res.json();
}

async function adminDelete(url) {
  const res = await adminFetch(url, { method: 'DELETE' });
  if (!res || !res.ok) {
    const err = await res?.json().catch(() => ({}));
    throw new Error(err.detail || `DELETE ${url} failed: ${res?.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Toast notifications
// ---------------------------------------------------------------------------
function toast(msg, type = 'success') {
  const t = document.createElement('div');
  t.className = `toast toast--${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add('toast--show'), 10);
  setTimeout(() => { t.classList.remove('toast--show'); setTimeout(() => t.remove(), 300); }, 3000);
}

// ---------------------------------------------------------------------------
// Expose globals
// ---------------------------------------------------------------------------
window.adminFetch  = adminFetch;
window.adminGet    = adminGet;
window.adminPost   = adminPost;
window.adminPut    = adminPut;
window.adminDelete = adminDelete;
window.toast       = toast;
