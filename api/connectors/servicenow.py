"""
BeaverView ServiceNow Connector
Follows mock/live pattern from main.py — reads incidents without exposing PII.

FERPA Compliance:
- Only fetches: number, short_description, state, sys_id, opened_at
- NEVER fetches: caller_id, u_requester, description, work_notes, contact info
- Falls back to mock data if credentials unavailable or API unreachable
"""

import os
import httpx
import asyncio
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Incident(BaseModel):
    """Incident data safe for display to techs — no PII"""
    number: str                      # e.g. INC0001234
    short_description: str           # "Projector won't display HDMI input"
    state: str                       # "1" (new), "2" (in progress), "7" (closed)
    sys_id: str                      # internal ServiceNow ID
    opened_at: Optional[str]         # ISO datetime


SN_INSTANCE = os.getenv("SN_INSTANCE")
SN_CLIENT_ID = os.getenv("SN_CLIENT_ID")
SN_CLIENT_SECRET = os.getenv("SN_CLIENT_SECRET")
SN_USERNAME = os.getenv("SN_USERNAME")
SN_PASSWORD = os.getenv("SN_PASSWORD")


async def get_servicenow_token(instance: str, client_id: str, client_secret: str) -> Optional[str]:
    """
    OAuth2 client credentials flow for ServiceNow.
    Falls back gracefully if unreachable or misconfigured.
    """
    if not all([instance, client_id, client_secret]):
        return None

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"https://{instance}/oauth_token.do",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            )
            if resp.status_code == 200:
                return resp.json().get("access_token")
    except (httpx.RequestError, ValueError):
        pass
    return None


async def get_incidents_for_room(
    room_id: str,
    room_code: str,
    building_name: str,
    instance: Optional[str] = None,
    token: Optional[str] = None,
    mode: str = "live"
) -> list[Incident]:
    """
    Fetch incidents for a room from ServiceNow.

    Args:
        room_id: BeaverView room ID (not used for ServiceNow lookup — for logging only)
        room_code: Building code + room number (e.g., "KA 101")
        building_name: Full building name (e.g., "Kerr Hall")
        instance: ServiceNow instance domain (e.g., "osu.service-now.com")
        token: OAuth access token (optional if basic auth preferred)
        mode: "live" (API) or "mock" (stub data)

    Returns:
        List of Incident objects safe for display (no PII)

    Note: If API unavailable, falls back to mock data silently.
    """
    if mode == "mock" or not instance:
        return get_incidents_mock(room_code)

    # Try OAuth first, fall back to basic auth if no token
    auth = None
    if token:
        headers = {"Authorization": f"Bearer {token}"}
    elif SN_USERNAME and SN_PASSWORD:
        auth = (SN_USERNAME, SN_PASSWORD)
        headers = {}
    else:
        return get_incidents_mock(room_code)

    try:
        # Query incidents assigned to this room/building.
        # Filter: assignment_group contains room code OR location contains building name
        query = (
            f"assignment_groupLIKE{room_code.split()[0]}"  # e.g., "KA" from "KA 101"
            f"ORlocation={building_name}"
        )
        url = (
            f"https://{instance}/api/now/table/incident?"
            f"sysparm_fields=number,short_description,state,sys_id,opened_at&"
            f"sysparm_query={query}&"
            f"sysparm_exclude_reference_link=true&"
            f"sysparm_limit=20"
        )

        async with httpx.AsyncClient(timeout=8, verify=False) as client:
            resp = await client.get(url, auth=auth, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                incidents = []
                for record in data.get("result", []):
                    try:
                        incidents.append(Incident(
                            number=record.get("number", ""),
                            short_description=record.get("short_description", ""),
                            state=_state_label(record.get("state", "")),
                            sys_id=record.get("sys_id", ""),
                            opened_at=record.get("opened_at")
                        ))
                    except ValueError:
                        # Skip malformed records silently
                        pass
                return incidents
    except (httpx.RequestError, asyncio.TimeoutError, ValueError):
        # Network error, timeout, or parse error — fall back to mock
        pass

    return get_incidents_mock(room_code)


def get_incidents_mock(room_code: str) -> list[Incident]:
    """Mock incident data for dev/demo when ServiceNow is unavailable."""
    mock_incidents = {
        "KA 101": [
            Incident(
                number="INC0001234",
                short_description="Projector not displaying HDMI input",
                state="In Progress",
                sys_id="a1b2c3d4e5f6g7h8",
                opened_at="2026-06-20T10:30:00Z"
            ),
            Incident(
                number="INC0001233",
                short_description="Audio system intermittent",
                state="Open",
                sys_id="b2c3d4e5f6g7h8i9",
                opened_at="2026-06-19T14:15:00Z"
            )
        ],
        "KA 205": [
            Incident(
                number="INC0001235",
                short_description="Control panel unresponsive",
                state="Open",
                sys_id="c3d4e5f6g7h8i9j0",
                opened_at="2026-06-22T09:00:00Z"
            )
        ]
    }
    return mock_incidents.get(room_code, [])


def _state_label(state_code: str) -> str:
    """Map ServiceNow state code to readable label."""
    state_map = {
        "1": "Open",
        "2": "In Progress",
        "3": "On Hold",
        "7": "Closed",
    }
    return state_map.get(state_code, "Unknown")


async def test_servicenow_connection(instance: str) -> dict:
    """
    Health check: can we reach ServiceNow?
    Returns: {status: "live"|"mock"|"error", latency_ms: int}
    """
    if not instance:
        return {"status": "mock", "latency_ms": 0, "reason": "No SN_INSTANCE configured"}

    import time
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5, verify=False) as client:
            resp = await client.get(f"https://{instance}/api/now/table/sys_user?sysparm_limit=0")
            latency_ms = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                return {"status": "live", "latency_ms": latency_ms}
            else:
                return {"status": "error", "latency_ms": latency_ms, "reason": f"HTTP {resp.status_code}"}
    except (httpx.RequestError, asyncio.TimeoutError) as e:
        latency_ms = int((time.time() - start) * 1000)
        return {"status": "mock", "latency_ms": latency_ms, "reason": str(e)[:50]}
