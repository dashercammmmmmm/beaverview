"""
BeaverView — Admin Panel Playbook PDF Generator
Run: python3 generate_admin_playbook.py
Output: BeaverView-AdminPanel-Playbook.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER

OSU_ORANGE  = colors.HexColor("#D73F09")
OSU_DARK    = colors.HexColor("#111827")
STATUS_OK   = colors.HexColor("#15803D")
STATUS_WARN = colors.HexColor("#B45309")
STATUS_INFO = colors.HexColor("#1D4ED8")
STATUS_PURPLE = colors.HexColor("#7C3AED")
BG_LIGHT    = colors.HexColor("#F3F4F6")
BG_CODE     = colors.HexColor("#1E293B")
TEXT_CODE   = colors.HexColor("#E2E8F0")
BORDER_GRAY = colors.HexColor("#D1D5DB")
TEXT_MUTED  = colors.HexColor("#6B7280")

def S():
    s = {}
    s["h1"]   = ParagraphStyle("h1",  fontName="Helvetica-Bold", fontSize=22, textColor=OSU_DARK,  spaceAfter=6,  spaceBefore=20, leading=28)
    s["h2"]   = ParagraphStyle("h2",  fontName="Helvetica-Bold", fontSize=15, textColor=OSU_ORANGE, spaceAfter=4,  spaceBefore=16, leading=20)
    s["h3"]   = ParagraphStyle("h3",  fontName="Helvetica-Bold", fontSize=11, textColor=OSU_DARK,  spaceAfter=3,  spaceBefore=10, leading=16)
    s["body"] = ParagraphStyle("body",fontName="Helvetica",       fontSize=10, textColor=OSU_DARK,  spaceAfter=6,  leading=15)
    s["muted"]= ParagraphStyle("muted",fontName="Helvetica",      fontSize=9,  textColor=TEXT_MUTED,spaceAfter=4,  leading=13)
    s["snum"] = ParagraphStyle("snum",fontName="Helvetica-Bold",  fontSize=11, textColor=colors.white, leading=14)
    s["sbod"] = ParagraphStyle("sbod",fontName="Helvetica",       fontSize=10, textColor=OSU_DARK,  spaceAfter=4,  leading=15)
    s["code"] = ParagraphStyle("code",fontName="Courier",         fontSize=8,  textColor=TEXT_CODE, spaceAfter=0,  leading=12)
    s["ctit"] = ParagraphStyle("ctit",fontName="Helvetica-Bold",  fontSize=10, textColor=OSU_DARK,  spaceAfter=2,  leading=14)
    s["cbod"] = ParagraphStyle("cbod",fontName="Helvetica",       fontSize=9,  textColor=OSU_DARK,  spaceAfter=0,  leading=13)
    s["sbld"] = ParagraphStyle("sbld",fontName="Helvetica-Bold",  fontSize=8,  textColor=TEXT_MUTED,spaceAfter=2,  leading=11)
    s["foot"] = ParagraphStyle("foot",fontName="Helvetica",       fontSize=8,  textColor=TEXT_MUTED,alignment=TA_CENTER)
    return s

def cb(lines, s, w=6.5*inch):
    rows = []
    for line in lines:
        safe = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace(" ","&nbsp;")
        rows.append([Paragraph(safe, s["code"])])
    t = Table(rows, colWidths=[w])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BG_CODE),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
    ]))
    return t

def box(title, lines, s, color=STATUS_INFO, w=6.5*inch):
    content = [Paragraph(title, s["ctit"])] + [Paragraph(l, s["cbod"]) for l in lines]
    t = Table([content], colWidths=[w])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BG_LIGHT),
        ("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LINEBEFORE",(0,0),(0,-1),4,color),
        ("BOX",(0,0),(-1,-1),0.5,BORDER_GRAY),
    ]))
    return t

def st(num, title, lines, s, w=6.5*inch):
    badge = Table([[Paragraph(str(num), s["snum"])]], colWidths=[22], rowHeights=[22])
    badge.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),OSU_ORANGE),("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
    ]))
    t = Table([[badge, [Paragraph(f"<b>{title}</b>", s["h3"])] + [Paragraph(l, s["sbod"]) for l in lines]]],
              colWidths=[30, w-30])
    t.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(1,0),(1,-1),10),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
    ]))
    return t

def tbl(rows, s, cw=None, hdr=None):
    if cw is None: cw = [2.5*inch, 4.0*inch]
    data = []
    if hdr: data.append([Paragraph(f"<b>{h}</b>", s["sbld"]) for h in hdr])
    for r in rows: data.append([Paragraph(str(c), s["body"]) for c in r])
    t = Table(data, colWidths=cw)
    ts = [
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,BG_LIGHT]),
        ("BOX",(0,0),(-1,-1),0.5,BORDER_GRAY),("INNERGRID",(0,0),(-1,-1),0.3,BORDER_GRAY),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]
    if hdr: ts += [("BACKGROUND",(0,0),(-1,0),OSU_DARK),("TEXTCOLOR",(0,0),(-1,0),colors.white)]
    t.setStyle(TableStyle(ts))
    return t

def on_page(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(OSU_DARK); canvas.rect(0,h-30,w,30,fill=1,stroke=0)
    canvas.setFillColor(OSU_ORANGE); canvas.rect(0,h-33,w,3,fill=1,stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold",9); canvas.drawString(0.75*inch,h-20,"BeaverView — Admin Panel Playbook")
    canvas.setFont("Helvetica",9); canvas.drawRightString(w-0.75*inch,h-20,"OSU Presentation Support")
    canvas.setFillColor(TEXT_MUTED); canvas.setFont("Helvetica",8)
    canvas.drawCentredString(w/2,24,f"Page {doc.page}")
    canvas.restoreState()

# ── COVER ──────────────────────────────────────────────────────────────────────
def cover(story, s):
    story.append(Spacer(1,1.0*inch))
    cover_data = [[
        Paragraph("BeaverView", ParagraphStyle("ct",fontName="Helvetica-Bold",fontSize=42,textColor=colors.white,leading=48)),
        Paragraph("Admin Panel", ParagraphStyle("ct2",fontName="Helvetica-Bold",fontSize=42,textColor=OSU_ORANGE,leading=48)),
        Spacer(1,0.08*inch),
        Paragraph("Implementation Playbook", ParagraphStyle("ctag",fontName="Helvetica-Bold",fontSize=14,textColor=colors.white,leading=18)),
        Spacer(1,0.04*inch),
        Paragraph("Room editor  ·  Log management  ·  Connector control  ·  User roles  ·  Summary dashboard",
            ParagraphStyle("cdesc",fontName="Helvetica",fontSize=10,textColor=colors.HexColor("#D1D5DB"),leading=15)),
    ]]
    c = Table([cover_data], colWidths=[6.5*inch])
    c.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),OSU_DARK),
        ("TOPPADDING",(0,0),(-1,-1),40),("BOTTOMPADDING",(0,0),(-1,-1),40),
        ("LEFTPADDING",(0,0),(-1,-1),40),("RIGHTPADDING",(0,0),(-1,-1),40),
        ("LINEBEFORE",(0,0),(0,-1),5,OSU_ORANGE),
    ]))
    story.append(c)
    story.append(Spacer(1,0.25*inch))

    story.append(box("What this playbook covers", [
        "BeaverView currently stores all room and building data in a static JavaScript file (data.js). "
        "This playbook adds a full admin panel at /admin that lets authorised staff:",
        "",
        "  •  Add, edit, and delete rooms and buildings through a web form — no code editing required",
        "  •  View, filter, search, and export the audit log to CSV/Excel",
        "  •  Archive or delete old log entries on a schedule",
        "  •  Toggle connectors between mock and live mode from the browser",
        "  •  Manage which OSU staff have Technician vs. Admin access",
        "  •  See a live summary dashboard: busiest rooms, most-used tools, recent alerts",
        "",
        "Access is restricted to users in the BeaverView Admins Azure AD group. "
        "Every admin action is logged to the same audit trail as technician actions.",
    ], s, color=OSU_ORANGE))

    story.append(Spacer(1,0.2*inch))
    story.append(Paragraph("Guide contents", s["h2"]))
    story.append(tbl([
        ["Part 1",  "Architecture overview",     "How the admin panel fits into the existing app"],
        ["Part 2",  "Database schema changes",   "New tables: campuses, buildings, rooms, devices, connector_config, user_roles"],
        ["Part 3",  "Data migration",            "One-time import of data.js into the database"],
        ["Part 4",  "New API endpoints",         "CRUD routes for rooms, buildings, connectors, users, log management"],
        ["Part 5",  "Admin panel frontend",      "HTML/CSS/JS for each admin page"],
        ["Part 6",  "Summary dashboard",         "Stats, activity charts, connector health overview"],
        ["Part 7",  "Room and building editor",  "Search, filter, inline edit, add/delete rooms"],
        ["Part 8",  "Log management",            "Filter, search, export CSV, archive, delete old entries"],
        ["Part 9",  "Connector management",      "Toggle live/mock, update credentials from the browser"],
        ["Part 10", "User role management",      "Assign Technician/Admin roles, sync with Entra groups"],
        ["Part 11", "Security and access control","Route protection, audit logging, input validation"],
        ["Part 12", "Deployment checklist",      "Steps to add the admin panel to an existing BeaverView install"],
    ], s, cw=[0.65*inch, 1.9*inch, 3.95*inch]))
    story.append(PageBreak())

# ── PART 1: ARCHITECTURE ───────────────────────────────────────────────────────
def part1(story, s):
    story.append(Paragraph("Part 1 — Architecture Overview", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "The admin panel is built into the existing BeaverView FastAPI application. "
        "No second server, no second deployment. The same nginx config and systemd service "
        "that run the dashboard also serve the admin panel.",
        s["body"]))

    story.append(Paragraph("URL structure", s["h2"]))
    story.append(tbl([
        ["https://beaverview/",                "Main dashboard — all authenticated users"],
        ["https://beaverview/admin",           "Admin home — summary dashboard"],
        ["https://beaverview/admin/rooms",     "Room and building editor"],
        ["https://beaverview/admin/connectors","Connector on/off and credential management"],
        ["https://beaverview/admin/users",     "Role assignment (Technician / Admin)"],
        ["https://beaverview/admin/logs",      "Audit log viewer, export, and archive"],
        ["https://beaverview/api/admin/...",   "Admin API endpoints (JSON, called by the admin UI)"],
    ], s, cw=[3.0*inch,3.5*inch], hdr=["URL","Who / what"]))

    story.append(Paragraph("How access control works", s["h2"]))
    story.append(Paragraph(
        "All /admin routes check the user's Entra session token. "
        "If the user is not in the BeaverView Admins Azure AD group, they get a 403 page. "
        "The check happens server-side — there is nothing in the HTML that exposes admin "
        "content to non-admins.",
        s["body"]))
    story.append(tbl([
        ["Not logged in",              "Redirected to Entra login, then back to /admin"],
        ["Logged in, Technician group","403 Forbidden — a plain error page with a 'Back to dashboard' link"],
        ["Logged in, Admin group",     "Full access to all /admin pages"],
    ], s, cw=[2.0*inch,4.5*inch], hdr=["User state","What they see"]))

    story.append(Paragraph("Data flow — before vs. after this playbook", s["h2"]))
    story.append(tbl([
        ["Room/building data","dashboard/data.js (static file)","SQLite database (campuses, buildings, rooms, devices tables)"],
        ["Connector config",  "Hardcoded in main.py CONNECTOR_REGISTRY","connector_config table in SQLite"],
        ["User roles",        "Azure AD group membership only","user_roles table + Azure AD group fallback"],
        ["Audit log",         "SQLite audit_log table (already)","Same table, new admin UI to query/export it"],
    ], s, cw=[1.5*inch,2.2*inch,2.8*inch], hdr=["Data","Before","After"]))

    story.append(box("Why move room data to the database?", [
        "Currently a bad edit in data.js can break the entire dashboard with a JavaScript syntax error. "
        "Once room data lives in SQLite:",
        "  •  Admin panel validates input before saving — no syntax errors possible",
        "  •  Changes are instantly visible to all users (no file save + browser reload cycle)",
        "  •  Every edit is timestamped and attributed to the admin who made it",
        "  •  Rollback is a database query, not a git checkout",
        "  •  data.js becomes a seed/backup file and is kept for reference",
    ], s, color=STATUS_OK))
    story.append(PageBreak())

# ── PART 2: DATABASE SCHEMA ────────────────────────────────────────────────────
def part2(story, s):
    story.append(Paragraph("Part 2 — Database Schema Changes", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "Add these tables to beaverview.db. The existing audit_log table is unchanged. "
        "Run this SQL once — either directly with the sqlite3 command or by adding it to "
        "main.py's startup code.",
        s["body"]))

    story.append(Paragraph("Run this SQL to create the new tables", s["h2"]))
    story.append(cb([
        "-- campuses",
        "CREATE TABLE IF NOT EXISTS campuses (",
        "    id        TEXT PRIMARY KEY,   -- 'corvallis' | 'cascades' | 'hatfield'",
        "    name      TEXT NOT NULL,",
        "    subtitle  TEXT,",
        "    center_lng REAL,              -- map center longitude",
        "    center_lat REAL,              -- map center latitude",
        "    zoom      REAL DEFAULT 15",
        ");",
        "",
        "-- buildings",
        "CREATE TABLE IF NOT EXISTS buildings (",
        "    id         INTEGER PRIMARY KEY AUTOINCREMENT,",
        "    campus_id  TEXT NOT NULL REFERENCES campuses(id),",
        "    code       TEXT NOT NULL,     -- e.g. 'KAd', 'LINC', 'MU'",
        "    name       TEXT NOT NULL,     -- e.g. 'Kerr Administration'",
        "    active     INTEGER DEFAULT 1  -- 0 = hidden from dashboard",
        ");",
        "",
        "-- rooms",
        "CREATE TABLE IF NOT EXISTS rooms (",
        "    id              TEXT PRIMARY KEY,    -- 'corvallis-kad-101'",
        "    building_id     INTEGER NOT NULL REFERENCES buildings(id),",
        "    number          TEXT NOT NULL,       -- '101'",
        "    type            TEXT,                -- 'Lecture Hall'",
        "    status          TEXT DEFAULT 'offline',",
        "    health          INTEGER DEFAULT 0,   -- 0-100",
        "    active_event    TEXT,",
        "    fusion          TEXT DEFAULT 'mock', -- 'online'|'offline'|'mock'",
        "    display         TEXT DEFAULT 'unknown',",
        "    screenconnect   INTEGER DEFAULT 0,   -- boolean",
        "    wattbox         INTEGER DEFAULT 0,",
        "    hybrid          INTEGER DEFAULT 0,",
        "    stale           INTEGER DEFAULT 0,",
        "    notes           TEXT,",
        "    updated_at      TEXT               -- ISO timestamp of last edit",
        ");",
        "",
        "-- devices (linked to a room)",
        "CREATE TABLE IF NOT EXISTS devices (",
        "    id          INTEGER PRIMARY KEY AUTOINCREMENT,",
        "    room_id     TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,",
        "    device_type TEXT NOT NULL,   -- 'Display', 'Control Processor', 'Camera', ...",
        "    manufacturer TEXT,",
        "    model       TEXT,",
        "    connection  TEXT,            -- 'Sanitized host' or real hostname (server-side only)",
        "    sort_order  INTEGER DEFAULT 0",
        ");",
        "",
        "-- incidents (linked to a room)",
        "CREATE TABLE IF NOT EXISTS incidents (",
        "    id        INTEGER PRIMARY KEY AUTOINCREMENT,",
        "    room_id   TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,",
        "    ticket    TEXT NOT NULL,     -- 'INC0012500 - Projector lamp warning'",
        "    status    TEXT DEFAULT 'open'  -- 'open' | 'closed'",
        ");",
        "",
        "-- connector configuration (replaces CONNECTOR_REGISTRY in main.py)",
        "CREATE TABLE IF NOT EXISTS connector_config (",
        "    campus_id       TEXT NOT NULL,",
        "    connector_name  TEXT NOT NULL,   -- 'fusion', 'live25', 'screenconnect', ...",
        "    mode            TEXT DEFAULT 'mock',  -- 'mock' | 'live'",
        "    enabled         INTEGER DEFAULT 1,",
        "    last_synced     TEXT,",
        "    PRIMARY KEY (campus_id, connector_name)",
        ");",
        "",
        "-- user role overrides (Entra group is the primary source of truth;",
        "--   this table adds overrides or notes for users not in either group)",
        "CREATE TABLE IF NOT EXISTS user_roles (",
        "    entra_id    TEXT PRIMARY KEY,   -- Azure AD object ID",
        "    email       TEXT,",
        "    display_name TEXT,",
        "    role        TEXT DEFAULT 'technician',  -- 'technician' | 'admin' | 'readonly'",
        "    notes       TEXT,",
        "    updated_at  TEXT,",
        "    updated_by  TEXT",
        ");",
    ], s))

    story.append(Spacer(1,0.15*inch))
    story.append(box("Add to api/main.py startup — auto-create tables on first run", [
        "In main.py, find the database initialization section and add the CREATE TABLE IF NOT EXISTS",
        "statements above. They are safe to run every startup because of the IF NOT EXISTS clause.",
        "The existing audit_log table will not be affected.",
    ], s, color=STATUS_INFO))
    story.append(PageBreak())

# ── PART 3: DATA MIGRATION ─────────────────────────────────────────────────────
def part3(story, s):
    story.append(Paragraph("Part 3 — Data Migration (data.js → Database)", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "This is a one-time operation. The migration script reads data.js, parses the "
        "campus/building/room structure, and inserts everything into the new database tables. "
        "data.js is not modified — it stays as a backup and seed file.",
        s["body"]))

    story.append(Paragraph("Save this as api/migrate_data.py and run it once", s["h2"]))
    story.append(cb([
        "\"\"\"",
        "One-time migration: imports data.js room inventory into SQLite.",
        "Run once from the api/ folder:  python3 migrate_data.py",
        "Safe to re-run — it clears existing rows first (does NOT touch audit_log).",
        "\"\"\"",
        "import sqlite3, json, re, os",
        "",
        "DB_PATH   = os.path.join(os.path.dirname(__file__), 'beaverview.db')",
        "DATA_PATH = os.path.join(os.path.dirname(__file__), '../dashboard/data.js')",
        "",
        "def extract_json(js_text):",
        "    # Strip 'window.dashboardData = ' prefix and trailing semicolons",
        "    match = re.search(r'window\\.dashboardData\\s*=\\s*(\\{.*\\})', js_text, re.DOTALL)",
        "    if not match:",
        "        raise ValueError('Could not find window.dashboardData in data.js')",
        "    # Replace JS true/false/null with JSON equivalents",
        "    json_str = match.group(1)",
        "    json_str = re.sub(r'\\btrue\\b',  'true',  json_str)",
        "    json_str = re.sub(r'\\bfalse\\b', 'false', json_str)",
        "    json_str = re.sub(r'\\bnull\\b',  'null',  json_str)",
        "    # Remove trailing commas before } or ]",
        "    json_str = re.sub(r',\\s*([}\\]])', r'\\1', json_str)",
        "    return json.loads(json_str)",
        "",
        "def migrate():",
        "    with open(DATA_PATH) as f:",
        "        data = extract_json(f.read())",
        "",
        "    con = sqlite3.connect(DB_PATH)",
        "    cur = con.cursor()",
        "",
        "    # Clear existing data (preserves audit_log and user_roles)",
        "    for tbl in ['devices','incidents','rooms','buildings','campuses','connector_config']:",
        "        cur.execute(f'DELETE FROM {tbl}')",
        "",
        "    for campus in data['campuses']:",
        "        cid = campus['id']",
        "        # Insert campus",
        "        cur.execute('INSERT INTO campuses(id,name,subtitle) VALUES(?,?,?)',",
        "                    (cid, campus['name'], campus.get('subtitle','')))",
        "",
        "        # Seed connector_config for this campus",
        "        for conn_name in ['fusion','live25','screenconnect','wattbox',",
        "                          'servicenow','sharepoint','xpanel','ptz']:",
        "            mode = campus.get('connectors',{}).get(conn_name,'mock')",
        "            cur.execute('INSERT INTO connector_config(campus_id,connector_name,mode)'",
        "                        ' VALUES(?,?,?)', (cid, conn_name, mode))",
        "",
        "        for bldg in campus.get('buildings',[]):",
        "            cur.execute('INSERT INTO buildings(campus_id,code,name) VALUES(?,?,?)'",
        "                        ' RETURNING id',",
        "                        (cid, bldg['code'], bldg['name']))",
        "            bldg_id = cur.fetchone()[0]",
        "",
        "            for room in bldg.get('rooms',[]):",
        "                room_id = f\"{cid}-{bldg['code'].lower()}-{room['number']}\".lower()",
        "                room_id = re.sub(r'[^a-z0-9]+','-', room_id).strip('-')",
        "                cur.execute(",
        "                    'INSERT INTO rooms(id,building_id,number,type,status,health,'",
        "                    '  active_event,fusion,display,screenconnect,wattbox,hybrid,stale)'",
        "                    ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',",
        "                    (room_id, bldg_id, room['number'], room.get('type',''),",
        "                     room.get('status','offline'), room.get('health',0),",
        "                     room.get('activeEvent',''), room.get('fusion','mock'),",
        "                     room.get('display','unknown'),",
        "                     int(room.get('screenconnect', False)),",
        "                     int(room.get('wattbox', False)),",
        "                     int(room.get('hybrid', False)),",
        "                     int(room.get('stale', False))))",
        "",
        "                for i, dev in enumerate(room.get('devices',[])):",
        "                    cur.execute(",
        "                        'INSERT INTO devices(room_id,device_type,manufacturer,model,connection,sort_order)'",
        "                        ' VALUES(?,?,?,?,?,?)',",
        "                        (room_id,",
        "                         dev[0] if len(dev)>0 else '',",
        "                         dev[1] if len(dev)>1 else '',",
        "                         dev[2] if len(dev)>2 else '',",
        "                         dev[3] if len(dev)>3 else '',",
        "                         i))",
        "",
        "                for inc in room.get('incidents',{}).get('open',[]):",
        "                    cur.execute('INSERT INTO incidents(room_id,ticket,status) VALUES(?,?,?)'",
        "                                ,(room_id, inc, 'open'))",
        "                for inc in room.get('incidents',{}).get('closed',[]):",
        "                    cur.execute('INSERT INTO incidents(room_id,ticket,status) VALUES(?,?,?)'",
        "                                ,(room_id, inc, 'closed'))",
        "",
        "    con.commit()",
        "    con.close()",
        "    print('Migration complete.')",
        "    # Print summary",
        "    con2 = sqlite3.connect(DB_PATH)",
        "    for tbl in ['campuses','buildings','rooms','devices']:",
        "        n = con2.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]",
        "        print(f'  {tbl}: {n} rows')",
        "    con2.close()",
        "",
        "if __name__ == '__main__':",
        "    migrate()",
    ], s))

    story.append(Spacer(1,0.1*inch))
    story.append(Paragraph("Run the migration", s["h2"]))
    story.append(cb([
        "# SSH into the VM, then:",
        "cd /home/beaverview/app/api",
        "sudo -u beaverview venv/bin/python3 migrate_data.py",
        "",
        "# Expected output:",
        "# Migration complete.",
        "#   campuses: 3 rows",
        "#   buildings: 278 rows",
        "#   rooms: 954 rows",
        "#   devices: ~2800 rows",
    ], s))

    story.append(Spacer(1,0.1*inch))
    story.append(box("After migration — update main.py to read from the database", [
        "The main.py API endpoints currently return data from data_mock.py (which reads data.js).",
        "After migration, update each endpoint to query the new tables instead.",
        "Part 4 shows the updated endpoint patterns.",
        "data.js and data_mock.py are kept as fallback references — do not delete them yet.",
    ], s, color=STATUS_WARN))
    story.append(PageBreak())

# ── PART 4: NEW API ENDPOINTS ──────────────────────────────────────────────────
def part4(story, s):
    story.append(Paragraph("Part 4 — New API Endpoints", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "Add these endpoints to api/main.py. All /api/admin/... endpoints require the "
        "Admin role check. All state-changing endpoints log to audit_log.",
        s["body"]))

    story.append(Paragraph("Room and building CRUD", s["h2"]))
    story.append(tbl([
        ["GET    /api/admin/campuses",                  "List all campuses with building/room counts"],
        ["GET    /api/admin/buildings?campus_id=...",   "List buildings for a campus"],
        ["GET    /api/admin/rooms?building_id=...",     "List rooms for a building (with devices)"],
        ["POST   /api/admin/rooms",                     "Create a new room"],
        ["PUT    /api/admin/rooms/{room_id}",           "Update a room's fields"],
        ["DELETE /api/admin/rooms/{room_id}",           "Delete a room and its devices"],
        ["POST   /api/admin/rooms/{room_id}/devices",   "Add a device to a room"],
        ["DELETE /api/admin/devices/{device_id}",       "Remove a device from a room"],
        ["POST   /api/admin/buildings",                 "Create a new building"],
        ["PUT    /api/admin/buildings/{building_id}",   "Update a building"],
        ["DELETE /api/admin/buildings/{building_id}",   "Delete a building and all its rooms"],
    ], s, cw=[2.8*inch,3.7*inch], hdr=["Endpoint","What it does"]))

    story.append(Paragraph("Log management", s["h2"]))
    story.append(tbl([
        ["GET  /api/admin/logs",             "Query audit log with filters: campus, room_id, user, action_type, date_from, date_to, limit, offset"],
        ["GET  /api/admin/logs/export",      "Download filtered log as CSV (streams the file)"],
        ["POST /api/admin/logs/archive",     "Move entries older than N days to audit_log_archive table"],
        ["DELETE /api/admin/logs/purge",     "Permanently delete entries older than N days (requires confirmation token)"],
        ["GET  /api/admin/logs/summary",     "Aggregated stats: top rooms, top actions, top users, daily counts"],
    ], s, cw=[2.8*inch,3.7*inch], hdr=["Endpoint","What it does"]))

    story.append(Paragraph("Connector management", s["h2"]))
    story.append(tbl([
        ["GET  /api/admin/connectors",                           "List all connectors and their current mode/status"],
        ["PUT  /api/admin/connectors/{campus}/{name}/mode",      "Set mode to 'live' or 'mock'"],
        ["POST /api/admin/connectors/{campus}/{name}/test",      "Test the connector and return live status"],
    ], s, cw=[2.8*inch,3.7*inch], hdr=["Endpoint","What it does"]))

    story.append(box("Connector credentials stay in .env — not in the database", [
        "API keys and passwords are NOT stored in the database. They stay in the .env file on disk "
        "(permissions 600, owned by the beaverview service account). The connector management UI "
        "shows which credentials are present (yes/no) without displaying their values, and lets "
        "admins toggle connectors on/off. To change a credential value, an admin still SSH's in "
        "and edits .env — this is intentional security hardening.",
    ], s, color=STATUS_WARN))

    story.append(Paragraph("User role management", s["h2"]))
    story.append(tbl([
        ["GET    /api/admin/users",             "List users who have logged in, with their current role"],
        ["PUT    /api/admin/users/{entra_id}",  "Override a user's role (technician/admin/readonly)"],
        ["DELETE /api/admin/users/{entra_id}",  "Remove override (user falls back to Entra group membership)"],
    ], s, cw=[2.8*inch,3.7*inch], hdr=["Endpoint","What it does"]))

    story.append(Paragraph("Admin auth middleware — add to main.py", s["h2"]))
    story.append(cb([
        "from fastapi import Depends, HTTPException, Request",
        "",
        "def require_admin(request: Request):",
        "    \"\"\"",
        "    Dependency injected into all /api/admin/... routes.",
        "    Checks that the session belongs to a user in the Admin group.",
        "    Raises 403 if not. Raises 401 if not logged in at all.",
        "    \"\"\"",
        "    session = request.session  # from starlette-sessions middleware",
        "    user = session.get('user')",
        "    if not user:",
        "        raise HTTPException(401, 'Not authenticated')",
        "    groups = user.get('groups', [])",
        "    admin_group = os.getenv('AZURE_GROUP_ADMIN', '')",
        "    if admin_group not in groups:",
        "        raise HTTPException(403, 'Admin access required')",
        "    return user",
        "",
        "# Usage on any admin endpoint:",
        "@app.get('/api/admin/rooms')",
        "def admin_list_rooms(campus_id: str, admin=Depends(require_admin)):",
        "    # admin = the logged-in user dict",
        "    ...",
    ], s))
    story.append(PageBreak())

# ── PART 5: ADMIN PANEL FRONTEND ───────────────────────────────────────────────
def part5(story, s):
    story.append(Paragraph("Part 5 — Admin Panel Frontend", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "The admin panel is a separate set of HTML/CSS/JS files served from the same FastAPI app. "
        "It lives in dashboard/admin/ and shares the same design tokens as the main dashboard.",
        s["body"]))

    story.append(Paragraph("File structure to create", s["h2"]))
    story.append(cb([
        "dashboard/",
        "  admin/",
        "    index.html        ← admin home / summary dashboard",
        "    rooms.html        ← room and building editor",
        "    logs.html         ← audit log viewer",
        "    connectors.html   ← connector toggle/status page",
        "    users.html        ← user role management",
        "    admin.js          ← shared JS: auth check, nav, API helpers",
        "    admin.css         ← admin-specific styles (imports main design tokens)",
    ], s))

    story.append(Paragraph("admin.js — shared auth check (add to every admin page)", s["h2"]))
    story.append(cb([
        "// admin.js — included by all admin pages",
        "// Redirects to dashboard if user is not an admin",
        "",
        "(async function() {",
        "  const res = await fetch('/api/me');   // returns {user, role} or 401",
        "  if (!res.ok) { window.location = '/auth/login?next=/admin'; return; }",
        "  const { role } = await res.json();",
        "  if (role !== 'admin') {",
        "    document.body.innerHTML = `",
        "      <div class='admin-403'>",
        "        <h1>Access denied</h1>",
        "        <p>Your account does not have admin access to BeaverView.</p>",
        "        <a href='/'>Back to dashboard</a>",
        "      </div>`;",
        "    return;",
        "  }",
        "  // Auth OK — render the page",
        "  document.dispatchEvent(new Event('admin-ready'));",
        "})();",
        "",
        "// Shared API helper with CSRF-safe headers",
        "async function adminFetch(url, options = {}) {",
        "  return fetch(url, {",
        "    ...options,",
        "    headers: { 'Content-Type': 'application/json', ...options.headers }",
        "  });",
        "}",
    ], s))

    story.append(Paragraph("Add /api/me endpoint to main.py", s["h2"]))
    story.append(cb([
        "@app.get('/api/me')",
        "def me(request: Request):",
        "    user = request.session.get('user')",
        "    if not user:",
        "        raise HTTPException(401, 'Not authenticated')",
        "    groups = user.get('groups', [])",
        "    admin_gid = os.getenv('AZURE_GROUP_ADMIN', '')",
        "    tech_gid  = os.getenv('AZURE_GROUP_TECHNICIAN', '')",
        "    if admin_gid and admin_gid in groups:",
        "        role = 'admin'",
        "    elif tech_gid and tech_gid in groups:",
        "        role = 'technician'",
        "    else:",
        "        role = 'readonly'",
        "    return {",
        "        'user':  user.get('preferred_username'),",
        "        'name':  user.get('name'),",
        "        'role':  role,",
        "        'groups': groups",
        "    }",
    ], s))

    story.append(Paragraph("Serve admin pages from FastAPI", s["h2"]))
    story.append(cb([
        "from fastapi.staticfiles import StaticFiles",
        "from fastapi.responses import FileResponse",
        "import os",
        "",
        "DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), '../dashboard')",
        "",
        "# Mount static files",
        "app.mount('/admin', StaticFiles(directory=os.path.join(DASHBOARD_DIR,'admin'),",
        "                                html=True), name='admin')",
        "",
        "# Fallback: any /admin path that doesn't match a file serves index.html",
        "@app.get('/admin/{path:path}')",
        "def admin_catch(path: str):",
        "    return FileResponse(os.path.join(DASHBOARD_DIR, 'admin', 'index.html'))",
    ], s))

    story.append(box("Admin link in the main dashboard header", [
        "In dashboard/index.html, add an 'Admin' link to the header that is only shown when",
        "the user's role is 'admin'. The /api/me endpoint provides the role. Wire it in app.js:",
        "",
        "  fetch('/api/me').then(r => r.json()).then(({role}) => {",
        "    if (role === 'admin')",
        "      document.getElementById('adminLink').style.display = 'inline';",
        "  });",
    ], s, color=STATUS_INFO))
    story.append(PageBreak())

# ── PART 6: SUMMARY DASHBOARD ──────────────────────────────────────────────────
def part6(story, s):
    story.append(Paragraph("Part 6 — Admin Summary Dashboard", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "The admin home page (/admin) shows a live summary of system activity. "
        "It fetches data from /api/admin/logs/summary and the connector health endpoints.",
        s["body"]))

    story.append(Paragraph("Summary dashboard — what to show", s["h2"]))
    story.append(tbl([
        ["Stat cards (top row)",    "Total rooms · Active rooms (in-use) · Open incidents · Connectors online"],
        ["Activity this week",      "Bar chart: actions per day for the past 7 days\n(use Chart.js — free, no CDN needed, copy to vendor/)"],
        ["Top 5 busiest rooms",     "Rooms with most audit log entries in the last 30 days"],
        ["Top 5 most-used tools",   "action_type count: xpanel_launched, screenconnect_launched, etc."],
        ["Recent activity feed",    "Last 20 audit entries across all campuses, live-polled every 60s"],
        ["Connector health grid",   "One badge per connector per campus — green/amber/gray"],
    ], s, cw=[1.9*inch,4.6*inch], hdr=["Section","Content"]))

    story.append(Paragraph("/api/admin/logs/summary — add to main.py", s["h2"]))
    story.append(cb([
        "@app.get('/api/admin/logs/summary')",
        "def logs_summary(days: int = 7, admin=Depends(require_admin)):",
        "    con = get_db()",
        "    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()",
        "",
        "    # Daily action counts",
        "    daily = con.execute(",
        "        'SELECT date(ts) as day, COUNT(*) as n FROM audit_log'",
        "        ' WHERE ts >= ? GROUP BY day ORDER BY day',",
        "        (cutoff,)).fetchall()",
        "",
        "    # Top rooms",
        "    top_rooms = con.execute(",
        "        'SELECT room_id, COUNT(*) as n FROM audit_log'",
        "        ' WHERE ts >= ? GROUP BY room_id ORDER BY n DESC LIMIT 5',",
        "        (cutoff,)).fetchall()",
        "",
        "    # Top actions",
        "    top_actions = con.execute(",
        "        'SELECT action_type, COUNT(*) as n FROM audit_log'",
        "        ' WHERE ts >= ? GROUP BY action_type ORDER BY n DESC LIMIT 10',",
        "        (cutoff,)).fetchall()",
        "",
        "    # Stat cards",
        "    total_rooms = con.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]",
        "    active_rooms = con.execute(",
        "        \"SELECT COUNT(*) FROM rooms WHERE status='in-use'\").fetchone()[0]",
        "    open_incidents = con.execute(",
        "        \"SELECT COUNT(*) FROM incidents WHERE status='open'\").fetchone()[0]",
        "",
        "    return {",
        "        'stats':       {'total_rooms': total_rooms, 'active_rooms': active_rooms,",
        "                        'open_incidents': open_incidents},",
        "        'daily':       [{'day': r[0], 'n': r[1]} for r in daily],",
        "        'top_rooms':   [{'room_id': r[0], 'n': r[1]} for r in top_rooms],",
        "        'top_actions': [{'action': r[0], 'n': r[1]} for r in top_actions],",
        "    }",
    ], s))
    story.append(PageBreak())

# ── PART 7: ROOM EDITOR ────────────────────────────────────────────────────────
def part7(story, s):
    story.append(Paragraph("Part 7 — Room and Building Editor", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "The rooms.html admin page lets admins add, edit, and delete rooms and buildings "
        "through a web form. No code editing or SSH required.",
        s["body"]))

    story.append(Paragraph("Page layout and UX flow", s["h2"]))
    story.append(tbl([
        ["Left panel: campus + building tree",
         "Three campus tabs (Corvallis / Cascades / Hatfield).\n"
         "Each campus shows its buildings in a collapsible list.\n"
         "Click a building to load its rooms in the right panel.\n"
         "'+ Add building' button at the bottom of each campus."],
        ["Right panel: room list for selected building",
         "Table: Room # | Type | Status | ScreenConnect | WattBox | Actions.\n"
         "Click a row to open the edit drawer.\n"
         "'+ Add room' button above the table."],
        ["Edit drawer (slides in from right)",
         "Form fields for all room properties.\n"
         "Devices section: add/remove device rows.\n"
         "Save button (PUT request) and Delete button with confirm dialog.\n"
         "All changes logged to audit_log with the admin's username."],
    ], s, cw=[1.9*inch,4.6*inch]))

    story.append(Paragraph("PUT /api/admin/rooms/{room_id} — add to main.py", s["h2"]))
    story.append(cb([
        "from pydantic import BaseModel",
        "from typing import Optional, List",
        "",
        "class DeviceIn(BaseModel):",
        "    device_type:  str",
        "    manufacturer: Optional[str] = ''",
        "    model:        Optional[str] = ''",
        "    connection:   Optional[str] = ''",
        "",
        "class RoomIn(BaseModel):",
        "    number:        str",
        "    type:          Optional[str] = ''",
        "    status:        str = 'offline'",
        "    health:        int = 0",
        "    active_event:  Optional[str] = ''",
        "    fusion:        str = 'mock'",
        "    display:       str = 'unknown'",
        "    screenconnect: bool = False",
        "    wattbox:       bool = False",
        "    hybrid:        bool = False",
        "    stale:         bool = False",
        "    notes:         Optional[str] = ''",
        "    devices:       List[DeviceIn] = []",
        "",
        "@app.put('/api/admin/rooms/{room_id}')",
        "def admin_update_room(room_id: str, body: RoomIn,",
        "                      request: Request, admin=Depends(require_admin)):",
        "    con = get_db()",
        "    now = _now()",
        "    con.execute(",
        "        'UPDATE rooms SET number=?,type=?,status=?,health=?,active_event=?,'",
        "        '  fusion=?,display=?,screenconnect=?,wattbox=?,hybrid=?,stale=?,'",
        "        '  notes=?,updated_at=? WHERE id=?',",
        "        (body.number, body.type, body.status, body.health, body.active_event,",
        "         body.fusion, body.display, int(body.screenconnect), int(body.wattbox),",
        "         int(body.hybrid), int(body.stale), body.notes, now, room_id))",
        "    # Replace devices",
        "    con.execute('DELETE FROM devices WHERE room_id=?', (room_id,))",
        "    for i, dev in enumerate(body.devices):",
        "        con.execute(",
        "            'INSERT INTO devices(room_id,device_type,manufacturer,model,connection,sort_order)'",
        "            ' VALUES(?,?,?,?,?,?)',",
        "            (room_id, dev.device_type, dev.manufacturer, dev.model, dev.connection, i))",
        "    con.commit()",
        "    # Log the admin action",
        "    con.execute(",
        "        'INSERT INTO audit_log(ts,user,room_id,action_type,outcome)'",
        "        ' VALUES(?,?,?,?,?)',",
        "        (now, admin['preferred_username'], room_id, 'admin_room_updated', 'success'))",
        "    con.commit()",
        "    return {'status': 'ok', 'room_id': room_id}",
    ], s))
    story.append(PageBreak())

# ── PART 8: LOG MANAGEMENT ─────────────────────────────────────────────────────
def part8(story, s):
    story.append(Paragraph("Part 8 — Log Management", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "The logs.html admin page is a full-featured audit log viewer with filtering, "
        "search, CSV export, and log archival.",
        s["body"]))

    story.append(Paragraph("Log viewer page layout", s["h2"]))
    story.append(tbl([
        ["Filter bar (top)",   "Campus dropdown · Room ID search · Action type · User · Date from/to · Reset button"],
        ["Results table",      "Columns: Timestamp · User · Campus · Room · Action · Outcome · Notes\nPaginated (50 per page).\nClick a row for full detail in a sidebar."],
        ["Export buttons",     "'Export CSV' and 'Export Excel' — downloads the current filtered set.\nNo page limit on export."],
        ["Bulk actions bar",   "'Archive entries older than:' date picker + Archive button.\n'Purge archived entries' button (requires typing CONFIRM to proceed)."],
    ], s, cw=[1.6*inch,4.9*inch]))

    story.append(Paragraph("GET /api/admin/logs — add to main.py", s["h2"]))
    story.append(cb([
        "@app.get('/api/admin/logs')",
        "def admin_logs(",
        "    campus:      str  = None,",
        "    room_id:     str  = None,",
        "    user:        str  = None,",
        "    action_type: str  = None,",
        "    date_from:   str  = None,   # ISO date: '2025-01-01'",
        "    date_to:     str  = None,",
        "    limit:       int  = 50,",
        "    offset:      int  = 0,",
        "    admin=Depends(require_admin)",
        "):",
        "    where, params = [], []",
        "    if campus:      where.append(\"room_id LIKE ?\");   params.append(f'{campus}-%')",
        "    if room_id:     where.append(\"room_id = ?\");      params.append(room_id)",
        "    if user:        where.append(\"user LIKE ?\");      params.append(f'%{user}%')",
        "    if action_type: where.append(\"action_type = ?\");  params.append(action_type)",
        "    if date_from:   where.append(\"ts >= ?\");          params.append(date_from)",
        "    if date_to:     where.append(\"ts <= ?\");          params.append(date_to + 'T23:59:59')",
        "    sql = 'SELECT * FROM audit_log'",
        "    if where: sql += ' WHERE ' + ' AND '.join(where)",
        "    sql += ' ORDER BY ts DESC LIMIT ? OFFSET ?'",
        "    params += [limit, offset]",
        "    con = get_db()",
        "    rows = con.execute(sql, params).fetchall()",
        "    total = con.execute('SELECT COUNT(*) FROM audit_log' +",
        "        (' WHERE ' + ' AND '.join(where) if where else ''),",
        "        params[:-2]).fetchone()[0]",
        "    cols = ['id','ts','user','room_id','action_type','target','outcome','notes']",
        "    return {'total': total, 'rows': [dict(zip(cols,r)) for r in rows]}",
    ], s))

    story.append(Paragraph("GET /api/admin/logs/export — CSV download", s["h2"]))
    story.append(cb([
        "from fastapi.responses import StreamingResponse",
        "import csv, io",
        "",
        "@app.get('/api/admin/logs/export')",
        "def export_logs(",
        "    # Same filter params as /api/admin/logs (no limit/offset)",
        "    campus: str = None, room_id: str = None, user: str = None,",
        "    action_type: str = None, date_from: str = None, date_to: str = None,",
        "    admin=Depends(require_admin)",
        "):",
        "    # Build the same WHERE clause as admin_logs() above",
        "    # ... (same filter logic, no LIMIT) ...",
        "    rows = con.execute(sql, params).fetchall()",
        "    cols = ['id','ts','user','room_id','action_type','target','outcome','notes']",
        "",
        "    output = io.StringIO()",
        "    writer = csv.writer(output)",
        "    writer.writerow(cols)   # header row",
        "    writer.writerows(rows)",
        "    output.seek(0)",
        "",
        "    return StreamingResponse(",
        "        iter([output.getvalue()]),",
        "        media_type='text/csv',",
        "        headers={'Content-Disposition': 'attachment; filename=beaverview-audit-log.csv'}",
        "    )",
    ], s))

    story.append(Paragraph("POST /api/admin/logs/archive — move old entries", s["h2"]))
    story.append(cb([
        "@app.post('/api/admin/logs/archive')",
        "def archive_logs(older_than_days: int = 90, admin=Depends(require_admin)):",
        "    \"\"\"Move entries older than N days to audit_log_archive table.\"\"\"",
        "    con = get_db()",
        "    # Create archive table if it doesn't exist (same schema as audit_log)",
        "    con.execute('CREATE TABLE IF NOT EXISTS audit_log_archive AS'",
        "                ' SELECT * FROM audit_log WHERE 0')",
        "    cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat()",
        "    con.execute('INSERT INTO audit_log_archive SELECT * FROM audit_log WHERE ts < ?'",
        "               , (cutoff,))",
        "    result = con.execute('DELETE FROM audit_log WHERE ts < ?', (cutoff,))",
        "    count = result.rowcount",
        "    con.commit()",
        "    # Log this admin action",
        "    con.execute('INSERT INTO audit_log(ts,user,room_id,action_type,notes,outcome)'",
        "                ' VALUES(?,?,?,?,?,?)',",
        "                (_now(), admin['preferred_username'], 'SYSTEM', 'admin_log_archive',",
        "                 f'archived {count} entries older than {older_than_days} days','success'))",
        "    con.commit()",
        "    return {'archived': count, 'cutoff': cutoff}",
    ], s))
    story.append(PageBreak())

# ── PART 9: CONNECTOR MANAGEMENT ──────────────────────────────────────────────
def part9(story, s):
    story.append(Paragraph("Part 9 — Connector Management", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "The connectors.html admin page shows the status of every connector across all campuses "
        "and lets admins toggle them between live and mock mode without SSHing into the server.",
        s["body"]))

    story.append(Paragraph("Connector management page layout", s["h2"]))
    story.append(tbl([
        ["Status grid",     "One row per connector, one column per campus.\n"
                            "Each cell shows a badge: green (live) / gray (mock) / amber (degraded).\n"
                            "Below each badge: last synced timestamp."],
        ["Toggle control",  "Click a badge to flip it between mock and live.\n"
                            "If switching to live but no credentials are present, shows a warning:\n"
                            "'No credentials configured — edit .env on the server to add them.'"],
        ["Test button",     "Runs a live health check for that connector right now.\n"
                            "Shows response time and any error message."],
        ["Credential status","A column showing whether credentials are present in .env (yes/no).\n"
                            "Never shows the actual value."],
    ], s, cw=[1.6*inch,4.9*inch]))

    story.append(Paragraph("PUT /api/admin/connectors/{campus}/{name}/mode — add to main.py", s["h2"]))
    story.append(cb([
        "@app.put('/api/admin/connectors/{campus_id}/{connector_name}/mode')",
        "def set_connector_mode(",
        "    campus_id: str,",
        "    connector_name: str,",
        "    mode: str,                     # 'live' or 'mock'",
        "    request: Request,",
        "    admin=Depends(require_admin)",
        "):",
        "    if mode not in ('live', 'mock'):",
        "        raise HTTPException(400, 'mode must be live or mock')",
        "    con = get_db()",
        "    # Warn if switching to live with no credentials",
        "    cred_check = {",
        "        'fusion':        bool(_FUSION_KEY),",
        "        'live25':        bool(_LIVE25_USER),",
        "        'screenconnect': bool(_SC_URL),",
        "        'wattbox':       bool(_WATTBOX_KEY or _WATTBOX_DIRECT_USER),",
        "        'servicenow':    bool(_SN_CLIENT),",
        "        'sharepoint':    bool(_SP_URL),",
        "    }",
        "    has_creds = cred_check.get(connector_name, False)",
        "    if mode == 'live' and not has_creds:",
        "        return {'status': 'warning',",
        "                'message': 'No credentials found in .env for this connector.',",
        "                'mode_set': False}",
        "    con.execute(",
        "        'UPDATE connector_config SET mode=? WHERE campus_id=? AND connector_name=?',",
        "        (mode, campus_id, connector_name))",
        "    con.commit()",
        "    # Log it",
        "    con.execute('INSERT INTO audit_log(ts,user,room_id,action_type,target,outcome)'",
        "                ' VALUES(?,?,?,?,?,?)',",
        "                (_now(), admin['preferred_username'], campus_id,",
        "                 'admin_connector_mode_changed', f'{connector_name}={mode}', 'success'))",
        "    con.commit()",
        "    return {'status': 'ok', 'campus_id': campus_id,",
        "            'connector_name': connector_name, 'mode': mode}",
    ], s))
    story.append(PageBreak())

# ── PART 10: USER ROLE MANAGEMENT ─────────────────────────────────────────────
def part10(story, s):
    story.append(Paragraph("Part 10 — User Role Management", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "The users.html admin page shows everyone who has logged into BeaverView "
        "and lets admins override their role. The primary source of truth is still "
        "the Azure AD group membership — this table adds exceptions.",
        s["body"]))

    story.append(Paragraph("User management page layout", s["h2"]))
    story.append(tbl([
        ["User table",       "Columns: Name · Email · Role (badge) · Role source · Last login · Actions"],
        ["Role source",      "'Azure AD group' — role comes from group membership (no override)\n"
                             "'Manual override' — role was set directly in this table"],
        ["Edit role button", "Dropdown: Technician / Admin / Read-only\nConfirm dialog shows what will change.\n"
                             "Notes field: reason for override (stored in user_roles.notes)."],
        ["Remove override",  "Returns user to their Entra group-based role."],
    ], s, cw=[1.6*inch,4.9*inch]))

    story.append(Paragraph("How roles are resolved at login", s["h2"]))
    story.append(cb([
        "def resolve_role(entra_id: str, entra_groups: list) -> str:",
        "    \"\"\"",
        "    Role resolution order:",
        "    1. Check user_roles table for a manual override",
        "    2. Fall back to Azure AD group membership",
        "    3. Default to 'readonly' if not in any group",
        "    \"\"\"",
        "    con = get_db()",
        "    row = con.execute(",
        "        'SELECT role FROM user_roles WHERE entra_id=?', (entra_id,)).fetchone()",
        "    if row:",
        "        return row[0]   # manual override wins",
        "",
        "    admin_gid = os.getenv('AZURE_GROUP_ADMIN', '')",
        "    tech_gid  = os.getenv('AZURE_GROUP_TECHNICIAN', '')",
        "    if admin_gid and admin_gid in entra_groups:",
        "        return 'admin'",
        "    if tech_gid and tech_gid in entra_groups:",
        "        return 'technician'",
        "    return 'readonly'",
    ], s))
    story.append(PageBreak())

# ── PART 11: SECURITY ──────────────────────────────────────────────────────────
def part11(story, s):
    story.append(Paragraph("Part 11 — Security and Access Control", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))

    story.append(Paragraph("Security rules for the admin panel", s["h2"]))
    story.append(tbl([
        ["All /admin and /api/admin/... routes",
         "Require valid Entra session + Admin group membership.\n"
         "Enforced server-side by the require_admin dependency.\n"
         "The JavaScript auth check in admin.js is a UX convenience only — not a security boundary."],
        ["All admin actions logged",
         "Every POST/PUT/DELETE endpoint writes an entry to audit_log before returning.\n"
         "action_type uses the prefix 'admin_' (e.g., admin_room_updated, admin_log_archive)."],
        ["Input validation",
         "All POST/PUT bodies go through Pydantic models — FastAPI rejects bad input automatically.\n"
         "room_id values are validated to match the pattern: {campus}-{building}-{room} (alphanumeric and hyphens only).\n"
         "Free-text fields (notes, names) are limited to 500 characters."],
        ["SQL injection prevention",
         "All database queries use parameterised statements (? placeholders).\n"
         "Never use string formatting to build SQL queries."],
        ["Credential protection",
         "Connector API keys stay in .env (permissions 600, never in the database).\n"
         "The connector management UI shows 'credentials present: yes/no' only.\n"
         "Admins who need to change credentials SSH into the server and edit .env directly."],
        ["Log deletion requires confirmation",
         "The purge endpoint requires a confirmation_token parameter.\n"
         "The token is generated server-side and returned by a separate /api/admin/logs/purge-token endpoint.\n"
         "Token expires after 60 seconds. This prevents accidental deletion via API replay."],
    ], s, cw=[1.9*inch,4.6*inch], hdr=["Area","Rule"]))

    story.append(Paragraph("Admin audit log action types", s["h2"]))
    story.append(tbl([
        ["admin_room_updated",          "A room's fields or device list was changed"],
        ["admin_room_created",          "A new room was added"],
        ["admin_room_deleted",          "A room was deleted"],
        ["admin_building_updated",      "A building's name or code was changed"],
        ["admin_building_created",      "A new building was added"],
        ["admin_building_deleted",      "A building and all its rooms were deleted"],
        ["admin_connector_mode_changed","A connector was toggled live or mock"],
        ["admin_log_archive",           "Old log entries were moved to the archive table"],
        ["admin_log_purge",             "Old log entries were permanently deleted"],
        ["admin_role_override_set",     "A user's role was manually overridden"],
        ["admin_role_override_removed", "A user's manual role override was removed"],
    ], s, cw=[2.5*inch,4.0*inch], hdr=["action_type","What happened"]))
    story.append(PageBreak())

# ── PART 12: DEPLOYMENT CHECKLIST ─────────────────────────────────────────────
def part12(story, s):
    story.append(Paragraph("Part 12 — Deployment Checklist", s["h1"]))
    story.append(HRFlowable(width="100%",thickness=2,color=OSU_ORANGE,spaceAfter=10))
    story.append(Paragraph(
        "Follow these steps in order on the production VM. Each step assumes the base "
        "BeaverView install from the main playbook is already running.",
        s["body"]))

    deploy_steps = [
        ("Back up the existing database",
         ["    sudo -u beaverview cp /home/beaverview/app/api/beaverview.db \\",
          "        /home/beaverview/backups/beaverview-before-admin-$(date +%Y%m%d).db"]),
        ("Pull the updated code",
         ["    cd /home/beaverview/app",
          "    sudo -u beaverview git pull"]),
        ("Run the database schema migration",
         ["    cd /home/beaverview/app/api",
          "    sudo -u beaverview venv/bin/python3 -c \\",
          "      \"from main import init_db; init_db()\"",
          "",
          "  Or run the SQL from Part 2 directly:",
          "    sudo -u beaverview sqlite3 beaverview.db < admin_schema.sql"]),
        ("Run the data migration (data.js → DB)",
         ["    sudo -u beaverview venv/bin/python3 migrate_data.py",
          "",
          "  Confirm row counts look right before proceeding.",
          "  If something looks wrong, restore the backup from Step 1 and investigate."]),
        ("Create the dashboard/admin/ folder and files",
         ["    sudo -u beaverview mkdir -p /home/beaverview/app/dashboard/admin",
          "  Copy or create: index.html, rooms.html, logs.html, connectors.html, users.html",
          "  Copy or create: admin.js, admin.css"]),
        ("Restart BeaverView",
         ["    sudo systemctl restart beaverview",
          "    sudo systemctl status beaverview   # confirm active (running)"]),
        ("Test admin access from Windows",
         ["  Open https://beaverview/admin in Chrome or Edge.",
          "  Log in with OSU credentials.",
          "  If in the Admins group: you should see the summary dashboard.",
          "  If in the Technicians group: you should see the 403 page.",
          "  If not in either group: you should see 403 page.",
          "",
          "  Test room edit: go to /admin/rooms, click a room, change the type, save.",
          "  Verify the change appears on the main dashboard at https://beaverview/.",
          "",
          "  Test log export: go to /admin/logs, click Export CSV.",
          "  Open the downloaded file in Excel and confirm it has data."]),
        ("Verify all admin actions appear in the audit log",
         ["    curl -k 'https://beaverview/api/audit?action_type=admin_room_updated'",
          "  Should return the room edit you made in Step 7."]),
    ]

    for i, (title, lines) in enumerate(deploy_steps):
        story.append(KeepTogether([
            st(i+1, title, lines, s),
            Spacer(1,0.12*inch),
        ]))

    story.append(box("Next steps after the admin panel is running", [
        "  •  Set up a cron job to auto-archive log entries older than 90 days (Part 8)",
        "  •  Point UptimeRobot at /api/health to monitor the service",
        "  •  Add the 'Admin' header link to the main dashboard (Part 5)",
        "  •  Train admins on the room editor and log export workflow",
        "  •  Consider adding a rate limit to /api/admin/logs/export to prevent large downloads",
    ], s, color=OSU_ORANGE))

    story.append(Spacer(1,0.3*inch))
    story.append(HRFlowable(width="100%",thickness=1,color=BORDER_GRAY,spaceAfter=8))
    story.append(Paragraph(
        "BeaverView Admin Panel Playbook  ·  OSU Presentation Support  ·  Generated 2025",
        s["foot"]))

# ── BUILD ──────────────────────────────────────────────────────────────────────
def build():
    output = "/Users/cam/Documents/New project/BeaverView-AdminPanel-Playbook.pdf"
    doc = SimpleDocTemplate(output, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.6*inch, bottomMargin=0.5*inch,
        title="BeaverView — Admin Panel Playbook",
        author="OSU Presentation Support",
        subject="Room editor, log management, connector control, user roles")
    styles = S()
    story = []
    cover(story, styles)
    part1(story, styles)
    part2(story, styles)
    part3(story, styles)
    part4(story, styles)
    part5(story, styles)
    part6(story, styles)
    part7(story, styles)
    part8(story, styles)
    part9(story, styles)
    part10(story, styles)
    part11(story, styles)
    part12(story, styles)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF written to: {output}")

if __name__ == "__main__":
    build()
