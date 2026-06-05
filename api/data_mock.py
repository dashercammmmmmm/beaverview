"""Mock room data for the direct-device connector stub.

This mirrors the structure in dashboard/data.js so the backend and frontend
use the same canonical room set until a real hardware import runs.

The 'processor' field reflects the reachability of the Crestron control
processor for that room.  In live mode this is populated by the background
poller (poll_all_processors) reading from the device_ips table.
"""

MOCK_ROOMS: list[dict] = [
    # Corvallis
    {"room_id": "corvallis-kad-101",   "campus": "corvallis", "building": "KAd",  "number": "101",   "processor": "online",  "display": "standby", "health": 72,  "stale": False},
    {"room_id": "corvallis-kad-105",   "campus": "corvallis", "building": "KAd",  "number": "105",   "processor": "online",  "display": "on",      "health": 96,  "stale": False},
    {"room_id": "corvallis-linc-100",  "campus": "corvallis", "building": "LINC", "number": "100",   "processor": "online",  "display": "on",      "health": 91,  "stale": False},
    {"room_id": "corvallis-linc-228",  "campus": "corvallis", "building": "LINC", "number": "228",   "processor": "online",  "display": "on",      "health": 98,  "stale": False},
    {"room_id": "corvallis-mu-208",    "campus": "corvallis", "building": "MU",   "number": "208",   "processor": "online",  "display": "on",      "health": 87,  "stale": False},
    {"room_id": "corvallis-als-4000",  "campus": "corvallis", "building": "ALS",  "number": "4000",  "processor": "offline", "display": "unknown", "health": 48,  "stale": True},
    {"room_id": "corvallis-dear-118",  "campus": "corvallis", "building": "Dear", "number": "118",   "processor": "online",  "display": "on",      "health": 93,  "stale": False},
    {"room_id": "corvallis-gilb-124",  "campus": "corvallis", "building": "Gilb", "number": "124",   "processor": "online",  "display": "on",      "health": 69,  "stale": False},
    {"room_id": "corvallis-cord-1109", "campus": "corvallis", "building": "Cord", "number": "1109",  "processor": "online",  "display": "off",     "health": 94,  "stale": False},
    {"room_id": "corvallis-bexl-415",  "campus": "corvallis", "building": "Bexl", "number": "415",   "processor": "online",  "display": "on",      "health": 89,  "stale": False},
    {"room_id": "corvallis-lsc-austin","campus": "corvallis", "building": "LSC",  "number": "Austin","processor": "online",  "display": "standby", "health": 97,  "stale": False},
    {"room_id": "corvallis-kec-1001",  "campus": "corvallis", "building": "KEC",  "number": "1001",  "processor": "online",  "display": "on",      "health": 95,  "stale": False},
    {"room_id": "corvallis-mlm-026",   "campus": "corvallis", "building": "Mlm",  "number": "026",   "processor": "online",  "display": "off",     "health": 90,  "stale": False},
    {"room_id": "corvallis-nash-032",  "campus": "corvallis", "building": "Nash", "number": "032",   "processor": "online",  "display": "on",      "health": 76,  "stale": False},
    # OSU-Cascades
    {"room_id": "cascades-tyke-111",   "campus": "cascades",  "building": "Tyke", "number": "111",   "processor": "mock",    "display": "on",      "health": 96,  "stale": False},
    {"room_id": "cascades-obsn-205",   "campus": "cascades",  "building": "Obsn", "number": "205",   "processor": "mock",    "display": "on",      "health": 88,  "stale": False},
    {"room_id": "cascades-cgrc-130",   "campus": "cascades",  "building": "CGRC", "number": "130",   "processor": "mock",    "display": "standby", "health": 92,  "stale": False},
    # Hatfield
    {"room_id": "hatfield-gvmsb-aud",  "campus": "hatfield",  "building": "GVMSB","number": "Aud",   "processor": "mock",    "display": "on",      "health": 94,  "stale": False},
    {"room_id": "hatfield-hmsc-204",   "campus": "hatfield",  "building": "HMSC", "number": "204",   "processor": "mock",    "display": "unknown", "health": 74,  "stale": True},
]
