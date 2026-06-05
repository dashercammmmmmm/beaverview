# BeaverView — Deployment Playbook
**Audience:** IT administrators setting up BeaverView for the first time.
**Scenario:** VMware VM running Ubuntu · Windows client computers on the same network · Self-signed SSL · OSU Entra SSO login.
**Purpose:** Step-by-step guide from a blank VM to a working dashboard accessible from Windows browsers.

> **Complete these parts in order.** Each part depends on the previous one.

---

## Deployment overview

| Component | Details |
|---|---|
| Server | Ubuntu 22.04 or 24.04 VM in VMware |
| Web server | nginx — handles HTTPS and forwards to the Python backend |
| Backend | Python (FastAPI) — runs as a systemd service, auto-restarts on crashes |
| Clients | Any Windows PC on the same network — open a browser, type the hostname |
| URL | `https://beaverview` (or whatever hostname you assign the VM) |
| SSL | Self-signed certificate — browsers show a one-time warning, then remember it |
| Login | OSU Entra (Azure AD) — technicians sign in with their OSU credentials |
| Database | SQLite — built-in, no separate database server needed |

---

## Part 1 — Prerequisites

Collect everything below before you start.

| Requirement | Details |
|---|---|
| VMware Workstation Pro or VMware ESXi | To create and run the Ubuntu VM. Workstation runs on your existing Windows or Mac. ESXi runs on a dedicated server. |
| Ubuntu 22.04 or 24.04 Server ISO | Free download from ubuntu.com/download/server. Download the **Server** edition (no desktop needed). |
| The BeaverView project files | A folder containing `api/` and `dashboard/` subfolders — either a ZIP or a Git repo URL. |
| SSH client on each Windows computer | Built into Windows 10/11 — use PowerShell or Windows Terminal. Alternative: PuTTY (putty.org). |
| VS Code with Remote SSH extension | Lets you edit files on the VM from Windows as if they were local. Install the **Remote - SSH** extension from the VS Code Extensions panel. |
| Access to OSU Azure portal | For registering the Entra SSO app. URL: portal.azure.com. You need permission to create App Registrations. |
| Admin rights on each Windows client PC | Needed once to edit the Windows hosts file. After that, regular users can open the dashboard with no admin rights. |

**You do NOT need:** Node.js, npm, Docker, a separate database server, or a public domain name.

---

## Part 2 — Create the Ubuntu VM in VMware

> If your IT team has already given you a running Ubuntu VM with SSH access, skip to Part 3.

### Step 1 — Create a new VM

1. Open VMware Workstation → **File → New Virtual Machine → Typical**
2. Choose **Installer disc image file (ISO)** → browse to the Ubuntu ISO
3. Click Next

### Step 2 — Name the VM

- **Name:** `BeaverView` (just a VMware display name)
- **Location:** anywhere with enough disk space
- Click Next

### Step 3 — Set disk size

- Minimum: **20 GB** — recommended: **40 GB**
- Choose **Store virtual disk as a single file**
- Click Next

### Step 4 — Customize hardware (IMPORTANT — Bridged networking)

Click **Customize Hardware** before finishing:

| Setting | Value | Why |
|---|---|---|
| RAM | 2 GB minimum, 4 GB recommended | — |
| Processors | 2 cores | — |
| **Network Adapter** | **Bridged** | Gives the VM its own IP on the real network. NAT mode hides the VM — Windows clients cannot reach it. |

Click Close → Finish.

> **VMware network adapter not working?** Go to **Edit → Virtual Network Editor** and set VMnet0 to the physical adapter your Windows host uses to connect to the office network. Restart the VM.

### Step 5 — Install Ubuntu

The VM boots from the ISO automatically.

1. Choose **Install Ubuntu Server**
2. Language: English · Keyboard: your layout
3. Network: leave as-is (DHCP — gets an IP automatically)
4. Storage: **Use entire disk** → Done → Continue
5. Profile setup:
   - Your name: (anything)
   - **Server name: `beaverview`** ← this becomes the hostname
   - Username + password: write these down — needed every time you SSH in
6. SSH: **✔ Install OpenSSH server** ← required
7. Featured snaps: skip all → Done
8. Wait 5–10 minutes, then reboot when prompted

### Step 6 — Find the VM's IP address

After Ubuntu boots, log in at the VM console and run:

```bash
ip addr show
```

Look for a line like: `inet 192.168.1.50/24`

**Write down that IP address.** You'll use it in Parts 4 and 5.

> **To make the IP permanent:** ask your network admin to add a DHCP reservation for the VM's MAC address. Otherwise the IP may change after a reboot, requiring you to update the hosts file on every Windows PC.

### Step 7 — Test SSH from Windows

Open PowerShell on your Windows computer:

```powershell
ssh your-username@192.168.1.50
```

Type `yes` when asked about the fingerprint, then enter your password. If you see a `$` prompt, SSH is working.

**All commands in the rest of this guide are typed in this SSH session.**

---

## Part 3 — Install BeaverView on the VM

All commands run inside your SSH session on the Ubuntu VM.

### Step 1 — Update Ubuntu and install required packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-venv python3-pip nginx -y
```

This takes 2–5 minutes.

### Step 2 — Create a service account

```bash
sudo useradd -m -s /bin/bash beaverview
```

### Step 3 — Copy the project files

**Option A — Git repository:**
```bash
sudo -u beaverview git clone https://your-repo-url /home/beaverview/app
```

**Option B — ZIP file (copy from Windows first):**

In a second PowerShell window on Windows (not the SSH one):
```powershell
scp "C:\path\to\project.zip" your-username@192.168.1.50:~/
```

Then back in the SSH window:
```bash
sudo mv ~/project.zip /home/beaverview/
sudo -u beaverview unzip /home/beaverview/project.zip -d /home/beaverview/app
```

### Step 4 — Verify folder structure

```bash
ls /home/beaverview/app
```

You should see: `api/   dashboard/   PLAYBOOK-*.md`

### Step 5 — Set up the Python virtual environment

```bash
cd /home/beaverview/app/api
sudo -u beaverview python3 -m venv venv
sudo -u beaverview venv/bin/pip install -r requirements.txt
```

This takes 1–3 minutes on first run.

### Step 6 — Configure the .env credentials file

```bash
sudo -u beaverview cp /home/beaverview/app/api/.env.example /home/beaverview/app/api/.env
sudo nano /home/beaverview/app/api/.env
```

At minimum, set `PROXY_SECRET`. Generate a random value:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the value of `PROXY_SECRET` in `.env`. Save with `Ctrl+O`, Enter, `Ctrl+X`.

```bash
sudo chmod 600 /home/beaverview/app/api/.env
sudo chown beaverview:beaverview /home/beaverview/app/api/.env
```

### Step 7 — Create the systemd service

```bash
sudo nano /etc/systemd/system/beaverview.service
```

Paste exactly:

```ini
[Unit]
Description=BeaverView API
After=network.target

[Service]
Type=simple
User=beaverview
WorkingDirectory=/home/beaverview/app/api
Environment="PATH=/home/beaverview/app/api/venv/bin"
ExecStart=/home/beaverview/app/api/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save with `Ctrl+O`, Enter, `Ctrl+X`.

### Step 8 — Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable beaverview
sudo systemctl start beaverview
sudo systemctl status beaverview
```

The last command should show: `Active: active (running)`

If it shows `failed`, check the logs:
```bash
sudo journalctl -u beaverview -n 30
```

---

## Part 4 — Set Up HTTPS with nginx

nginx sits in front of BeaverView and handles HTTPS encryption.

> **About self-signed certificates:** A self-signed certificate encrypts the connection just as well as a paid certificate. The only difference is browsers can't automatically verify the issuer, so they show a warning the first time. Users click **Advanced → Proceed** once — after that, the browser remembers it. Part 5 covers how to permanently trust the certificate so the warning never appears.

### Step 1 — Generate the SSL certificate

Replace `192.168.1.50` with your VM's actual IP address:

```bash
sudo mkdir -p /etc/ssl/beaverview
sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /etc/ssl/beaverview/beaverview.key \
    -out /etc/ssl/beaverview/beaverview.crt \
    -subj "/CN=beaverview" \
    -addext "subjectAltName=DNS:beaverview,IP:192.168.1.50"
```

`-days 3650` = 10 years before renewal is needed.

### Step 2 — Configure nginx

```bash
sudo nano /etc/nginx/sites-available/beaverview
```

Paste the following (replace `192.168.1.50` with your VM's actual IP):

```nginx
server {
    listen 80;
    server_name beaverview 192.168.1.50;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name beaverview 192.168.1.50;

    ssl_certificate     /etc/ssl/beaverview/beaverview.crt;
    ssl_certificate_key /etc/ssl/beaverview/beaverview.key;

    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
```

### Step 3 — Enable the site and restart nginx

```bash
sudo ln -s /etc/nginx/sites-available/beaverview /etc/nginx/sites-enabled/
sudo nginx -t          # should print: syntax is ok  and  test is successful
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 4 — Allow HTTPS through the firewall

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw --force enable
sudo ufw status
```

You should see `Nginx Full` and `OpenSSH` listed as ALLOW.

### Step 5 — Test HTTPS from the VM

```bash
curl -k https://localhost/api/health
```

Expected response: `{"status": "ok", "ts": "...", "version": "0.4.0"}`

---

## Part 5 — Configure Windows Client Computers

Do these steps on **each Windows computer** that needs access. Step 1 is required. Steps 2 and 3 permanently remove the browser warning.

### Step 1 — Edit the Windows hosts file (required)

This tells Windows what IP to use for the hostname `beaverview`.

1. Press the Windows key, type `Notepad`
2. **Right-click Notepad → Run as administrator** → Yes
3. File → Open
4. In the file path box type exactly:
   ```
   C:\Windows\System32\drivers\etc\hosts
   ```
   Change the file type dropdown to **All Files**, click Open
5. Scroll to the bottom and add a new line:
   ```
   192.168.1.50   beaverview
   ```
   *(replace with your VM's actual IP)*
6. File → Save. Close Notepad.

Test: open a browser and go to `https://beaverview`. You'll see a certificate warning — click through it once.

### Step 2 — (Optional) Trust the certificate permanently in Chrome and Edge

This removes the "Your connection is not private" warning forever on this computer.

**Copy the certificate from the VM to Windows** (run in PowerShell on Windows):
```powershell
scp your-username@192.168.1.50:/etc/ssl/beaverview/beaverview.crt C:\Users\YourName\Desktop\beaverview.crt
```

**Install the certificate:**
1. Double-click `beaverview.crt` on your Desktop
2. Click **Install Certificate**
3. Choose **Local Machine** → Next → allow the admin prompt
4. Choose **Place all certificates in the following store**
5. Click Browse → select **Trusted Root Certification Authorities** → OK
6. Click Next → Finish → OK
7. Restart Chrome or Edge

The warning will no longer appear.

### Step 3 — (Optional) Trust the certificate permanently in Firefox

Firefox manages its own certificate store.

1. Open Firefox and go to `https://beaverview`
2. Click **Advanced…** → **Accept the Risk and Continue**
3. Click the padlock icon in the address bar → **Connection not secure** → **More information**
4. Click **View Certificate** → download the PEM file
5. Firefox menu → Settings → Privacy & Security → scroll to **Certificates** → **View Certificates**
6. **Authorities** tab → Import → select the downloaded `.pem` file
7. Check **Trust this CA to identify websites** → OK
8. Restart Firefox

### Step 4 — Test from Windows

Open a browser and go to `https://beaverview`.

You should see the BeaverView dashboard with the OSU orange header and campus map.

**If the page doesn't load:**

| Symptom | Fix |
|---|---|
| Browser says "site can't be reached" | Open PowerShell and run `ping 192.168.1.50`. If ping fails, check VMware network adapter is set to **Bridged** (Part 2, Step 4). |
| Ping works but browser fails | Check the hosts file edit (Step 1 above) — confirm the line was saved. |
| nginx error page | SSH into VM and run `sudo systemctl status nginx` |

---

## Part 6 — Set Up OSU Entra SSO Login

Entra SSO lets technicians log in with their OSU credentials. It adds real user identity to audit logs and enables role-based access.

> **You need access to portal.azure.com with permission to create App Registrations.**

### Step 1 — Register BeaverView in the Azure portal

1. Go to [portal.azure.com](https://portal.azure.com) → log in with OSU admin credentials
2. Search for **Azure Active Directory** → **App registrations** → **New registration**
3. Fill in:
   - **Name:** `BeaverView`
   - **Account types:** Accounts in this organizational directory only (OSU only)
   - **Redirect URI:** `Web` → `https://beaverview/auth/callback`
4. Click **Register**

Leave this tab open.

### Step 2 — Copy the IDs you need

On the app Overview page:
- Copy **Application (client) ID** → paste into a Notepad file
- Copy **Directory (tenant) ID** → paste into the same Notepad file

### Step 3 — Create a client secret

1. Left menu → **Certificates & secrets** → **+ New client secret**
2. Description: `BeaverView Server` | Expires: `24 months`
3. Click **Add**
4. **Immediately copy the Value column** (not the Secret ID)
   - It disappears after you leave this page and cannot be recovered
   - Paste it into your Notepad file

### Step 4 — Create security groups

1. Back in Azure Active Directory → **Groups** → **New group**
2. Create **BeaverView Technicians**:
   - Group type: Security
   - Click Create
3. Create **BeaverView Admins** (same steps)
4. Open each group → **Properties** → copy the **Object ID** into your Notepad file
5. Open **BeaverView Technicians** → **Members** → **Add members** → add the relevant OSU staff
6. Repeat for **BeaverView Admins**

### Step 5 — Add credentials to .env on the VM

```bash
sudo nano /home/beaverview/app/api/.env
```

Fill in these lines (paste from your Notepad file):

```env
AZURE_TENANT_ID=your-directory-tenant-id
AZURE_CLIENT_ID=your-application-client-id
AZURE_CLIENT_SECRET=your-client-secret-value
AZURE_GROUP_TECHNICIAN=object-id-of-technicians-group
AZURE_GROUP_ADMIN=object-id-of-admins-group
```

Save, then restart:

```bash
sudo systemctl restart beaverview
```

### Step 6 — Install the MSAL library

```bash
sudo -u beaverview /home/beaverview/app/api/venv/bin/pip install msal
echo 'msal>=1.28.0' | sudo tee -a /home/beaverview/app/api/requirements.txt
```

### Step 7 — Test the login flow

From a Windows computer, open `https://beaverview`. You should be redirected to the OSU Microsoft login page. After logging in, you return to the BeaverView dashboard.

**If you see a redirect error:** confirm the Redirect URI in Azure portal matches exactly `https://beaverview/auth/callback` — no trailing slash, no different capitalization.

---

## Security checklist before going live

Run through this before announcing the URL to users:

- [ ] **HTTPS only** — port 80 redirects to 443
- [ ] **`.env` permissions** — run `ls -la /home/beaverview/app/api/.env` — should show `-rw-------`
- [ ] **`.env` not in Git** — run `git -C /home/beaverview/app status` — confirm `.env` is not listed
- [ ] **No raw IPs in browser** — open DevTools → Network tab → confirm no `10.x.x.x` or `192.168.x.x` addresses in API responses
- [ ] **Audit log working** — click a tool action, then `curl -k https://beaverview/api/audit` and confirm the entry appears
- [ ] **CORS restricted** — in `main.py`, change `allow_origins=["*"]` to `allow_origins=["https://beaverview"]`
- [ ] **Live reload removed** — delete the `<!-- Live reload -->` block from `dashboard/index.html`
- [ ] **Dev helper removed** — delete the `window._dev = { selectBuilding }` line from `dashboard/app.js`

---

## Day-to-day operations

### Check if BeaverView is running

```bash
sudo systemctl status beaverview
curl -k https://localhost/api/health
```

### View live logs

```bash
sudo journalctl -u beaverview -f    # Ctrl+C to stop
```

### Update after code changes

```bash
cd /home/beaverview/app
sudo -u beaverview git pull
sudo systemctl restart beaverview
# Frontend static files update on next browser load
# If you changed app.js or styles.css, bump the ?v= number in index.html first
```

### Back up the database

```bash
sudo -u beaverview mkdir -p /home/beaverview/backups
sudo -u beaverview crontab -e
```

Add this line (runs every night at 2 AM):
```
0 2 * * * cp /home/beaverview/app/api/beaverview.db /home/beaverview/backups/beaverview-$(date +\%Y\%m\%d).db
```

### Roll back after a bad update

```bash
cd /home/beaverview/app
git log --oneline                         # find last good commit hash
git checkout <hash> -- dashboard/app.js   # restore one file
# or full rollback:
git reset --hard <hash>
sudo systemctl restart beaverview
```

### Reboot the VM

```bash
sudo reboot
# Wait ~30 seconds, then test:
curl -k https://192.168.1.50/api/health
```

BeaverView and nginx start automatically on boot — no manual steps needed.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| BeaverView service failed to start | `sudo journalctl -u beaverview -n 50` — look at the last few lines for the error. Common cause: syntax error in main.py. |
| Windows browser can't reach `https://beaverview` | 1. `ping 192.168.1.50` from PowerShell. 2. If ping fails: VMware adapter not Bridged. 3. If ping works: hosts file issue. |
| Certificate warning keeps appearing | Follow Part 5 Steps 2 or 3 to permanently install the cert, or just click Advanced → Proceed each time. |
| Entra login redirects to an error page | Check Redirect URI in Azure portal matches exactly `https://beaverview/auth/callback`. |
| Connector badge stays gray after adding credentials | `sudo systemctl restart beaverview` — the backend only reads `.env` at startup. |
| A user can't log in (Entra error 403) | Confirm they are a member of either the BeaverView Technicians or BeaverView Admins Azure AD group. |
| VM got a new IP after reboot | Update the hosts file on each Windows PC. Long-term fix: DHCP reservation for the VM's MAC address. |

---

## Quick SSH reference

```bash
# Connect from Windows PowerShell:
ssh your-username@192.168.1.50

# Service management:
sudo systemctl status beaverview
sudo systemctl restart beaverview
sudo journalctl -u beaverview -f

# nginx:
sudo systemctl status nginx
sudo nginx -t                        # test config syntax
sudo systemctl restart nginx

# Copy file FROM VM to Windows (run in Windows PowerShell):
scp your-username@192.168.1.50:/path/on/vm  C:\local\path

# Copy file FROM Windows to VM (run in Windows PowerShell):
scp C:\local\file.txt  your-username@192.168.1.50:~/destination/
```
