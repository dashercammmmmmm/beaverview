# BeaverView — Admin Panel Playbook
**Audience:** Developers implementing the BeaverView admin panel.
**Purpose:** Step-by-step guide to build the `/admin` panel — room editor, log management, connector control, user roles, and summary dashboard.

> **Prerequisite:** BeaverView must already be running. Complete `PLAYBOOK-DEPLOYMENT.md` first.

---

## What this adds

| Feature | URL | Access |
|---|---|---|
| Summary dashboard | `/admin` | Admins only |
| Room and building editor | `/admin/rooms` | Admins only |
| Connector management | `/admin/connectors` | Admins only |
| User role management | `/admin/users` | Admins only |
| Audit log viewer + export | `/admin/logs` | Admins only |

All `/admin` routes check the user's Entra session. Users not in the **BeaverView Admins** Azure AD group receive a 403 page. Every admin action is written to the same `audit_log` table as technician actions.

---

## Architecture overview

The admin panel is **built into the existing FastAPI app** — no second server, no second deployment. The same nginx and systemd service that run the dashboard also serve `/admin`.

### Data flow — before vs. after

| Data | Before | After |
|---|---|---|
| Room and building data | `dashboard/data.js` (static file) | SQLite database (new tables) |
| Connector config | Hardcoded `CONNECTOR_REGISTRY` in `main.py` | `connector_config` table in SQLite |
| User roles | Azure AD group membership only | `user_roles` table + Azure AD fallback |
| Audit log | SQLite `audit_log` (already exists) | Same table, new admin UI |

### Why move room data to the database?

- A bad edit in `data.js` can break the entire dashboard with a JS syntax error — the admin panel validates input before saving
- Changes are instantly visible to all users
- Every edit is timestamped and attributed to the admin who made it
- Rollback is a database query, not a `git checkout`
- `data.js` is kept as a seed/backup reference

---

## Part 1 — Database Schema

Add these tables to `beaverview.db`. The existing `audit_log` table is unchanged. The `CREATE TABLE IF NOT EXISTS` statements are safe to run on every startup.

Add to `api/main.py` in the database initialization section:

```sql
-- campuses
CREATE TABLE IF NOT EXISTS campuses (
    id         TEXT PRIMARY KEY,   -- 'corvallis' | 'cascades' | 'hatfield'
    name       TEXT NOT NULL,
    subtitle   TEXT,
    center_lng REAL,
    center_lat REAL,
    zoom       REAL DEFAULT 15
);

-- buildings
CREATE TABLE IF NOT EXISTS buildings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_id TEXT NOT NULL REFERENCES campuses(id),
    code      TEXT NOT NULL,   -- e.g. 'KAd', 'LINC', 'MU'
    name      TEXT NOT NULL,   -- e.g. 'Kerr Administration'
    active    INTEGER DEFAULT 1
);

-- rooms
CREATE TABLE IF NOT EXISTS rooms (
    id            TEXT PRIMARY KEY,   -- 'corvallis-kad-101'
    building_id   INTEGER NOT NULL REFERENCES buildings(id),
    number        TEXT NOT NULL,
    type          TEXT,
    status        TEXT DEFAULT 'offline',
    health        INTEGER DEFAULT 0,
    active_event  TEXT,
    processor     TEXT DEFAULT 'mock',  -- set by background device poller
    display       TEXT DEFAULT 'unknown',
    screenconnect INTEGER DEFAULT 0,
    wattbox       INTEGER DEFAULT 0,
    hybrid        INTEGER DEFAULT 0,
    stale         INTEGER DEFAULT 0,
    notes         TEXT,
    updated_at    TEXT
);

-- devices (one row per device per room)
CREATE TABLE IF NOT EXISTS devices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id      TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    device_type  TEXT NOT NULL,
    manufacturer TEXT,
    model        TEXT,
    connection   TEXT,
    sort_order   INTEGER DEFAULT 0
);

-- incidents (one row per incident per room)
CREATE TABLE IF NOT EXISTS incidents (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    ticket  TEXT NOT NULL,
    status  TEXT DEFAULT 'open'
);

-- connector configuration (replaces CONNECTOR_REGISTRY)
CREATE TABLE IF NOT EXISTS connector_config (
    campus_id      TEXT NOT NULL,
    connector_name TEXT NOT NULL,
    mode           TEXT DEFAULT 'mock',
    enabled        INTEGER DEFAULT 1,
    last_synced    TEXT,
    PRIMARY KEY (campus_id, connector_name)
);

-- user role overrides (Entra group is primary source of truth)
CREATE TABLE IF NOT EXISTS user_roles (
    entra_id     TEXT PRIMARY KEY,
    email        TEXT,
    display_name TEXT,
    role         TEXT DEFAULT 'technician',   -- 'technician' | 'admin' | 'readonly'
    notes        TEXT,
    updated_at   TEXT,
    updated_by   TEXT
);
```

---

## Part 2 — Data Migration (data.js → Database)

This is a one-time import. Save as `api/migrate_data.py` and run it once after the schema is in place.

```python
"""
One-time migration: imports data.js room inventory into SQLite.
Run once from the api/ folder:  python3 migrate_data.py
Safe to re-run — clears existing rows first (does NOT touch audit_log).
"""
import sqlite3, json, re, os

DB_PATH   = os.path.join(os.path.dirname(__file__), 'beaverview.db')
DATA_PATH = os.path.join(os.path.dirname(__file__), '../dashboard/data.js')

def extract_json(js_text):
    match = re.search(r'window\.dashboardData\s*=\s*(\{.*\})', js_text, re.DOTALL)
    if not match:
        raise ValueError('Could not find window.dashboardData in data.js')
    json_str = match.group(1)
    json_str = re.sub(r'\btrue\b',  'true',  json_str)
    json_str = re.sub(r'\bfalse\b', 'false', json_str)
    json_str = re.sub(r'\bnull\b',  'null',  json_str)
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # trailing commas
    return json.loads(json_str)

def migrate():
    with open(DATA_PATH) as f:
        data = extract_json(f.read())

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Clear existing data (preserves audit_log and user_roles)
    for tbl in ['devices', 'incidents', 'rooms', 'buildings', 'campuses', 'connector_config']:
        cur.execute(f'DELETE FROM {tbl}')

    for campus in data['campuses']:
        cid = campus['id']
        cur.execute('INSERT INTO campuses(id,name,subtitle) VALUES(?,?,?)',
                    (cid, campus['name'], campus.get('subtitle', '')))

        # Seed connector_config
        for conn_name in ['crestron','live25','screenconnect','wattbox',
                          'servicenow','sharepoint','ptz']:
            mode = campus.get('connectors', {}).get(conn_name, 'mock')
            cur.execute('INSERT INTO connector_config(campus_id,connector_name,mode)'
                        ' VALUES(?,?,?)', (cid, conn_name, mode))

        for bldg in campus.get('buildings', []):
            cur.execute('INSERT INTO buildings(campus_id,code,name) VALUES(?,?,?)'
                        ' RETURNING id',
                        (cid, bldg['code'], bldg['name']))
            bldg_id = cur.fetchone()[0]

            for room in bldg.get('rooms', []):
                room_id = f"{cid}-{bldg['code'].lower()}-{room['number']}".lower()
                room_id = re.sub(r'[^a-z0-9]+', '-', room_id).strip('-')
                cur.execute(
                    'INSERT INTO rooms(id,building_id,number,type,status,health,'
                    '  active_event,fusion,display,screenconnect,wattbox,hybrid,stale)'
                    ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (room_id, bldg_id, room['number'], room.get('type',''),
                     room.get('status','offline'), room.get('health', 0),
                     room.get('activeEvent',''), room.get('fusion','mock'),
                     room.get('display','unknown'),
                     int(room.get('screenconnect', False)),
                     int(room.get('wattbox', False)),
                     int(room.get('hybrid', False)),
                     int(room.get('stale', False))))

                for i, dev in enumerate(room.get('devices', [])):
                    cur.execute(
                        'INSERT INTO devices(room_id,device_type,manufacturer,model,connection,sort_order)'
                        ' VALUES(?,?,?,?,?,?)',
                        (room_id,
                         dev[0] if len(dev) > 0 else '',
                         dev[1] if len(dev) > 1 else '',
                         dev[2] if len(dev) > 2 else '',
                         dev[3] if len(dev) > 3 else '',
                         i))

                for inc in room.get('incidents', {}).get('open', []):
                    cur.execute('INSERT INTO incidents(room_id,ticket,status) VALUES(?,?,?)',
                                (room_id, inc, 'open'))
                for inc in room.get('incidents', {}).get('closed', []):
                    cur.execute('INSERT INTO incidents(room_id,ticket,status) VALUES(?,?,?)',
                                (room_id, inc, 'closed'))

    con.commit()
    con.close()
    print('Migration complete.')
    con2 = sqlite3.connect(DB_PATH)
    for tbl in ['campuses', 'buildings', 'rooms', 'devices']:
        n = con2.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]
        print(f'  {tbl}: {n} rows')
    con2.close()

if __name__ == '__main__':
    migrate()
```

### Run the migration

```bash
cd /home/beaverview/app/api
sudo -u beaverview venv/bin/python3 migrate_data.py
```

Expected output:
```
Migration complete.
  campuses: 3 rows
  buildings: 278 rows
  rooms: 954 rows
  devices: ~2800 rows
```

> After migration, update `main.py` API endpoints to query the new tables instead of `data_mock.py`. Keep `data.js` and `data_mock.py` as fallback references — do not delete them yet.

---

## Part 3 — Admin Auth Middleware

Add to `api/main.py`:

```python
from fastapi import Depends, HTTPException, Request

def require_admin(request: Request):
    """
    Dependency injected into all /api/admin/... routes.
    Raises 403 if user is not in the Admin group.
    Raises 401 if not logged in at all.
    """
    session = request.session  # requires starlette-sessions middleware
    user = session.get('user')
    if not user:
        raise HTTPException(401, 'Not authenticated')
    groups = user.get('groups', [])
    admin_group = os.getenv('AZURE_GROUP_ADMIN', '')
    if admin_group not in groups:
        raise HTTPException(403, 'Admin access required')
    return user

# Role resolver (used at login and by /api/me)
def resolve_role(entra_id: str, entra_groups: list) -> str:
    """
    Order: manual override in user_roles table → Azure AD group → readonly fallback.
    """
    con = get_db()
    row = con.execute('SELECT role FROM user_roles WHERE entra_id=?', (entra_id,)).fetchone()
    if row:
        return row[0]
    admin_gid = os.getenv('AZURE_GROUP_ADMIN', '')
    tech_gid  = os.getenv('AZURE_GROUP_TECHNICIAN', '')
    if admin_gid and admin_gid in entra_groups:
        return 'admin'
    if tech_gid and tech_gid in entra_groups:
        return 'technician'
    return 'readonly'

@app.get('/api/me')
def me(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(401, 'Not authenticated')
    role = resolve_role(user.get('oid', ''), user.get('groups', []))
    return {
        'user':  user.get('preferred_username'),
        'name':  user.get('name'),
        'role':  role,
    }
```

---

## Part 4 — Admin Panel File Structure

Create `dashboard/admin/` with these files:

```
dashboard/admin/
  index.html        ← admin home / summary dashboard
  rooms.html        ← room and building editor
  logs.html         ← audit log viewer
  connectors.html   ← connector toggle/status
  users.html        ← user role management
  admin.js          ← shared: auth check, API helpers, nav
  admin.css         ← admin-specific styles
```

### admin.js — shared auth check (include on every admin page)

```js
// Checks login state and redirects non-admins before rendering the page.
(async function () {
  const res = await fetch('/api/me');
  if (!res.ok) { window.location = '/auth/login?next=/admin'; return; }
  const { role } = await res.json();
  if (role !== 'admin') {
    document.body.innerHTML = `
      <div style="padding:2rem;font-family:sans-serif">
        <h1>Access denied</h1>
        <p>Your account does not have admin access to BeaverView.</p>
        <a href="/">Back to dashboard</a>
      </div>`;
    return;
  }
  document.dispatchEvent(new Event('admin-ready'));
})();

// Shared API helper
async function adminFetch(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers }
  });
}
```

### Serve admin pages from FastAPI

Add to `api/main.py`:

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), '../dashboard')

app.mount('/admin', StaticFiles(directory=os.path.join(DASHBOARD_DIR, 'admin'),
                                html=True), name='admin')

@app.get('/admin/{path:path}')
def admin_catch(path: str):
    return FileResponse(os.path.join(DASHBOARD_DIR, 'admin', 'index.html'))
```

---

## Part 5 — API Endpoints

### Room and building CRUD

| Endpoint | What it does |
|---|---|
| `GET  /api/admin/campuses` | List campuses with building/room counts |
| `GET  /api/admin/buildings?campus_id=...` | List buildings for a campus |
| `GET  /api/admin/rooms?building_id=...` | List rooms with devices |
| `POST /api/admin/rooms` | Create a new room |
| `PUT  /api/admin/rooms/{room_id}` | Update a room |
| `DELETE /api/admin/rooms/{room_id}` | Delete a room and its devices |
| `POST /api/admin/rooms/{room_id}/devices` | Add a device |
| `DELETE /api/admin/devices/{device_id}` | Remove a device |
| `POST /api/admin/buildings` | Create a building |
| `PUT  /api/admin/buildings/{building_id}` | Update a building |
| `DELETE /api/admin/buildings/{building_id}` | Delete building and all rooms |

#### PUT /api/admin/rooms/{room_id}

```python
from pydantic import BaseModel
from typing import Optional, List

class DeviceIn(BaseModel):
    device_type:  str
    manufacturer: Optional[str] = ''
    model:        Optional[str] = ''
    connection:   Optional[str] = ''

class RoomIn(BaseModel):
    number:        str
    type:          Optional[str] = ''
    status:        str = 'offline'
    health:        int = 0
    active_event:  Optional[str] = ''
    fusion:        str = 'mock'
    display:       str = 'unknown'
    screenconnect: bool = False
    wattbox:       bool = False
    hybrid:        bool = False
    stale:         bool = False
    notes:         Optional[str] = ''
    devices:       List[DeviceIn] = []

@app.put('/api/admin/rooms/{room_id}')
def admin_update_room(room_id: str, body: RoomIn,
                      request: Request, admin=Depends(require_admin)):
    con = get_db()
    now = _now()
    con.execute(
        'UPDATE rooms SET number=?,type=?,status=?,health=?,active_event=?,'
        '  fusion=?,display=?,screenconnect=?,wattbox=?,hybrid=?,stale=?,'
        '  notes=?,updated_at=? WHERE id=?',
        (body.number, body.type, body.status, body.health, body.active_event,
         body.fusion, body.display, int(body.screenconnect), int(body.wattbox),
         int(body.hybrid), int(body.stale), body.notes, now, room_id))
    con.execute('DELETE FROM devices WHERE room_id=?', (room_id,))
    for i, dev in enumerate(body.devices):
        con.execute(
            'INSERT INTO devices(room_id,device_type,manufacturer,model,connection,sort_order)'
            ' VALUES(?,?,?,?,?,?)',
            (room_id, dev.device_type, dev.manufacturer, dev.model, dev.connection, i))
    con.commit()
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,outcome) VALUES(?,?,?,?,?)',
        (now, admin['preferred_username'], room_id, 'admin_room_updated', 'success'))
    con.commit()
    return {'status': 'ok', 'room_id': room_id}
```

### Log management endpoints

| Endpoint | What it does |
|---|---|
| `GET  /api/admin/logs` | Query with filters: campus, room_id, user, action_type, date_from, date_to, limit, offset |
| `GET  /api/admin/logs/export` | Download filtered log as CSV |
| `GET  /api/admin/logs/summary` | Aggregated stats for the summary dashboard |
| `POST /api/admin/logs/archive` | Move entries older than N days to `audit_log_archive` |
| `DELETE /api/admin/logs/purge` | Permanently delete old entries (requires confirmation token) |

#### GET /api/admin/logs

```python
@app.get('/api/admin/logs')
def admin_logs(
    campus:      str = None,
    room_id:     str = None,
    user:        str = None,
    action_type: str = None,
    date_from:   str = None,
    date_to:     str = None,
    limit:       int = 50,
    offset:      int = 0,
    admin=Depends(require_admin)
):
    where, params = [], []
    if campus:      where.append("room_id LIKE ?");   params.append(f'{campus}-%')
    if room_id:     where.append("room_id = ?");      params.append(room_id)
    if user:        where.append("user LIKE ?");      params.append(f'%{user}%')
    if action_type: where.append("action_type = ?");  params.append(action_type)
    if date_from:   where.append("ts >= ?");          params.append(date_from)
    if date_to:     where.append("ts <= ?");          params.append(date_to + 'T23:59:59')
    sql = 'SELECT * FROM audit_log'
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY ts DESC LIMIT ? OFFSET ?'
    params += [limit, offset]
    con = get_db()
    rows = con.execute(sql, params).fetchall()
    total = con.execute(
        'SELECT COUNT(*) FROM audit_log' + (' WHERE ' + ' AND '.join(where) if where else ''),
        params[:-2]).fetchone()[0]
    cols = ['id','ts','user','room_id','action_type','target','outcome','notes']
    return {'total': total, 'rows': [dict(zip(cols, r)) for r in rows]}
```

#### GET /api/admin/logs/export (CSV download)

```python
from fastapi.responses import StreamingResponse
import csv, io

@app.get('/api/admin/logs/export')
def export_logs(
    campus: str = None, room_id: str = None, user: str = None,
    action_type: str = None, date_from: str = None, date_to: str = None,
    admin=Depends(require_admin)
):
    # Build same WHERE clause as admin_logs() — no LIMIT
    where, params = [], []
    if campus:      where.append("room_id LIKE ?");   params.append(f'{campus}-%')
    if room_id:     where.append("room_id = ?");      params.append(room_id)
    if user:        where.append("user LIKE ?");      params.append(f'%{user}%')
    if action_type: where.append("action_type = ?");  params.append(action_type)
    if date_from:   where.append("ts >= ?");          params.append(date_from)
    if date_to:     where.append("ts <= ?");          params.append(date_to + 'T23:59:59')
    sql = 'SELECT * FROM audit_log'
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY ts DESC'
    rows = get_db().execute(sql, params).fetchall()
    cols = ['id','ts','user','room_id','action_type','target','outcome','notes']

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(cols)
    writer.writerows(rows)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=beaverview-audit-log.csv'}
    )
```

#### POST /api/admin/logs/archive

```python
@app.post('/api/admin/logs/archive')
def archive_logs(older_than_days: int = 90, admin=Depends(require_admin)):
    """Move entries older than N days to audit_log_archive."""
    con = get_db()
    con.execute('CREATE TABLE IF NOT EXISTS audit_log_archive AS'
                ' SELECT * FROM audit_log WHERE 0')
    cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat()
    con.execute('INSERT INTO audit_log_archive SELECT * FROM audit_log WHERE ts < ?', (cutoff,))
    result = con.execute('DELETE FROM audit_log WHERE ts < ?', (cutoff,))
    count = result.rowcount
    con.commit()
    con.execute('INSERT INTO audit_log(ts,user,room_id,action_type,notes,outcome) VALUES(?,?,?,?,?,?)',
                (_now(), admin['preferred_username'], 'SYSTEM', 'admin_log_archive',
                 f'archived {count} entries older than {older_than_days} days', 'success'))
    con.commit()
    return {'archived': count, 'cutoff': cutoff}
```

#### GET /api/admin/logs/summary (for the dashboard charts)

```python
@app.get('/api/admin/logs/summary')
def logs_summary(days: int = 7, admin=Depends(require_admin)):
    con = get_db()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    daily = con.execute(
        'SELECT date(ts) as day, COUNT(*) as n FROM audit_log'
        ' WHERE ts >= ? GROUP BY day ORDER BY day', (cutoff,)).fetchall()

    top_rooms = con.execute(
        'SELECT room_id, COUNT(*) as n FROM audit_log'
        ' WHERE ts >= ? GROUP BY room_id ORDER BY n DESC LIMIT 5', (cutoff,)).fetchall()

    top_actions = con.execute(
        'SELECT action_type, COUNT(*) as n FROM audit_log'
        ' WHERE ts >= ? GROUP BY action_type ORDER BY n DESC LIMIT 10', (cutoff,)).fetchall()

    total_rooms    = con.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
    active_rooms   = con.execute("SELECT COUNT(*) FROM rooms WHERE status='in-use'").fetchone()[0]
    open_incidents = con.execute("SELECT COUNT(*) FROM incidents WHERE status='open'").fetchone()[0]

    return {
        'stats':       {'total_rooms': total_rooms, 'active_rooms': active_rooms,
                        'open_incidents': open_incidents},
        'daily':       [{'day': r[0], 'n': r[1]} for r in daily],
        'top_rooms':   [{'room_id': r[0], 'n': r[1]} for r in top_rooms],
        'top_actions': [{'action': r[0], 'n': r[1]} for r in top_actions],
    }
```

### Connector management

| Endpoint | What it does |
|---|---|
| `GET  /api/admin/connectors` | List all connectors and their current mode |
| `PUT  /api/admin/connectors/{campus}/{name}/mode` | Set mode to `live` or `mock` |
| `POST /api/admin/connectors/{campus}/{name}/test` | Test connector and return live status |

> **Credentials stay in `.env` — not in the database.** The connector management UI shows whether credentials are present (yes/no) without displaying the values. To change a credential, SSH into the server and edit `.env`.

#### PUT /api/admin/connectors/{campus_id}/{connector_name}/mode

```python
@app.put('/api/admin/connectors/{campus_id}/{connector_name}/mode')
def set_connector_mode(
    campus_id: str, connector_name: str, mode: str,
    request: Request, admin=Depends(require_admin)
):
    if mode not in ('live', 'mock'):
        raise HTTPException(400, 'mode must be live or mock')
    # Map connector names to their credential env vars
    cred_check = {
        'fusion':        bool(os.getenv('FUSION_API_KEY')),
        'live25':        bool(os.getenv('LIVE25_USERNAME')),
        'screenconnect': bool(os.getenv('SC_BASE_URL')),
        'wattbox':       bool(os.getenv('WATTBOX_OVRC_API_KEY') or os.getenv('WATTBOX_DIRECT_USERNAME')),
        'servicenow':    bool(os.getenv('SERVICENOW_CLIENT_ID')),
        'sharepoint':    bool(os.getenv('SHAREPOINT_BASE_URL')),
    }
    if mode == 'live' and not cred_check.get(connector_name, False):
        return {'status': 'warning',
                'message': 'No credentials found in .env for this connector.',
                'mode_set': False}
    con = get_db()
    con.execute('UPDATE connector_config SET mode=? WHERE campus_id=? AND connector_name=?',
                (mode, campus_id, connector_name))
    con.commit()
    con.execute('INSERT INTO audit_log(ts,user,room_id,action_type,target,outcome) VALUES(?,?,?,?,?,?)',
                (_now(), admin['preferred_username'], campus_id,
                 'admin_connector_mode_changed', f'{connector_name}={mode}', 'success'))
    con.commit()
    return {'status': 'ok', 'campus_id': campus_id, 'connector_name': connector_name, 'mode': mode}
```

### User role management

| Endpoint | What it does |
|---|---|
| `GET  /api/admin/users` | List users who have logged in, with current role and source |
| `PUT  /api/admin/users/{entra_id}` | Override a user's role |
| `DELETE /api/admin/users/{entra_id}` | Remove override (falls back to Entra group) |

---

## Part 6 — Admin Panel Pages

### Summary dashboard (`admin/index.html`)

**Sections to build:**

| Section | Content |
|---|---|
| Stat cards (top row) | Total rooms · Active rooms · Open incidents · Connectors online |
| Activity chart | Bar chart: actions per day for the past 7 days — use [Chart.js](https://www.chartjs.org/) (copy to `vendor/` — no CDN) |
| Top 5 busiest rooms | Rooms with most audit entries in last 30 days |
| Top 5 most-used tools | `action_type` counts |
| Recent activity feed | Last 20 audit entries, auto-refreshes every 60 seconds |
| Connector health grid | One badge per connector per campus |

Fetch data from `GET /api/admin/logs/summary?days=7`.

### Room and building editor (`admin/rooms.html`)

**Layout:**

```
┌─────────────────────────┬─────────────────────────────────────────┐
│  Campus tabs            │  Room list for selected building        │
│  └ Building list        │  ┌──────────────────────────────────┐   │
│    (collapsible)        │  │ Room # │ Type │ Status │ Actions │   │
│                         │  ├──────────────────────────────────┤   │
│  [ + Add building ]     │  │ 101    │ ...  │ ...    │ Edit    │   │
│                         │  │ 102    │ ...  │ ...    │ Edit    │   │
│                         │  └──────────────────────────────────┘   │
│                         │  [ + Add room ]                         │
└─────────────────────────┴─────────────────────────────────────────┘
                               Edit drawer slides in from right →
```

**Edit drawer fields:** number, type, status, health, active_event, fusion, display, screenconnect (checkbox), wattbox (checkbox), hybrid (checkbox), stale (checkbox), notes, devices table (add/remove rows).

**On save:** `PUT /api/admin/rooms/{room_id}` — response updates the row in the table without a full page reload.

**On delete:** confirm dialog → `DELETE /api/admin/rooms/{room_id}` → remove row from table.

### Log viewer (`admin/logs.html`)

**Filter bar:** campus dropdown · room ID text search · action type dropdown · user text search · date from/to pickers · Reset button

**Results table:** Timestamp · User · Campus · Room · Action · Outcome — paginated 50 per page

**Export buttons:** "Export CSV" — calls `GET /api/admin/logs/export` with current filters applied

**Archive section:**
```
Archive entries older than: [ 90 days ] [ Archive ]
⚠️  Purge archived entries: type CONFIRM to proceed [ ________ ] [ Purge ]
```

### Connector management (`admin/connectors.html`)

**Grid layout:** one row per connector, one column per campus. Each cell:
- Badge: `live` (green) / `mock` (gray) / `degraded` (amber)
- Last synced timestamp
- Toggle button (flip between live and mock)
- Test button (calls `POST /api/admin/connectors/{campus}/{name}/test`)
- Credential status: `credentials: ✓` or `credentials: missing`

**Important:** if toggling to live with no credentials, show a yellow warning banner — do not fail silently.

### User management (`admin/users.html`)

**Table:** Name · Email · Role (badge) · Role source · Last login · Edit button

**Role source column values:**
- `Azure AD group` — using group membership, no override
- `Manual override` — set directly in the `user_roles` table

**Edit role dialog:** dropdown (Technician / Admin / Read-only) + notes field + confirm button

---

## Part 7 — Security Rules

| Area | Rule |
|---|---|
| Route protection | All `/api/admin/...` routes use `Depends(require_admin)`. The JS auth check in `admin.js` is a UX convenience only — not a security boundary. |
| Audit logging | Every POST/PUT/DELETE endpoint writes to `audit_log` before returning. Admin actions use the `admin_` prefix in `action_type`. |
| Input validation | All request bodies go through Pydantic models. `room_id` values validated to match `[a-z0-9-]+` only. Text fields capped at 500 characters. |
| SQL injection | All queries use parameterised statements (`?` placeholders). Never string-format SQL. |
| Credential protection | API keys stay in `.env` (permissions `600`). Admin UI shows presence (yes/no) only. Admins who need to change credentials SSH in and edit `.env`. |
| Log deletion safety | Purge endpoint requires a `confirmation_token` that is generated server-side and expires after 60 seconds. This prevents accidental deletion via API replay. |

### Admin audit log action types

| `action_type` | What happened |
|---|---|
| `admin_room_updated` | A room's fields or device list was changed |
| `admin_room_created` | A new room was added |
| `admin_room_deleted` | A room was deleted |
| `admin_building_updated` | A building's name or code was changed |
| `admin_building_created` | A new building was added |
| `admin_building_deleted` | A building and all its rooms were deleted |
| `admin_connector_mode_changed` | A connector was toggled live or mock |
| `admin_log_archive` | Old log entries were moved to the archive table |
| `admin_log_purge` | Old log entries were permanently deleted |
| `admin_role_override_set` | A user's role was manually overridden |
| `admin_role_override_removed` | A user's manual role override was removed |

---

## Part 8 — Deployment Checklist

Run these steps on the production VM **in order**. Assumes BeaverView is already running.

### Step 1 — Back up the database

```bash
sudo -u beaverview cp /home/beaverview/app/api/beaverview.db \
    /home/beaverview/backups/beaverview-before-admin-$(date +%Y%m%d).db
```

### Step 2 — Pull updated code

```bash
cd /home/beaverview/app
sudo -u beaverview git pull
```

### Step 3 — Run the schema migration

```bash
cd /home/beaverview/app/api
sudo -u beaverview venv/bin/python3 -c "from main import init_db; init_db()"
```

Or apply the SQL directly:
```bash
sudo -u beaverview sqlite3 beaverview.db < admin_schema.sql
```

### Step 4 — Run the data migration

```bash
sudo -u beaverview venv/bin/python3 migrate_data.py
```

Confirm the row counts look right before continuing. If something looks wrong, restore the backup from Step 1.

### Step 5 — Create the admin frontend files

```bash
sudo -u beaverview mkdir -p /home/beaverview/app/dashboard/admin
```

Create `index.html`, `rooms.html`, `logs.html`, `connectors.html`, `users.html`, `admin.js`, `admin.css` in that folder.

### Step 6 — Restart BeaverView

```bash
sudo systemctl restart beaverview
sudo systemctl status beaverview   # confirm: active (running)
```

### Step 7 — Test from Windows

1. Open `https://beaverview/admin` in Chrome or Edge
2. Log in with OSU credentials
3. **If in Admins group:** summary dashboard should load
4. **If in Technicians group:** should see 403 page
5. Test room edit: go to `/admin/rooms`, click a room, change a field, save
6. Verify the change appears at `https://beaverview/`
7. Test log export: go to `/admin/logs`, click Export CSV, open in Excel

### Step 8 — Verify admin actions are logged

```bash
curl -k 'https://beaverview/api/audit?action_type=admin_room_updated'
```

Should return the edit you made in Step 7.

---

## Post-launch tasks

- [ ] Set up a cron job to auto-archive log entries older than 90 days (Part 5, archive endpoint)
- [ ] Add an **Admin** link to the main dashboard header (show only when `role === 'admin'`)
- [ ] Train admins on the room editor and log export workflow
- [ ] Consider rate-limiting `GET /api/admin/logs/export` to prevent very large downloads
- [ ] Add `Chart.js` to `dashboard/vendor/` — copy from [chartjs.org](https://www.chartjs.org/) (do not use CDN)
