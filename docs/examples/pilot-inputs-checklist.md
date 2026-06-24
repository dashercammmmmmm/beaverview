# BeaverView Pilot Inputs Checklist

Use this checklist to collect the external inputs that stay out of Git. Do not paste real secrets into this file. Put deployment values only in ignored `api/.env`, and put real hardware IP data only in ignored `api/hardware_ips.csv`.

After any update, restart BeaverView and run:

```bash
python3 scripts/check_pilot_readiness.py
```

For a handoff report with next actions for each remaining external input, run:

```bash
python3 scripts/check_pilot_readiness.py --markdown
```

## Local Secret Baseline

Create or update ignored `api/.env`:

```bash
bash scripts/init_local_env.sh
```

Required generated values:

- `PROXY_SECRET`
- `SESSION_SECRET_KEY`

## Production HTTP Origin

Set this in ignored `api/.env` before VM pilot use:

```bash
BEAVERVIEW_CORS_ORIGINS=https://beaverview
```

Use a comma-separated list only if the deployment has multiple approved HTTPS hostnames. Do not use `*` for pilot or production.

## Hardware IP Records

Target file: ignored `api/hardware_ips.csv`

Validate before import:

```bash
scripts/check_hardware_ip_import.sh
```

Required CSV columns:

- `room_id`
- `device_type`
- `ip_address`
- `notes`

Required pilot device types:

- `xpanel`
- `wattbox`
- `ptz`

CSV rules enforced by validation:

- Each `room_id` must already exist in the migrated SQLite room inventory.
- Each `room_id` / `device_type` pair must appear only once.
- Device IP addresses must be private or link-local by default.
- `--allow-public` may be used only after explicit network review.
- Validation errors identify CSV rows without printing raw IP values.

Import after validation:

```bash
cd api && venv/bin/python import_device_ips.py hardware_ips.csv
```

## First Live-Room Target

Set only after OSU selects the non-critical room and first connector.

List candidate room IDs and connector hints from sanitized SQLite data:

```bash
scripts/check_first_live_room_preflight.py --list-candidates
```

Required `api/.env` values:

- `FIRST_LIVE_ROOM_ID`
- `FIRST_LIVE_CONNECTOR`

Allowed connector values:

- `xpanel`
- `crestron_poll`
- `wattbox`
- `ptz`
- `25live`
- `screenconnect`
- `sharepoint`
- `servicenow`

Validate the selected room and connector prerequisites:

```bash
scripts/check_first_live_room_preflight.py
```

## Azure / Entra App

Detailed setup: `docs/examples/azure-entra-app-registration.md`

Required `api/.env` values:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_REDIRECT_URI`

Redirect URI:

- `https://beaverview/auth/callback`

## Azure / Entra Groups

Required `api/.env` values:

- `AZURE_GROUP_TECHNICIAN`
- `AZURE_GROUP_ADMIN`

## Crestron Poll Credentials

Required `api/.env` values:

- `CRESTRON_POLL_USERNAME`
- `CRESTRON_POLL_PASSWORD`

Optional `api/.env` values:

- `CRESTRON_POLL_INTERVAL_SECONDS`
- `CRESTRON_POLL_SCHEME`
- `CRESTRON_VERIFY_SSL`

## XPanel Proxy Credentials

Required `api/.env` values:

- `CRESTRON_PROXY_USERNAME`
- `CRESTRON_PROXY_PASSWORD`
- `CRESTRON_PROXY_SCHEME`

## ScreenConnect Launch URL

Required `api/.env` value:

- `SC_BASE_URL`

No ScreenConnect service password is stored in BeaverView. Technicians authenticate through their existing OSU browser session when the live launch URL opens.

## WattBox Direct Proxy Credentials

Required `api/.env` values:

- `WATTBOX_DIRECT_USERNAME`
- `WATTBOX_DIRECT_PASSWORD`
- `WATTBOX_PROXY_SCHEME`

Optional OvrC values:

- `WATTBOX_OVRC_BASE_URL`
- `WATTBOX_OVRC_API_KEY`

## PTZ Proxy Credentials

Required `api/.env` values:

- `PTZ_PROXY_USERNAME`
- `PTZ_PROXY_PASSWORD`
- `PTZ_PROXY_SCHEME`

## 25Live Credentials

Required `api/.env` values:

- `LIVE25_BASE_URL`
- `LIVE25_USERNAME`
- `LIVE25_PASSWORD`

## SharePoint Launch URL

Required `api/.env` value:

- `SHAREPOINT_BASE_URL`

No SharePoint password is stored in BeaverView. Technicians authenticate through their existing OSU O365 browser session when the live documentation URL opens.

## Hermes Chat Endpoint

Required `api/.env` value:

- `CHAT_BASE_URL`

Optional `api/.env` values:

- `CHAT_MODEL`
- `CHAT_TIMEOUT`

Hermes uses a local OpenAI-compatible endpoint. Do not route room context to a public model endpoint unless OSU approves that data path.

## ServiceNow Credentials

Required instance value:

- `SN_INSTANCE`

OAuth option:

- `SN_CLIENT_ID`
- `SN_CLIENT_SECRET`

Basic Auth option:

- `SN_USERNAME`
- `SN_PASSWORD`

## Final Verification

Before the first live connector test, use:

```bash
docs/examples/first-live-room-validation.md
```

Run all local gates:

```bash
scripts/smoke_check.sh
scripts/check_data_migration.sh
scripts/check_hardware_ip_import.sh
scripts/check_deployment_assets.sh
scripts/check_api_contracts.py
scripts/check_first_live_room_preflight_cases.py
scripts/check_readiness_actions.py
python3 scripts/check_env_template.py
python3 scripts/check_live_validation_doc.py
python3 scripts/check_pilot_readiness.py
```

Expected result before external inputs are available: local checks pass, and the preflight lists pending external prerequisites. Expected result after external inputs are available: local checks pass and pending prerequisite count drops as each input is filled.
