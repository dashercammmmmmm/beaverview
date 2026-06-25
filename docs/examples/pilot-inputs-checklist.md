# BeaverView Pilot Inputs Checklist

Use this checklist to collect the external inputs that stay out of Git. Do not paste real secrets into this file. Put deployment values only in ignored `api/.env`, and put real hardware IP data only in ignored `api/hardware_ips.csv`.

After any update, restart BeaverView and run:

```bash
python3 scripts/check_pilot_readiness.py
```

For a handoff report with next actions for each remaining external input, run:

```bash
python3 scripts/check_pilot_readiness.py --markdown
python3 scripts/check_pilot_readiness.py --json > /tmp/beaverview-readiness.json
scripts/render_pilot_intake_packet.py --readiness-json /tmp/beaverview-readiness.json
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

Required origin shape:

- Each origin must start with `https://`
- Each origin must include a host name
- Do not include wildcard, path-only, or `http://` origins for pilot use

## Hardware IP Records

Target file: ignored `api/hardware_ips.csv`

Validate before import:

```bash
scripts/check_hardware_ip_csv.py
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

- Shared parsing rules live in `api/hardware_ip_csv.py`.
- Blank required fields fail validation.
- Each `room_id` must already exist in the migrated SQLite room inventory.
- Unknown room IDs fail import and first-live Hardware CSV preview.
- Each `room_id` / `device_type` pair must appear only once.
- Device IP addresses must be valid IPv4 values.
- Device IP addresses must be private or link-local by default.
- Invalid, non-proxyable, or unreviewed public IP rows fail validation.
- `--allow-public` may be used only after explicit network review.
- Validation errors identify CSV rows without printing raw IP values.

Import after validation:

```bash
(cd api && venv/bin/python import_device_ips.py hardware_ips.csv)
```

## First Live-Room Target

Set only after OSU selects the non-critical room and first connector.

List candidate room IDs and connector hints from sanitized SQLite data:

```bash
scripts/check_first_live_room_preflight.py --list-candidates
scripts/check_hardware_ip_csv.py
scripts/check_first_live_room_preflight.py --list-candidates --connector xpanel --hardware-csv api/hardware_ips.csv
```

Run the shared Hardware CSV validator before using `--hardware-csv` so preview failures are treated as source-export corrections, not room-selection results.

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
scripts/check_hardware_ip_csv.py
scripts/check_hardware_ip_import.sh
(cd api && venv/bin/python import_device_ips.py hardware_ips.csv)
scripts/check_first_live_room_preflight.py
python3 scripts/check_pilot_readiness.py --json > /tmp/beaverview-readiness.json
scripts/check_first_live_room_preflight.py --list-candidates --connector xpanel --json > /tmp/beaverview-candidates.json
scripts/render_first_live_room_report.py --readiness-json /tmp/beaverview-readiness.json --candidates-json /tmp/beaverview-candidates.json
```

For device-backed connectors, import the validated Hardware IP rows before running the selected-room preflight and rendering the report. Replace `xpanel` in the candidate JSON command with the selected `FIRST_LIVE_CONNECTOR`, or omit `--connector` only when intentionally comparing several possible first connectors.

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

Scheme values:

- `CRESTRON_POLL_SCHEME` may be `http` or `https`

## XPanel Proxy Credentials

Required `api/.env` values:

- `CRESTRON_PROXY_USERNAME`
- `CRESTRON_PROXY_PASSWORD`
- `CRESTRON_PROXY_SCHEME`

Scheme values:

- `CRESTRON_PROXY_SCHEME` may be `http` or `https`

## ScreenConnect Launch URL

Required `api/.env` value:

- `SC_BASE_URL`

Required shape:

- Must start with `https://`

No ScreenConnect service password is stored in BeaverView. Technicians authenticate through their existing OSU browser session when the live launch URL opens.

## WattBox Direct Proxy Credentials

Required `api/.env` values:

- `WATTBOX_DIRECT_USERNAME`
- `WATTBOX_DIRECT_PASSWORD`
- `WATTBOX_PROXY_SCHEME`

Scheme values:

- `WATTBOX_PROXY_SCHEME` may be `http` or `https`

Optional OvrC values:

- `WATTBOX_OVRC_BASE_URL`
- `WATTBOX_OVRC_API_KEY`

## PTZ Proxy Credentials

Required `api/.env` values:

- `PTZ_PROXY_USERNAME`
- `PTZ_PROXY_PASSWORD`
- `PTZ_PROXY_SCHEME`

Scheme values:

- `PTZ_PROXY_SCHEME` may be `http` or `https`

## 25Live Credentials

Required `api/.env` values:

- `LIVE25_BASE_URL`
- `LIVE25_USERNAME`
- `LIVE25_PASSWORD`

Required URL shape:

- `LIVE25_BASE_URL` must start with `https://`

## SharePoint Launch URL

Required `api/.env` value:

- `SHAREPOINT_BASE_URL`

Required shape:

- Must start with `https://`

No SharePoint password is stored in BeaverView. Technicians authenticate through their existing OSU O365 browser session when the live documentation URL opens.

## Hermes Chat Endpoint

Required `api/.env` value:

- `CHAT_BASE_URL`

Required URL shape:

- Must start with `http://` or `https://`
- Must include a host name

Optional `api/.env` values:

- `CHAT_MODEL`
- `CHAT_TIMEOUT`

Hermes uses a local OpenAI-compatible endpoint. Do not route room context to a public model endpoint unless OSU approves that data path.

## ServiceNow Credentials

Required instance value:

- `SN_INSTANCE`

Required instance shape:

- Host name only, such as `oregonstate.service-now.com`
- Do not include `https://` or a path

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
scripts/check_hardware_ip_csv.py
scripts/check_hardware_ip_import.sh
scripts/check_deployment_assets.sh
python3 scripts/check_deployment_playbook.py
scripts/check_api_contracts.py
python3 scripts/check_inventory_parity.py
scripts/check_dashboard_browser.sh
scripts/check_admin_browser.sh
python3 scripts/check_env_template.py
python3 scripts/check_init_local_env.py
python3 scripts/check_pilot_inputs_doc.py
python3 scripts/check_pilot_intake_packet.py
python3 scripts/check_playbook_html.py
python3 scripts/check_project_log.py
python3 scripts/check_readiness_actions.py
python3 scripts/check_readiness_env_prereqs.py
python3 scripts/check_sanitize_output.py
python3 scripts/check_readiness_output.py
python3 scripts/check_readiness_diagnostics.py
python3 scripts/check_production_safety.py
python3 scripts/check_live_validation_doc.py
python3 scripts/check_first_live_connectors.py
scripts/check_first_live_room_preflight_cases.py
scripts/check_first_live_room_report.py
python3 scripts/check_pilot_readiness.py
```

Expected result before external inputs are available: local checks pass, and the preflight lists pending external prerequisites. Expected result after external inputs are available: local checks pass and pending prerequisite count drops as each input is filled.
