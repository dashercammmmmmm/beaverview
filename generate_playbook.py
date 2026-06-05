"""
BeaverView — Complete Implementation Playbook PDF Generator
Scenario: VMware VM (Ubuntu) · Windows clients on same network · Self-signed SSL · Entra SSO
Run: python3 generate_playbook.py
Output: BeaverView-Playbook.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Brand colors ───────────────────────────────────────────────────────────────
OSU_ORANGE   = colors.HexColor("#D73F09")
OSU_DARK     = colors.HexColor("#111827")
OSU_ORANGE_F = colors.HexColor("#FFF0EB")
STATUS_OK    = colors.HexColor("#15803D")
STATUS_WARN  = colors.HexColor("#B45309")
STATUS_INFO  = colors.HexColor("#1D4ED8")
BG_LIGHT     = colors.HexColor("#F3F4F6")
BG_CODE      = colors.HexColor("#1E293B")
TEXT_CODE    = colors.HexColor("#E2E8F0")
BORDER_GRAY  = colors.HexColor("#D1D5DB")
TEXT_MUTED   = colors.HexColor("#6B7280")

# ── Styles ─────────────────────────────────────────────────────────────────────
def make_styles():
    styles = {}
    styles["h1"] = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=22,
        textColor=OSU_DARK, spaceAfter=6, spaceBefore=20, leading=28)
    styles["h2"] = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15,
        textColor=OSU_ORANGE, spaceAfter=4, spaceBefore=16, leading=20)
    styles["h3"] = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11,
        textColor=OSU_DARK, spaceAfter=3, spaceBefore=10, leading=16)
    styles["body"] = ParagraphStyle("body", fontName="Helvetica", fontSize=10,
        textColor=OSU_DARK, spaceAfter=6, leading=15)
    styles["body_muted"] = ParagraphStyle("body_muted", fontName="Helvetica", fontSize=9,
        textColor=TEXT_MUTED, spaceAfter=4, leading=13)
    styles["step_num"] = ParagraphStyle("step_num", fontName="Helvetica-Bold", fontSize=11,
        textColor=colors.white, leading=14)
    styles["step_body"] = ParagraphStyle("step_body", fontName="Helvetica", fontSize=10,
        textColor=OSU_DARK, spaceAfter=4, leading=15)
    styles["code"] = ParagraphStyle("code", fontName="Courier", fontSize=8.5,
        textColor=TEXT_CODE, spaceAfter=0, leading=13)
    styles["callout_title"] = ParagraphStyle("callout_title", fontName="Helvetica-Bold",
        fontSize=10, textColor=OSU_DARK, spaceAfter=2, leading=14)
    styles["callout_body"] = ParagraphStyle("callout_body", fontName="Helvetica", fontSize=9,
        textColor=OSU_DARK, spaceAfter=0, leading=13)
    styles["small_bold"] = ParagraphStyle("small_bold", fontName="Helvetica-Bold", fontSize=8,
        textColor=TEXT_MUTED, spaceAfter=2, leading=11)
    return styles

# ── Helper: code block ─────────────────────────────────────────────────────────
def code_block(lines, styles, width=6.5*inch):
    paras = []
    for line in lines:
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace(" ", "&nbsp;")
        paras.append(Paragraph(safe, styles["code"]))
    t = Table([[p] for p in paras], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), BG_CODE),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING",  (0,0),(-1,-1), 12),
        ("RIGHTPADDING", (0,0),(-1,-1), 12),
    ]))
    return t

# ── Helper: callout box ────────────────────────────────────────────────────────
def callout(title, body_lines, styles, color=STATUS_INFO, width=6.5*inch):
    content = [Paragraph(title, styles["callout_title"])]
    for line in body_lines:
        content.append(Paragraph(line, styles["callout_body"]))
    t = Table([content], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), BG_LIGHT),
        ("LEFTPADDING",  (0,0),(-1,-1), 14),
        ("RIGHTPADDING", (0,0),(-1,-1), 14),
        ("TOPPADDING",   (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("LINEBEFORE",   (0,0),(0,-1), 4, color),
        ("BOX",          (0,0),(-1,-1), 0.5, BORDER_GRAY),
    ]))
    return t

# ── Helper: numbered step ──────────────────────────────────────────────────────
def step(num, title, body_lines, styles, width=6.5*inch):
    badge = Table([[Paragraph(str(num), styles["step_num"])]],
                  colWidths=[22], rowHeights=[22])
    badge.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), OSU_ORANGE),
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
    ]))
    title_p = Paragraph(f"<b>{title}</b>", styles["h3"])
    body_ps = [Paragraph(line, styles["step_body"]) for line in body_lines]
    t = Table([[badge, [title_p] + body_ps]], colWidths=[30, width-30])
    t.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING",  (1,0),(1,-1), 10),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
    ]))
    return t

# ── Helper: info table ─────────────────────────────────────────────────────────
def info_table(rows, styles, col_widths=None, header=None):
    if col_widths is None:
        col_widths = [2.5*inch, 4.0*inch]
    data = []
    if header:
        data.append([Paragraph(f"<b>{h}</b>", styles["small_bold"]) for h in header])
    for row in rows:
        data.append([Paragraph(str(c), styles["body"]) for c in row])
    t = Table(data, colWidths=col_widths)
    ts = [
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.white, BG_LIGHT]),
        ("BOX",           (0,0),(-1,-1), 0.5, BORDER_GRAY),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BORDER_GRAY),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]
    if header:
        ts += [("BACKGROUND",(0,0),(-1,0), OSU_DARK),
               ("TEXTCOLOR", (0,0),(-1,0), colors.white)]
    t.setStyle(TableStyle(ts))
    return t

# ── Page header/footer ─────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(OSU_DARK)
    canvas.rect(0, h-30, w, 30, fill=1, stroke=0)
    canvas.setFillColor(OSU_ORANGE)
    canvas.rect(0, h-33, w, 3, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(0.75*inch, h-20, "BeaverView — Implementation Playbook")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(w-0.75*inch, h-20, "OSU Presentation Support")
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w/2, 24, f"Page {doc.page}")
    canvas.restoreState()

# ══════════════════════════════════════════════════════════════════════════════
# COVER
# ══════════════════════════════════════════════════════════════════════════════
def cover_page(story, styles):
    story.append(Spacer(1, 1.0*inch))
    cover_data = [[
        Paragraph("BeaverView", ParagraphStyle("ct", fontName="Helvetica-Bold",
            fontSize=42, textColor=colors.white, leading=48)),
        Paragraph("OSU Presentation Support Dashboard", ParagraphStyle("cs",
            fontName="Helvetica", fontSize=13, textColor=colors.HexColor("#FCA07A"), leading=18)),
        Spacer(1, 0.08*inch),
        Paragraph("Complete Implementation Playbook", ParagraphStyle("ctag",
            fontName="Helvetica-Bold", fontSize=13, textColor=colors.white, leading=18)),
        Spacer(1, 0.04*inch),
        Paragraph("VMware Ubuntu VM  ·  Windows clients on local network  ·  Entra SSO",
            ParagraphStyle("cdesc", fontName="Helvetica", fontSize=10,
            textColor=colors.HexColor("#D1D5DB"), leading=15)),
    ]]
    cover = Table([cover_data], colWidths=[6.5*inch])
    cover.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), OSU_DARK),
        ("TOPPADDING",   (0,0),(-1,-1), 40),
        ("BOTTOMPADDING",(0,0),(-1,-1), 40),
        ("LEFTPADDING",  (0,0),(-1,-1), 40),
        ("RIGHTPADDING", (0,0),(-1,-1), 40),
        ("LINEBEFORE",   (0,0),(0,-1), 5, OSU_ORANGE),
    ]))
    story.append(cover)
    story.append(Spacer(1, 0.25*inch))

    story.append(callout("What is BeaverView?", [
        "BeaverView is a web dashboard for OSU Presentation Support technicians. It shows every "
        "classroom and conference room on a live map across all three campuses, and lets technicians "
        "take action directly in the browser: launch remote desktop, control A/V equipment, cycle "
        "power, pull up documentation, and file ServiceNow tickets — without opening a dozen "
        "separate systems.",
        "",
        "This playbook covers everything from creating the Ubuntu virtual machine to the moment "
        "a Windows technician logs in with their OSU credentials and sees the dashboard.",
    ], styles, color=OSU_ORANGE))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Deployment overview", styles["h2"]))
    story.append(info_table([
        ["Server",       "Ubuntu 22.04 or 24.04 VM running in VMware on your network"],
        ["Web server",   "nginx — handles HTTPS and forwards requests to the Python backend"],
        ["Backend",      "Python (FastAPI) — runs as a systemd service, auto-restarts on crashes"],
        ["Clients",      "Any Windows PC on the same network — open a browser, type the hostname"],
        ["URL",          "https://beaverview  (or whatever hostname you assign the VM)"],
        ["SSL",          "Self-signed certificate — browsers show a one-time warning, then remember it"],
        ["Login",        "OSU Entra (Azure AD) — technicians sign in with their OSU credentials"],
        ["Database",     "SQLite — built-in, no separate database server needed"],
    ], styles, col_widths=[1.2*inch, 5.3*inch]))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Guide contents", styles["h2"]))
    story.append(info_table([
        ["Part 1", "Prerequisites",                "Software and access you need before starting"],
        ["Part 2", "Create the Ubuntu VM",         "VMware setup, Ubuntu install, network configuration"],
        ["Part 3", "Install BeaverView on the VM", "Python, project files, service setup"],
        ["Part 4", "Set up HTTPS",                 "Self-signed SSL certificate + nginx reverse proxy"],
        ["Part 5", "Configure Windows clients",    "Hosts file, browser trust, test from Windows"],
        ["Part 6", "Set up Entra SSO login",       "Azure portal registration, .env credentials"],
        ["Part 7", "Editing content",              "Add rooms, change colors — from Windows via SSH"],
        ["Part 8", "Connecting live data",         "Wire up Fusion, ScreenConnect, ServiceNow, etc."],
        ["Part 9", "Day-to-day operations",        "Updates, backups, monitoring, troubleshooting"],
        ["Part 10","Reference",                    "File map, API endpoints, status codes"],
    ], styles, col_widths=[0.65*inch, 1.8*inch, 4.05*inch]))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — PREREQUISITES
# ══════════════════════════════════════════════════════════════════════════════
def part1(story, styles):
    story.append(Paragraph("Part 1 — Prerequisites", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))
    story.append(Paragraph(
        "Collect everything below before you start. Most of this is one-time access you "
        "request from OSU IT — do it early because approvals can take a few days.",
        styles["body"]))

    story.append(Paragraph("What you need", styles["h2"]))
    story.append(info_table([
        ["VMware Workstation Pro\nor VMware ESXi",
         "To create and run the Ubuntu VM.\n"
         "Workstation Pro runs on your existing Windows or Mac computer.\n"
         "ESXi runs on a dedicated server — ask OSU IT if one is available."],
        ["Ubuntu 22.04 or 24.04 ISO",
         "The Linux operating system for the VM. Free download from ubuntu.com/download/server.\n"
         "Download the Server edition (no desktop needed)."],
        ["The BeaverView project files",
         "A folder containing api/ and dashboard/ subfolders.\n"
         "Either a ZIP file you received, or a Git repository URL from your team."],
        ["An SSH client on your Windows computer",
         "You'll use this to type commands on the VM from Windows.\n"
         "Windows 10/11 have SSH built in (use PowerShell or Windows Terminal).\n"
         "Alternatively: download PuTTY from putty.org (free)."],
        ["VS Code with Remote SSH extension (recommended)",
         "Lets you edit files on the VM directly from Windows as if they were local.\n"
         "Free download from code.visualstudio.com.\n"
         "After installing: open Extensions (Ctrl+Shift+X), search 'Remote SSH', install it."],
        ["Access to OSU Azure portal",
         "For registering BeaverView as an Entra SSO application.\n"
         "URL: portal.azure.com — log in with your OSU admin credentials.\n"
         "You need permission to create App Registrations. Ask OSU IT if you don't have it."],
        ["Admin rights on each Windows client PC",
         "Needed once to edit the Windows hosts file (Part 5).\n"
         "After that, regular users can access the dashboard with no admin rights."],
    ], styles, col_widths=[2.1*inch, 4.4*inch],
       header=["Requirement", "Details"]))

    story.append(Spacer(1, 0.1*inch))
    story.append(callout("You do NOT need:", [
        "Node.js, npm, Docker, or any build tools",
        "A separate database server (SQLite is built-in to Python)",
        "A public domain name or external SSL certificate",
        "Any cloud subscription beyond the OSU Azure account you already have",
    ], styles, color=STATUS_OK))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — CREATE THE UBUNTU VM
# ══════════════════════════════════════════════════════════════════════════════
def part2(story, styles):
    story.append(Paragraph("Part 2 — Create the Ubuntu VM in VMware", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))
    story.append(Paragraph(
        "This part walks you through creating a new virtual machine and installing Ubuntu on it. "
        "If your IT team has already given you a running Ubuntu VM, skip to Step 6.",
        styles["body"]))

    vm_steps = [
        ("Open VMware and create a new VM",
         ["In VMware Workstation: click File → New Virtual Machine → Typical.",
          "Choose 'Installer disc image file (ISO)' and browse to the Ubuntu ISO you downloaded.",
          "VMware may auto-detect Ubuntu — click Next."]),
        ("Name the VM and choose a location",
         ["Name: BeaverView  (this is just the VMware display name)",
          "Location: anywhere with enough disk space (default is fine).",
          "Click Next."]),
        ("Set disk size",
         ["Recommended: 20 GB minimum. 40 GB is comfortable.",
          "Choose 'Store virtual disk as a single file'.",
          "Click Next."]),
        ("Set RAM and CPU (click 'Customize Hardware')",
         ["RAM: 2 GB minimum. 4 GB recommended.",
          "Processors: 2 cores recommended.",
          "Network Adapter: IMPORTANT — set this to Bridged (not NAT).",
          "  Bridged mode gives the VM its own IP on your real network.",
          "  NAT mode hides the VM behind your computer — Windows clients cannot reach it.",
          "Click Close, then Finish."]),
        ("Install Ubuntu",
         ["The VM starts and boots from the ISO automatically.",
          "Choose 'Install Ubuntu Server'.",
          "Language: English. Keyboard: your layout.",
          "Network: leave as-is (DHCP — gets an IP automatically).",
          "Storage: 'Use entire disk' → Done → Continue.",
          "Profile setup: fill in your name, server name (use: beaverview), username, and password.",
          "  Write down the username and password — you'll need them every time you SSH in.",
          "SSH: CHECK 'Install OpenSSH server'. This is required.",
          "Featured snaps: skip all. Click Done.",
          "Wait 5–10 minutes for installation to complete, then reboot when prompted."]),
        ("Find the VM's IP address",
         ["After Ubuntu boots and you see the login prompt, log in and run:",
          "    ip addr show",
          "Look for a line like:  inet 192.168.1.50/24",
          "That number (e.g., 192.168.1.50) is the VM's IP address.",
          "Write it down — you'll use it in Part 4 and Part 5.",
          "",
          "Tip: to make this IP permanent (so it doesn't change after a reboot),",
          "ask your network admin to assign a DHCP reservation for the VM's MAC address."]),
        ("Test SSH from Windows",
         ["Open PowerShell or Windows Terminal on your Windows computer and type:",
          "    ssh your-username@192.168.1.50",
          "(Replace with your actual username and IP address.)",
          "Type 'yes' when asked about the fingerprint, then enter your password.",
          "If you see a $ prompt, SSH is working. Type  exit  to disconnect.",
          "",
          "From this point on, all commands in this guide are typed in this SSH session."]),
    ]

    for i, (title, lines) in enumerate(vm_steps):
        story.append(KeepTogether([
            step(i+1, title, lines, styles),
            Spacer(1, 0.12*inch),
        ]))

    story.append(callout("If VMware shows 'Bridged' but Windows clients still can't connect", [
        "In VMware: Edit → Virtual Network Editor → change VMnet0 to the correct physical adapter "
        "(the network card your Windows computer uses to connect to the office network).",
        "Then restart the VM.",
    ], styles, color=STATUS_WARN))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — INSTALL BEAVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
def part3(story, styles):
    story.append(Paragraph("Part 3 — Install BeaverView on the VM", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))
    story.append(Paragraph(
        "All commands in this part are typed into your SSH session on the Ubuntu VM "
        "(from the PowerShell window you opened in Part 2, Step 7).",
        styles["body"]))

    install_steps = [
        ("Update Ubuntu and install required packages",
         ["    sudo apt update && sudo apt upgrade -y",
          "    sudo apt install python3 python3-venv python3-pip nginx -y",
          "This takes 2–5 minutes. Wait for it to finish."]),
        ("Create a service account for BeaverView",
         ["A service account is a special user that runs only BeaverView — it can't log in interactively.",
          "    sudo useradd -m -s /bin/bash beaverview"]),
        ("Copy the project files to the VM",
         ["Option A — if you have a Git repository:",
          "    sudo -u beaverview git clone https://your-repo-url /home/beaverview/app",
          "",
          "Option B — if you have a ZIP file, copy it from Windows using SCP:",
          "  Open a second PowerShell on Windows (not the SSH one) and run:",
          "    scp 'C:\\path\\to\\project.zip' your-username@192.168.1.50:~/",
          "  Then back in the SSH window:",
          "    sudo mv ~/project.zip /home/beaverview/",
          "    sudo -u beaverview unzip /home/beaverview/project.zip -d /home/beaverview/app"]),
        ("Verify the folder structure",
         ["    ls /home/beaverview/app",
          "You should see:  api/   dashboard/   PLAYBOOK-*.md",
          "If you see those, the files are in the right place."]),
        ("Set up the Python virtual environment",
         ["    cd /home/beaverview/app/api",
          "    sudo -u beaverview python3 -m venv venv",
          "    sudo -u beaverview venv/bin/pip install -r requirements.txt",
          "This takes 1–3 minutes on first run."]),
        ("Configure the .env credentials file",
         ["    sudo -u beaverview cp /home/beaverview/app/api/.env.example /home/beaverview/app/api/.env",
          "    sudo nano /home/beaverview/app/api/.env",
          "",
          "At minimum, set PROXY_SECRET by generating a random value:",
          "    python3 -c \"import secrets; print(secrets.token_hex(32))\"",
          "Copy the output and paste it as the value of PROXY_SECRET in the .env file.",
          "Save with Ctrl+O, Enter, Ctrl+X.",
          "",
          "    sudo chmod 600 /home/beaverview/app/api/.env",
          "    sudo chown beaverview:beaverview /home/beaverview/app/api/.env"]),
        ("Create the systemd service",
         ["Systemd makes BeaverView start automatically when the VM boots and restart if it crashes.",
          "    sudo nano /etc/systemd/system/beaverview.service",
          "",
          "Paste the following exactly:",
          "  [Unit]",
          "  Description=BeaverView API",
          "  After=network.target",
          "",
          "  [Service]",
          "  Type=simple",
          "  User=beaverview",
          "  WorkingDirectory=/home/beaverview/app/api",
          "  Environment=\"PATH=/home/beaverview/app/api/venv/bin\"",
          "  ExecStart=/home/beaverview/app/api/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000",
          "  Restart=on-failure",
          "  RestartSec=5",
          "",
          "  [Install]",
          "  WantedBy=multi-user.target",
          "",
          "Save with Ctrl+O, Enter, Ctrl+X."]),
        ("Enable and start the service",
         ["    sudo systemctl daemon-reload",
          "    sudo systemctl enable beaverview",
          "    sudo systemctl start beaverview",
          "    sudo systemctl status beaverview",
          "",
          "The last command should show:  Active: active (running)",
          "If it shows 'failed', run:  sudo journalctl -u beaverview -n 30  to see the error."]),
    ]

    for i, (title, lines) in enumerate(install_steps):
        story.append(KeepTogether([
            step(i+1, title, lines, styles),
            Spacer(1, 0.12*inch),
        ]))

    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 4 — SET UP HTTPS
# ══════════════════════════════════════════════════════════════════════════════
def part4(story, styles):
    story.append(Paragraph("Part 4 — Set Up HTTPS with nginx", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))
    story.append(Paragraph(
        "nginx is a web server that sits in front of BeaverView and handles HTTPS. "
        "This part creates a self-signed SSL certificate and configures nginx to use it.",
        styles["body"]))

    story.append(callout("About self-signed certificates", [
        "A self-signed certificate encrypts the connection just as well as a paid certificate. "
        "The only difference is that browsers can't automatically verify who issued it, so they "
        "show a warning the first time a user visits. Each Windows user will see:",
        "",
        "'Your connection is not private' (Chrome) or 'This site is not secure' (Edge).",
        "",
        "They click 'Advanced' then 'Proceed to beaverview (unsafe)' — just once. "
        "After that, their browser remembers it and never shows the warning again. "
        "Part 5 covers how to permanently trust the certificate so the warning never appears.",
    ], styles, color=STATUS_WARN))

    https_steps = [
        ("Create the SSL certificate",
         ["Run these commands on the VM (in your SSH session):",
          "    sudo mkdir -p /etc/ssl/beaverview",
          "    sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \\",
          "        -keyout /etc/ssl/beaverview/beaverview.key \\",
          "        -out /etc/ssl/beaverview/beaverview.crt \\",
          "        -subj \"/CN=beaverview\" \\",
          "        -addext \"subjectAltName=DNS:beaverview,IP:192.168.1.50\"",
          "",
          "IMPORTANT: replace 192.168.1.50 with the VM's actual IP address from Part 2.",
          "The -days 3650 means the cert lasts 10 years before you need to renew it."]),
        ("Configure nginx",
         ["    sudo nano /etc/nginx/sites-available/beaverview",
          "",
          "Paste the following exactly (replace 192.168.1.50 with your VM's IP):",
          "",
          "  server {",
          "      listen 80;",
          "      server_name beaverview 192.168.1.50;",
          "      return 301 https://$host$request_uri;",
          "  }",
          "",
          "  server {",
          "      listen 443 ssl;",
          "      server_name beaverview 192.168.1.50;",
          "",
          "      ssl_certificate     /etc/ssl/beaverview/beaverview.crt;",
          "      ssl_certificate_key /etc/ssl/beaverview/beaverview.key;",
          "",
          "      add_header Strict-Transport-Security \"max-age=63072000\" always;",
          "      add_header X-Frame-Options DENY always;",
          "      add_header X-Content-Type-Options nosniff always;",
          "",
          "      location / {",
          "          proxy_pass         http://127.0.0.1:8000;",
          "          proxy_set_header   Host $host;",
          "          proxy_set_header   X-Real-IP $remote_addr;",
          "          proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;",
          "          proxy_set_header   X-Forwarded-Proto $scheme;",
          "          proxy_read_timeout 30s;",
          "      }",
          "  }",
          "",
          "Save with Ctrl+O, Enter, Ctrl+X."]),
        ("Enable the site and restart nginx",
         ["    sudo ln -s /etc/nginx/sites-available/beaverview /etc/nginx/sites-enabled/",
          "    sudo nginx -t",
          "  This should print: syntax is ok  and  test is successful",
          "  If there's an error, re-check the config for typos.",
          "",
          "    sudo systemctl restart nginx",
          "    sudo systemctl enable nginx"]),
        ("Allow HTTPS through the firewall",
         ["Ubuntu has a firewall (ufw) that may be blocking port 443.",
          "    sudo ufw allow 'Nginx Full'",
          "    sudo ufw allow OpenSSH",
          "    sudo ufw --force enable",
          "    sudo ufw status",
          "",
          "You should see 'Nginx Full' and 'OpenSSH' listed as ALLOW."]),
        ("Test HTTPS from the VM itself",
         ["    curl -k https://localhost/api/health",
          "",
          "The -k flag tells curl to accept the self-signed certificate.",
          "Expected response:  {\"status\": \"ok\", \"ts\": \"...\", \"version\": \"0.4.0\"}",
          "If you see that, nginx and BeaverView are working together correctly."]),
    ]

    for i, (title, lines) in enumerate(https_steps):
        story.append(KeepTogether([
            step(i+1, title, lines, styles),
            Spacer(1, 0.12*inch),
        ]))

    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 5 — CONFIGURE WINDOWS CLIENTS
# ══════════════════════════════════════════════════════════════════════════════
def part5(story, styles):
    story.append(Paragraph("Part 5 — Configure Windows Client Computers", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))
    story.append(Paragraph(
        "Do these steps on each Windows computer that needs to access the dashboard. "
        "Step 1 is required. Steps 2 and 3 are optional but eliminate the browser warning permanently.",
        styles["body"]))

    win_steps = [
        ("Edit the Windows hosts file to map the hostname to the VM's IP",
         ["The hosts file tells Windows what IP address to use for a hostname, without needing DNS.",
          "",
          "1. Press the Windows key, type 'Notepad'.",
          "2. Right-click Notepad and choose 'Run as administrator'. Click Yes.",
          "3. In Notepad: File → Open.",
          "4. In the file path box at the bottom, type exactly:",
          "       C:\\Windows\\System32\\drivers\\etc\\hosts",
          "   Make sure the file type dropdown shows 'All Files', then click Open.",
          "5. Scroll to the very bottom of the file and add a new line:",
          "       192.168.1.50   beaverview",
          "   (replace 192.168.1.50 with the VM's actual IP address from Part 2)",
          "6. File → Save. Close Notepad.",
          "",
          "Test it: open a browser and go to  https://beaverview",
          "You'll see a certificate warning — that's expected. Click through it once."]),
        ("(Optional) Trust the certificate permanently — Chrome and Edge",
         ["This removes the 'not private' warning forever on this computer.",
          "",
          "First, copy the certificate from the VM to your Windows computer.",
          "In PowerShell on Windows:",
          "    scp your-username@192.168.1.50:/etc/ssl/beaverview/beaverview.crt C:\\Users\\YourName\\Desktop\\beaverview.crt",
          "",
          "Then install it:",
          "1. Double-click the .crt file on your Desktop.",
          "2. Click 'Install Certificate'.",
          "3. Choose 'Local Machine'. Click Next. Allow the admin prompt.",
          "4. Choose 'Place all certificates in the following store'.",
          "5. Click Browse → select 'Trusted Root Certification Authorities'. Click OK.",
          "6. Click Next → Finish. Click OK on the success message.",
          "7. Restart Chrome or Edge.",
          "",
          "The warning will no longer appear."]),
        ("(Optional) Trust the certificate permanently — Firefox",
         ["Firefox manages its own certificate store separately from Windows.",
          "",
          "1. Open Firefox and go to  https://beaverview",
          "2. Click 'Advanced...' then 'Accept the Risk and Continue'.",
          "3. Click the padlock icon in the address bar.",
          "4. Click 'Connection not secure' → 'More information'.",
          "5. Click 'View Certificate' → 'beaverview' tab.",
          "6. Scroll to 'Miscellaneous' → download the PEM (cert) file.",
          "7. Firefox menu → Settings → Privacy & Security → scroll to 'Certificates'.",
          "8. Click 'View Certificates' → 'Authorities' tab → Import.",
          "9. Select the downloaded .pem file. Check 'Trust this CA to identify websites'. OK.",
          "",
          "Restart Firefox. The warning will no longer appear."]),
        ("Test from the Windows browser",
         ["Open Chrome, Edge, or Firefox and go to:  https://beaverview",
          "",
          "You should see the BeaverView dashboard with the OSU orange header and campus map.",
          "If the Entra login is not configured yet (Part 6), the dashboard opens directly.",
          "After Part 6, you'll be redirected to OSU login first.",
          "",
          "If the page doesn't load:",
          "  - Ping the VM: open PowerShell and run:  ping 192.168.1.50",
          "  - If ping fails: check VMware network adapter is set to Bridged (Part 2, Step 4)",
          "  - If ping works but browser fails: check hosts file edit (Step 1 above)",
          "  - Check nginx is running on VM:  sudo systemctl status nginx"]),
    ]

    for i, (title, lines) in enumerate(win_steps):
        story.append(KeepTogether([
            step(i+1, title, lines, styles),
            Spacer(1, 0.12*inch),
        ]))

    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 6 — ENTRA SSO
# ══════════════════════════════════════════════════════════════════════════════
def part6(story, styles):
    story.append(Paragraph("Part 6 — Set Up OSU Entra SSO Login", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))
    story.append(Paragraph(
        "Entra SSO (formerly Azure AD) lets technicians log in with their OSU username and "
        "password. It also adds real user identity to the audit log and enables role-based "
        "access (Technician vs. Admin). You need access to the OSU Azure portal to complete "
        "this part.",
        styles["body"]))

    sso_steps = [
        ("Register BeaverView in the Azure portal",
         ["1. Go to portal.azure.com and log in with your OSU admin credentials.",
          "2. Search for 'Azure Active Directory' in the top search bar.",
          "3. In the left menu click 'App registrations' → 'New registration'.",
          "4. Fill in:",
          "     Name:          BeaverView",
          "     Account types: Accounts in this organizational directory only (OSU only)",
          "     Redirect URI:  Web  →  https://beaverview/auth/callback",
          "5. Click Register.",
          "",
          "You'll land on the app's Overview page. Leave this tab open."]),
        ("Copy the IDs you need",
         ["On the app Overview page, find and copy two values:",
          "  Application (client) ID  — a long string like  a1b2c3d4-...",
          "  Directory (tenant) ID    — another long string",
          "",
          "Open a text file (Notepad) and paste both — you'll need them in Step 5."]),
        ("Create a client secret",
         ["1. In the left menu click 'Certificates & secrets'.",
          "2. Click '+ New client secret'.",
          "3. Description: BeaverView Server  |  Expires: 24 months",
          "4. Click Add.",
          "5. IMMEDIATELY copy the Value column (not the Secret ID).",
          "   It disappears after you leave this page and cannot be recovered.",
          "   Paste it into your Notepad file."]),
        ("Create Azure AD security groups",
         ["Groups control who gets Technician access vs. Admin access.",
          "",
          "1. Go back to Azure Active Directory → Groups → New group.",
          "2. Create: BeaverView Technicians",
          "     Group type: Security  |  Group name: BeaverView Technicians",
          "     Click Create.",
          "3. Create a second group: BeaverView Admins (same steps).",
          "4. Open each group, click Properties, and copy the Object ID.",
          "   Add both Object IDs to your Notepad file.",
          "",
          "5. Open BeaverView Technicians → Members → Add members.",
          "   Add the OSU staff who should have technician access.",
          "   Repeat for BeaverView Admins."]),
        ("Add the credentials to the .env file on the VM",
         ["SSH into the VM and edit the .env file:",
          "    sudo nano /home/beaverview/app/api/.env",
          "",
          "Find and fill in these lines (paste from your Notepad file):",
          "    AZURE_TENANT_ID=your-directory-tenant-id",
          "    AZURE_CLIENT_ID=your-application-client-id",
          "    AZURE_CLIENT_SECRET=your-client-secret-value",
          "    AZURE_GROUP_TECHNICIAN=object-id-of-technicians-group",
          "    AZURE_GROUP_ADMIN=object-id-of-admins-group",
          "",
          "Save with Ctrl+O, Enter, Ctrl+X.",
          "",
          "Then restart BeaverView:",
          "    sudo systemctl restart beaverview"]),
        ("Install the MSAL authentication library",
         ["    sudo -u beaverview /home/beaverview/app/api/venv/bin/pip install msal",
          "    echo 'msal>=1.28.0' | sudo tee -a /home/beaverview/app/api/requirements.txt",
          "",
          "MSAL is Microsoft's Python library for Azure AD authentication.",
          "The authentication routes are already scaffolded in main.py — see PLAYBOOK-DEVELOPMENT.md",
          "for the full implementation guide if you need to customize the session handling."]),
        ("Test the login flow",
         ["From a Windows computer, open a browser and go to:  https://beaverview",
          "",
          "You should be redirected to the OSU Microsoft login page.",
          "Log in with your OSU credentials.",
          "After successful login you should return to the BeaverView dashboard.",
          "",
          "If you see a redirect error: double-check the Redirect URI in the Azure portal",
          "matches exactly:  https://beaverview/auth/callback  (no trailing slash)."]),
    ]

    for i, (title, lines) in enumerate(sso_steps):
        story.append(KeepTogether([
            step(i+1, title, lines, styles),
            Spacer(1, 0.12*inch),
        ]))

    story.append(callout("Security checklist before going live", [
        "[ ]  .env permissions are 600:  ls -la /home/beaverview/app/api/.env",
        "[ ]  .env is NOT in Git:  git -C /home/beaverview/app status (confirm .env not listed)",
        "[ ]  No raw IP addresses visible in browser DevTools Network tab",
        "[ ]  Audit log working:  curl -k https://beaverview/api/audit",
        "[ ]  CORS restricted: in main.py change allow_origins=[\"*\"] to allow_origins=[\"https://beaverview\"]",
        "[ ]  Live reload block removed from dashboard/index.html",
        "[ ]  window._dev line removed from dashboard/app.js",
    ], styles, color=STATUS_WARN))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 7 — EDITING CONTENT FROM WINDOWS
# ══════════════════════════════════════════════════════════════════════════════
def part7(story, styles):
    story.append(Paragraph("Part 7 — Editing Content from Windows", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))
    story.append(Paragraph(
        "The dashboard files live on the VM. To edit them from Windows, you connect "
        "VS Code directly to the VM over SSH — then you edit files on the VM as if they "
        "were local. Changes appear in the browser within 2 seconds.",
        styles["body"]))

    story.append(Paragraph("Connecting VS Code to the VM", styles["h2"]))
    story.append(info_table([
        ["1.", "Open VS Code on Windows."],
        ["2.", "Press Ctrl+Shift+P to open the command palette."],
        ["3.", "Type: Remote-SSH: Connect to Host  and press Enter."],
        ["4.", "Type: your-username@192.168.1.50  and press Enter."],
        ["5.", "A new VS Code window opens. It may take 30 seconds the first time."],
        ["6.", "Click 'Open Folder' and navigate to:  /home/beaverview/app"],
        ["7.", "You can now see and edit all project files in the VS Code file tree."],
    ], styles, col_widths=[0.25*inch, 6.25*inch]))

    story.append(Paragraph("Files you'll edit most", styles["h2"]))
    story.append(info_table([
        ["dashboard/data.js",   "Add/edit rooms, buildings, and campuses"],
        ["dashboard/styles.css","Change colors, sizes, and layout"],
        ["dashboard/index.html","Change static text, page title, help dialog"],
        ["api/.env",            "Add credentials for live connectors"],
        ["api/main.py",         "Backend code — only needed for new features"],
    ], styles, col_widths=[2.0*inch, 4.5*inch],
       header=["File", "Edit when you want to..."]))

    story.append(Paragraph("Adding a room", styles["h2"]))
    story.append(Paragraph(
        "Open <b>dashboard/data.js</b> in VS Code. Use Ctrl+F to search for the building "
        "code (e.g., KAd). Find its rooms array and add a new object. Copy an existing "
        "room and change the values:",
        styles["body"]))
    story.append(code_block([
        '{',
        '  number:        "210",',
        '  type:          "Seminar Room",',
        '  status:        "available",    // available | in-use | issue | offline',
        '  health:        94,             // 0-100',
        '  activeEvent:   "Available",',
        '  fusion:        "online",',
        '  display:       "on",',
        '  screenconnect: true,           // true = ScreenConnect button shown',
        '  wattbox:       false,          // true = WattBox buttons shown',
        '  hybrid:        true,',
        '  stale:         false,',
        '  incidents: { open: [], closed: [] },',
        '  devices: [',
        '    ["Display",           "NEC",     "P-series", "Sanitized host"],',
        '    ["Control Processor", "Crestron","CP4",      "Sanitized host"]',
        '  ]',
        '},',
    ], styles))

    story.append(Paragraph("After saving, open https://beaverview in your browser. The new room "
        "appears within 2 seconds automatically.", styles["body_muted"]))

    story.append(Paragraph("Changing a color", styles["h2"]))
    story.append(Paragraph(
        "Open <b>dashboard/styles.css</b>. The very top section (DESIGN TOKENS) lists "
        "every color as a named variable. Change the hex value and save:",
        styles["body"]))
    story.append(code_block([
        '--osu-orange:     #D73F09;   /* active tabs, buttons, selected rooms */',
        '--status-ok:      #15803D;   /* available rooms — green              */',
        '--status-active:  #1D6A9F;   /* in-use rooms — blue                  */',
        '--status-warn:    #B45309;   /* rooms with issues — amber            */',
        '--status-offline: #6B7280;   /* offline rooms — gray                 */',
        '--bg-page:        #EEF2F7;   /* overall page background              */',
    ], styles))

    story.append(Paragraph("After editing .env (credentials), you must restart BeaverView", styles["h2"]))
    story.append(Paragraph(
        "The backend only reads .env at startup. After editing it, SSH into the VM and run:",
        styles["body"]))
    story.append(code_block([
        'sudo systemctl restart beaverview',
        'sudo systemctl status beaverview   # confirm it shows "active (running)"',
    ], styles))

    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 8 — CONNECTING LIVE DATA
# ══════════════════════════════════════════════════════════════════════════════
def part8(story, styles):
    story.append(Paragraph("Part 8 — Connecting Live Data", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))
    story.append(Paragraph(
        "Each connector is independent — wire them one at a time. The dashboard runs on "
        "mock data for any connector you haven't configured yet.",
        styles["body"]))

    story.append(Paragraph("How to add credentials (same process for every connector)", styles["h2"]))
    story.append(code_block([
        '# SSH into the VM, then:',
        'sudo nano /home/beaverview/app/api/.env',
        '',
        '# Find the section for your connector and fill in the values',
        '# Save with Ctrl+O, Enter, Ctrl+X',
        '',
        '# Restart to apply:',
        'sudo systemctl restart beaverview',
        '',
        '# Connector badge in dashboard sidebar turns green automatically',
    ], styles))

    story.append(Paragraph("Connector quick reference", styles["h2"]))
    story.append(info_table([
        ["Crestron Fusion\n(room status, display power)",
         "Pattern: REST API\n"
         "Credentials needed:\n"
         "  FUSION_BASE_URL=https://fusion.oregonstate.edu\n"
         "  FUSION_API_KEY=your-api-key\n"
         "Get credentials from: CIS / Presentation Support admin"],
        ["ScreenConnect\n(remote desktop to lectern PCs)",
         "Pattern: SSO passthrough — no password stored\n"
         "Credentials needed:\n"
         "  SC_BASE_URL=https://screenconnect.oregonstate.edu\n"
         "Requirement: each PC must be named BUILDING-ROOM-PC in ScreenConnect\n"
         "  Example: KAD-101-PC"],
        ["WattBox / OvrC\n(outlet power control)",
         "Pattern: REST API\n"
         "Credentials needed:\n"
         "  WATTBOX_OVRC_BASE_URL=https://my.ovrc.com/api/v1\n"
         "  WATTBOX_OVRC_API_KEY=your-ovrc-api-key\n"
         "Get credentials from: my.ovrc.com account settings"],
        ["ServiceNow\n(incident tickets)",
         "Pattern: OAuth\n"
         "Credentials needed:\n"
         "  SERVICENOW_INSTANCE=oregonstate\n"
         "  SERVICENOW_CLIENT_ID=your-client-id\n"
         "  SERVICENOW_CLIENT_SECRET=your-client-secret\n"
         "Get credentials from: ServiceNow OAuth app registration in OSU instance"],
        ["SharePoint\n(room documentation)",
         "Pattern: SSO passthrough — no password stored\n"
         "Credentials needed:\n"
         "  SHAREPOINT_BASE_URL=https://oregonstate.sharepoint.com/sites/AVSupport\n"
         "Organize room docs at: /sites/AVSupport/SitePages/Rooms/{room-id}.aspx"],
        ["25Live\n(room schedule / active events)",
         "Pattern: REST API with basic auth\n"
         "Credentials needed:\n"
         "  LIVE25_BASE_URL=https://25live.collegenet.com/25live/data/oregonstate\n"
         "  LIVE25_USERNAME=svc-beaverview@oregonstate.edu\n"
         "  LIVE25_PASSWORD=service-account-password\n"
         "Use a service account, not a personal account"],
    ], styles, col_widths=[1.7*inch, 4.8*inch],
       header=["Connector", "Setup details"]))

    story.append(Spacer(1, 0.1*inch))
    story.append(callout("To revert a connector back to mock mode", [
        "Comment out its credentials in .env (add # at the start of each line) and restart. "
        "The connector returns to mock mode instantly. All audit log entries are preserved.",
    ], styles, color=STATUS_INFO))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 9 — DAY-TO-DAY OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════
def part9(story, styles):
    story.append(Paragraph("Part 9 — Day-to-Day Operations", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))

    story.append(Paragraph("Checking if BeaverView is running", styles["h2"]))
    story.append(code_block([
        'sudo systemctl status beaverview    # should show "active (running)"',
        'curl -k https://localhost/api/health # should return {"status":"ok",...}',
    ], styles))

    story.append(Paragraph("Viewing live logs", styles["h2"]))
    story.append(code_block([
        'sudo journalctl -u beaverview -f    # streams live log output',
        '                                    # press Ctrl+C to stop',
    ], styles))

    story.append(Paragraph("Updating BeaverView after code changes", styles["h2"]))
    story.append(code_block([
        'cd /home/beaverview/app',
        'sudo -u beaverview git pull',
        'sudo systemctl restart beaverview',
        '# Frontend static files update on next browser load',
        '# If you changed app.js or styles.css, bump the ?v= number in index.html first',
    ], styles))

    story.append(Paragraph("Backing up the audit database", styles["h2"]))
    story.append(Paragraph(
        "The SQLite database at /home/beaverview/app/api/beaverview.db contains the full "
        "audit trail. Set up automatic daily backups with cron:",
        styles["body"]))
    story.append(code_block([
        'sudo mkdir -p /home/beaverview/backups',
        'sudo chown beaverview:beaverview /home/beaverview/backups',
        'sudo -u beaverview crontab -e',
        '',
        '# Add this line in the crontab editor (runs every night at 2am):',
        '0 2 * * * cp /home/beaverview/app/api/beaverview.db /home/beaverview/backups/beaverview-$(date +\\%Y\\%m\\%d).db',
    ], styles))

    story.append(Paragraph("Rolling back after a bad update", styles["h2"]))
    story.append(code_block([
        'cd /home/beaverview/app',
        'git log --oneline           # find the last good commit hash',
        'git checkout <hash> -- dashboard/app.js   # restore one file',
        '# or for a full rollback:',
        'git reset --hard <hash>',
        'sudo systemctl restart beaverview',
    ], styles))

    story.append(Paragraph("Rebooting the VM", styles["h2"]))
    story.append(Paragraph(
        "BeaverView starts automatically when the VM boots (systemd handles this). "
        "To safely reboot the VM:", styles["body"]))
    story.append(code_block([
        'sudo reboot',
        '# Wait ~30 seconds, then test:',
        'curl -k https://192.168.1.50/api/health',
    ], styles))

    story.append(Paragraph("Troubleshooting", styles["h2"]))
    story.append(info_table([
        ["BeaverView service failed to start",
         "Run: sudo journalctl -u beaverview -n 50\nLook for the error message on the last lines.\nCommon cause: syntax error in main.py after an edit."],
        ["Windows browser can't reach https://beaverview",
         "1. Ping the VM from Windows: ping 192.168.1.50\n"
         "2. If ping fails: check VMware network adapter is Bridged\n"
         "3. If ping works: check the hosts file edit (Part 5, Step 1)\n"
         "4. Check nginx: sudo systemctl status nginx"],
        ["Certificate warning keeps appearing on Windows",
         "Follow Part 5 Steps 2 or 3 to permanently install the certificate.\n"
         "Or: just click Advanced → Proceed each time (connection is still encrypted)."],
        ["Entra login redirects to an error page",
         "Check that the Redirect URI in Azure portal matches exactly:\n"
         "https://beaverview/auth/callback\n"
         "No trailing slash. No different capitalization."],
        ["Connector badge stays gray after adding credentials",
         "Check you restarted BeaverView:  sudo systemctl restart beaverview\n"
         "Check .env for typos:  sudo cat /home/beaverview/app/api/.env\n"
         "Check the logs for errors:  sudo journalctl -u beaverview -n 30"],
        ["A Windows user can't log in (Entra error)",
         "Confirm the user is a member of either the BeaverView Technicians\n"
         "or BeaverView Admins Azure AD group (Part 6, Step 4)."],
        ["The VM got a new IP address after a reboot",
         "Update the hosts file on each Windows PC (Part 5, Step 1) with the new IP.\n"
         "Long-term fix: ask your network admin for a DHCP reservation for the VM's MAC."],
    ], styles, col_widths=[1.9*inch, 4.6*inch],
       header=["Problem", "Solution"]))

    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PART 10 — REFERENCE
# ══════════════════════════════════════════════════════════════════════════════
def part10(story, styles):
    story.append(Paragraph("Part 10 — Reference", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=2, color=OSU_ORANGE, spaceAfter=10))

    story.append(Paragraph("File map", styles["h2"]))
    story.append(info_table([
        ["dashboard/index.html",         "Page structure — labels, headings, layout skeleton"],
        ["dashboard/styles.css",         "All visual design: colors, sizes, fonts"],
        ["dashboard/data.js",            "Mock room and building inventory for all campuses"],
        ["dashboard/app.js",             "All interactivity: map, tabs, tool panels, API calls"],
        ["dashboard/osu-map-buildings.js","278+ OSU building footprints — regenerate, don't edit"],
        ["dashboard/vendor/maplibre/",   "Local MapLibre GL map library — do not modify"],
        ["api/main.py",                  "FastAPI backend: endpoints, connector registry, audit log"],
        ["api/data_mock.py",             "Mock data returned before live connectors are wired"],
        ["api/.env",                     "Live credentials — never commit to Git"],
        ["api/.env.example",             "Template with all available credential slots"],
        ["api/beaverview.db",            "SQLite database: audit_log, device_ips tables"],
        ["api/requirements.txt",         "Python package dependencies"],
        ["api/start.sh",                 "Dev startup script (not used in production — systemd handles it)"],
        ["/etc/nginx/sites-available/beaverview", "nginx HTTPS reverse-proxy config"],
        ["/etc/systemd/system/beaverview.service","systemd service definition"],
        ["/etc/ssl/beaverview/",         "Self-signed SSL certificate and private key"],
    ], styles, col_widths=[2.6*inch, 3.9*inch],
       header=["File / Path", "What it does"]))

    story.append(Paragraph("API endpoints", styles["h2"]))
    story.append(info_table([
        ["GET  /",                              "Serves the dashboard (index.html)"],
        ["GET  /api/health",                   "Health check: {status, ts, version}"],
        ["GET  /api/campus/{id}/connectors",   "Connector health for a campus"],
        ["GET  /api/campus/{id}/fusion/rooms", "Room status from Fusion (mock or live)"],
        ["GET  /api/rooms/{room_id}/status",   "Combined status for one room"],
        ["POST /api/rooms/{room_id}/action",   "Log an action to the audit trail"],
        ["GET  /api/rooms/{room_id}/launch/{tool}", "Get launch URL for SSO-passthrough tools"],
        ["GET  /api/audit",                    "Query audit log (params: campus, action_type, limit)"],
        ["GET  /auth/login",                   "Redirects browser to OSU Entra login page"],
        ["GET  /auth/callback",                "Entra login returns here after authentication"],
        ["GET  /docs",                         "Interactive API docs (Swagger UI)"],
    ], styles, col_widths=[2.8*inch, 3.7*inch],
       header=["Endpoint", "What it does"]))

    story.append(Paragraph("Room status values", styles["h2"]))
    story.append(info_table([
        ['"available"', "Green", "Room is free, all equipment healthy"],
        ['"in-use"',    "Blue",  "Class or event in progress"],
        ['"issue"',     "Amber", "Device problem or open incident"],
        ['"offline"',   "Gray",  "Control processor not reporting"],
    ], styles, col_widths=[1.1*inch, 0.8*inch, 4.6*inch],
       header=["Value", "Color", "Meaning"]))

    story.append(Paragraph("Useful SSH commands — quick reference", styles["h2"]))
    story.append(code_block([
        '# Connect to the VM from Windows PowerShell:',
        'ssh your-username@192.168.1.50',
        '',
        '# BeaverView service:',
        'sudo systemctl status beaverview    # check status',
        'sudo systemctl restart beaverview   # restart after .env changes',
        'sudo journalctl -u beaverview -f    # live logs',
        '',
        '# nginx:',
        'sudo systemctl status nginx',
        'sudo nginx -t                       # test config before restarting',
        'sudo systemctl restart nginx',
        '',
        '# Quick health check (run from VM or Windows):',
        'curl -k https://beaverview/api/health',
        '',
        '# Copy a file FROM the VM TO Windows (run from Windows PowerShell):',
        'scp your-username@192.168.1.50:/path/on/vm  C:\\local\\path',
        '',
        '# Copy a file FROM Windows TO the VM (run from Windows PowerShell):',
        'scp C:\\local\\file.txt  your-username@192.168.1.50:~/destination/',
    ], styles))

    story.append(Spacer(1, 0.25*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    story.append(Paragraph(
        "BeaverView — OSU Presentation Support  ·  Generated 2025",
        ParagraphStyle("footer", fontName="Helvetica", fontSize=8,
                       textColor=TEXT_MUTED, alignment=TA_CENTER)))

# ══════════════════════════════════════════════════════════════════════════════
# BUILD
# ══════════════════════════════════════════════════════════════════════════════
def build():
    output = "/Users/cam/Documents/New project/BeaverView-Playbook.pdf"
    doc = SimpleDocTemplate(
        output, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.6*inch, bottomMargin=0.5*inch,
        title="BeaverView — Implementation Playbook",
        author="OSU Presentation Support",
        subject="VMware VM · Ubuntu · Windows clients · Entra SSO",
    )
    styles = make_styles()
    story = []
    cover_page(story, styles)
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
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF written to: {output}")

if __name__ == "__main__":
    build()
