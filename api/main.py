"""BeaverView API — backend proxy scaffold (Phase 4).

Run:  uvicorn main:app --reload --port 8000
Open: http://localhost:8000/
"""

import asyncio
import csv
import datetime
import io
import ipaddress
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from starlette.middleware.sessions import SessionMiddleware
    _SESSION_MIDDLEWARE_AVAILABLE = True
except ImportError:
    _SESSION_MIDDLEWARE_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).parent
DASHBOARD_DIR = BASE_DIR.parent / "dashboard"
DB_PATH = BASE_DIR / "beaverview.db"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           TEXT    NOT NULL,
            user         TEXT    NOT NULL DEFAULT 'technician',
            room_id      TEXT    NOT NULL,
            action_type  TEXT    NOT NULL,
            target       TEXT,
            outcome      TEXT    NOT NULL DEFAULT 'success',
            notes        TEXT
        );

        CREATE TABLE IF NOT EXISTS campuses (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            subtitle   TEXT,
            center_lng REAL,
            center_lat REAL,
            zoom       REAL DEFAULT 15
        );

        CREATE TABLE IF NOT EXISTS buildings (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            campus_id TEXT NOT NULL REFERENCES campuses(id),
            code      TEXT NOT NULL,
            name      TEXT NOT NULL,
            active    INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id            TEXT PRIMARY KEY,
            building_id   INTEGER NOT NULL REFERENCES buildings(id),
            number        TEXT NOT NULL,
            type          TEXT,
            status        TEXT DEFAULT 'offline',
            health        INTEGER DEFAULT 0,
            active_event  TEXT,
            processor     TEXT DEFAULT 'mock',
            display       TEXT DEFAULT 'unknown',
            screenconnect INTEGER DEFAULT 0,
            wattbox       INTEGER DEFAULT 0,
            hybrid        INTEGER DEFAULT 0,
            stale         INTEGER DEFAULT 0,
            notes         TEXT,
            updated_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS devices (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id      TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            device_type  TEXT NOT NULL,
            manufacturer TEXT,
            model        TEXT,
            connection   TEXT,
            sort_order   INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS incidents (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            ticket  TEXT NOT NULL,
            status  TEXT DEFAULT 'open'
        );

        CREATE TABLE IF NOT EXISTS connector_config (
            campus_id      TEXT NOT NULL,
            connector_name TEXT NOT NULL,
            mode           TEXT DEFAULT 'mock',
            enabled        INTEGER DEFAULT 1,
            last_synced    TEXT,
            PRIMARY KEY (campus_id, connector_name)
        );

        CREATE TABLE IF NOT EXISTS user_roles (
            entra_id     TEXT PRIMARY KEY,
            email        TEXT,
            display_name TEXT,
            role         TEXT DEFAULT 'technician',
            notes        TEXT,
            updated_at   TEXT,
            updated_by   TEXT
        );

        CREATE TABLE IF NOT EXISTS device_ips (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id     TEXT NOT NULL,
            device_type TEXT NOT NULL,
            ip_address  TEXT NOT NULL,
            last_seen   TEXT,
            reachable   INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Connector registry (mock until real credentials are provided)
# ---------------------------------------------------------------------------

CONNECTOR_REGISTRY: dict[str, dict[str, dict]] = {
    "corvallis": {
        "crestron":       {"status": "mock", "mode": "mock", "last_synced": None},
        "live25":         {"status": "mock", "mode": "mock", "last_synced": None},
        "screenconnect":  {"status": "mock", "mode": "mock", "last_synced": None},
        "wattbox":        {"status": "mock", "mode": "mock", "last_synced": None},
        "servicenow":     {"status": "mock", "mode": "mock", "last_synced": None},
    },
    "cascades": {
        "crestron":       {"status": "mock", "mode": "mock", "last_synced": None},
        "live25":         {"status": "mock", "mode": "mock", "last_synced": None},
        "screenconnect":  {"status": "mock", "mode": "mock", "last_synced": None},
        "wattbox":        {"status": "mock", "mode": "mock", "last_synced": None},
        "servicenow":     {"status": "mock", "mode": "mock", "last_synced": None},
    },
    "hatfield": {
        "crestron":       {"status": "mock", "mode": "mock", "last_synced": None},
        "live25":         {"status": "mock", "mode": "mock", "last_synced": None},
        "screenconnect":  {"status": "mock", "mode": "mock", "last_synced": None},
        "wattbox":        {"status": "mock", "mode": "mock", "last_synced": None},
        "servicenow":     {"status": "mock", "mode": "mock", "last_synced": None},
    },
}

# ---------------------------------------------------------------------------
# Connector auto-detection
# Each block checks whether the required env vars are present.
# When they are, the connector flips from "mock" → "live" automatically.
# Nothing in the frontend needs to change — the sidebar badge updates itself.
# ---------------------------------------------------------------------------

# Pattern 2 — Crestron direct device polling
# Credentials are the same admin account shared across all processors.
# Device IPs come from the device_ips table in beaverview.db.
_CRESTRON_POLL_USER = os.getenv("CRESTRON_POLL_USERNAME", "")
_CRESTRON_POLL_PASS = os.getenv("CRESTRON_POLL_PASSWORD", "")
_CRESTRON_POLL_INTERVAL = int(os.getenv("CRESTRON_POLL_INTERVAL_SECONDS", "60"))
if _CRESTRON_POLL_USER and _CRESTRON_POLL_PASS:
    for campus in CONNECTOR_REGISTRY.values():
        campus["crestron"]["mode"] = "live"

# Pattern 1 — 25Live REST API
_LIVE25_URL  = os.getenv("LIVE25_BASE_URL", "")
_LIVE25_USER = os.getenv("LIVE25_USERNAME", "")
_LIVE25_PASS = os.getenv("LIVE25_PASSWORD", "")
if _LIVE25_URL and _LIVE25_USER and _LIVE25_PASS:
    for campus in CONNECTOR_REGISTRY.values():
        campus["live25"]["mode"] = "live"

# Pattern 3 — ScreenConnect (Entra SSO passthrough, just needs base URL)
_SC_URL = os.getenv("SC_BASE_URL", "")
if _SC_URL:
    for campus in CONNECTOR_REGISTRY.values():
        campus["screenconnect"]["mode"] = "live"

# Pattern 1+2 — WattBox / OvrC
_WATTBOX_URL = os.getenv("WATTBOX_OVRC_BASE_URL", "")
_WATTBOX_KEY = os.getenv("WATTBOX_OVRC_API_KEY", "")
_WATTBOX_DIRECT_USER = os.getenv("WATTBOX_DIRECT_USERNAME", "")
_WATTBOX_DIRECT_PASS = os.getenv("WATTBOX_DIRECT_PASSWORD", "")
if _WATTBOX_URL and _WATTBOX_KEY:
    for campus in CONNECTOR_REGISTRY.values():
        campus["wattbox"]["mode"] = "live"

# Pattern 1 — ServiceNow OAuth
_SN_INSTANCE = os.getenv("SN_INSTANCE") or os.getenv("SERVICENOW_INSTANCE", "")
_SN_CLIENT   = os.getenv("SN_CLIENT_ID") or os.getenv("SERVICENOW_CLIENT_ID", "")
_SN_SECRET   = os.getenv("SN_CLIENT_SECRET") or os.getenv("SERVICENOW_CLIENT_SECRET", "")
if _SN_INSTANCE and _SN_CLIENT and _SN_SECRET:
    for campus in CONNECTOR_REGISTRY.values():
        campus["servicenow"]["mode"] = "live"

# Pattern 3 — SharePoint (Entra passthrough, just needs base URL)
_SP_URL = os.getenv("SHAREPOINT_BASE_URL", "")

# Pattern 2 — Crestron XPanel proxy
_CRESTRON_USER = os.getenv("CRESTRON_PROXY_USERNAME", "")
_CRESTRON_PASS = os.getenv("CRESTRON_PROXY_PASSWORD", "")

# Pattern 2 — PTZ camera proxy
_PTZ_USER = os.getenv("PTZ_PROXY_USERNAME", "")
_PTZ_PASS = os.getenv("PTZ_PROXY_PASSWORD", "")

_ALLOW_PUBLIC_DEVICE_PROXY = os.getenv("DEVICE_PROXY_ALLOW_PUBLIC", "").lower() in ("1", "true", "yes")


def _now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _stamp_connectors() -> None:
    """Give every connector a last_synced timestamp on startup."""
    ts = _now()
    for campus in CONNECTOR_REGISTRY.values():
        for connector in campus.values():
            if connector["last_synced"] is None:
                connector["last_synced"] = ts


def _device_proxy_config(tool: str) -> dict:
    """Return backend-only proxy settings for supported device web tools."""
    configs = {
        "xpanel": {
            "device_type": "xpanel",
            "username": _CRESTRON_USER,
            "password": _CRESTRON_PASS,
            "scheme": os.getenv("CRESTRON_PROXY_SCHEME", "http"),
        },
        "wattbox": {
            "device_type": "wattbox",
            "username": _WATTBOX_DIRECT_USER,
            "password": _WATTBOX_DIRECT_PASS,
            "scheme": os.getenv("WATTBOX_PROXY_SCHEME", "http"),
        },
        "ptz": {
            "device_type": "ptz",
            "username": _PTZ_USER,
            "password": _PTZ_PASS,
            "scheme": os.getenv("PTZ_PROXY_SCHEME", "http"),
        },
    }
    if tool not in configs:
        raise HTTPException(status_code=404, detail=f"Unknown proxy tool '{tool}'")
    return configs[tool]


def _lookup_device_ip(room_id: str, device_type: str) -> str:
    con = get_db()
    row = con.execute(
        "SELECT ip_address FROM device_ips WHERE room_id=? AND device_type=?",
        (room_id, device_type),
    ).fetchone()
    con.close()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No {device_type} IP on record for {room_id}. Import hardware_ips.csv first.",
        )
    return row["ip_address"]


def _validate_proxy_ip(ip_address: str) -> str:
    try:
        parsed = ipaddress.ip_address(ip_address)
    except ValueError:
        raise HTTPException(status_code=400, detail="Stored device IP is invalid")

    if parsed.is_loopback or parsed.is_unspecified or parsed.is_multicast:
        raise HTTPException(status_code=400, detail="Stored device IP is not proxyable")

    if not _ALLOW_PUBLIC_DEVICE_PROXY and not (parsed.is_private or parsed.is_link_local):
        raise HTTPException(
            status_code=400,
            detail="Stored device IP is not private/link-local; set DEVICE_PROXY_ALLOW_PUBLIC=true only after review.",
        )

    return str(parsed)


def _proxy_auth(tool: str, config: dict):
    if not config["username"] or not config["password"]:
        raise HTTPException(
            status_code=400,
            detail=f"{tool} proxy credentials are not configured in api/.env",
        )
    return (config["username"], config["password"])


def _servicenow_base_url(instance: str) -> str:
    if not instance:
        return ""
    cleaned = instance.removeprefix("https://").removeprefix("http://").strip("/")
    if "." not in cleaned:
        cleaned = f"{cleaned}.service-now.com"
    return f"https://{cleaned}"


# ---------------------------------------------------------------------------
# Mock Crestron direct-device connector
# ---------------------------------------------------------------------------

def crestron_processor_status_mock(campus_id: str) -> list[dict]:
    """Return mock processor status for all rooms on a campus.

    In live mode this is replaced by background polling of each processor's
    HTTP API (see /api/campus/{id}/crestron/poll and the poll_all_processors
    background task).  The device IPs come from the device_ips table.
    """
    from data_mock import MOCK_ROOMS
    return [
        {
            "room_id":        room["room_id"],
            "processor":      room.get("processor", "online"),
            "display_power":  room.get("display", "unknown"),
            "health_score":   room.get("health", 90),
            "stale_data":     room.get("stale", False),
            "last_polled":    _now(),
        }
        for room in MOCK_ROOMS
        if room["campus"] == campus_id
    ]


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

async def _poll_single_processor(
    httpx_client,
    semaphore: asyncio.Semaphore,
    room_id: str,
    ip: str,
    now: str,
) -> None:
    """Poll one Crestron processor and update the rooms table."""
    async with semaphore:
        try:
            resp = await httpx_client.get(
                f"http://{ip}/Device/DeviceInfo",
                auth=(_CRESTRON_POLL_USER, _CRESTRON_POLL_PASS),
                timeout=5.0,
            )
            reachable = resp.status_code < 400
        except Exception:
            reachable = False

        con = get_db()
        con.execute(
            "UPDATE rooms SET processor=?, stale=?, updated_at=? WHERE id=?",
            ("online" if reachable else "offline", 0 if reachable else 1, now, room_id),
        )
        con.execute(
            "UPDATE device_ips SET last_seen=?, reachable=?"
            " WHERE room_id=? AND device_type='xpanel'",
            (now, 1 if reachable else 0, room_id),
        )
        con.commit()
        con.close()


async def poll_all_processors() -> None:
    """Background task: polls all Crestron processors every CRESTRON_POLL_INTERVAL_SECONDS."""
    # Cap concurrent connections to avoid hammering AV network
    semaphore = asyncio.Semaphore(20)

    try:
        import httpx
    except ImportError:
        print("[poller] httpx not installed — Crestron polling disabled. pip install httpx")
        return

    while True:
        if not (_CRESTRON_POLL_USER and _CRESTRON_POLL_PASS):
            await asyncio.sleep(_CRESTRON_POLL_INTERVAL)
            continue

        now = _now()
        con = get_db()
        ips = con.execute(
            "SELECT room_id, ip_address FROM device_ips WHERE device_type='xpanel'"
        ).fetchall()
        con.close()

        if ips:
            async with httpx.AsyncClient() as client:
                tasks = [
                    _poll_single_processor(client, semaphore, row[0], row[1], now)
                    for row in ips
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
            # Update connector registry last_synced
            for campus in CONNECTOR_REGISTRY.values():
                if "crestron" in campus:
                    campus["crestron"]["last_synced"] = now

        await asyncio.sleep(_CRESTRON_POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _stamp_connectors()
    # Start background Crestron poller (only runs if credentials are present)
    poller_task = asyncio.create_task(poll_all_processors())
    yield
    # Graceful shutdown
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="BeaverView API", version="0.4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

if _SESSION_MIDDLEWARE_AVAILABLE:
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET_KEY", "change-me-in-production"),
        session_cookie="beaverview_session",
        https_only=os.getenv("SESSION_HTTPS_ONLY", "true").lower() == "true",
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' blob:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data: https://tile.openstreetmap.org; "
        "connect-src 'self' https://tile.openstreetmap.org https://demotiles.maplibre.org; "
        "worker-src blob:; "
        "frame-ancestors 'none';"
    )
    return response


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def require_admin(request: Request):
    """Dependency for all /api/admin/... routes. Raises 401/403 if not an admin."""
    session = getattr(request, 'session', {})
    user = session.get('user')
    if not user:
        raise HTTPException(401, 'Not authenticated')
    groups = user.get('groups', [])
    admin_group = os.getenv('AZURE_GROUP_ADMIN', '')
    if admin_group and admin_group not in groups:
        raise HTTPException(403, 'Admin access required')
    return user


def resolve_role(entra_id: str, entra_groups: list) -> str:
    """Manual override → Azure AD group → readonly fallback."""
    con = get_db()
    row = con.execute('SELECT role FROM user_roles WHERE entra_id=?', (entra_id,)).fetchone()
    con.close()
    if row:
        return row[0]
    admin_gid = os.getenv('AZURE_GROUP_ADMIN', '')
    tech_gid  = os.getenv('AZURE_GROUP_TECHNICIAN', '')
    if admin_gid and admin_gid in entra_groups:
        return 'admin'
    if tech_gid and tech_gid in entra_groups:
        return 'technician'
    return 'readonly'


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ActionRequest(BaseModel):
    action_type: str
    target: str | None = None
    outcome: str = "success"
    notes: str | None = None


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    room_id: str | None = None
    history: list[ChatMessage] | None = None


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def api_health():
    return {"status": "ok", "ts": _now(), "version": "0.4.0"}


@app.get("/api/campus/{campus_id}/connectors")
def campus_connectors(campus_id: str):
    if campus_id not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Campus '{campus_id}' not found")
    return {
        "campus_id": campus_id,
        "connectors": CONNECTOR_REGISTRY[campus_id],
        "ts": _now(),
    }


@app.get("/api/campus/{campus_id}/crestron/rooms")
def crestron_rooms(campus_id: str):
    """Processor status for all rooms on a campus.

    Mock mode: returns data from MOCK_ROOMS.
    Live mode: returns last-polled values from the rooms table in the database.
               The background poller (poll_all_processors) updates these values
               every CRESTRON_POLL_INTERVAL_SECONDS seconds.
    """
    if campus_id not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Campus '{campus_id}' not found")
    mode = CONNECTOR_REGISTRY[campus_id]["crestron"]["mode"]
    if mode == "live":
        # Return last-polled values from DB
        con = get_db()
        rows = con.execute(
            "SELECT r.id, r.status, r.health, r.stale, r.updated_at,"
            "  d.ip_address, d.last_seen, d.reachable"
            " FROM rooms r"
            " LEFT JOIN device_ips d ON d.room_id = r.id AND d.device_type = 'xpanel'"
            " WHERE r.id LIKE ?",
            (f"{campus_id}-%",)
        ).fetchall()
        data = [dict(row) for row in rows]
    else:
        data = crestron_processor_status_mock(campus_id)
    CONNECTOR_REGISTRY[campus_id]["crestron"]["last_synced"] = _now()
    return {"campus_id": campus_id, "mode": mode, "rooms": data, "ts": _now()}


@app.get("/api/rooms/{room_id}/launch/{tool}")
def room_launch(room_id: str, tool: str, request: Request):
    """Return the URL a tool panel should open for a given room + tool.

    In mock mode: returns a placeholder explanation.
    In live mode: returns a real URL (or a proxied path for device UIs).

    The browser opens whatever URL this returns in a new tab.
    Device IPs never appear in the response — they stay on the backend.

    Tools:
        screenconnect — builds a ScreenConnect session URL for the room's PC
        sharepoint    — builds a SharePoint document library URL by room type
        servicenow    — builds a ServiceNow pre-filled incident URL
        xpanel        — returns the backend proxy path for the CP's XPanel UI
        wattbox       — returns the backend proxy path for the WattBox outlet page
        ptz           — returns the backend proxy path for the PTZ camera UI
    """
    # Parse room_id: "{campus}-{building_code}-{room_number}"
    # e.g. "corvallis-kad-101"
    parts = room_id.split("-", 2)
    campus = parts[0] if len(parts) > 0 else "unknown"

    # ── Pattern 3 — SSO passthrough tools ──────────────────────────────────
    if tool == "screenconnect":
        if _SC_URL:
            machine = room_id.replace("-", "").upper() + "-PC"
            url = f"{_SC_URL}/Host#Access/All%20Machines/{machine}"
        else:
            url = None
        return {
            "tool": tool, "room_id": room_id,
            "mode": "live" if _SC_URL else "mock",
            "url": url,
            "note": "Opens ScreenConnect filtered to this room's machine. OSU Entra SSO handles auth.",
        }

    if tool == "sharepoint":
        base = _SP_URL or "https://oregonstate.sharepoint.com/sites/AVSupport"
        url = f"{base}/SitePages/Rooms/{room_id}.aspx"
        return {
            "tool": tool, "room_id": room_id,
            "mode": "live" if _SP_URL else "mock",
            "url": url,
            "note": "Opens the SharePoint documentation page for this room. OSU O365 session handles auth.",
        }

    if tool == "servicenow":
        if _SN_INSTANCE and _SN_CLIENT:
            # Real: open SN with pre-filled fields in the URL
            desc = f"AV issue in room {room_id}"
            base_url = _servicenow_base_url(_SN_INSTANCE)
            url = (
                f"{base_url}/nav_to.do?"
                f"uri=incident.do?sys_id=-1"
                f"%26sysparm_query=short_description={desc}"
            )
        else:
            url = None
        return {
            "tool": tool, "room_id": room_id,
            "mode": "live" if (_SN_INSTANCE and _SN_CLIENT) else "mock",
            "url": url,
            "note": "Opens a pre-filled ServiceNow incident. OSU SSO handles auth.",
        }

    # ── Pattern 2 — device web proxy tools ─────────────────────────────────
    # In production: the proxy endpoints below forward requests to the device IP.
    # The device IP is looked up from the Hardware IP database, never sent to the browser.
    if tool in ("xpanel", "wattbox", "ptz"):
        proxy_path = f"/api/rooms/{room_id}/proxy/{tool}/"
        mode = "mock"
        if tool == "xpanel"  and _CRESTRON_USER: mode = "live"
        if tool == "wattbox" and _WATTBOX_DIRECT_USER: mode = "live"
        if tool == "ptz"     and _PTZ_USER:      mode = "live"
        return {
            "tool": tool, "room_id": room_id,
            "mode": mode,
            "url": proxy_path if mode == "live" else None,
            "note": f"Device web UI proxied through the backend. The device IP stays server-side.",
        }

    raise HTTPException(status_code=404, detail=f"Unknown tool '{tool}'")


@app.get("/api/rooms/{room_id}/proxy/{tool}/{path:path}")
async def device_proxy(room_id: str, tool: str, path: str, request: Request):
    """Reverse-proxy a device's web UI to the browser.

    Pattern 2 — device IP is looked up from the Hardware IP database.
    Credentials are injected server-side. Browser never sees the IP or password.
    """
    if request.method != "GET":
        raise HTTPException(status_code=405, detail="Device proxy supports GET only")

    config = _device_proxy_config(tool)
    device_ip = _validate_proxy_ip(_lookup_device_ip(room_id, config["device_type"]))
    auth = _proxy_auth(tool, config)
    scheme = config["scheme"].lower()
    if scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail=f"Invalid proxy scheme for {tool}")

    quoted_path = quote(path or "", safe="/:@!$&'()*+,;=-._~")
    query = request.url.query
    target_url = f"{scheme}://{device_ip}/{quoted_path}"
    if query:
        target_url = f"{target_url}?{query}"

    try:
        import httpx
    except ImportError:
        raise HTTPException(status_code=500, detail="httpx is not installed in the API environment")

    forwarded_for = request.client.host if request.client else ""
    headers = {
        "Accept": request.headers.get("accept", "*/*"),
        "User-Agent": "BeaverViewDeviceProxy/1.0",
    }
    if forwarded_for:
        headers["X-Forwarded-For"] = forwarded_for

    try:
        async with httpx.AsyncClient(verify=False, follow_redirects=False, timeout=10.0) as client:
            upstream = await client.get(target_url, auth=auth, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"{tool} device proxy timed out")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"{tool} device proxy failed: {str(exc)[:120]}")

    content_type = upstream.headers.get("content-type", "application/octet-stream")
    response_headers = {"Cache-Control": "no-store"}
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=content_type,
        headers=response_headers,
    )


@app.post("/api/rooms/{room_id}/action")
def room_action(room_id: str, body: ActionRequest, request: Request):
    user = request.headers.get("X-User", "technician")
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (ts, user, room_id, action_type, target, outcome, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (_now(), user, room_id, body.action_type, body.target, body.outcome, body.notes),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "room_id": room_id, "action_type": body.action_type, "ts": _now()}


@app.get("/api/rooms/{room_id}/log")
def room_log(room_id: str, limit: int = 50):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE room_id = ? ORDER BY ts DESC LIMIT ?",
        (room_id, limit),
    ).fetchall()
    conn.close()
    return {"room_id": room_id, "events": [dict(r) for r in rows]}


# ServiceNow incidents endpoint
@app.get("/api/rooms/{room_id}/incidents")
async def room_incidents(room_id: str, request: Request = None):
    """
    Fetch incidents for a room from ServiceNow.
    FERPA-safe: returns only incident number, short description, state.
    Falls back to mock data if ServiceNow unavailable.
    """
    from connectors.servicenow import get_incidents_for_room

    # Get room details for ServiceNow query
    conn = get_db()
    room = conn.execute("SELECT id, number, building_id FROM rooms WHERE id = ?", (room_id,)).fetchone()
    building = None
    if room:
        building = conn.execute("SELECT code, name FROM buildings WHERE id = ?", (room[2],)).fetchone()
    conn.close()

    if not room or not building:
        return {"room_id": room_id, "incidents": []}

    # Query ServiceNow for incidents
    room_code = f"{building[0]} {room[1]}"  # "KA 101"
    building_name = building[1]             # "Kerr Hall"

    incidents = await get_incidents_for_room(
        room_id=room_id,
        room_code=room_code,
        building_name=building_name,
        instance=os.getenv("SN_INSTANCE"),
        mode="live" if os.getenv("SN_INSTANCE") else "mock"
    )

    return {
        "room_id": room_id,
        "incidents": [
            {
                "number": i.number,
                "short_description": i.short_description,
                "state": i.state,
                "sys_id": i.sys_id,
                "opened_at": i.opened_at
            }
            for i in incidents
        ]
    }


@app.get("/api/connectors/servicenow/test")
async def test_servicenow():
    """Health check for ServiceNow connector."""
    from connectors.servicenow import test_servicenow_connection

    result = await test_servicenow_connection(os.getenv("SN_INSTANCE") or "")
    return result


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Chat with Hermes (DGX Spark local LLM).

    Request: {message, room_id (optional), history (optional)}
    Response: {reply, model, tokens_used, timestamp}

    FERPA-safe: context includes room/devices/incidents only, never PII.
    System prompt is hardcoded and not overridable.
    """
    from connectors.chat import chat_with_hermes

    conn = get_db()
    try:
        response = await chat_with_hermes(
            message=req.message,
            room_id=req.room_id,
            conversation_history=[msg.dict() for msg in (req.history or [])],
            db=conn
        )
        return response
    finally:
        conn.close()


@app.get("/api/connectors/chat/test")
async def test_chat():
    """Health check for chat/Hermes connector."""
    from connectors.chat import test_chat_connection

    result = await test_chat_connection()
    return result


@app.get("/api/audit")
def audit_log(
    limit: int = 200,
    campus: str | None = None,
    user: str | None = None,
    action_type: str | None = None,
):
    conn = get_db()
    query = "SELECT * FROM audit_log WHERE 1=1"
    params: list = []
    if campus:
        query += " AND room_id LIKE ?"
        params.append(f"{campus}-%")
    if user:
        query += " AND user = ?"
        params.append(user)
    if action_type:
        query += " AND action_type = ?"
        params.append(action_type)
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {"events": [dict(r) for r in rows], "count": len(rows)}


# ---------------------------------------------------------------------------
# Entra SSO (MSAL) — auth flow
# ---------------------------------------------------------------------------

_AZURE_TENANT   = os.getenv("AZURE_TENANT_ID", "")
_AZURE_CLIENT   = os.getenv("AZURE_CLIENT_ID", "")
_AZURE_SECRET   = os.getenv("AZURE_CLIENT_SECRET", "")
_AZURE_REDIRECT = os.getenv("AZURE_REDIRECT_URI", "https://beaverview/auth/callback")

def _get_msal_app():
    try:
        import msal
        return msal.ConfidentialClientApplication(
            _AZURE_CLIENT,
            authority=f"https://login.microsoftonline.com/{_AZURE_TENANT}",
            client_credential=_AZURE_SECRET,
        )
    except ImportError:
        return None


@app.get("/auth/login")
def auth_login(request: Request, next: str = "/admin/"):
    """Redirect browser to Microsoft login page."""
    msal_app = _get_msal_app()
    if not msal_app or not (_AZURE_TENANT and _AZURE_CLIENT):
        raise HTTPException(503, "Entra SSO not configured. Set AZURE_TENANT_ID, "
                                 "AZURE_CLIENT_ID, AZURE_CLIENT_SECRET in .env")
    from fastapi.responses import RedirectResponse
    session = request.session
    session["auth_state"] = os.urandom(16).hex()
    session["auth_next"]  = next
    flow = msal_app.initiate_auth_code_flow(
        scopes=["openid", "profile", "email",
                "https://graph.microsoft.com/GroupMember.Read.All"],
        redirect_uri=_AZURE_REDIRECT,
        state=session["auth_state"],
    )
    session["auth_flow"] = flow
    return RedirectResponse(flow["auth_uri"])


@app.get("/auth/callback")
def auth_callback(request: Request):
    """Microsoft redirects here after login. Exchange code for token."""
    from fastapi.responses import RedirectResponse
    msal_app = _get_msal_app()
    if not msal_app:
        raise HTTPException(503, "MSAL not available")
    session  = request.session
    flow     = session.get("auth_flow", {})
    next_url = session.pop("auth_next", "/admin/")
    try:
        result = msal_app.acquire_token_by_auth_code_flow(
            flow, dict(request.query_params)
        )
    except Exception as exc:
        raise HTTPException(400, f"Auth callback error: {exc}")

    if "error" in result:
        raise HTTPException(401, result.get("error_description", result["error"]))

    claims = result.get("id_token_claims", {})
    # Fetch group memberships from Graph API
    groups = []
    access_token = result.get("access_token", "")
    if access_token:
        try:
            import httpx as _httpx
            r = _httpx.get(
                "https://graph.microsoft.com/v1.0/me/memberOf?$select=id",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
            if r.status_code == 200:
                groups = [g.get("id","") for g in r.json().get("value", [])]
        except Exception:
            pass  # groups stays empty — user gets readonly role

    user = {
        "oid":                  claims.get("oid", ""),
        "preferred_username":   claims.get("preferred_username", ""),
        "name":                 claims.get("name", ""),
        "email":                claims.get("email", claims.get("upn", "")),
        "groups":               groups,
    }
    session["user"] = user

    # Upsert into user_roles so admins can see everyone who has logged in
    try:
        con = get_db()
        con.execute(
            "INSERT INTO user_roles(entra_id,email,display_name,updated_at)"
            " VALUES(?,?,?,?)"
            " ON CONFLICT(entra_id) DO UPDATE SET email=excluded.email,"
            "   display_name=excluded.display_name, updated_at=excluded.updated_at",
            (user["oid"], user["email"], user["name"], _now())
        )
        con.commit()
        con.close()
    except Exception:
        pass

    return RedirectResponse(next_url)


@app.get("/auth/logout")
def auth_logout(request: Request):
    from fastapi.responses import RedirectResponse
    request.session.clear()
    # Redirect to Microsoft logout
    if _AZURE_TENANT:
        return RedirectResponse(
            f"https://login.microsoftonline.com/{_AZURE_TENANT}/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri=https://beaverview/"
        )
    return RedirectResponse("/")


# ---------------------------------------------------------------------------
# Auth / session endpoints
# ---------------------------------------------------------------------------

@app.get('/api/me')
def me(request: Request):
    user = None
    if _SESSION_MIDDLEWARE_AVAILABLE:
        try:
            user = request.session.get('user')
        except (AssertionError, KeyError):
            pass
    if not user:
        # Dev bypass: when SSO is not configured (no AZURE_CLIENT_ID) AND
        # the request comes from localhost, return a local admin session.
        # This auto-disables in production once AZURE_CLIENT_ID is set in .env.
        client_host = (request.client.host if request.client else "") or ""
        if not _AZURE_CLIENT and client_host in ("127.0.0.1", "::1", "localhost"):
            return {
                'user':  'dev@localhost',
                'name':  'Dev Admin (localhost)',
                'role':  'admin',
                '_dev':  True,
            }
        raise HTTPException(401, 'Not authenticated')
    role = resolve_role(user.get('oid', ''), user.get('groups', []))
    return {
        'user': user.get('preferred_username'),
        'name': user.get('name'),
        'role': role,
    }


# ---------------------------------------------------------------------------
# Admin Pydantic models
# ---------------------------------------------------------------------------

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
    processor:     str = 'mock'
    display:       str = 'unknown'
    screenconnect: bool = False
    wattbox:       bool = False
    hybrid:        bool = False
    stale:         bool = False
    notes:         Optional[str] = ''
    devices:       List[DeviceIn] = []


class BuildingIn(BaseModel):
    campus_id: str
    code:      str
    name:      str


class UserRoleIn(BaseModel):
    role:  str   # 'technician' | 'admin' | 'readonly'
    notes: Optional[str] = ''


# ---------------------------------------------------------------------------
# Admin API — campuses
# ---------------------------------------------------------------------------

@app.get('/api/admin/campuses')
def admin_campuses(admin=Depends(require_admin)):
    con = get_db()
    rows = con.execute('''
        SELECT c.id, c.name, c.subtitle,
               COUNT(DISTINCT b.id) AS building_count,
               COUNT(DISTINCT r.id) AS room_count
        FROM campuses c
        LEFT JOIN buildings b ON b.campus_id = c.id
        LEFT JOIN rooms r ON r.building_id = b.id
        GROUP BY c.id
    ''').fetchall()
    con.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Admin API — buildings
# ---------------------------------------------------------------------------

@app.get('/api/admin/buildings')
def admin_buildings(campus_id: Optional[str] = None, admin=Depends(require_admin)):
    con = get_db()
    if campus_id:
        rows = con.execute(
            'SELECT b.*, COUNT(r.id) AS room_count FROM buildings b'
            ' LEFT JOIN rooms r ON r.building_id = b.id'
            ' WHERE b.campus_id=? GROUP BY b.id ORDER BY b.code',
            (campus_id,)
        ).fetchall()
    else:
        rows = con.execute(
            'SELECT b.*, COUNT(r.id) AS room_count FROM buildings b'
            ' LEFT JOIN rooms r ON r.building_id = b.id'
            ' GROUP BY b.id ORDER BY b.campus_id, b.code'
        ).fetchall()
    con.close()
    return [dict(r) for r in rows]


@app.post('/api/admin/buildings')
def admin_create_building(body: BuildingIn, admin=Depends(require_admin)):
    con = get_db()
    cur = con.execute(
        'INSERT INTO buildings(campus_id,code,name) VALUES(?,?,?) RETURNING id',
        (body.campus_id, body.code.upper(), body.name)
    )
    bldg_id = cur.fetchone()[0]
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,target,outcome) VALUES(?,?,?,?,?,?)',
        (_now(), admin.get('preferred_username','admin'), body.campus_id,
         'admin_building_created', f'{body.code}:{body.name}', 'success')
    )
    con.commit()
    con.close()
    return {'status': 'ok', 'building_id': bldg_id}


@app.put('/api/admin/buildings/{building_id}')
def admin_update_building(building_id: int, body: BuildingIn, admin=Depends(require_admin)):
    con = get_db()
    con.execute(
        'UPDATE buildings SET code=?,name=? WHERE id=?',
        (body.code.upper(), body.name, building_id)
    )
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,target,outcome) VALUES(?,?,?,?,?,?)',
        (_now(), admin.get('preferred_username','admin'), str(building_id),
         'admin_building_updated', f'{body.code}:{body.name}', 'success')
    )
    con.commit()
    con.close()
    return {'status': 'ok', 'building_id': building_id}


@app.delete('/api/admin/buildings/{building_id}')
def admin_delete_building(building_id: int, admin=Depends(require_admin)):
    con = get_db()
    con.execute('PRAGMA foreign_keys = ON')
    row = con.execute('SELECT code FROM buildings WHERE id=?', (building_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Building not found')
    con.execute('DELETE FROM buildings WHERE id=?', (building_id,))
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,target,outcome) VALUES(?,?,?,?,?,?)',
        (_now(), admin.get('preferred_username','admin'), str(building_id),
         'admin_building_deleted', row[0], 'success')
    )
    con.commit()
    con.close()
    return {'status': 'ok'}


# ---------------------------------------------------------------------------
# Admin API — rooms
# ---------------------------------------------------------------------------

@app.get('/api/admin/rooms')
def admin_rooms(building_id: Optional[int] = None, admin=Depends(require_admin)):
    con = get_db()
    if building_id:
        rooms = con.execute(
            'SELECT * FROM rooms WHERE building_id=? ORDER BY number', (building_id,)
        ).fetchall()
    else:
        rooms = con.execute('SELECT * FROM rooms ORDER BY id').fetchall()
    result = []
    for room in rooms:
        rd = dict(room)
        rd['devices'] = [dict(d) for d in con.execute(
            'SELECT * FROM devices WHERE room_id=? ORDER BY sort_order', (room['id'],)
        ).fetchall()]
        result.append(rd)
    con.close()
    return result


@app.post('/api/admin/rooms')
def admin_create_room(body: RoomIn, building_id: int, admin=Depends(require_admin)):
    con = get_db()
    bldg = con.execute(
        'SELECT b.campus_id, b.code FROM buildings b WHERE b.id=?', (building_id,)
    ).fetchone()
    if not bldg:
        raise HTTPException(404, 'Building not found')
    raw_id = f"{bldg['campus_id']}-{bldg['code'].lower()}-{body.number}".lower()
    room_id = re.sub(r'[^a-z0-9]+', '-', raw_id).strip('-')
    now = _now()
    con.execute(
        'INSERT INTO rooms(id,building_id,number,type,status,health,active_event,'
        '  processor,display,screenconnect,wattbox,hybrid,stale,notes,updated_at)'
        ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (room_id, building_id, body.number, body.type, body.status, body.health,
         body.active_event, body.processor, body.display,
         int(body.screenconnect), int(body.wattbox), int(body.hybrid),
         int(body.stale), body.notes, now)
    )
    for i, dev in enumerate(body.devices):
        con.execute(
            'INSERT INTO devices(room_id,device_type,manufacturer,model,connection,sort_order)'
            ' VALUES(?,?,?,?,?,?)',
            (room_id, dev.device_type, dev.manufacturer, dev.model, dev.connection, i)
        )
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,outcome) VALUES(?,?,?,?,?)',
        (now, admin.get('preferred_username','admin'), room_id, 'admin_room_created', 'success')
    )
    con.commit()
    con.close()
    return {'status': 'ok', 'room_id': room_id}


@app.put('/api/admin/rooms/{room_id}')
def admin_update_room(room_id: str, body: RoomIn, admin=Depends(require_admin)):
    if not re.match(r'^[a-z0-9-]+$', room_id):
        raise HTTPException(400, 'Invalid room_id format')
    con = get_db()
    now = _now()
    con.execute(
        'UPDATE rooms SET number=?,type=?,status=?,health=?,active_event=?,'
        '  processor=?,display=?,screenconnect=?,wattbox=?,hybrid=?,stale=?,'
        '  notes=?,updated_at=? WHERE id=?',
        (body.number, body.type, body.status, body.health, body.active_event,
         body.processor, body.display,
         int(body.screenconnect), int(body.wattbox), int(body.hybrid),
         int(body.stale), body.notes, now, room_id)
    )
    con.execute('DELETE FROM devices WHERE room_id=?', (room_id,))
    for i, dev in enumerate(body.devices):
        con.execute(
            'INSERT INTO devices(room_id,device_type,manufacturer,model,connection,sort_order)'
            ' VALUES(?,?,?,?,?,?)',
            (room_id, dev.device_type, dev.manufacturer, dev.model, dev.connection, i)
        )
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,outcome) VALUES(?,?,?,?,?)',
        (now, admin.get('preferred_username','admin'), room_id, 'admin_room_updated', 'success')
    )
    con.commit()
    con.close()
    return {'status': 'ok', 'room_id': room_id}


@app.delete('/api/admin/rooms/{room_id}')
def admin_delete_room(room_id: str, admin=Depends(require_admin)):
    if not re.match(r'^[a-z0-9-]+$', room_id):
        raise HTTPException(400, 'Invalid room_id format')
    con = get_db()
    con.execute('PRAGMA foreign_keys = ON')
    con.execute('DELETE FROM rooms WHERE id=?', (room_id,))
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,outcome) VALUES(?,?,?,?,?)',
        (_now(), admin.get('preferred_username','admin'), room_id, 'admin_room_deleted', 'success')
    )
    con.commit()
    con.close()
    return {'status': 'ok'}


@app.post('/api/admin/rooms/{room_id}/devices')
def admin_add_device(room_id: str, body: DeviceIn, admin=Depends(require_admin)):
    con = get_db()
    max_order = con.execute(
        'SELECT COALESCE(MAX(sort_order),0) FROM devices WHERE room_id=?', (room_id,)
    ).fetchone()[0]
    con.execute(
        'INSERT INTO devices(room_id,device_type,manufacturer,model,connection,sort_order)'
        ' VALUES(?,?,?,?,?,?)',
        (room_id, body.device_type, body.manufacturer, body.model, body.connection, max_order+1)
    )
    con.commit()
    con.close()
    return {'status': 'ok'}


@app.delete('/api/admin/devices/{device_id}')
def admin_delete_device(device_id: int, admin=Depends(require_admin)):
    con = get_db()
    con.execute('DELETE FROM devices WHERE id=?', (device_id,))
    con.commit()
    con.close()
    return {'status': 'ok'}


# ---------------------------------------------------------------------------
# Admin API — log management
# ---------------------------------------------------------------------------

def _build_log_where(campus, room_id, user, action_type, date_from, date_to):
    where, params = [], []
    if campus:      where.append('room_id LIKE ?');   params.append(f'{campus}-%')
    if room_id:     where.append('room_id = ?');      params.append(room_id)
    if user:        where.append('user LIKE ?');      params.append(f'%{user}%')
    if action_type: where.append('action_type = ?');  params.append(action_type)
    if date_from:   where.append('ts >= ?');          params.append(date_from)
    if date_to:     where.append('ts <= ?');          params.append(date_to + 'T23:59:59')
    return where, params


@app.get('/api/admin/logs')
def admin_logs(
    campus:      Optional[str] = None,
    room_id:     Optional[str] = None,
    user:        Optional[str] = None,
    action_type: Optional[str] = None,
    date_from:   Optional[str] = None,
    date_to:     Optional[str] = None,
    limit:       int = 50,
    offset:      int = 0,
    admin=Depends(require_admin)
):
    where, params = _build_log_where(campus, room_id, user, action_type, date_from, date_to)
    sql = 'SELECT * FROM audit_log'
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY ts DESC LIMIT ? OFFSET ?'
    con = get_db()
    rows  = con.execute(sql, params + [limit, offset]).fetchall()
    total = con.execute(
        'SELECT COUNT(*) FROM audit_log' + (' WHERE ' + ' AND '.join(where) if where else ''),
        params
    ).fetchone()[0]
    con.close()
    cols = ['id','ts','user','room_id','action_type','target','outcome','notes']
    return {'total': total, 'rows': [dict(zip(cols, r)) for r in rows]}


@app.get('/api/admin/logs/export')
def admin_logs_export(
    campus:      Optional[str] = None,
    room_id:     Optional[str] = None,
    user:        Optional[str] = None,
    action_type: Optional[str] = None,
    date_from:   Optional[str] = None,
    date_to:     Optional[str] = None,
    admin=Depends(require_admin)
):
    where, params = _build_log_where(campus, room_id, user, action_type, date_from, date_to)
    sql = 'SELECT * FROM audit_log'
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
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


@app.get('/api/admin/logs/summary')
def admin_logs_summary(days: int = 7, admin=Depends(require_admin)):
    con = get_db()
    cutoff = (datetime.datetime.utcnow() - timedelta(days=days)).isoformat()
    daily = con.execute(
        'SELECT date(ts) AS day, COUNT(*) AS n FROM audit_log'
        ' WHERE ts >= ? GROUP BY day ORDER BY day', (cutoff,)
    ).fetchall()
    top_rooms = con.execute(
        'SELECT room_id, COUNT(*) AS n FROM audit_log'
        ' WHERE ts >= ? GROUP BY room_id ORDER BY n DESC LIMIT 5', (cutoff,)
    ).fetchall()
    top_actions = con.execute(
        'SELECT action_type, COUNT(*) AS n FROM audit_log'
        ' WHERE ts >= ? GROUP BY action_type ORDER BY n DESC LIMIT 10', (cutoff,)
    ).fetchall()
    total_rooms    = con.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
    active_rooms   = con.execute("SELECT COUNT(*) FROM rooms WHERE status='in-use'").fetchone()[0]
    open_incidents = con.execute("SELECT COUNT(*) FROM incidents WHERE status='open'").fetchone()[0]
    con.close()
    return {
        'stats':       {'total_rooms': total_rooms, 'active_rooms': active_rooms,
                        'open_incidents': open_incidents},
        'daily':       [{'day': r[0], 'n': r[1]} for r in daily],
        'top_rooms':   [{'room_id': r[0], 'n': r[1]} for r in top_rooms],
        'top_actions': [{'action': r[0], 'n': r[1]} for r in top_actions],
    }


@app.post('/api/admin/logs/archive')
def admin_logs_archive(older_than_days: int = 90, admin=Depends(require_admin)):
    con = get_db()
    con.execute(
        'CREATE TABLE IF NOT EXISTS audit_log_archive AS SELECT * FROM audit_log WHERE 0'
    )
    cutoff = (datetime.datetime.utcnow() - timedelta(days=older_than_days)).isoformat()
    con.execute('INSERT INTO audit_log_archive SELECT * FROM audit_log WHERE ts < ?', (cutoff,))
    result = con.execute('DELETE FROM audit_log WHERE ts < ?', (cutoff,))
    count = result.rowcount
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,notes,outcome) VALUES(?,?,?,?,?,?)',
        (_now(), admin.get('preferred_username','admin'), 'SYSTEM',
         'admin_log_archive', f'archived {count} entries older than {older_than_days} days', 'success')
    )
    con.commit()
    con.close()
    return {'archived': count, 'cutoff': cutoff}


# Purge token store (in-memory; single-process only)
_purge_tokens: dict = {}

@app.get('/api/admin/logs/purge-token')
def admin_logs_purge_token(admin=Depends(require_admin)):
    """Generate a one-time token required to purge archived logs."""
    import secrets
    token = secrets.token_urlsafe(16)
    expires = datetime.datetime.utcnow() + timedelta(seconds=60)
    _purge_tokens[token] = expires
    return {'token': token, 'expires_in': 60}

@app.delete('/api/admin/logs/purge')
def admin_logs_purge(token: str, older_than_days: int = 90, admin=Depends(require_admin)):
    """Permanently delete archived log entries. Requires a valid purge token."""
    expires = _purge_tokens.pop(token, None)
    if not expires or datetime.datetime.utcnow() > expires:
        raise HTTPException(403, 'Invalid or expired purge token')
    con = get_db()
    cutoff = (datetime.datetime.utcnow() - timedelta(days=older_than_days)).isoformat()
    # Only purge from the archive table
    try:
        result = con.execute('DELETE FROM audit_log_archive WHERE ts < ?', (cutoff,))
        count = result.rowcount
    except Exception:
        count = 0
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,notes,outcome) VALUES(?,?,?,?,?,?)',
        (_now(), admin.get('preferred_username','admin'), 'SYSTEM',
         'admin_log_purge', f'purged {count} archived entries older than {older_than_days} days', 'success')
    )
    con.commit()
    con.close()
    return {'purged': count}


# ---------------------------------------------------------------------------
# Admin API — connector management
# ---------------------------------------------------------------------------

@app.get('/api/admin/connectors')
def admin_connectors(admin=Depends(require_admin)):
    con = get_db()
    rows = con.execute('SELECT * FROM connector_config ORDER BY campus_id, connector_name').fetchall()
    con.close()
    # Annotate credential presence without exposing values
    cred_present = {
        'crestron':      bool(os.getenv('CRESTRON_POLL_USERNAME')),
        'live25':        bool(os.getenv('LIVE25_USERNAME')),
        'screenconnect': bool(os.getenv('SC_BASE_URL')),
        'wattbox':       bool(os.getenv('WATTBOX_OVRC_API_KEY') or os.getenv('WATTBOX_DIRECT_USERNAME')),
        'servicenow':    bool(os.getenv('SN_CLIENT_ID') or os.getenv('SERVICENOW_CLIENT_ID')),
        'sharepoint':    bool(os.getenv('SHAREPOINT_BASE_URL')),
        'ptz':           bool(os.getenv('PTZ_PROXY_USERNAME')),
    }
    result = []
    for r in rows:
        d = dict(r)
        d['credentials_present'] = cred_present.get(r['connector_name'], False)
        result.append(d)
    return result


@app.put('/api/admin/connectors/{campus_id}/{connector_name}/mode')
def admin_set_connector_mode(
    campus_id: str, connector_name: str, mode: str,
    admin=Depends(require_admin)
):
    if mode not in ('live', 'mock'):
        raise HTTPException(400, 'mode must be live or mock')
    cred_check = {
        'crestron':      bool(os.getenv('CRESTRON_POLL_USERNAME')),
        'live25':        bool(os.getenv('LIVE25_USERNAME')),
        'screenconnect': bool(os.getenv('SC_BASE_URL')),
        'wattbox':       bool(os.getenv('WATTBOX_OVRC_API_KEY') or os.getenv('WATTBOX_DIRECT_USERNAME')),
        'servicenow':    bool(os.getenv('SN_CLIENT_ID') or os.getenv('SERVICENOW_CLIENT_ID')),
        'sharepoint':    bool(os.getenv('SHAREPOINT_BASE_URL')),
        'ptz':           bool(os.getenv('PTZ_PROXY_USERNAME')),
    }
    if mode == 'live' and not cred_check.get(connector_name, False):
        return {'status': 'warning',
                'message': 'No credentials found in .env for this connector.',
                'mode_set': False}
    con = get_db()
    con.execute(
        'UPDATE connector_config SET mode=? WHERE campus_id=? AND connector_name=?',
        (mode, campus_id, connector_name)
    )
    # Also update in-memory registry if campus/connector exists
    if campus_id in CONNECTOR_REGISTRY and connector_name in CONNECTOR_REGISTRY[campus_id]:
        CONNECTOR_REGISTRY[campus_id][connector_name]['mode'] = mode
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,target,outcome) VALUES(?,?,?,?,?,?)',
        (_now(), admin.get('preferred_username','admin'), campus_id,
         'admin_connector_mode_changed', f'{connector_name}={mode}', 'success')
    )
    con.commit()
    con.close()
    return {'status': 'ok', 'campus_id': campus_id, 'connector_name': connector_name, 'mode': mode}


@app.post('/api/admin/connectors/{campus_id}/{connector_name}/test')
def admin_test_connector(campus_id: str, connector_name: str, admin=Depends(require_admin)):
    """Lightweight connectivity test for a connector."""
    con = get_db()
    row = con.execute(
        'SELECT mode FROM connector_config WHERE campus_id=? AND connector_name=?',
        (campus_id, connector_name)
    ).fetchone()
    con.close()
    if not row:
        raise HTTPException(404, 'Connector not found')
    # In mock mode, always return healthy
    if row['mode'] == 'mock':
        return {'status': 'mock', 'reachable': True, 'message': 'Mock mode — no real connection made'}
    # In live mode, return a placeholder (real ping logic goes here per connector)
    return {'status': 'live', 'reachable': None,
            'message': 'Live connectivity test not yet implemented for this connector'}


# ---------------------------------------------------------------------------
# Admin API — user role management
# ---------------------------------------------------------------------------

@app.get('/api/admin/users')
def admin_users(admin=Depends(require_admin)):
    con = get_db()
    rows = con.execute('SELECT * FROM user_roles ORDER BY email').fetchall()
    con.close()
    return [dict(r) for r in rows]


@app.put('/api/admin/users/{entra_id}')
def admin_set_user_role(entra_id: str, body: UserRoleIn, admin=Depends(require_admin)):
    if body.role not in ('technician', 'admin', 'readonly'):
        raise HTTPException(400, 'role must be technician, admin, or readonly')
    now = _now()
    con = get_db()
    con.execute(
        'INSERT INTO user_roles(entra_id,role,notes,updated_at,updated_by)'
        ' VALUES(?,?,?,?,?)'
        ' ON CONFLICT(entra_id) DO UPDATE SET role=excluded.role,'
        '   notes=excluded.notes, updated_at=excluded.updated_at,'
        '   updated_by=excluded.updated_by',
        (entra_id, body.role, body.notes, now, admin.get('preferred_username','admin'))
    )
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,target,outcome) VALUES(?,?,?,?,?,?)',
        (now, admin.get('preferred_username','admin'), 'SYSTEM',
         'admin_role_override_set', f'{entra_id}={body.role}', 'success')
    )
    con.commit()
    con.close()
    return {'status': 'ok', 'entra_id': entra_id, 'role': body.role}


@app.delete('/api/admin/users/{entra_id}')
def admin_remove_user_role(entra_id: str, admin=Depends(require_admin)):
    con = get_db()
    con.execute('DELETE FROM user_roles WHERE entra_id=?', (entra_id,))
    con.execute(
        'INSERT INTO audit_log(ts,user,room_id,action_type,target,outcome) VALUES(?,?,?,?,?,?)',
        (_now(), admin.get('preferred_username','admin'), 'SYSTEM',
         'admin_role_override_removed', entra_id, 'success')
    )
    con.commit()
    con.close()
    return {'status': 'ok'}


# ---------------------------------------------------------------------------
# Static frontend — must come last (catches all non-API paths)
# ---------------------------------------------------------------------------

if DASHBOARD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"error": "Dashboard directory not found", "expected": str(DASHBOARD_DIR)}
