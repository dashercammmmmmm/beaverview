# BeaverView — Production Playbook
**Audience:** IT administrators deploying BeaverView to a real server.
**Purpose:** Step-by-step guide to go from localhost to a production URL.

> **Complete these in order.** Each section depends on the previous one.

---

## Prerequisites

| Item | Notes |
|---|---|
| A Linux server (Ubuntu 22.04+ recommended) | On OSU network or VPN-accessible |
| Python 3.11+ installed | `python3 --version` |
| A domain name or hostname | e.g. `beaverview.oregonstate.edu` |
| An SSL certificate | OSU IT can issue one, or use Let's Encrypt |
| Access to OSU Azure portal | For Entra SSO registration |
| The project files on the server | Clone from Git or copy via scp |

---

## Step 1 — Server setup

```bash
# Install system dependencies
sudo apt update
sudo apt install python3 python3-venv python3-pip nginx certbot -y

# Create a service account
sudo useradd -m -s /bin/bash beaverview
sudo su - beaverview

# Clone or copy project files
git clone <repo-url> ~/app
cd ~/app/api

# Create the virtual environment
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

---

## Step 2 — Configure environment

```bash
cp .env.example .env
nano .env
```

At minimum, fill in:
- `PROXY_SECRET` — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`
- Any connector credentials you want active at launch (see `PLAYBOOK-CONNECTORS.md`)
- Azure/Entra credentials when SSO is ready (Step 6 below)

Set file permissions so only the service account can read it:
```bash
chmod 600 .env
```

---

## Step 3 — Create a systemd service

This runs the backend automatically and restarts it on crashes.

```bash
sudo nano /etc/systemd/system/beaverview.service
```

Paste:
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

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable beaverview
sudo systemctl start beaverview
sudo systemctl status beaverview   # should show "active (running)"
```

---

## Step 4 — Configure nginx as a reverse proxy

```bash
sudo nano /etc/nginx/sites-available/beaverview
```

Paste:
```nginx
server {
    listen 80;
    server_name beaverview.oregonstate.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name beaverview.oregonstate.edu;

    ssl_certificate     /etc/ssl/certs/beaverview.crt;   # adjust path
    ssl_certificate_key /etc/ssl/private/beaverview.key;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

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

Enable and test:
```bash
sudo ln -s /etc/nginx/sites-available/beaverview /etc/nginx/sites-enabled/
sudo nginx -t        # should say "syntax is ok"
sudo systemctl restart nginx
```

---

## Step 5 — Remove development-only code

Before going to production, remove or disable the live-reload script in `index.html`.
It runs on localhost only (the `if` check ensures this), but it's cleaner to remove it:

Open `dashboard/index.html` and delete the block at the bottom labeled `<!-- Live reload -->`.

Also remove the `window._dev` line at the bottom of `app.js`:
```js
// Delete this line:
window._dev = { selectBuilding };
```

Bump the `?v=N` cache busters on all script tags in `index.html` so browsers fetch fresh files:
```html
<script src="app.js?v=3"></script>
<link rel="stylesheet" href="styles.css?v=3">
```

---

## Step 6 — Set up OSU Entra SSO (login)

This adds real user identity to audit logs and enables role-based access.

### Register BeaverView in Azure Portal

1. Go to [portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**
2. Name: `BeaverView`
3. Redirect URI: `https://beaverview.oregonstate.edu/auth/callback`
4. Click Register

5. Note the **Application (client) ID** → `AZURE_CLIENT_ID` in `.env`
6. Note the **Directory (tenant) ID** → `AZURE_TENANT_ID` in `.env`
7. Go to **Certificates & secrets** → New client secret → copy the value → `AZURE_CLIENT_SECRET` in `.env`

### Create security groups

In Azure AD → Groups, create (or find existing):
- **BeaverView Technicians** — note the Object ID → `AZURE_GROUP_TECHNICIAN` in `.env`
- **BeaverView Admins** — note the Object ID → `AZURE_GROUP_ADMIN` in `.env`

Assign OSU staff to these groups.

### Implement SSO in main.py

Install the Microsoft authentication library:
```bash
venv/bin/pip install msal
echo "msal>=1.28.0" >> requirements.txt
```

Add to `main.py`:
```python
import msal

MSAL_APP = msal.ConfidentialClientApplication(
    client_id=os.getenv("AZURE_CLIENT_ID"),
    client_credential=os.getenv("AZURE_CLIENT_SECRET"),
    authority=f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}",
)

@app.get("/auth/login")
def auth_login(request: Request):
    from fastapi.responses import RedirectResponse
    auth_url = MSAL_APP.get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=str(request.url_for("auth_callback")),
    )
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
def auth_callback(code: str, request: Request):
    from fastapi.responses import RedirectResponse
    result = MSAL_APP.acquire_token_by_authorization_code(
        code=code,
        scopes=["User.Read"],
        redirect_uri=str(request.url_for("auth_callback")),
    )
    if "error" in result:
        raise HTTPException(401, result.get("error_description"))
    # Store token in session cookie and redirect to dashboard
    # Full implementation depends on your session management approach
    return RedirectResponse("/")
```

> **Note:** Full SSO implementation requires a session management library (e.g., `fastapi-sessions`
> or `starlette-sessions`). The stub above shows the MSAL flow — complete it based on
> OSU IT's preferred session approach.

---

## Step 7 — Set up database backups

The SQLite database at `api/beaverview.db` contains the full audit trail.

Simple daily backup with cron:
```bash
crontab -e
```
Add:
```
0 2 * * * cp /home/beaverview/app/api/beaverview.db /home/beaverview/backups/beaverview-$(date +\%Y\%m\%d).db
```

For production, consider migrating to PostgreSQL:
1. Install `asyncpg` and update the SQLAlchemy connection string in `main.py`
2. PostgreSQL supports concurrent writes and point-in-time recovery

---

## Step 8 — Security checklist

Before announcing the URL to users, verify each item:

- [ ] **HTTPS only** — port 80 redirects to 443, HSTS header set
- [ ] **`.env` file permissions** — `chmod 600 .env`, readable only by service account
- [ ] **`.env` not in Git** — run `git status` and confirm `.env` is not listed
- [ ] **No raw IPs in browser** — open DevTools → Network tab, click every tool panel, confirm no `10.x.x.x` addresses appear in responses
- [ ] **Audit log working** — click a tool action, then `curl https://beaverview.oregonstate.edu/api/audit` and confirm the entry appears
- [ ] **CORS restricted** — in `main.py`, change `allow_origins=["*"]` to `allow_origins=["https://beaverview.oregonstate.edu"]`
- [ ] **Rate limiting** — add `slowapi` or nginx `limit_req` to prevent API abuse
- [ ] **Live reload removed** — confirm the `<!-- Live reload -->` block is gone from `index.html`
- [ ] **Dev helper removed** — confirm `window._dev` is gone from `app.js`
- [ ] **X-User header hardened** — once SSO is live, reject requests where `X-User` doesn't match a valid Entra-issued identity

---

## Updating the production deployment

When you push new code:

```bash
# On the server:
cd ~/app
git pull

# Restart the backend:
sudo systemctl restart beaverview

# The frontend (static files) updates immediately on next browser load.
# If you changed app.js or styles.css, bump the ?v= number first.
```

---

## Rollback

```bash
# Roll back to a previous git commit:
git log --oneline   # find the commit hash
git checkout <hash> -- dashboard/app.js   # restore just one file
sudo systemctl restart beaverview

# Or full rollback:
git reset --hard <hash>
sudo systemctl restart beaverview
```

---

## Monitoring

Check service health:
```bash
sudo systemctl status beaverview
sudo journalctl -u beaverview -f    # live logs
curl https://beaverview.oregonstate.edu/api/health
```

The `/api/health` endpoint returns:
```json
{ "status": "ok", "ts": "2025-06-02T18:00:00Z", "version": "0.4.0" }
```

Set up an uptime monitor (UptimeRobot, Pingdom, or OSU's internal monitoring) pointing
at `https://beaverview.oregonstate.edu/api/health` with a 60-second interval.
