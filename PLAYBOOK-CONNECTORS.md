# BeaverView — Connectors Playbook
**Audience:** IT staff / backend administrators connecting real data sources.
**Purpose:** Step-by-step guide to wire up each external system.

> Each connector is independent. Wire them one at a time.
> The dashboard runs on mock data until you add credentials — you can't break anything by
> trying. The sidebar badge changes from gray (mock) to green (ok) when a connector is live.

> **Note:** BeaverView connects directly to each Crestron control processor and AV device
> over the network. There is no dependency on Crestron Fusion or any central aggregator.

---

## How connectors work

All credentials live in `api/.env` — a file that is **never committed to Git**.
The backend reads `.env` on startup and automatically switches any connector that has valid
credentials from mock mode to live mode. No code changes needed.

```
.env file → backend reads on startup → connector badge turns green
```

**One-time setup (do this first):**
```bash
cd api
cp .env.example .env
```

Then open `api/.env` in a text editor and fill in values as you go through each section below.

After editing `.env`, restart the backend:
```bash
# Press Ctrl+C in the terminal running start.sh, then:
./start.sh
```

---

## Three credential patterns (understand these first)

### Pattern 1 — REST API
The backend calls the external service directly using a key or OAuth token.
The browser never sees the credential.
*Used by: 25Live, ServiceNow*

### Pattern 2 — Direct device / device web proxy
BeaverView talks directly to each AV device over the local network using its built-in
HTTP API. The device IP never reaches the browser — the backend either polls the device
for status (Crestron processors) or proxies requests to it (XPanel UI, WattBox, PTZ).
*Used by: Crestron processors, XPanel, WattBox (direct), PTZ cameras*

### Pattern 3 — Entra SSO passthrough
The external system already accepts OSU Azure AD / SAML login. The backend builds a
context-aware URL; the user's existing OSU browser session handles authentication.
No password stored in `.env`.
*Used by: ScreenConnect, SharePoint, ServiceNow (web UI)*

---

## Connector 1 — Crestron Direct Device (processor status + XPanel)

**What it provides:** Control processor reachability, display power state, health scores,
and in-browser XPanel control — all via direct HTTP to each processor on the local network.
**Pattern:** 2 (direct device / device web proxy)

### How it works

BeaverView polls each Crestron control processor's built-in HTTP API on a configurable
interval (default 60 seconds). The result — online/offline, display state, health score —
is written to the `rooms` table in the database and served to the dashboard.
The device IP for each room comes from the `device_ips` database table, which is populated
from your Hardware IP spreadsheet.

```
[Background poller, every 60s]
  For each room in device_ips:
    GET https://{processor_ip}/Device/DeviceInfo   (4-Series REST API)
    → update rooms table (processor status, health, last_polled)

[Frontend request]
  GET /api/campus/corvallis/crestron/rooms
  → returns last-polled values from the database
```

### Prerequisites
- Crestron admin credentials (typically the same account across all processors)
- The Hardware IP spreadsheet exported to CSV
- Python `httpx` package (add to `requirements.txt` — see Step 3)
- Network route from the BeaverView VM to the AV device VLAN

> **VLAN note:** AV devices are almost always on a separate network segment (e.g., 10.20.x.x).
> The Ubuntu VM needs a route to reach that subnet. Ask your network admin to add a static
> route, or place the VM in a VLAN that has access to both the office network and the AV VLAN.

### Crestron API compatibility

| Processor series | API type | Endpoint |
|---|---|---|
| 4-Series (CP4, MC4, VC-4) | CH5 REST API | `GET https://{ip}/Device/DeviceInfo` |
| 3-Series (CP3, MC3) | XPanel heartbeat / SIMPL | Poll `/heartbeat` or use ping as fallback |
| Virtual Control (VC-4) | CH5 REST API | Same as 4-Series |

For 3-Series processors without a REST API, the poller falls back to a TCP ping on port 41794
(the Crestron XPanel port). A successful connection means the processor is reachable.

### Step 1 — Import the Hardware IP spreadsheet

Export your Hardware IP spreadsheet to CSV (columns: `room_id`, `device_type`, `ip_address`, `notes`).
Save as `api/hardware_ips.csv`. Then run the import script:

**Save as `api/import_device_ips.py`:**
```python
"""
Import Hardware IP spreadsheet into the device_ips table.
Run:  python3 import_device_ips.py hardware_ips.csv
The CSV must have columns: room_id, device_type, ip_address, notes
"""
import csv, sqlite3, sys, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'beaverview.db')

def import_ips(csv_path: str):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS device_ips (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id     TEXT NOT NULL,
            device_type TEXT NOT NULL,   -- 'xpanel' | 'wattbox' | 'ptz' | 'display'
            ip_address  TEXT NOT NULL,
            last_seen   TEXT,            -- ISO timestamp of last successful poll
            reachable   INTEGER DEFAULT 0,
            notes       TEXT
        )
    """)
    con.execute("DELETE FROM device_ips")  # clear before re-import
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        rows = [(r['room_id'], r['device_type'], r['ip_address'], r.get('notes',''))
                for r in reader if r.get('ip_address')]
    con.executemany(
        'INSERT INTO device_ips(room_id,device_type,ip_address,notes) VALUES(?,?,?,?)', rows)
    con.commit()
    print(f"Imported {len(rows)} device IP entries.")
    con.close()

if __name__ == '__main__':
    import_ips(sys.argv[1] if len(sys.argv) > 1 else 'hardware_ips.csv')
```

Run it:
```bash
cd /home/beaverview/app/api
sudo -u beaverview venv/bin/python3 import_device_ips.py hardware_ips.csv
```

> **Security:** The `hardware_ips.csv` file must never be committed to Git. Add it to `.gitignore`.
> It contains internal network addresses. Keep it in the `api/` folder on the server only.

### Step 2 — Add credentials to .env

```
CRESTRON_POLL_USERNAME=admin
CRESTRON_POLL_PASSWORD=your-crestron-admin-password
CRESTRON_POLL_INTERVAL_SECONDS=60
CRESTRON_VERIFY_SSL=false
```

`CRESTRON_VERIFY_SSL=false` accepts the self-signed certificates that Crestron processors
ship with by default. Set to `true` if you have installed valid certificates on your processors.

Also add the XPanel proxy credentials (used when a technician opens the XPanel tool panel):
```
CRESTRON_PROXY_USERNAME=admin
CRESTRON_PROXY_PASSWORD=your-crestron-admin-password
PROXY_SECRET=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
```

### Step 3 — Add httpx to requirements.txt

```bash
echo "httpx>=0.27.0" >> requirements.txt
venv/bin/pip install httpx
```

### Step 4 — Add the background poller to main.py

Add this to `api/main.py` (inside or after the lifespan function):

```python
import asyncio
import httpx

async def poll_processor(room_id: str, ip: str, device_id: int):
    """Poll one Crestron processor and update the database."""
    verify_ssl = os.getenv("CRESTRON_VERIFY_SSL", "false").lower() != "false"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=5) as client:
            resp = await client.get(
                f"https://{ip}/Device/DeviceInfo",
                auth=(_CRESTRON_POLL_USER, _CRESTRON_POLL_PASS),
            )
            reachable = resp.status_code == 200
    except Exception:
        reachable = False

    now = _now()
    con = get_db()
    con.execute(
        "UPDATE device_ips SET last_seen=?, reachable=? WHERE id=?",
        (now, int(reachable), device_id)
    )
    # Update room processor status based on reachability
    processor_state = "online" if reachable else "offline"
    con.execute(
        "UPDATE rooms SET stale=?, updated_at=? WHERE id=?",
        (int(not reachable), now, room_id)
    )
    con.commit()
    con.close()

async def poll_all_processors():
    """Background task: poll all Crestron processors on a schedule."""
    interval = _CRESTRON_POLL_INTERVAL
    while True:
        con = get_db()
        devices = con.execute(
            "SELECT id, room_id, ip_address FROM device_ips WHERE device_type='xpanel'"
        ).fetchall()
        con.close()
        tasks = [poll_processor(d["room_id"], d["ip_address"], d["id"]) for d in devices]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(interval)

# Update the lifespan function to start the poller:
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _stamp_connectors()
    if _CRESTRON_POLL_USER and _CRESTRON_POLL_PASS:
        asyncio.create_task(poll_all_processors())
    yield
```

### Test it

```bash
# Check the connector badge in the sidebar
curl http://localhost:8000/api/campus/corvallis/connectors
# Look for "crestron": {"mode": "live", ...}

# Check processor status for all rooms
curl http://localhost:8000/api/campus/corvallis/crestron/rooms

# Check device_ips table directly
sqlite3 api/beaverview.db "SELECT room_id, ip_address, reachable, last_seen FROM device_ips LIMIT 10;"
```

---

## Connector 2 — 25Live (CollegeNET)

**What it provides:** Room schedule — what event is in each room right now.
**Pattern:** 1 (REST API with basic auth)

### Prerequisites
- A 25Live service account (not a personal account — contact CollegeNET or OSU scheduling)
- The OSU 25Live instance URL

### Steps
1. In `api/.env`, uncomment and fill in:
   ```
   LIVE25_BASE_URL=https://25live.collegenet.com/25live/data/oregonstate
   LIVE25_USERNAME=svc-beaverview@oregonstate.edu
   LIVE25_PASSWORD=your-service-account-password
   ```
2. Restart the backend.
3. The **25Live** badge in the sidebar turns green.

BeaverView includes the campus schedule endpoint:

```http
GET /api/campus/{campus_id}/schedule
```

When 25Live credentials are missing, the endpoint returns seeded mock schedule data from `rooms.active_event`. When `LIVE25_BASE_URL`, `LIVE25_USERNAME`, and `LIVE25_PASSWORD` are configured, the backend calls 25Live with server-side Basic Auth and returns the upstream schedule payload. Credentials are never returned to the browser.

Validate offline behavior:

```bash
scripts/check_api_contracts.py
```

The contract covers mock schedule output and unknown campus handling without requiring live 25Live access.

---

## Connector 3 — ScreenConnect (ConnectWise Control)

**What it provides:** Remote desktop access to lectern PCs.
**Pattern:** 3 (Entra SSO passthrough — no password stored)

### Prerequisites
- The ScreenConnect server URL for OSU (e.g., `https://screenconnect.oregonstate.edu`)
- OSU Azure AD SSO must already be configured on the ScreenConnect server (contact IT)
- Each machine must be tagged with the room ID format (e.g., `KAD-101-PC`)

### Steps
1. In `api/.env`, uncomment and fill in:
   ```
   SC_BASE_URL=https://screenconnect.oregonstate.edu
   ```
2. Restart the backend.
3. The **ScreenConnect** badge turns green.

### How it works
When a technician clicks "Launch Remote Session" in the dashboard:
1. The frontend calls `GET /api/rooms/corvallis-kad-101/launch/screenconnect`
2. The backend builds the URL: `https://screenconnect.oregonstate.edu/Host#Access/All Machines/KAD-101-PC`
3. The frontend opens that URL in a new tab
4. The technician's existing OSU Entra session handles authentication

### Machine naming convention
ScreenConnect machines must be named in the format: `{BUILDINGCODE}-{ROOM}-PC`
(uppercase). Examples: `KAD-101-PC`, `LINC-100-PC`, `MU-208-PC`

---

## Connector 4 — WattBox / OvrC

**What it provides:** Outlet power status and remote power cycling.
**Pattern:** 1 (OvrC cloud REST API) or 2 (direct device proxy)

### Option A — OvrC cloud (recommended)

**Prerequisites:** An OvrC account at my.ovrc.com with the WattBoxes registered.

1. In `api/.env`, uncomment and fill in:
   ```
   WATTBOX_OVRC_BASE_URL=https://my.ovrc.com/api/v1
   WATTBOX_OVRC_API_KEY=your-ovrc-api-key
   ```
2. Restart the backend. The **WattBox/OvrC** badge turns green.

BeaverView includes backend OvrC outlet endpoints:

```http
GET  /api/rooms/{room_id}/wattbox/outlets
POST /api/rooms/{room_id}/wattbox/outlets/{outlet_num}/cycle
```

The endpoints inject the OvrC API key server-side, never return the API key, and log outlet-cycle attempts in the audit log. `outlet_num` must be between 1 and 48.

Validate offline behavior:

```bash
scripts/check_api_contracts.py
```

The contract covers missing OvrC credentials and invalid outlet numbers without requiring live WattBox/OvrC access.

### Option B — Direct device access (no cloud)

For WattBoxes on the local network without OvrC (uses the same `device_ips` table as Crestron):
1. In `api/.env`:
   ```
   WATTBOX_DIRECT_USERNAME=admin
   WATTBOX_DIRECT_PASSWORD=your-wattbox-password
   ```
2. WattBox IPs must be in the `device_ips` table with `device_type = 'wattbox'`.
   Include them in your `hardware_ips.csv` and re-run the import script (Connector 1, Step 1).

---

## Connector 5 — Crestron XPanel (device web proxy)

**What it provides:** In-browser room control UI — source select, display on/off, volume.
**Pattern:** 2 (device web proxy)

> **Note:** XPanel credentials overlap with the Crestron Direct Device connector (Connector 1).
> If you have already set `CRESTRON_PROXY_USERNAME` and `CRESTRON_PROXY_PASSWORD` in Step 2
> of Connector 1, skip Step 1 here.

### Prerequisites
- Crestron admin credentials set in `.env` (see Connector 1, Step 2)
- `PROXY_SECRET` set in `.env` (see Connector 1, Step 2)
- Processor IPs imported into `device_ips` (see Connector 1, Step 1)

### Steps
1. Confirm in `api/.env`:
   ```
   CRESTRON_PROXY_USERNAME=admin
   CRESTRON_PROXY_PASSWORD=your-crestron-admin-password
   PROXY_SECRET=your-random-secret-here
   ```
2. Validate the proxy foundation locally:
   ```bash
   scripts/check_api_contracts.py
   ```
3. After real processor IPs are imported, open a room and launch XPanel. The browser should receive a BeaverView `/api/rooms/.../proxy/xpanel/` URL; the raw processor IP must stay server-side.
4. Use the admin connector test button, or call:
   ```bash
   curl -X POST http://localhost:8000/api/admin/connectors/corvallis/crestron/test
   ```

---

## Connector 6 — PTZ Cameras

**What it provides:** Pan, tilt, zoom, and preset recall for PTZOptics cameras.
**Pattern:** 2 (direct device HTTP CGI commands via backend proxy)

### Prerequisites
- PTZ admin credentials
- Camera IPs imported into `device_ips` with `device_type = 'ptz'` (see Connector 1, Step 1)

### Steps
1. In `api/.env`:
   ```
   PTZ_PROXY_USERNAME=admin
   PTZ_PROXY_PASSWORD=your-ptz-admin-password
   ```
2. BeaverView includes the PTZ command endpoint:

   ```http
   POST /api/rooms/{room_id}/ptz/{command}
   ```

   Supported commands: `up`, `down`, `left`, `right`, `home`, `stop`, `zoom_in`, `zoom_out`, `preset_1`, `preset_2`, `preset_3`, `preset_4`.

   The endpoint looks up the camera IP from `device_ips`, validates that it is proxyable, injects `PTZ_PROXY_USERNAME`/`PTZ_PROXY_PASSWORD` server-side, sends the PTZOptics HTTP CGI request, and writes an audit-log row. Responses never include the raw camera IP or credentials.

3. Validate offline behavior:

   ```bash
   scripts/check_api_contracts.py
   ```

   The contract covers unknown commands, missing credentials, and missing camera IP behavior without requiring a live PTZ camera.

---

## Connector 7 — ServiceNow

**What it provides:** Incident creation from room context.
**Pattern:** 1 (OAuth) for API calls + Pattern 3 (SSO) for the web UI

### Prerequisites
- ServiceNow OAuth application registered in the OSU instance
- Client ID and secret from the OAuth app record

### Steps — OAuth (for API ticket creation)
1. In `api/.env`:
   ```
   SN_INSTANCE=oregonstate.service-now.com
   SN_CLIENT_ID=your-client-id
   SN_CLIENT_SECRET=your-client-secret
   ```
2. BeaverView includes the incident creation endpoint:

   ```http
   POST /api/rooms/{room_id}/servicenow/incident
   ```

   Request body:

   ```json
   {
     "short_description": "Projector will not show HDMI",
     "description": "Room context and technician notes",
     "category": "AV Equipment",
     "urgency": "3",
     "impact": "3"
   }
   ```

   When ServiceNow credentials are missing, the endpoint returns a mock draft payload and does not create an external ticket. When `SN_INSTANCE` plus either OAuth (`SN_CLIENT_ID`/`SN_CLIENT_SECRET`) or Basic Auth (`SN_USERNAME`/`SN_PASSWORD`) are configured, the backend creates the incident server-side and returns only the incident number, sys_id, and state.

3. Validate offline behavior:

   ```bash
   scripts/check_api_contracts.py
   ```

   The contract covers mock draft creation and missing-room behavior without requiring live ServiceNow access.

### Steps — SSO web UI (for opening a pre-filled form)
No credentials needed. The launch endpoint already builds the pre-filled URL.
The technician's OSU session handles authentication when the new tab opens.

---

## Connector 8 — SharePoint

**What it provides:** Room documentation, training PDFs, troubleshooting runbooks.
**Pattern:** 3 (Entra SSO passthrough — no password)

### Prerequisites
- The SharePoint site URL
- OSU O365 account (technicians are already authenticated via their browser session)

### Steps
1. In `api/.env`:
   ```
   SHAREPOINT_BASE_URL=https://oregonstate.sharepoint.com/sites/AVSupport
   ```
2. Restart. The dashboard's SharePoint links will now point to real URLs.

### Document library structure expected
```
/sites/AVSupport/
  SitePages/Rooms/{room-id}.aspx        ← per-room page
  Shared Documents/
    Guides/
      Classroom AV Quick Guide.pdf
      Conference Room Setup.pdf
      Lecture Hall Operations.pdf
      Active Learning AV Guide.pdf
      Event AV Setup Checklist.pdf
    Runbooks/
      Troubleshooting Runbook.pdf
```

---

## Testing a connector

After restarting with new `.env` values:

1. **Check the badge** — open the dashboard and look at the Connector Health section in the sidebar. The badge should change from gray (mock) to green (ok) or amber (degraded).

2. **Check the API directly:**
   ```bash
   curl http://localhost:8000/api/campus/corvallis/connectors
   ```
   Look for `"mode": "live"` on your connector.

3. **Check the API docs** — open `http://localhost:8000/docs` for an interactive Swagger UI.

---

## Hardware IP spreadsheet CSV format

The import script (`import_device_ips.py`) expects this CSV structure:

| Column | Description | Example |
|---|---|---|
| `room_id` | BeaverView room ID | `corvallis-kad-101` |
| `device_type` | One of: `xpanel` \| `wattbox` \| `ptz` \| `display` | `xpanel` |
| `ip_address` | Device IP on the AV VLAN | `10.20.1.45` |
| `notes` | Optional — model, location, etc. | `CP4, rack left` |

One row per device. A room with both a Crestron processor and a WattBox gets two rows
(same `room_id`, different `device_type` and `ip_address`).

```csv
room_id,device_type,ip_address,notes
corvallis-kad-101,xpanel,10.20.1.45,CP4 rack
corvallis-kad-101,wattbox,10.20.1.46,WattBox 700
corvallis-kad-105,xpanel,10.20.1.47,CP4 rack
corvallis-linc-100,xpanel,10.20.2.10,CP3
corvallis-linc-100,ptz,10.20.2.11,PTZOptics 20X-SDI
```

> **Never commit this file to Git.** Add `hardware_ips.csv` to `.gitignore`.

A safe sample is committed at `docs/examples/hardware_ips.sample.csv`. Validate the sample and, if present, the real local `api/hardware_ips.csv` without changing the database:

```bash
scripts/check_hardware_ip_import.sh
```

Dry-run a specific file manually:

```bash
cd api
venv/bin/python import_device_ips.py --dry-run hardware_ips.csv
```

Only after the dry run passes, import the real secure CSV:

```bash
cd api
venv/bin/python import_device_ips.py hardware_ips.csv
```

---

## Rollback (revert to mock)

Simply remove or comment out the credentials in `.env` and restart.
The connector reverts to mock mode with no data loss.
All past audit entries in `beaverview.db` are preserved.
