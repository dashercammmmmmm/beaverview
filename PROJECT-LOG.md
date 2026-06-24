# BeaverView Project Log

This is the durable local work log for BeaverView v2. Add an entry every time the project changes materially so the Mac Mini checkout remains the source of truth between assistant sessions.

## 2026-06-24 - Source-of-truth stabilization

- Confirmed canonical local repo: `/Users/benjaminfranklinautomation/projects/beaverview`.
- Confirmed GitHub remote: `https://github.com/dashercammmmmmm/beaverview`.
- At the start of stabilization, confirmed local `main` was five commits ahead of `origin/main`; latest local commit was `9a4cb4f fix: allow maplibre and osm tiles via relaxed CSP header`.
- Confirmed working tree was clean before edits.
- Confirmed `/Users/benjaminfranklinautomation/Documents/Beaverview` is not the active v2 repo; it has no commits and no configured remote.
- Found local venv was missing `httpx`, which disables Crestron polling and connector health paths even though `httpx` is listed in `api/requirements.txt`.
- Updated `api/start.sh` so new and existing venvs install from `api/requirements.txt`.
- Added `scripts/smoke_check.sh` for repeatable local checks: Python imports, app import/startup, `/api/health`, `/api/me`, ServiceNow mock fallback, and chat mock fallback.
- Updated handoff docs to point at the Mac Mini path and current v2/GitHub state.
- Repaired the current local `api/venv` with `./venv/bin/pip install -r requirements.txt`.
- Verified `scripts/smoke_check.sh` passes at `http://127.0.0.1:8017`.

### Next

- Run `scripts/smoke_check.sh` before pushing or starting feature work.
- Pushed to GitHub on 2026-06-24 after `gh auth setup-git` enabled the existing GitHub CLI credentials.

## 2026-06-24 - Data migration repair

- Found `api/beaverview.db` had the expected tables but zero seeded campuses, buildings, rooms, and devices.
- Verified `api/migrate_data.py` failed because `dashboard/data.js` is a JavaScript object literal with unquoted keys, not strict JSON.
- Updated `api/migrate_data.py` to parse the current `data.js` shape, initialize the schema before seeding, preserve legacy `crestron` fields as `rooms.processor`, and normalize connector modes to `mock`/`live`.
- Added `scripts/check_data_migration.sh` to rerun migration and verify non-empty inventory counts plus valid connector modes.
- Ran the migration successfully. Local ignored SQLite counts: 3 campuses, 18 buildings, 20 rooms, 22 devices.

### Next

- Import real device IP data with `api/import_device_ips.py` after the secure `hardware_ips.csv` is available locally.
- Replace the `/api/rooms/{room_id}/proxy/{tool}/{path}` 501 placeholder with Hardware IP lookup and safe proxying for the first device class.

## 2026-06-24 - Device proxy foundation

- Initial `git push origin main` attempt failed before GitHub CLI credentials were wired into Git; this was resolved later with `gh auth setup-git`.
- Replaced the `/api/rooms/{room_id}/proxy/{tool}/{path}` 501 stub with a conservative GET-only proxy foundation for `xpanel`, `wattbox`, and `ptz`.
- Proxy now looks up device IPs from `device_ips`, validates proxyable IP addresses, injects backend-only credentials, disables redirects, sets a short timeout, and returns `Cache-Control: no-store`.
- Added private/link-local IP enforcement by default; `DEVICE_PROXY_ALLOW_PUBLIC=true` is available only for reviewed deployments.
- Fixed ServiceNow env compatibility so `SN_INSTANCE`, `SN_CLIENT_ID`, and `SN_CLIENT_SECRET` from `.env.example` are honored by `main.py`.
- Fixed ServiceNow launch URL construction for documented full instance domains such as `oregonstate.service-now.com`.
- Hardened `api/import_device_ips.py` to initialize schema and reject invalid/non-proxyable IP rows.

### Next

- GitHub sync is complete; continue to run smoke checks before future pushes.
- Load the real secure `hardware_ips.csv` and device credentials, then test one actual XPanel or WattBox path on the AV network.

## 2026-06-24 - GitHub sync completed

- Verified GitHub CLI was authenticated as `dashercammmmmmm` with HTTPS git operations.
- Ran `gh auth setup-git` to configure Git credential access.
- Fetched `origin/main` and confirmed the remote had not advanced.
- Pushed local `main` to `https://github.com/dashercammmmmmm/beaverview`.
- Verified local `HEAD`, `origin/main`, and `origin/HEAD` were synced after the push.
- Added and pushed `docs: record github sync status` so the handoff docs also exist on GitHub.

## 2026-06-24 - Pilot readiness preflight

- Added `scripts/check_pilot_readiness.py`.
- The preflight verifies local repo sync, ignored local-only files, Python dependency imports, SQLite seed counts, and `.env`/connector prerequisite status without printing secret values.
- It treats missing Azure credentials, missing connector credentials, and missing hardware IP rows as pending external prerequisites instead of local failures.

### Next

- Run this preflight after any environment, deployment, or connector change.
- When secure `api/.env` and `api/hardware_ips.csv` are available, rerun the preflight and use the pending list as the pilot-readiness punch list.

## 2026-06-24 - Hardware IP import validation

- Added `--dry-run` support to `api/import_device_ips.py`.
- The importer now validates that referenced `room_id` values exist in the seeded rooms table before replacing `device_ips`.
- Added safe committed sample data at `docs/examples/hardware_ips.sample.csv`.
- Added `scripts/check_hardware_ip_import.sh` to dry-run the sample and dry-run the real ignored `api/hardware_ips.csv` when present.
- Wired the hardware IP sample validation into `scripts/check_pilot_readiness.py`.

### Next

- When the real secure spreadsheet is available, place it at `api/hardware_ips.csv`, run `scripts/check_hardware_ip_import.sh`, then run `api/venv/bin/python api/import_device_ips.py api/hardware_ips.csv`.

## 2026-06-24 - Deployment template validation

- Added reusable VM deployment assets under `deploy/`.
- Added `deploy/systemd/beaverview.service`.
- Added `deploy/nginx/beaverview.conf.template` with `__VM_IP__` placeholder.
- Added `scripts/check_deployment_assets.sh` to validate the templates locally.
- Wired deployment asset validation into `scripts/check_pilot_readiness.py`.
- Updated `PLAYBOOK-DEPLOYMENT.md` to reference the checked-in templates instead of only manual paste blocks.

### Next

- On the Ubuntu VM, copy the systemd template and render the nginx template with the VM IP before running `systemctl`/`nginx -t`.

## 2026-06-24 - Local env initialization

- Added `scripts/init_local_env.sh`.
- The script creates ignored `api/.env` from `api/.env.example` when missing, appends a generated `PROXY_SECRET`, sets file mode `600`, and does not print the secret.
- Documented the initializer in `CLAUDE.md`, `SESSION-CONTEXT.md`, and `PLAYBOOK-DEPLOYMENT.md`.

### Next

- Fill OSU Azure, connector, and device credentials in `api/.env` when they are available.

## 2026-06-24 - Azure readiness checklist

- Added `docs/examples/azure-entra-app-registration.md`.
- Added `AZURE_REDIRECT_URI=https://beaverview/auth/callback` to `api/.env.example`.
- Updated `scripts/check_pilot_readiness.py` to verify the Azure checklist exists and validate the redirect URI shape when configured.
- Strengthened readiness checks so obvious placeholder values do not count as configured credentials.

### Next

- Have an OSU Entra admin create the app registration, client secret, and technician/admin groups, then fill the Azure values in ignored `api/.env`.

## 2026-06-24 - API contract validation

- Added `scripts/check_api_contracts.py`.
- The contract check runs the FastAPI app in-process with deterministic mock connector settings and no secret output.
- It verifies health, localhost dev auth, admin inventory, xpanel launch/proxy behavior, ServiceNow/chat mock fallbacks, `/api/chat`, and room incidents.
- Wired the API contract check into `scripts/check_pilot_readiness.py`.

### Next

- Run `scripts/check_api_contracts.py` after API route, auth, connector fallback, or device proxy changes.

## 2026-06-24 - Environment template validation

- Added `scripts/check_env_template.py`.
- The check verifies `api/.env.example` matches env vars used by runtime code and readiness checks, with no duplicate or stale keys.
- Wired the env-template check into `scripts/check_pilot_readiness.py`.
- Made `CRESTRON_VERIFY_SSL` active in the Crestron processor poller and added `CRESTRON_POLL_SCHEME`.
- Added missing `SESSION_SECRET_KEY` and `SESSION_HTTPS_ONLY` entries to `api/.env.example`.
- Consolidated the duplicate `SN_INSTANCE` documentation in `api/.env.example`.

### Next

- Run `scripts/check_env_template.py` after adding, renaming, or removing any `.env` setting.

## 2026-06-24 - Admin connector live probes

- Replaced the placeholder live response in `POST /api/admin/connectors/{campus_id}/{connector_name}/test`.
- Added connector-specific test behavior for Crestron, 25Live, ScreenConnect, WattBox, ServiceNow, SharePoint, and PTZ.
- Tests return mock status locally, pending status for missing live prerequisites, and live/error status for configured HTTP probes without printing secrets or raw device IPs.
- Tightened credential-presence checks so live mode requires complete credential sets where appropriate.
- ServiceNow now honors both documented auth paths: OAuth client credentials and Basic Auth service accounts.
- Updated the API contract check to clear local `.env` values deterministically and cover admin connector test behavior.
- Cleaned stale handoff/playbook references to the old XPanel proxy 501 stub.
- Updated handoff commands to run pilot readiness through `python3 scripts/check_pilot_readiness.py`, while the script also self-selects the project venv when available.

### Next

- After real OSU credentials and `hardware_ips.csv` are available, use the admin connector test endpoint to validate one connector at a time before enabling technician workflows.

## 2026-06-24 - Session secret readiness

- Updated `scripts/init_local_env.sh` to idempotently generate both `PROXY_SECRET` and `SESSION_SECRET_KEY`.
- Updated the pilot readiness preflight to require `SESSION_SECRET_KEY` and reject obvious placeholder values such as `change-me`.
- Ran the initializer locally; ignored `api/.env` now has both required local secrets set without printing values.
- Updated deployment and handoff docs to use `bash scripts/init_local_env.sh` and describe both generated secrets.

### Next

- Keep Azure and connector credentials out of Git; fill them only in ignored `api/.env` when OSU provides them.

## 2026-06-24 - Pilot input checklist

- Added `docs/examples/pilot-inputs-checklist.md` as the non-secret collection packet for remaining OSU pilot inputs.
- Added `scripts/check_pilot_inputs_doc.py` to validate the checklist still covers the preflight external prerequisite categories.
- Wired the pilot input checklist validator into `scripts/check_pilot_readiness.py`.
- Updated `docs/examples/azure-entra-app-registration.md` to use the reliable `python3 scripts/check_pilot_readiness.py` command.

### Next

- Use the checklist to collect external values, then enter them only into ignored `api/.env` or ignored `api/hardware_ips.csv`.

## 2026-06-24 - Machine-readable readiness output

- Added `--json` support to `scripts/check_pilot_readiness.py`.
- JSON output includes status, pass/pending/failure arrays, and counts without printing secret values.
- Added `--markdown` support for human-readable readiness reports.
- Documented the JSON mode for future reporting or automation.

### Next

- Use `python3 scripts/check_pilot_readiness.py --json` when another tool needs to consume readiness state, or `--markdown` when a person needs a paste-ready report.

## 2026-06-24 - Nginx render helper

- Added `scripts/render_nginx_config.sh` to validate a VM IP and render `deploy/nginx/beaverview.conf.template`.
- Updated `scripts/check_deployment_assets.sh` to render a sample nginx config and fail if `__VM_IP__` remains.
- Updated deployment docs to use the renderer instead of a raw `sed` pipeline.

### Next

- On the Ubuntu VM, render nginx with the actual VM IP before running `nginx -t`.

## 2026-06-24 - Self-signed certificate helper

- Added `scripts/generate_self_signed_cert.sh` to validate a VM IP and generate the BeaverView self-signed cert/key pair.
- Updated `scripts/check_deployment_assets.sh` to generate a sample cert locally and verify both DNS and IP subject alternative names.
- Updated deployment docs to use the helper instead of a raw multi-line `openssl` command.

### Next

- On the Ubuntu VM, generate the cert with the actual VM IP before copying the rendered nginx config into place.

## 2026-06-24 - Readiness covers data import validators

- Updated `scripts/check_pilot_readiness.py` to run `scripts/check_data_migration.sh`.
- Updated `scripts/check_pilot_readiness.py` to run `scripts/check_hardware_ip_import.sh` instead of duplicating only part of that validation inline.
- Documented that the main readiness preflight now exercises the data migration and hardware IP import gates directly.
- Updated the Ubuntu deployment package list to include the `sqlite3` CLI used by the data migration validator.

### Next

- Keep using `python3 scripts/check_pilot_readiness.py` as the single local go/no-go command before push or deployment.
