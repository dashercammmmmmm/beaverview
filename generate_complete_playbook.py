"""
BeaverView — COMPLETE BUILD PLAYBOOK Generator
Covers every file, every step, copy-paste ready.
Run: python3 generate_complete_playbook.py
Output: BeaverView-Complete-Build-Playbook.pdf
"""

import os, html
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

HERE       = os.path.dirname(os.path.abspath(__file__))
API_DIR    = os.path.join(HERE, "api")
DASH_DIR   = os.path.join(HERE, "dashboard")
ADMIN_DIR  = os.path.join(DASH_DIR, "admin")
OUT_PATH   = os.path.join(HERE, "BeaverView-Complete-Build-Playbook.pdf")

# ── Colors ─────────────────────────────────────────────────────────────────
OSU_ORANGE  = colors.HexColor("#D73F09")
OSU_DARK    = colors.HexColor("#111827")
BG_CODE     = colors.HexColor("#1E293B")
TEXT_CODE   = colors.HexColor("#E2E8F0")
BG_LIGHT    = colors.HexColor("#F3F4F6")
BG_ORANGE   = colors.HexColor("#FFF0EB")
BG_YELLOW   = colors.HexColor("#FFFBEB")
BG_BLUE     = colors.HexColor("#EFF6FF")
BG_GREEN    = colors.HexColor("#F0FDF4")
BG_RED      = colors.HexColor("#FFF1F2")
BORDER      = colors.HexColor("#D1D5DB")
TEXT_MUTED  = colors.HexColor("#6B7280")
GREEN       = colors.HexColor("#15803D")
BLUE        = colors.HexColor("#1D4ED8")
RED         = colors.HexColor("#B91C1C")

# ── Styles ─────────────────────────────────────────────────────────────────
def S():
    d = {}
    d["cover_title"]  = ParagraphStyle("ct",  fontName="Helvetica-Bold",   fontSize=34,
        textColor=colors.white, spaceAfter=8,  leading=42)
    d["cover_sub"]    = ParagraphStyle("cs",  fontName="Helvetica",        fontSize=14,
        textColor=colors.HexColor("#FFD0B8"),  spaceAfter=6, leading=20)
    d["part_title"]   = ParagraphStyle("pt",  fontName="Helvetica-Bold",   fontSize=20,
        textColor=colors.white, spaceAfter=6,  leading=26)
    d["h1"]           = ParagraphStyle("h1",  fontName="Helvetica-Bold",   fontSize=18,
        textColor=OSU_DARK,     spaceAfter=6,  spaceBefore=18, leading=24)
    d["h2"]           = ParagraphStyle("h2",  fontName="Helvetica-Bold",   fontSize=13,
        textColor=OSU_ORANGE,   spaceAfter=4,  spaceBefore=14, leading=18)
    d["h3"]           = ParagraphStyle("h3",  fontName="Helvetica-Bold",   fontSize=11,
        textColor=OSU_DARK,     spaceAfter=3,  spaceBefore=10, leading=15)
    d["body"]         = ParagraphStyle("body",fontName="Helvetica",         fontSize=10,
        textColor=OSU_DARK,     spaceAfter=5,  leading=15)
    d["body_sm"]      = ParagraphStyle("bsm", fontName="Helvetica",         fontSize=9,
        textColor=OSU_DARK,     spaceAfter=4,  leading=13)
    d["muted"]        = ParagraphStyle("mut", fontName="Helvetica",         fontSize=9,
        textColor=TEXT_MUTED,   spaceAfter=4,  leading=13)
    d["code"]         = ParagraphStyle("cod", fontName="Courier",            fontSize=7.5,
        textColor=TEXT_CODE,    spaceAfter=0,  leading=11)
    d["code_label"]   = ParagraphStyle("cl",  fontName="Helvetica-Bold",    fontSize=8,
        textColor=colors.HexColor("#94A3B8"),  spaceAfter=0, leading=11)
    d["step_body"]    = ParagraphStyle("sb",  fontName="Helvetica",         fontSize=10,
        textColor=OSU_DARK,     spaceAfter=3,  leading=14)
    d["warn_title"]   = ParagraphStyle("wt",  fontName="Helvetica-Bold",    fontSize=9,
        textColor=colors.HexColor("#92400E"),  spaceAfter=2, leading=13)
    d["warn_body"]    = ParagraphStyle("wb",  fontName="Helvetica",          fontSize=9,
        textColor=colors.HexColor("#78350F"),  spaceAfter=0, leading=13)
    d["tip_body"]     = ParagraphStyle("tb",  fontName="Helvetica",          fontSize=9,
        textColor=colors.HexColor("#1E40AF"),  spaceAfter=0, leading=13)
    d["ok_body"]      = ParagraphStyle("ob",  fontName="Helvetica",          fontSize=9,
        textColor=colors.HexColor("#065F46"),  spaceAfter=0, leading=13)
    d["toc_item"]     = ParagraphStyle("ti",  fontName="Helvetica",          fontSize=10,
        textColor=OSU_DARK,     spaceAfter=2,  leading=15)
    d["toc_part"]     = ParagraphStyle("tp",  fontName="Helvetica-Bold",     fontSize=11,
        textColor=OSU_ORANGE,   spaceAfter=2,  spaceBefore=6, leading=16)
    return d

# ── Helpers ─────────────────────────────────────────────────────────────────
def read_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"[FILE NOT FOUND: {path}]"

def esc(text):
    """HTML-escape text for use in Paragraph."""
    return html.escape(str(text))

def _make_code_table(lines, S, width, is_first, label=None):
    """Single page-fitting code table (≤45 lines)."""
    rows = []
    if is_first and label:
        rows.append([Paragraph(esc(label), S["code_label"])])
    text = "<br/>".join(esc(ln) if ln.strip() else "&nbsp;" for ln in lines)
    rows.append([Paragraph(text, S["code"])])
    t = Table(rows, colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BG_CODE),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
    ]))
    return t

def code_block(content, S, label=None, width=6.5*inch):
    """Return a LIST of page-safe code tables. Callers must use story.extend()."""
    all_lines = content.split("\n")
    CHUNK = 45   # 45 lines × 11pt leading ≈ 495pt — fits in 697pt frame
    tables = []
    for i in range(0, len(all_lines), CHUNK):
        chunk = all_lines[i:i+CHUNK]
        tables.append(_make_code_table(chunk, S, width, i == 0, label))
    return tables

def step_block(num, title, body_paras, S):
    """Numbered step with orange badge."""
    badge_cell = Table([[Paragraph(str(num), ParagraphStyle(
        "sn", fontName="Helvetica-Bold", fontSize=12,
        textColor=colors.white, leading=14))]], colWidths=[0.38*inch])
    badge_cell.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,0), OSU_ORANGE),
        ("ALIGN",        (0,0),(0,0), "CENTER"),
        ("VALIGN",       (0,0),(0,0), "MIDDLE"),
        ("TOPPADDING",   (0,0),(0,0), 6),
        ("BOTTOMPADDING",(0,0),(0,0), 6),
        ("LEFTPADDING",  (0,0),(0,0), 4),
        ("RIGHTPADDING", (0,0),(0,0), 4),
    ]))
    content_rows  = [[Paragraph(f"<b>{esc(title)}</b>", S["h3"])]]
    for p in body_paras:
        content_rows.append([p])
    content_table = Table(content_rows, colWidths=[6.0*inch])
    content_table.setStyle(TableStyle([
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
    ]))
    outer = Table([[badge_cell, content_table]], colWidths=[0.48*inch, 6.02*inch])
    outer.setStyle(TableStyle([
        ("VALIGN",      (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 0),
        ("TOPPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    return outer

def callout(text, S, kind="warn"):
    bg    = {"warn": BG_YELLOW, "tip": BG_BLUE, "ok": BG_GREEN, "stop": BG_RED}.get(kind, BG_YELLOW)
    icon  = {"warn": "⚠", "tip": "ℹ", "ok": "✓", "stop": "✗"}.get(kind, "⚠")
    color = {"warn": "warn_body", "tip": "tip_body", "ok": "ok_body", "stop": "warn_body"}.get(kind, "warn_body")
    t = Table([[Paragraph(f"<b>{icon}</b>  {esc(text)}", S[color])]], colWidths=[6.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), bg),
        ("TOPPADDING",   (0,0),(-1,-1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",  (0,0),(-1,-1), 12),
        ("RIGHTPADDING", (0,0),(-1,-1), 12),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t

def part_divider(num, title, subtitle, S):
    t = Table([[
        Paragraph(f"PART {num}", ParagraphStyle("pn", fontName="Helvetica-Bold",
            fontSize=11, textColor=colors.HexColor("#FFD0B8"), leading=14)),
        Paragraph(title, S["part_title"]),
        Paragraph(subtitle, S["cover_sub"]),
    ]], colWidths=[0.8*inch, 5.2*inch, 0.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), OSU_DARK),
        ("TOPPADDING", (0,0),(-1,-1), 22),
        ("BOTTOMPADDING",(0,0),(-1,-1), 22),
        ("LEFTPADDING", (0,0),(-1,-1), 16),
        ("RIGHTPADDING",(0,0),(-1,-1), 16),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
    ]))
    return t

def file_section(filename, filepath, S, note=None):
    """Full file content block with header."""
    story = []
    story.append(Spacer(1, 10))
    header = Table([[Paragraph(f"📄  {esc(filename)}", ParagraphStyle(
        "fh", fontName="Helvetica-Bold", fontSize=10,
        textColor=colors.white, leading=14))]], colWidths=[6.5*inch])
    header.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), colors.HexColor("#374151")),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING",  (0,0),(-1,-1), 12),
        ("RIGHTPADDING", (0,0),(-1,-1), 12),
    ]))
    story.append(header)
    if note:
        story.append(callout(note, S, "tip"))
    content = read_file(filepath)
    story.extend(code_block(content, S))
    story.append(Spacer(1, 8))
    return story

def two_col_table(rows, S, col1=2.2*inch, col2=4.3*inch):
    data = []
    for a, b in rows:
        data.append([Paragraph(esc(a), S["body_sm"]), Paragraph(esc(b), S["body_sm"])])
    t = Table(data, colWidths=[col1, col2])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BG_LIGHT),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [BG_LIGHT, colors.white]),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("GRID",          (0,0),(-1,-1), 0.5, BORDER),
        ("FONTNAME",      (0,0),(0,-1),  "Helvetica-Bold"),
    ]))
    return t

# ── Page template ────────────────────────────────────────────────────────────
def make_doc():
    def header_footer(canvas, doc):
        canvas.saveState()
        w, h = letter
        # Header bar
        canvas.setFillColor(OSU_DARK)
        canvas.rect(0, h - 0.35*inch, w, 0.35*inch, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#FFD0B8"))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(0.5*inch, h - 0.24*inch, "BeaverView — Complete Build Playbook")
        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - 0.5*inch, h - 0.24*inch,
            getattr(doc, "_current_section", ""))
        # Footer
        canvas.setFillColor(BORDER)
        canvas.rect(0, 0, w, 0.3*inch, fill=1, stroke=0)
        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(0.5*inch, 0.1*inch,
            "Oregon State University — AV Presentation Support")
        canvas.drawRightString(w - 0.5*inch, 0.1*inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        OUT_PATH,
        pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.65*inch,  bottomMargin=0.5*inch,
    )
    doc.multiBuild = None
    return doc, header_footer

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD STORY
# ═══════════════════════════════════════════════════════════════════════════════
def build_story(S):
    story = []
    sp = lambda n=8: Spacer(1, n)
    hr = lambda: HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8, spaceBefore=8)

    # ── COVER ──────────────────────────────────────────────────────────────────
    cover = Table([[
        Paragraph("BeaverView", S["cover_title"]),
        Paragraph("COMPLETE BUILD PLAYBOOK", S["cover_sub"]),
        sp(4),
        Paragraph("Every file. Every step. Copy-paste ready.", S["cover_sub"]),
        sp(4),
        Paragraph("Oregon State University — AV Presentation Support Dashboard", S["muted"]),
        sp(16),
        Paragraph("What this playbook covers:", ParagraphStyle("wcp",
            fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#FFD0B8"), leading=16)),
        sp(4),
        Paragraph("Part 1 — Project overview &amp; architecture", S["cover_sub"]),
        Paragraph("Part 2 — Server setup (Ubuntu VM + VMware)", S["cover_sub"]),
        Paragraph("Part 3 — Python backend (FastAPI, SQLite)", S["cover_sub"]),
        Paragraph("Part 4 — Frontend dashboard (MapLibre, vanilla JS)", S["cover_sub"]),
        Paragraph("Part 5 — Admin panel (HTML/JS + all API endpoints)", S["cover_sub"]),
        Paragraph("Part 6 — Azure Entra SSO login", S["cover_sub"]),
        Paragraph("Part 7 — Production deployment (nginx, SSL, systemd)", S["cover_sub"]),
        Paragraph("Part 8 — First-run checklist &amp; troubleshooting", S["cover_sub"]),
    ]], colWidths=[6.5*inch])
    cover.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), OSU_DARK),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("LEFTPADDING",  (0,0),(-1,-1), 40),
        ("RIGHTPADDING", (0,0),(-1,-1), 40),
    ]))
    # Full-height cover by wrapping in a sized table
    page_cover = Table([[cover]], colWidths=[6.5*inch], rowHeights=[9.5*inch])
    page_cover.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), OSU_DARK),
        ("TOPPADDING",  (0,0),(-1,-1), 60),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(page_cover)
    story.append(PageBreak())

    # ── TABLE OF CONTENTS ──────────────────────────────────────────────────────
    story.append(Paragraph("Table of Contents", S["h1"]))
    story.append(hr())
    toc = [
        ("PART 1", "Project Overview & Architecture",          "Understand what you're building before you build it"),
        ("PART 2", "Server Setup",                             "Ubuntu VM, Python, user account, packages"),
        ("PART 3", "Python Backend — All Code Files",          "requirements.txt · main.py · data_mock.py · migrate scripts"),
        ("PART 4", "Frontend Dashboard — All Code Files",      "index.html · data.js · app.js · styles.css"),
        ("PART 5", "Admin Panel — All Code Files",             "admin.js · admin.css · index/rooms/logs/connectors/users HTML"),
        ("PART 6", "Database Setup & Data Migration",          "Create tables · seed data · import device IPs"),
        ("PART 7", "Azure Entra SSO Configuration",            "App registration · groups · environment variables"),
        ("PART 8", "Production Deployment",                    "nginx config · self-signed SSL · systemd service"),
        ("PART 9", "Windows Client Setup",                     "hosts file · certificate install"),
        ("PART 10","First-Run Checklist & Troubleshooting",    "Verify everything works"),
    ]
    for part, title, desc in toc:
        story.append(Paragraph(f"<b>{esc(part)} — {esc(title)}</b>", S["toc_part"]))
        story.append(Paragraph(f"   {esc(desc)}", S["muted"]))
    story.append(PageBreak())

    # ═══════════════════ PART 1 — OVERVIEW ══════════════════════════════════════
    story.append(part_divider(1, "Project Overview", "What you're building", S))
    story.append(sp(12))

    story.append(Paragraph("What is BeaverView?", S["h2"]))
    story.append(Paragraph(
        "BeaverView is a web dashboard for the Oregon State University AV Presentation Support team. "
        "It shows every AV-equipped classroom and meeting room on a live campus map, letting technicians "
        "see device status, open remote tools, file service tickets, and review audit logs — all from "
        "one browser tab. No VPN required.", S["body"]))

    story.append(Paragraph("Technology Stack", S["h2"]))
    story.append(two_col_table([
        ("Python / FastAPI",     "Backend API — handles authentication, database, device polling"),
        ("SQLite",               "On-disk database — rooms, devices, audit log, user roles"),
        ("Vanilla JavaScript",   "Frontend — no React or Vue; plain HTML/CSS/JS for reliability"),
        ("MapLibre GL",          "Interactive campus map with OSU building footprints"),
        ("nginx",                "Reverse proxy — terminates SSL, forwards to FastAPI"),
        ("Ubuntu 22.04/24.04",   "Server OS running inside a VMware virtual machine"),
        ("Entra SSO (MSAL)",     "OSU Azure AD login — technicians use their OSU credentials"),
    ], S))

    story.append(sp(10))
    story.append(Paragraph("Architecture Diagram", S["h2"]))
    arch_text = (
        "Windows PC Browser\n"
        "       │  HTTPS (port 443)\n"
        "       ▼\n"
        "    nginx\n"
        "   (reverse proxy, SSL termination)\n"
        "       │  HTTP (localhost:8000)\n"
        "       ▼\n"
        "  FastAPI app (uvicorn)\n"
        "  api/main.py\n"
        "       │                    │\n"
        "       ▼                    ▼\n"
        " beaverview.db        device_ips table\n"
        " (SQLite)             → Crestron processors\n"
        "                        (background poller)\n"
        "       │\n"
        "       ▼\n"
        " dashboard/ folder\n"
        " (static HTML/JS/CSS served by FastAPI)\n"
    )
    story.extend(code_block(arch_text, S, width=4*inch))

    story.append(sp(10))
    story.append(Paragraph("Complete File Map", S["h2"]))
    file_map = (
        "New project/                   ← project root\n"
        "├── .gitignore\n"
        "├── .env.example               ← credential template (safe to commit)\n"
        "├── api/\n"
        "│   ├── main.py                ← FastAPI app — ALL backend code (1343 lines)\n"
        "│   ├── data_mock.py           ← 19 mock room records for dev/test\n"
        "│   ├── requirements.txt       ← Python package list\n"
        "│   ├── .env                   ← YOUR credentials (NEVER commit this)\n"
        "│   ├── .env.example           ← blank template\n"
        "│   ├── migrate_data.py        ← one-time: data.js → SQLite\n"
        "│   ├── import_device_ips.py   ← one-time: hardware_ips.csv → SQLite\n"
        "│   ├── beaverview.db          ← SQLite database (auto-created)\n"
        "│   └── start.sh               ← dev startup shortcut\n"
        "└── dashboard/\n"
        "    ├── index.html             ← main dashboard page\n"
        "    ├── app.js                 ← all dashboard interactivity (1113 lines)\n"
        "    ├── styles.css             ← all dashboard styles (1400 lines)\n"
        "    ├── data.js                ← room inventory + campus data (472 lines)\n"
        "    ├── osu-map-buildings.js   ← 278 OSU building footprints (DO NOT EDIT)\n"
        "    ├── vendor/maplibre/       ← MapLibre GL local copy (DO NOT EDIT)\n"
        "    └── admin/\n"
        "        ├── admin.js           ← shared auth check + API helpers\n"
        "        ├── admin.css          ← admin panel styles\n"
        "        ├── index.html         ← admin summary dashboard\n"
        "        ├── rooms.html         ← room + building editor\n"
        "        ├── logs.html          ← audit log viewer + export\n"
        "        ├── connectors.html    ← connector toggle management\n"
        "        └── users.html         ← user role management\n"
    )
    story.extend(code_block(file_map, S))
    story.append(PageBreak())

    # ═══════════════════ PART 2 — SERVER SETUP ══════════════════════════════════
    story.append(part_divider(2, "Server Setup", "Ubuntu VM + packages + user account", S))
    story.append(sp(12))

    story.append(Paragraph("What you need before starting", S["h2"]))
    story.append(two_col_table([
        ("VMware Workstation/Player", "Installed on a Windows PC connected to the AV LAN"),
        ("Ubuntu 22.04/24.04 ISO",   "Download from ubuntu.com — Server or Desktop both work"),
        ("Network access",           "VM bridged adapter — same subnet as AV devices and Windows clients"),
        ("DNS / hosts file entry",   "Windows clients will type 'https://beaverview' in their browser"),
    ], S))

    story.append(Paragraph("Step 1 — Create the VMware VM", S["h2"]))
    story.append(callout(
        "Use Bridged networking (not NAT). The VM must be reachable from Windows "
        "PCs on the same network. Assign a static IP using your network's DHCP "
        "reservation or set a static IP in Ubuntu's netplan config.", S, "warn"))
    story.append(sp(6))
    for n, title, lines in [
        (1, "Create a new VM in VMware",
            ["File → New Virtual Machine → Typical",
             "Installer disc image file: browse to ubuntu-22.04.iso",
             "Name: BeaverView  |  Disk size: 40 GB  |  Memory: 4 GB  |  CPUs: 2"]),
        (2, "Network adapter",
            ["Settings → Network Adapter → Bridged",
             "Check 'Replicate physical network connection state'"]),
        (3, "Install Ubuntu",
            ["Boot VM, follow Ubuntu installer",
             "Create user: beaverview  |  hostname: beaverview",
             "Enable OpenSSH server during install (optional but useful)"]),
    ]:
        story.append(step_block(n, title, [Paragraph(ln, S["step_body"]) for ln in lines], S))
        story.append(sp(6))

    story.append(Paragraph("Step 2 — Install system packages", S["h2"]))
    story.append(Paragraph("Open a terminal on the Ubuntu VM and run these commands one at a time:", S["body"]))
    story.extend(code_block(
        "# Update package lists\n"
        "sudo apt update && sudo apt upgrade -y\n\n"
        "# Install Python 3, pip, git, nginx, sqlite3\n"
        "sudo apt install -y python3 python3-pip python3-venv git nginx sqlite3\n\n"
        "# Confirm Python version (need 3.10 or higher)\n"
        "python3 --version", S))

    story.append(Paragraph("Step 3 — Create the app directory and user account", S["h2"]))
    story.extend(code_block(
        "# Create dedicated user (if not already created during install)\n"
        "sudo useradd -m -s /bin/bash beaverview\n\n"
        "# Create app directory\n"
        "sudo mkdir -p /home/beaverview/app\n"
        "sudo mkdir -p /home/beaverview/backups\n"
        "sudo chown -R beaverview:beaverview /home/beaverview/\n\n"
        "# Switch to the beaverview user for all further steps\n"
        "sudo -u beaverview bash", S))

    story.append(Paragraph("Step 4 — Copy project files to the server", S["h2"]))
    story.append(callout(
        "The simplest approach: copy the entire project folder from your Mac/PC to the VM "
        "using SCP or a USB drive. Or use git if you have a repository.", S, "tip"))
    story.extend(code_block(
        "# Option A: Copy from Mac/PC via SCP (run this on your Mac, not the VM)\n"
        "scp -r \"/path/to/New project\" beaverview@<VM-IP>:/home/beaverview/app/\n\n"
        "# Option B: If you have git\n"
        "cd /home/beaverview/app\n"
        "git clone https://your-repo-url.git .\n\n"
        "# Verify the files are there\n"
        "ls /home/beaverview/app/", S))

    story.append(Paragraph("Step 5 — Create Python virtual environment", S["h2"]))
    story.extend(code_block(
        "cd /home/beaverview/app/api\n\n"
        "# Create virtual environment\n"
        "python3 -m venv venv\n\n"
        "# Activate it\n"
        "source venv/bin/activate\n\n"
        "# Install all Python packages\n"
        "pip install -r requirements.txt\n\n"
        "# Confirm FastAPI installed\n"
        "python3 -c \"import fastapi; print('FastAPI OK')\"", S))
    story.append(PageBreak())

    # ═══════════════════ PART 3 — BACKEND CODE ══════════════════════════════════
    story.append(part_divider(3, "Python Backend — All Code Files", "Copy these files exactly as shown", S))
    story.append(sp(12))
    story.append(callout(
        "CREATE EACH FILE exactly as shown. Use a text editor (nano, vi, VS Code) "
        "to create/paste each file on the server, or copy the files directly from your Mac. "
        "File paths are shown above each code block.", S, "tip"))
    story.append(sp(8))

    # requirements.txt
    story.append(Paragraph("api/requirements.txt", S["h2"]))
    story.append(Paragraph("This lists every Python package the backend needs. Paste this into api/requirements.txt:", S["body"]))
    for s in file_section("api/requirements.txt", os.path.join(API_DIR, "requirements.txt"), S):
        story.append(s)

    # .env.example
    story.append(Paragraph("api/.env.example", S["h2"]))
    story.append(Paragraph(
        "This is a template for your .env file. The actual .env file (with real passwords) "
        "NEVER gets committed to git. Copy .env.example to .env and fill in the values.", S["body"]))
    story.extend(code_block(
        "# On the server:\n"
        "cp /home/beaverview/app/api/.env.example /home/beaverview/app/api/.env\n"
        "nano /home/beaverview/app/api/.env   # edit with real credentials", S))
    for s in file_section("api/.env.example", os.path.join(API_DIR, ".env.example"), S):
        story.append(s)

    # data_mock.py
    story.append(Paragraph("api/data_mock.py", S["h2"]))
    story.append(Paragraph(
        "Mock room data used by the API in development mode. "
        "These 19 rooms power the dashboard until you run the data migration.", S["body"]))
    for s in file_section("api/data_mock.py", os.path.join(API_DIR, "data_mock.py"), S):
        story.append(s)

    # migrate_data.py
    story.append(Paragraph("api/migrate_data.py", S["h2"]))
    story.append(Paragraph(
        "One-time migration script. Run this ONCE after the database tables are created. "
        "It reads data.js and inserts all campuses, buildings, and rooms into SQLite.", S["body"]))
    story.append(callout(
        "Safe to re-run — it clears and reloads the data tables each time. "
        "Does NOT touch audit_log or user_roles.", S, "ok"))
    for s in file_section("api/migrate_data.py", os.path.join(API_DIR, "migrate_data.py"), S):
        story.append(s)

    # import_device_ips.py
    story.append(Paragraph("api/import_device_ips.py", S["h2"]))
    story.append(Paragraph(
        "Loads the hardware IP spreadsheet (CSV) into the device_ips table. "
        "Run this after you have a CSV file with columns: room_id, device_type, ip_address.", S["body"]))
    story.append(Paragraph("Expected CSV format:", S["h3"]))
    story.extend(code_block(
        "room_id,device_type,ip_address\n"
        "corvallis-kad-101,xpanel,10.20.1.101\n"
        "corvallis-kad-101,wattbox,10.20.1.201\n"
        "corvallis-linc-100,xpanel,10.20.2.100\n"
        "corvallis-linc-100,ptz,10.20.2.150", S))
    for s in file_section("api/import_device_ips.py", os.path.join(API_DIR, "import_device_ips.py"), S):
        story.append(s)

    # main.py — the big one
    story.append(Paragraph("api/main.py — Complete Backend", S["h1"]))
    story.append(callout(
        "This is the complete FastAPI backend — 1343 lines. It includes: database setup, "
        "all API endpoints, Crestron background poller, Entra SSO auth flow, and admin panel APIs. "
        "Copy the entire file exactly as shown.", S, "warn"))
    story.append(Paragraph("What's inside main.py:", S["h3"]))
    story.append(two_col_table([
        ("Lines 1–30",      "Imports — asyncio, csv, FastAPI, Pydantic, SQLite, MSAL"),
        ("Lines 31–100",    "Database: get_db(), init_db() — creates all 9 tables"),
        ("Lines 101–240",   "Connector registry — auto-detects live mode from env vars"),
        ("Lines 241–280",   "Background Crestron poller — polls device IPs every 60 seconds"),
        ("Lines 281–320",   "App setup — FastAPI, CORS, session middleware"),
        ("Lines 321–360",   "Auth helpers — require_admin(), resolve_role()"),
        ("Lines 361–430",   "Existing API routes — health, campus connectors, room actions"),
        ("Lines 431–600",   "Entra SSO — /auth/login, /auth/callback, /auth/logout"),
        ("Lines 601–900",   "Admin API — rooms, buildings, devices CRUD"),
        ("Lines 901–1200",  "Admin API — logs query/export/archive/purge, connectors, users"),
        ("Lines 1201–1343", "Static file serving — dashboard and admin panel"),
    ], S))
    for s in file_section("api/main.py", os.path.join(API_DIR, "main.py"), S):
        story.append(s)
    story.append(PageBreak())

    # ═══════════════════ PART 4 — FRONTEND ══════════════════════════════════════
    story.append(part_divider(4, "Frontend Dashboard — All Code Files", "The map, rooms, and device tools", S))
    story.append(sp(12))

    story.append(Paragraph("How the frontend works", S["h2"]))
    story.append(Paragraph(
        "The dashboard is plain HTML + CSS + JavaScript — no build step, no npm. "
        "Four files work together:", S["body"]))
    story.append(two_col_table([
        ("index.html",           "Page skeleton — header, sidebar, map column, detail panel"),
        ("data.js",              "Room inventory — all campuses, buildings, rooms, and connectors"),
        ("app.js",               "All interactivity — map rendering, room selection, tool panels"),
        ("styles.css",           "All visual design — design tokens, layout, animations"),
        ("osu-map-buildings.js", "278 OSU building footprints — DO NOT EDIT (pre-bundled data)"),
        ("vendor/maplibre/",     "MapLibre GL library — DO NOT EDIT (pre-bundled vendor)"),
    ], S))
    story.append(callout(
        "osu-map-buildings.js and the vendor/maplibre/ folder are pre-built files "
        "that you copy as-is from the project. You never need to edit them.", S, "tip"))
    story.append(sp(8))

    # index.html
    story.append(Paragraph("dashboard/index.html", S["h2"]))
    story.append(Paragraph(
        "The main dashboard page. It references styles.css, MapLibre, and the four JS files. "
        "Contains the HTML structure — the JavaScript fills in the content.", S["body"]))
    for s in file_section("dashboard/index.html", os.path.join(DASH_DIR, "index.html"), S):
        story.append(s)

    # data.js — important guidance
    story.append(Paragraph("dashboard/data.js", S["h2"]))
    story.append(callout(
        "data.js is 472 lines of room inventory data. It defines window.dashboardData "
        "with campuses, buildings, rooms, and connector status. After you run the data "
        "migration (Part 6), the backend reads from the database instead — but data.js "
        "stays as a fallback reference. Copy it unchanged from the project folder.", S, "tip"))
    story.append(Paragraph(
        "The structure of data.js (for reference):", S["h3"]))
    story.extend(code_block(
        "window.dashboardData = {\n"
        "  campuses: [\n"
        "    {\n"
        "      id: 'corvallis',\n"
        "      name: 'Corvallis',\n"
        "      subtitle: 'Main Campus',\n"
        "      connectors: { crestron:'mock', live25:'mock', screenconnect:'mock',\n"
        "                    wattbox:'mock', servicenow:'mock' },\n"
        "      buildings: [\n"
        "        {\n"
        "          code: 'KAd',\n"
        "          name: 'Kerr Administration',\n"
        "          rooms: [\n"
        "            {\n"
        "              number: '101',\n"
        "              type: 'Classroom',\n"
        "              status: 'available',   // 'available'|'in-use'|'issue'|'offline'\n"
        "              health: 96,            // 0-100\n"
        "              processor: 'online',   // was 'fusion' — renamed\n"
        "              display: 'on',\n"
        "              screenconnect: true,\n"
        "              wattbox: true,\n"
        "              hybrid: false,\n"
        "              stale: false,\n"
        "              incidents: { open: [], closed: [] },\n"
        "              devices: [\n"
        "                ['Crestron CP4', 'Crestron', 'CP4N', 'Ethernet'],\n"
        "                ['Projector', 'Epson', 'EB-L735U', 'HDMI'],\n"
        "              ]\n"
        "            }\n"
        "          ]\n"
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "// Note: the full data.js file has 3 campuses, ~20 buildings, ~50 rooms.", S))
    story.append(Paragraph(
        "The full data.js file is pre-built and included in the project folder. "
        "Copy it to dashboard/data.js as-is.", S["body"]))

    # app.js
    story.append(Paragraph("dashboard/app.js", S["h2"]))
    story.append(callout(
        "app.js is 1113 lines of dashboard logic. It handles: campus switching, "
        "MapLibre map rendering with OSU building footprints, room selection, tab navigation, "
        "device tool panels (XPanel, ScreenConnect, WattBox, PTZ, ServiceNow, SharePoint), "
        "and audit log display. Copy it unchanged from the project folder.", S, "tip"))
    story.append(Paragraph("Key functions in app.js:", S["h3"]))
    story.append(two_col_table([
        ("initMap(campus)",         "Renders the MapLibre map, adds building polygons"),
        ("selectBuilding(code)",    "Highlights a building and shows its rooms below the map"),
        ("selectRoom(room)",        "Loads room status, tabs, and device tool panels in the right panel"),
        ("renderToolPanel(tool)",   "Shows the interactive control UI for XPanel/WattBox/PTZ/etc"),
        ("logAction(room, action)", "Sends an audit log entry to POST /api/rooms/{id}/action"),
        ("renderConnectors()",      "Updates the connector health badges in the left sidebar"),
    ], S))
    for s in file_section("dashboard/app.js", os.path.join(DASH_DIR, "app.js"), S,
                          note="Full app.js — 1113 lines. Copy this file exactly as shown."):
        story.append(s)

    # styles.css
    story.append(Paragraph("dashboard/styles.css", S["h2"]))
    story.append(callout(
        "styles.css is 1400 lines. It uses CSS custom properties (design tokens) "
        "defined in :root{} at the top. To change colors or fonts, only edit the tokens — "
        "do not hunt for individual color values throughout the file.", S, "tip"))
    for s in file_section("dashboard/styles.css", os.path.join(DASH_DIR, "styles.css"), S,
                          note="Full styles.css — 1400 lines. Copy this file exactly as shown."):
        story.append(s)
    story.append(PageBreak())

    # ═══════════════════ PART 5 — ADMIN PANEL ═══════════════════════════════════
    story.append(part_divider(5, "Admin Panel — All Code Files", "dashboard/admin/ folder", S))
    story.append(sp(12))

    story.append(Paragraph("Admin Panel Overview", S["h2"]))
    story.append(Paragraph(
        "The admin panel lives at https://beaverview/admin/. It is served by the same "
        "FastAPI app as the main dashboard — no second server. Access is restricted to "
        "users in the BeaverView Admins Azure AD group.", S["body"]))
    story.append(two_col_table([
        ("/admin/",              "Summary dashboard — stat cards, activity feed, connector health"),
        ("/admin/rooms.html",    "Room and building editor with slide-in drawer"),
        ("/admin/logs.html",     "Audit log viewer — search, filter, CSV export, archive/purge"),
        ("/admin/connectors.html","Toggle connectors live/mock per campus"),
        ("/admin/users.html",    "Manual role overrides — grant/revoke admin access"),
    ], S))
    story.append(callout(
        "Every admin page includes admin.js which checks /api/me on load. "
        "If the user is not logged in, they are redirected to /auth/login. "
        "If they are logged in but not admin, they see a 403 page.", S, "tip"))
    story.append(sp(8))

    for fname, fpath, note in [
        ("admin/admin.js",
         os.path.join(ADMIN_DIR, "admin.js"),
         "Include this on every admin page. Handles auth check, API helpers, and toast notifications."),
        ("admin/admin.css",
         os.path.join(ADMIN_DIR, "admin.css"),
         "Full admin panel stylesheet. OSU orange color scheme, responsive grid, drawers, badges."),
        ("admin/index.html",
         os.path.join(ADMIN_DIR, "index.html"),
         "Summary dashboard — stat cards (total rooms, active, incidents), activity feed, connector health grid."),
        ("admin/rooms.html",
         os.path.join(ADMIN_DIR, "rooms.html"),
         "Room and building editor. Left sidebar shows buildings; right panel shows rooms with edit/delete drawer."),
        ("admin/logs.html",
         os.path.join(ADMIN_DIR, "logs.html"),
         "Audit log viewer with filter bar, pagination, CSV export, and archive/purge controls."),
        ("admin/connectors.html",
         os.path.join(ADMIN_DIR, "connectors.html"),
         "Connector management — toggle each connector live/mock per campus, run connectivity tests."),
        ("admin/users.html",
         os.path.join(ADMIN_DIR, "users.html"),
         "User role management — override Azure AD group roles, remove overrides."),
    ]:
        story.append(Paragraph(f"dashboard/{fname}", S["h2"]))
        for s in file_section(f"dashboard/{fname}", fpath, S, note=note):
            story.append(s)

    story.append(PageBreak())

    # ═══════════════════ PART 6 — DATABASE SETUP ════════════════════════════════
    story.append(part_divider(6, "Database Setup & Data Migration", "Create tables, seed data, import IPs", S))
    story.append(sp(12))

    story.append(Paragraph("What the database contains", S["h2"]))
    story.append(two_col_table([
        ("audit_log",       "Every action taken by every user — technicians and admins"),
        ("campuses",        "Corvallis, Cascades, Hatfield — seeded by migrate_data.py"),
        ("buildings",       "All buildings per campus — seeded by migrate_data.py"),
        ("rooms",           "All AV rooms — seeded by migrate_data.py"),
        ("devices",         "One row per device per room — seeded by migrate_data.py"),
        ("incidents",       "Open and closed tickets per room — seeded by migrate_data.py"),
        ("connector_config","Live/mock mode per connector per campus"),
        ("user_roles",      "Manual role overrides — populated via admin panel or Entra login"),
        ("device_ips",      "Hardware IP addresses — loaded by import_device_ips.py"),
    ], S))
    story.append(sp(8))

    story.append(Paragraph("Step 1 — Create all database tables", S["h2"]))
    story.append(Paragraph(
        "The tables are created automatically when FastAPI starts (init_db() runs in the lifespan hook). "
        "But you can also create them manually:", S["body"]))
    story.extend(code_block(
        "cd /home/beaverview/app/api\n"
        "source venv/bin/activate\n\n"
        "# Option A: Start the server (tables created automatically on startup)\n"
        "uvicorn main:app --port 8000\n\n"
        "# Option B: Run init_db() directly without starting the server\n"
        "python3 -c \"from main import init_db; init_db(); print('Tables created')\"\n\n"
        "# Verify tables were created\n"
        "sqlite3 beaverview.db '.tables'", S))
    story.append(callout("Expected output: audit_log  campuses  buildings  rooms  devices  incidents  connector_config  user_roles  device_ips", S, "ok"))

    story.append(Paragraph("Step 2 — Run the data migration", S["h2"]))
    story.append(Paragraph(
        "This imports all the room data from dashboard/data.js into SQLite. "
        "Run this once after creating the tables.", S["body"]))
    story.extend(code_block(
        "cd /home/beaverview/app/api\n"
        "source venv/bin/activate\n"
        "python3 migrate_data.py", S))
    story.append(callout(
        "Expected output:\n"
        "Migration complete.\n"
        "  campuses: 3 rows\n"
        "  buildings: (number depends on data.js)\n"
        "  rooms: (number depends on data.js)\n"
        "  devices: (number depends on data.js)", S, "ok"))

    story.append(Paragraph("Step 3 — Import hardware IP addresses (when ready)", S["h2"]))
    story.append(Paragraph(
        "Create a CSV file with the IP address of each AV device. "
        "The Crestron background poller will use these IPs to poll processors.", S["body"]))
    story.extend(code_block(
        "# Create your CSV file (hardware_ips.csv) with this format:\n"
        "# room_id,device_type,ip_address\n"
        "# corvallis-kad-101,xpanel,10.20.1.101\n"
        "# corvallis-kad-101,wattbox,10.20.1.201\n\n"
        "# Run the import:\n"
        "python3 import_device_ips.py hardware_ips.csv\n\n"
        "# Verify:\n"
        "sqlite3 beaverview.db 'SELECT COUNT(*) FROM device_ips'", S))
    story.append(callout(
        "SECURITY: hardware_ips.csv contains device IP addresses. "
        "It is in .gitignore and should NEVER be committed to git.", S, "stop"))
    story.append(PageBreak())

    # ═══════════════════ PART 7 — ENTRA SSO ═════════════════════════════════════
    story.append(part_divider(7, "Azure Entra SSO Configuration", "Register BeaverView in Azure AD", S))
    story.append(sp(12))

    story.append(callout(
        "You need Global Administrator or Application Administrator access in your OSU Azure AD tenant "
        "to complete this section. If you don't have this access, submit a ticket to IT.", S, "warn"))
    story.append(sp(8))

    story.append(Paragraph("Step 1 — Register the application in Azure Portal", S["h2"]))
    for n, title, lines in [
        (1, "Go to Azure Portal",
            ["Open https://portal.azure.com",
             "Sign in with your OSU admin account",
             "Search for 'App registrations' in the top search bar"]),
        (2, "Create a new registration",
            ["Click '+ New registration'",
             "Name: BeaverView",
             "Supported account types: Accounts in this organizational directory only (Single tenant)",
             "Redirect URI: Web  →  https://beaverview/auth/callback",
             "Click Register"]),
        (3, "Note the IDs",
            ["Copy 'Application (client) ID' — this is AZURE_CLIENT_ID",
             "Copy 'Directory (tenant) ID' — this is AZURE_TENANT_ID",
             "You'll add these to .env in Step 4"]),
        (4, "Create a client secret",
            ["Click 'Certificates & secrets' in the left menu",
             "Click '+ New client secret'",
             "Description: beaverview-prod  |  Expiry: 24 months",
             "Click Add",
             "COPY THE VALUE NOW — it only shows once",
             "This is AZURE_CLIENT_SECRET"]),
        (5, "Add API permissions",
            ["Click 'API permissions' in the left menu",
             "Click '+ Add a permission' → Microsoft Graph → Delegated",
             "Add: openid, profile, email, GroupMember.Read.All",
             "Click 'Grant admin consent for <your org>'"]),
    ]:
        story.append(step_block(n, title, [Paragraph(ln, S["step_body"]) for ln in lines], S))
        story.append(sp(6))

    story.append(Paragraph("Step 2 — Create Azure AD Groups", S["h2"]))
    story.append(Paragraph(
        "BeaverView uses two groups to control access. Create them in Azure AD → Groups:", S["body"]))
    story.append(two_col_table([
        ("BeaverView Technicians", "Members can use the main dashboard"),
        ("BeaverView Admins",      "Members can access the /admin panel (also includes all technician access)"),
    ], S))
    story.extend(code_block(
        "# To find the Object ID of each group:\n"
        "# Azure Portal → Azure Active Directory → Groups\n"
        "# Search for 'BeaverView' → click the group → copy Object ID\n\n"
        "# These IDs go in .env:\n"
        "# AZURE_GROUP_TECHNICIAN=<object-id-of-BeaverView-Technicians-group>\n"
        "# AZURE_GROUP_ADMIN=<object-id-of-BeaverView-Admins-group>", S))

    story.append(Paragraph("Step 3 — Assign users to groups", S["h2"]))
    story.extend(code_block(
        "# Azure Portal → Azure Active Directory → Groups\n"
        "# Click 'BeaverView Technicians' → Members → + Add members\n"
        "# Add all AV support technicians\n\n"
        "# Click 'BeaverView Admins' → Members → + Add members\n"
        "# Add the AV support supervisor/admin accounts\n\n"
        "# Note: Admins should ALSO be added to the Technicians group\n"
        "# (the dashboard checks group membership separately)", S))

    story.append(Paragraph("Step 4 — Configure .env on the server", S["h2"]))
    story.extend(code_block(
        "# On the Ubuntu server:\n"
        "nano /home/beaverview/app/api/.env\n\n"
        "# Add these lines (replace with your real values):\n"
        "AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n"
        "AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n"
        "AZURE_CLIENT_SECRET=your-client-secret-value\n"
        "AZURE_REDIRECT_URI=https://beaverview/auth/callback\n"
        "AZURE_GROUP_TECHNICIAN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n"
        "AZURE_GROUP_ADMIN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n\n"
        "# Session secret — generate a random string:\n"
        "python3 -c \"import secrets; print(secrets.token_hex(32))\"\n"
        "SESSION_SECRET_KEY=<output-from-above-command>\n\n"
        "# SSL setting (true = require HTTPS for session cookie)\n"
        "SESSION_HTTPS_ONLY=true", S))

    story.append(Paragraph("Step 5 — Test the login flow", S["h2"]))
    story.extend(code_block(
        "# Restart BeaverView after updating .env\n"
        "sudo systemctl restart beaverview\n\n"
        "# On a Windows PC, open Chrome and go to:\n"
        "# https://beaverview/auth/login\n\n"
        "# Expected: redirect to Microsoft login → OSU credentials → redirect back to /admin/\n\n"
        "# Verify session:\n"
        "# In Chrome DevTools → Application → Cookies\n"
        "# You should see a 'beaverview_session' cookie", S))
    story.append(PageBreak())

    # ═══════════════════ PART 8 — PRODUCTION DEPLOYMENT ═════════════════════════
    story.append(part_divider(8, "Production Deployment", "nginx + SSL + systemd service", S))
    story.append(sp(12))

    story.append(Paragraph("Step 1 — Generate the self-signed SSL certificate", S["h2"]))
    story.append(callout(
        "Self-signed certificates are fine for internal LAN use. Windows clients "
        "will see a browser warning the first time. They can click 'Advanced → Proceed' "
        "once, or you can install the cert on their machines (Part 9).", S, "tip"))
    story.extend(code_block(
        "# Create the certificate directory\n"
        "sudo mkdir -p /etc/ssl/beaverview\n\n"
        "# Generate a self-signed certificate (valid for 10 years)\n"
        "sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \\\n"
        "  -keyout /etc/ssl/beaverview/beaverview.key \\\n"
        "  -out    /etc/ssl/beaverview/beaverview.crt \\\n"
        "  -subj \"/C=US/ST=Oregon/L=Corvallis/O=Oregon State University/CN=beaverview\"\n\n"
        "# Lock down permissions\n"
        "sudo chmod 600 /etc/ssl/beaverview/beaverview.key\n"
        "sudo chmod 644 /etc/ssl/beaverview/beaverview.crt\n\n"
        "# Verify:\n"
        "sudo openssl x509 -in /etc/ssl/beaverview/beaverview.crt -text -noout | grep -E 'Subject:|Not After'", S))

    story.append(Paragraph("Step 2 — Create the nginx configuration", S["h2"]))
    story.append(Paragraph("Create this file at /etc/nginx/sites-available/beaverview:", S["body"]))
    story.extend(code_block(
        "server {\n"
        "    listen 80;\n"
        "    server_name beaverview;\n"
        "    return 301 https://$host$request_uri;\n"
        "}\n\n"
        "server {\n"
        "    listen 443 ssl;\n"
        "    server_name beaverview;\n\n"
        "    ssl_certificate     /etc/ssl/beaverview/beaverview.crt;\n"
        "    ssl_certificate_key /etc/ssl/beaverview/beaverview.key;\n\n"
        "    ssl_protocols TLSv1.2 TLSv1.3;\n"
        "    ssl_ciphers HIGH:!aNULL:!MD5;\n\n"
        "    location / {\n"
        "        proxy_pass         http://127.0.0.1:8000;\n"
        "        proxy_set_header   Host $host;\n"
        "        proxy_set_header   X-Real-IP $remote_addr;\n"
        "        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        "        proxy_set_header   X-Forwarded-Proto $scheme;\n"
        "        proxy_read_timeout 60s;\n"
        "        proxy_connect_timeout 10s;\n"
        "    }\n"
        "}", S))
    story.extend(code_block(
        "# Enable the site\n"
        "sudo ln -s /etc/nginx/sites-available/beaverview \\\n"
        "           /etc/nginx/sites-enabled/beaverview\n\n"
        "# Test the config\n"
        "sudo nginx -t\n\n"
        "# Start/reload nginx\n"
        "sudo systemctl enable nginx\n"
        "sudo systemctl restart nginx", S))

    story.append(Paragraph("Step 3 — Create the systemd service", S["h2"]))
    story.append(Paragraph("Create this file at /etc/systemd/system/beaverview.service:", S["body"]))
    story.extend(code_block(
        "[Unit]\n"
        "Description=BeaverView AV Dashboard\n"
        "After=network.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        "User=beaverview\n"
        "WorkingDirectory=/home/beaverview/app/api\n"
        "EnvironmentFile=/home/beaverview/app/api/.env\n"
        "ExecStart=/home/beaverview/app/api/venv/bin/uvicorn \\\n"
        "          main:app \\\n"
        "          --host 127.0.0.1 \\\n"
        "          --port 8000 \\\n"
        "          --workers 2\n"
        "Restart=always\n"
        "RestartSec=5\n"
        "StandardOutput=journal\n"
        "StandardError=journal\n\n"
        "[Install]\n"
        "WantedBy=multi-user.target", S))
    story.extend(code_block(
        "# Enable and start the service\n"
        "sudo systemctl daemon-reload\n"
        "sudo systemctl enable beaverview\n"
        "sudo systemctl start beaverview\n\n"
        "# Check status\n"
        "sudo systemctl status beaverview\n\n"
        "# View live logs\n"
        "sudo journalctl -u beaverview -f", S))
    story.append(callout(
        "If the service fails to start, check the logs: sudo journalctl -u beaverview -n 50\n"
        "Common issue: .env file not found → verify path in EnvironmentFile=", S, "warn"))
    story.append(PageBreak())

    # ═══════════════════ PART 9 — WINDOWS CLIENT ════════════════════════════════
    story.append(part_divider(9, "Windows Client Setup", "hosts file + certificate trust", S))
    story.append(sp(12))

    story.append(Paragraph("Step 1 — Find the VM's IP address", S["h2"]))
    story.extend(code_block(
        "# On the Ubuntu VM:\n"
        "ip addr show\n"
        "# Look for the inet address under your bridged network interface\n"
        "# Example output:  inet 192.168.1.50/24\n"
        "# Your VM IP is the part before /24 — e.g. 192.168.1.50", S))

    story.append(Paragraph("Step 2 — Edit the Windows hosts file", S["h2"]))
    story.append(Paragraph(
        "Do this on every Windows PC that needs to access BeaverView.", S["body"]))
    story.append(callout(
        "You must run Notepad as Administrator to edit the hosts file.", S, "warn"))
    story.extend(code_block(
        "# Windows hosts file location:\n"
        "C:\\Windows\\System32\\drivers\\etc\\hosts\n\n"
        "# Open Notepad as Administrator:\n"
        "# Start → search 'Notepad' → right-click → Run as administrator\n"
        "# File → Open → navigate to C:\\Windows\\System32\\drivers\\etc\\\n"
        "# Change 'Text Documents' to 'All Files' → open 'hosts'\n\n"
        "# Add this line at the bottom (replace with your VM's IP):\n"
        "192.168.1.50   beaverview\n\n"
        "# Save the file (Ctrl+S)\n\n"
        "# Test from a browser:\n"
        "# Open Chrome or Edge → type:  https://beaverview\n"
        "# You should see the BeaverView dashboard (with a certificate warning)", S))

    story.append(Paragraph("Step 3 — Install the certificate (optional — removes the warning)", S["h2"]))
    story.append(Paragraph(
        "Copy the certificate file from the server to the Windows PC, then install it.", S["body"]))
    story.extend(code_block(
        "# On the Ubuntu server — copy the cert to a shared location:\n"
        "sudo cp /etc/ssl/beaverview/beaverview.crt /home/beaverview/beaverview.crt\n"
        "sudo chmod 644 /home/beaverview/beaverview.crt\n\n"
        "# On Windows — copy via SCP or USB:\n"
        "# scp beaverview@192.168.1.50:/home/beaverview/beaverview.crt C:\\Temp\\beaverview.crt\n\n"
        "# Install on Windows:\n"
        "# Double-click beaverview.crt\n"
        "# Click 'Install Certificate'\n"
        "# Store location: Local Machine\n"
        "# Place in: Trusted Root Certification Authorities\n"
        "# Click Finish\n\n"
        "# Restart Chrome/Edge\n"
        "# https://beaverview should now load with a green padlock", S))
    story.append(PageBreak())

    # ═══════════════════ PART 10 — FIRST RUN CHECKLIST ══════════════════════════
    story.append(part_divider(10, "First-Run Checklist & Troubleshooting", "Verify everything works", S))
    story.append(sp(12))

    story.append(Paragraph("First-Run Checklist", S["h2"]))
    checklist = [
        ("1",  "VM is running and reachable from Windows PC",
                "ping <VM-IP> from Windows Command Prompt — should reply"),
        ("2",  "Python packages installed",
                "cd api && source venv/bin/activate && python3 -c \"import fastapi,msal,httpx; print('OK')\""),
        ("3",  "Database tables created",
                "sqlite3 beaverview.db '.tables'  — should show 9 tables"),
        ("4",  "Data migration ran",
                "sqlite3 beaverview.db 'SELECT COUNT(*) FROM rooms'  — should be > 0"),
        ("5",  "BeaverView service running",
                "sudo systemctl status beaverview  — should show 'active (running)'"),
        ("6",  "API health check passes",
                "curl http://localhost:8000/api/health  — should return {\"status\":\"ok\"}"),
        ("7",  "nginx running",
                "sudo systemctl status nginx  — should show 'active (running)'"),
        ("8",  "Dashboard loads from Windows",
                "Open https://beaverview in Chrome — should show the map"),
        ("9",  "Entra login works",
                "Open https://beaverview/auth/login — should redirect to Microsoft login"),
        ("10", "Admin panel accessible",
                "After login, open https://beaverview/admin/ — should show summary dashboard"),
    ]
    for num, check, how in checklist:
        story.append(KeepTogether([
            step_block(num, check, [Paragraph(how, S["muted"])], S),
            sp(5),
        ]))

    story.append(Paragraph("Troubleshooting", S["h2"]))
    story.append(sp(4))
    issues = [
        ("Dashboard shows 'Cannot connect to API'",
         "The FastAPI service is not running. Check: sudo systemctl status beaverview\n"
         "Fix: sudo systemctl restart beaverview\n"
         "Logs: sudo journalctl -u beaverview -n 50"),
        ("HTTPS certificate warning on every page load",
         "Install the self-signed certificate on Windows (Part 9, Step 3).\n"
         "Or click Advanced → Proceed to beaverview (unsafe) to bypass once per browser session."),
        ("'https://beaverview' does not resolve (can't reach site)",
         "The hosts file entry is missing or has a typo.\n"
         "Check: open C:\\Windows\\System32\\drivers\\etc\\hosts in Notepad\n"
         "Verify the IP matches the VM's actual IP (ip addr show on the VM)"),
        ("Entra login redirects to error page",
         "Verify AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET in .env\n"
         "Verify the redirect URI https://beaverview/auth/callback is registered in Azure\n"
         "Verify GROUP IDs are correct (find in Azure AD → Groups → Properties)"),
        ("Admin panel shows 'Access Denied' even for admins",
         "Verify the user is in the BeaverView Admins group in Azure AD\n"
         "Verify AZURE_GROUP_ADMIN in .env matches the group's Object ID exactly\n"
         "Log out and log back in (session may have old group data)"),
        ("Rooms show 'offline' even when processors are running",
         "The Crestron poller needs credentials and IPs.\n"
         "Set CRESTRON_POLL_USERNAME and CRESTRON_POLL_PASSWORD in .env\n"
         "Run import_device_ips.py with your hardware_ips.csv\n"
         "Check: sqlite3 beaverview.db 'SELECT COUNT(*) FROM device_ips'"),
        ("Data migration fails with 'Could not find window.dashboardData'",
         "The regex in migrate_data.py expects window.dashboardData = {...} in data.js\n"
         "Check that dashboard/data.js starts with that assignment\n"
         "Also check for unclosed trailing commas that break JSON parsing"),
        ("Service fails on restart: ModuleNotFoundError",
         "The virtual environment is not activated for the systemd service.\n"
         "Check the ExecStart= line in beaverview.service uses venv/bin/uvicorn, not /usr/bin/uvicorn"),
    ]
    for title, detail in issues:
        story.append(callout(f"Issue: {title}", S, "warn"))
        story.extend(code_block(detail, S))
        story.append(sp(6))

    story.append(Paragraph("Useful commands reference", S["h2"]))
    story.append(two_col_table([
        ("Check API directly",         "curl http://localhost:8000/api/health"),
        ("Check audit log",            "sqlite3 beaverview.db 'SELECT * FROM audit_log ORDER BY ts DESC LIMIT 10'"),
        ("Check room count",           "sqlite3 beaverview.db 'SELECT COUNT(*) FROM rooms'"),
        ("Restart BeaverView",         "sudo systemctl restart beaverview"),
        ("View service logs",          "sudo journalctl -u beaverview -f"),
        ("Backup database",            "cp api/beaverview.db backups/beaverview-$(date +%Y%m%d).db"),
        ("Re-run data migration",      "cd api && source venv/bin/activate && python3 migrate_data.py"),
        ("Update packages",            "cd api && source venv/bin/activate && pip install -r requirements.txt"),
        ("Check nginx config",         "sudo nginx -t"),
        ("Reload nginx",               "sudo systemctl reload nginx"),
    ], S))

    story.append(sp(12))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=12))
    story.append(Paragraph("Build Complete", S["h1"]))
    story.append(Paragraph(
        "You now have a fully functional BeaverView deployment. The admin panel at "
        "/admin/ lets you manage rooms, view logs, toggle connectors, and control user "
        "access — all without editing code files.", S["body"]))
    story.append(Paragraph("Next improvements to consider:", S["h3"]))
    for item in [
        "Add real device IPs to hardware_ips.csv and run import_device_ips.py",
        "Set Crestron polling credentials in .env (CRESTRON_POLL_USERNAME/PASSWORD)",
        "Set up a cron job to auto-archive logs older than 90 days",
        "Add an 'Admin' link to the main dashboard header (only for admin role)",
        "Configure VLAN routing on the Ubuntu VM for the AV device subnet (10.20.x.x)",
        "Add slowapi rate limiting for the log export endpoint",
        "Deploy Chart.js to dashboard/vendor/ for admin summary bar charts",
    ]:
        story.append(Paragraph(f"  •  {item}", S["body"]))

    return story

# ── Build PDF ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Building BeaverView Complete Build Playbook PDF...")
    S = S()
    doc, hf = make_doc()
    story = build_story(S)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    size_mb = os.path.getsize(OUT_PATH) / 1_048_576
    print(f"Done: {OUT_PATH}")
    print(f"Size: {size_mb:.1f} MB")
