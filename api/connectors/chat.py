"""
BeaverView Hermes Chat Agent
Proxies chat messages to DGX Spark (local LLM via OpenAI-compatible API).

FERPA Compliance:
- Context includes: room name, building, campus, device list (no IPs/serials exposed)
- Context includes: open incident numbers + short descriptions (no caller info)
- NEVER context: user names, personal information, student info
- System prompt is hardcoded, never overridable via API body

Architecture:
  Browser → POST /api/chat {message, room_id, history}
         ↓
    chat.py builds FERPA-safe context
         ↓
    DGX Spark (local LLM, OpenAI-compatible endpoint)
         ↓
    Reply → browser
"""

import os
import httpx
import json
from typing import Optional
from datetime import datetime

CHAT_BASE_URL = os.getenv("CHAT_BASE_URL", "").rstrip("/")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3")
CHAT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT", "30"))

SYSTEM_PROMPT = """You are Hermes, a helpful AV support assistant for Oregon State University.

Your role:
- Help AV technicians troubleshoot presentation systems and audio/video equipment
- Explain how to use room control panels, ScreenConnect, WattBox, and other AV tools
- Help them understand past incidents and what was resolved
- Point to documentation and best practices for common issues
- Never assume personal information about anyone

Context about this room:
- You have access to the room's device list, current status, and open incidents
- Use this information to provide targeted troubleshooting advice
- If a device is offline or has an issue, acknowledge that in your response
- Never share PII, student names, or personal information
- Keep responses focused on technical AV support

Tone: professional, friendly, concise. Prefer short paragraphs and bullet points for clarity.
"""


async def build_chat_context(room_id: Optional[str], db) -> str:
    """
    Build FERPA-safe context about the selected room.
    Includes: room name, building, devices, open incidents (numbers only).
    Excludes: user names, student info, personal data.
    """
    if not room_id:
        return "(No room selected — general AV support mode)"

    try:
        # Fetch room + building from SQLite
        cursor = db.execute(
            """SELECT r.name, r.campus, b.name as building_name, b.campus_id
               FROM rooms r
               JOIN buildings b ON r.building_id = b.id
               WHERE r.id = ?""",
            (room_id,)
        )
        room = cursor.fetchone()

        if not room:
            return "(Room not found)"

        room_name, campus, building_name, _ = room
        context = f"**Room Context:**\n- Room: {room_name}\n- Building: {building_name}\n- Campus: {campus}\n"

        # Fetch devices for this room
        cursor = db.execute(
            "SELECT name FROM devices WHERE room_id = ? ORDER BY name",
            (room_id,)
        )
        devices = [row[0] for row in cursor.fetchall()]
        if devices:
            context += f"- Devices: {', '.join(devices)}\n"

        # Fetch open incidents (number + short_description only — no PII)
        cursor = db.execute(
            """SELECT number, short_description, state
               FROM incidents
               WHERE room_id = ? AND state IN ('open', 'in progress')
               ORDER BY opened_at DESC LIMIT 5""",
            (room_id,)
        )
        incidents = cursor.fetchall()
        if incidents:
            context += "- Open Incidents:\n"
            for number, desc, state in incidents:
                context += f"  - {number} ({state}): {desc}\n"
        else:
            context += "- No open incidents\n"

        return context

    except Exception as e:
        return f"(Context unavailable: {str(e)[:50]})"


async def chat_with_hermes(
    message: str,
    room_id: Optional[str] = None,
    conversation_history: list = None,
    db = None
) -> dict:
    """
    Send a message to Hermes (DGX Spark local LLM).

    Args:
        message: User's question/statement
        room_id: Selected room (optional, for context)
        conversation_history: List of {role: "user"|"assistant", content: str} dicts
        db: SQLite connection (for building context)

    Returns:
        {
            "reply": str (or error message if unavailable),
            "model": str,
            "tokens_used": int or null,
            "timestamp": ISO datetime
        }
    """

    if not CHAT_BASE_URL:
        return {
            "reply": "Chat agent not configured. Set CHAT_BASE_URL in .env to enable Hermes.",
            "model": "unavailable",
            "tokens_used": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    # Build FERPA-safe context
    context_str = ""
    if db:
        context_str = await build_chat_context(room_id, db)

    # Construct the messages list for the LLM
    messages = []

    # Add room context as a system note if available
    if context_str and "(No room selected" not in context_str:
        messages.append({
            "role": "user",
            "content": f"[CONTEXT] {context_str}"
        })
        messages.append({
            "role": "assistant",
            "content": "Understood. I have context about this room. How can I help?"
        })

    # Add conversation history (last 10 messages to keep context manageable)
    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

    # Add current message
    messages.append({
        "role": "user",
        "content": message
    })

    try:
        async with httpx.AsyncClient(timeout=CHAT_TIMEOUT) as client:
            response = await client.post(
                f"{CHAT_BASE_URL}/v1/chat/completions",
                json={
                    "model": CHAT_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        *messages
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "stream": False
                }
            )

            if response.status_code == 200:
                data = response.json()
                reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens_used = data.get("usage", {}).get("total_tokens")

                return {
                    "reply": reply if reply else "(No response from Hermes)",
                    "model": CHAT_MODEL,
                    "tokens_used": tokens_used,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "reply": f"Hermes error: HTTP {response.status_code}",
                    "model": CHAT_MODEL,
                    "tokens_used": None,
                    "timestamp": datetime.utcnow().isoformat()
                }

    except (httpx.RequestError, httpx.TimeoutException) as e:
        return {
            "reply": f"Hermes unavailable: {str(e)[:100]}. Check CHAT_BASE_URL and that DGX Spark is running.",
            "model": CHAT_MODEL,
            "tokens_used": None,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "reply": f"Hermes error: {str(e)[:100]}",
            "model": CHAT_MODEL,
            "tokens_used": None,
            "timestamp": datetime.utcnow().isoformat()
        }


async def test_chat_connection() -> dict:
    """
    Health check: can we reach DGX Spark?
    Returns: {status: "live"|"mock"|"error", latency_ms: int, model: str}
    """
    if not CHAT_BASE_URL:
        return {
            "status": "mock",
            "latency_ms": 0,
            "model": "unavailable",
            "reason": "No CHAT_BASE_URL configured"
        }

    import time
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{CHAT_BASE_URL}/v1/chat/completions",
                json={
                    "model": CHAT_MODEL,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1
                }
            )
            latency_ms = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                return {
                    "status": "live",
                    "latency_ms": latency_ms,
                    "model": CHAT_MODEL,
                    "reason": "DGX Spark is running"
                }
            else:
                return {
                    "status": "error",
                    "latency_ms": latency_ms,
                    "model": CHAT_MODEL,
                    "reason": f"HTTP {resp.status_code}"
                }
    except (httpx.RequestError, httpx.TimeoutException) as e:
        latency_ms = int((time.time() - start) * 1000)
        return {
            "status": "error",
            "latency_ms": latency_ms,
            "model": CHAT_MODEL,
            "reason": f"Connection failed: {str(e)[:50]}"
        }
