# BeaverView Project Log

This is the durable local work log for BeaverView v2. Add an entry every time the project changes materially so the Mac Mini checkout remains the source of truth between assistant sessions.

## 2026-06-24 - First live-room candidate listing

- Added `--list-candidates` to `scripts/check_first_live_room_preflight.py`.
- Added `--connector <name>` filtering for candidate lists so OSU can shortlist rooms for a chosen first connector.
- Added `--hardware-csv <path>` preview support so device-backed connector candidates can be checked from a validated secure Hardware IP CSV before import.
- The candidate list reports sanitized room IDs, building/room labels, status, health, eligible connector hints, and Hardware IP device types without printing raw IP addresses.
- Extended `scripts/check_first_live_room_preflight_cases.py` to verify candidate-list JSON behavior and no raw IP leakage against an isolated temp DB.
- Updated the pilot input checklist and first live-room validation runbook to run the candidate shortlist before setting `FIRST_LIVE_ROOM_ID` and `FIRST_LIVE_CONNECTOR`.

### Next

- After the secure Hardware IP export is validated, use `scripts/check_first_live_room_preflight.py --list-candidates --connector xpanel --hardware-csv api/hardware_ips.csv --json` to choose the first non-critical target with OSU before import.

## 2026-06-24 - Deployment playbook validation

- Updated `PLAYBOOK-DEPLOYMENT.md` so VM dependency verification uses the committed venv and `api/requirements.txt` instead of installing MSAL ad hoc and appending to requirements on the VM.
- Added a required pilot-readiness command before login-flow testing in the deployment playbook.
- Added `scripts/check_deployment_playbook.py` to validate core VM setup, nginx/systemd, CORS, Azure redirect, dependency, and readiness commands.
- Wired the deployment playbook validator into `scripts/check_pilot_readiness.py`.

### Next

- Keep deployment command changes in the repository and rerun `python3 scripts/check_deployment_playbook.py` before updating VM-facing instructions.

## 2026-06-24 - Production safety guardrails

- Replaced hardcoded wildcard CORS middleware config with `BEAVERVIEW_CORS_ORIGINS`, preserving wildcard behavior only as the local default.
- Added readiness tracking for unrestricted CORS so VM pilot use requires `BEAVERVIEW_CORS_ORIGINS=https://beaverview` in ignored `api/.env`.
- Guarded dashboard `window._dev` so it is created only on localhost-style hosts.
- Added `scripts/check_production_safety.py` and wired it into pilot readiness to verify CORS configurability, localhost-only dev helpers/live reload, and deployment playbook guidance.

### Next

- Before VM pilot use, set `BEAVERVIEW_CORS_ORIGINS=https://beaverview` in the ignored VM `api/.env`, restart BeaverView, and rerun pilot readiness.

## 2026-06-24 - Readiness pending-action coverage

- Added explicit `PENDING_ACTIONS` entries for missing `api/.env`, `PROXY_SECRET`, `SESSION_SECRET_KEY`, and Azure redirect URI readiness states.
- Strengthened `scripts/check_readiness_actions.py` so literal `pending(...)` calls must have mapped next actions.
- The validator now also expands known loop-generated credential and launch URL pending messages and fails if any generated message is missing an action.

### Next

- Any new dynamic readiness pending pattern must be added to `ALLOWED_DYNAMIC_PENDING` with a matching coverage rule before it can pass readiness.

## 2026-06-24 - Readiness action reference validation

- Added `scripts/check_readiness_actions.py` to statically validate `PENDING_ACTIONS` in `scripts/check_pilot_readiness.py`.
- The validator checks that each pending action has text, references an existing file, and that Markdown anchors resolve.
- Wired the validator into `scripts/check_pilot_readiness.py` as a local gate.

### Next

- When adding or renaming readiness pending messages, update `PENDING_ACTIONS` and run `scripts/check_readiness_actions.py` before push.

## 2026-06-24 - Readiness pending-action report

- Extended `scripts/check_pilot_readiness.py` so each known pending external prerequisite includes a concrete next action and reference document.
- Added `pending_actions` to JSON output and a `Pending Next Actions` section to Markdown/text output.
- Kept the report no-secrets: it names ignored files and env keys, but does not print configured values.

### Next

- Use `python3 scripts/check_pilot_readiness.py --markdown` as the external-input handoff after every deployment-input update.

## 2026-06-24 - First live-room preflight case coverage

- Added `scripts/check_first_live_room_preflight_cases.py` to exercise first live-room preflight pass, pending, and fail behavior against an isolated temporary SQLite DB.
- Added a test-only `BEAVERVIEW_DB_PATH` override for the preflight script so validator coverage does not touch ignored local project data.
- Wired the case validator into `scripts/check_pilot_readiness.py` as a local gate.

### Next

- Keep using `scripts/check_first_live_room_preflight.py` for the real selected room; the case validator only proves the preflight logic itself still behaves safely.

## 2026-06-24 - First live-room target preflight

- Added `scripts/check_first_live_room_preflight.py` to validate a selected first live-room target without printing secrets or raw IPs.
- Added `FIRST_LIVE_ROOM_ID` and `FIRST_LIVE_CONNECTOR` to `api/.env.example` and pilot input docs.
- Wired the preflight into `scripts/check_pilot_readiness.py`: unset target selection is pending, selected-but-incomplete prerequisites remain pending, and invalid selected room/connector data fails locally.

### Next

- After OSU picks the non-critical first room and connector, set the two ignored `.env` values and rerun pilot readiness before importing Hardware IP rows or changing connector mode.

## 2026-06-24 - Hardware IP import guardrails

- Hardened `api/import_device_ips.py` so Hardware IP validation rejects missing required fields, duplicate `room_id`/`device_type` mappings, and public IP addresses unless `--allow-public` is explicitly supplied after review.
- Changed IP validation errors to report CSV row numbers without echoing raw IP values.
- Expanded `scripts/check_hardware_ip_import.sh` with negative fixtures for duplicate mappings and unreviewed public IPs.

### Next

- When the real secure `api/hardware_ips.csv` arrives, run `scripts/check_hardware_ip_import.sh` before import; any failure should be corrected in the source export before first live-room validation.

## 2026-06-24 - Dashboard backend inventory read path

- Added `scripts/check_inventory_parity.py` to compare `dashboard/data.js` with `GET /api/campus/{campus_id}/inventory` for every seeded campus.
- Wired the active dashboard to load sanitized SQLite inventory from FastAPI when the backend is online, while keeping `data.js` as the static/offline fallback.
- Expanded dashboard browser smoke and pilot readiness so the backend inventory read path is verified before pilot-facing changes.

### Next

- Use the backend inventory path as the default local review mode; the remaining production blocker is still the secure Hardware IP import plus first live-room connector validation.

## 2026-06-24 - Backend inventory endpoint

- Added `GET /api/campus/{campus_id}/inventory` as a read-only SQLite inventory endpoint for campus, building, room, device, and incident data.
- Kept hardware IP records out of the response; browser-visible inventory now has a backend target without exposing `device_ips`.
- Expanded offline API contracts to verify the inventory response shape, seeded counts, missing-campus 404, and no raw hardware IP fields.

### Next

- Compare one campus between `dashboard/data.js` and `/api/campus/corvallis/inventory`, then switch the dashboard room read path only after the UI behavior remains unchanged.

## 2026-06-24 - First live-room validation runbook

- Added `docs/examples/first-live-room-validation.md` as the no-secrets runbook for the first non-critical room and connector validation.
- Added `scripts/check_live_validation_doc.py` and wired it into `scripts/check_pilot_readiness.py`.
- Updated the pilot input checklist and handoff docs to point at the live-room validation runbook before any live connector test.

### Next

- When OSU provides the selected non-critical room, real Hardware IP data, and the first connector credentials, follow the runbook and record only a sanitized outcome in this log.

## 2026-06-24 - Room diagnostics guard

- Added a room Overview diagnostics card that summarizes likely causes from room status, health, display state, open incidents, stale inventory, and device types.
- Added an "Open WattBox Auto-Fix" path that routes to WattBox outlet review, but stays disabled when the room appears occupied, when no WattBox is mapped, or when no fix is recommended.
- Expanded `scripts/check_dashboard_browser.py` to verify the occupied-room Auto-Fix guard in headless Chromium.

### Next

- After live schedule and Hardware IP data are loaded, validate the empty-room guard against a non-critical room before allowing any real outlet cycle workflow.

## 2026-06-24 - Admin CSP hardening

- Moved the admin dashboard, rooms, connectors, logs, and users page scripts out of inline `<script>` blocks into external `*-page.js` files.
- Replaced the remaining generated inline admin event handlers with data attributes and delegated listeners.
- Restored the app CSP to `script-src 'self' blob:` so admin JavaScript can run without `script-src 'unsafe-inline'`.

### Next

- Keep admin browser smoke in the pilot readiness gate so CSP regressions are caught before deployment work.
- Later hardening can address inline style attributes separately; `style-src 'unsafe-inline'` is still required by current dashboard/admin markup.

## 2026-06-24 - Admin browser smoke coverage

- Added `scripts/check_admin_browser.py` and `scripts/check_admin_browser.sh`.
- The admin browser smoke starts BeaverView locally, opens `/admin/`, and verifies summary, room listing/edit drawer, connector management, logs, and user role pages in headless Chromium.
- Wired the admin browser smoke into `scripts/check_pilot_readiness.py` so pilot readiness now covers both technician dashboard workflows and admin management pages.
- Fixed the current admin implementation under the app CSP by allowing existing inline admin scripts/handlers from self-served pages.
- Made localhost dev auth consistent for `/api/admin/*` when Azure SSO is not fully configured, matching `/api/me`.
- Replaced brittle raw JSON `onclick` payloads in room/user edit rows with encoded data attributes and delegated handlers.

## 2026-06-24 - Device web UI readiness state

- Reworked the dashboard Device web UIs panel so it no longer displays dead "Open UI" buttons.
- The panel now shows room device inventory plus an explicit pending state until Hardware IP records are imported and supported device types have approved backend proxy routes.
- Expanded `scripts/check_dashboard_browser.py` to verify the Device web UI panel stays guarded in headless Chromium.

### Next

- After real Hardware IP records are loaded, add explicit backend proxy/launch coverage for each approved web UI device type instead of introducing a generic raw-IP launcher.

## 2026-06-24 - Hermes readiness and browser coverage

- Added `CHAT_BASE_URL` to the pilot readiness pending-prerequisite list so the visible Ask Hermes tab is tracked before pilot use.
- Updated the pilot input checklist and validator to collect the local OpenAI-compatible Hermes endpoint details.
- Expanded `scripts/check_dashboard_browser.py` to verify the dashboard chat tab surfaces the offline "Chat agent not configured" fallback when `CHAT_BASE_URL` is missing.

### Next

- When the approved local AI endpoint is available, add `CHAT_BASE_URL` to ignored `api/.env`, optionally set `CHAT_MODEL` and `CHAT_TIMEOUT`, and rerun browser smoke before pilot review.

## 2026-06-24 - Active docs guarded-workflow refresh

- Updated setup and development docs that still described active tool panels as mock-only placeholders.
- Updated the in-app first-run tour note to describe backend-guarded workflows and pending prerequisites.
- Updated the active dashboard phased playbook to reflect implemented FastAPI endpoints, guarded dashboard tool panels, and first live-room validation as the next phase.
- Regenerated the HTML playbook copies with `scripts/build_playbook_html.py`.

### Next

- Continue treating archived dashboard/playbook snapshots as historical; update only active docs unless an archive correction is explicitly needed.
- Once real `api/.env` values and `api/hardware_ips.csv` are available, document the first live-room validation result.

## 2026-06-24 - Launch URL readiness tracking

- Updated `scripts/check_pilot_readiness.py` to report missing `SC_BASE_URL` and `SHAREPOINT_BASE_URL` as pending external prerequisites.
- Kept ScreenConnect and SharePoint separate from stored connector credentials because they use OSU browser-session passthrough instead of service passwords.
- Updated `docs/examples/pilot-inputs-checklist.md` and its validator so the external-input packet now covers ScreenConnect and SharePoint launch URLs.

### Next

- When OSU provides ScreenConnect and SharePoint base URLs, add them to ignored `api/.env`, restart the backend, and verify the dashboard launch buttons.

## 2026-06-24 - Dashboard browser smoke coverage

- Added `scripts/check_dashboard_browser.py` and `scripts/check_dashboard_browser.sh`.
- The browser smoke starts BeaverView locally, opens the active dashboard in headless Chromium, selects real seeded rooms, and verifies UI-level guarded flows for ServiceNow, XPanel, ScreenConnect, SharePoint, WattBox, and PTZ.
- The check verifies that backend-wired dashboard controls show pending/prerequisite messages instead of silently acting as mock controls when credentials and Hardware IP records are absent.
- Wired the browser smoke into `scripts/check_pilot_readiness.py` so pilot readiness now includes a UI workflow gate, not only backend API contracts.

### Next

- Keep `scripts/smoke_check.sh` as the fast backend gate and use `scripts/check_dashboard_browser.sh` or `scripts/check_pilot_readiness.py` before pilot-facing UI changes.
- After real credentials are loaded, extend the browser smoke with a live-mode test for one non-critical room.

## 2026-06-24 - Dashboard launch endpoint wiring

- Wired XPanel, ScreenConnect, and SharePoint launch buttons to `GET /api/rooms/{room_id}/launch/{tool}`.
- Launch buttons now open a new tab only when the backend reports `mode: live` and returns a URL; otherwise the panel shows the connector prerequisite message.
- Tightened the SharePoint launch contract so mock mode returns `url: null` instead of a default-looking SharePoint URL.
- Expanded offline API contracts and smoke checks for ScreenConnect and SharePoint launch behavior.

### Next

- Configure `SC_BASE_URL` and `SHAREPOINT_BASE_URL`, then verify one ScreenConnect machine and one SharePoint room page open through the dashboard launch buttons.
- Load real Hardware IP data before validating XPanel live launch, because the backend proxy depends on `device_ips`.

## 2026-06-24 - Dashboard PTZ and WattBox guarded controls

- Wired PTZ dashboard controls to `POST /api/rooms/{room_id}/ptz/{command}` for pan, tilt, zoom, home, and preset recall commands.
- Wired WattBox cycle buttons to `POST /api/rooms/{room_id}/wattbox/outlets/{outlet_num}/cycle` with an explicit browser confirmation.
- The WattBox panel now checks `GET /api/rooms/{room_id}/wattbox/outlets` on open and keeps the local mock outlet list when OvrC credentials are missing.
- PTZ and WattBox panels now show inline backend status/prerequisite messages instead of acting as silent mock controls.
- Expanded `scripts/smoke_check.sh` to verify the offline PTZ and WattBox guardrails in addition to the existing backend smoke endpoints.

### Next

- Load the real secure `api/hardware_ips.csv`, configure PTZ/WattBox credentials in `api/.env`, and test one real non-critical room before enabling pilot use.
- Once one room validates live, replace mock WattBox outlet labels with normalized OvrC outlet data.

## 2026-06-24 - Dashboard 25Live schedule overlay

- Wired the active dashboard to fetch `GET /api/campus/{campus_id}/schedule` when the backend is reachable.
- Added a campus-level schedule cache keyed by `room_id` so room overview schedule text and campus active-room counts can use backend schedule data instead of only static `dashboard/data.js` values.
- The overview Schedule metric now shows whether the value came from 25Live, backend mock fallback, or static inventory.
- Added the campus schedule endpoint to `scripts/smoke_check.sh` so the fast local gate verifies the offline 25Live mock fallback.

### Next

- When real 25Live credentials are available, compare one live room payload with the expected room identifiers and add a normalizer if OSU's 25Live response shape differs from the current mock fallback event shape.
- After the real Hardware IP import is loaded, wire PTZ and WattBox panels to their guarded backend endpoints.

## 2026-06-24 - Dashboard ServiceNow backend wiring

- Wired the active dashboard ServiceNow draft form to `POST /api/rooms/{room_id}/servicenow/incident`.
- The form now sends short description, category, priority-derived urgency/impact, and description to the backend.
- Added inline submit status so technicians can see whether the backend created a live incident, returned the offline mock draft, or rejected the room/request.
- Updated the room log tab to show recent local actions as well as recent room visits.
- Added `node --check dashboard/app.js` to `scripts/smoke_check.sh` so dashboard syntax regressions fail the fast local gate.
- Updated `dashboard/README.md` so it no longer describes the active dashboard as having no backend/API path for ServiceNow drafts.

### Next

- Wire the PTZ and WattBox tool panels to their guarded backend endpoints after validating the first real hardware IP records.
- Add browser-level smoke coverage for the ServiceNow form once the frontend test harness is chosen.

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

## 2026-06-24 - Broader connector contract coverage

- Expanded `scripts/check_api_contracts.py` to verify every seeded Corvallis connector returns a safe mock test result offline.
- Added contract coverage for admin live-mode toggles without credentials; each connector must warn and avoid changing DB mode.
- Added contract coverage for live-mode connector tests with prerequisites missing; each connector must return a pending, unreachable response with an explanatory message.
- The contract restores connector modes after the run so the ignored local DB is not left in a live-test state.

### Next

- When real credentials and hardware IPs are available, use the same admin connector test endpoint to validate one live connector at a time.

## 2026-06-24 - PTZ command endpoint scaffold

- Added `POST /api/rooms/{room_id}/ptz/{command}` for allowlisted PTZOptics CGI commands.
- The endpoint uses existing backend-only `device_ips` lookup, PTZ credentials, proxyable-IP validation, and audit logging.
- Expanded offline API contracts to cover unknown PTZ commands, missing PTZ credentials, and missing PTZ camera IP behavior without a live camera.
- Updated connector docs to describe the implemented PTZ endpoint and its validation path.

### Next

- After real PTZ credentials and camera IPs are available, test one room with `home` and a preset command before wiring dashboard controls to the endpoint.

## 2026-06-24 - WattBox OvrC outlet endpoints

- Added `GET /api/rooms/{room_id}/wattbox/outlets` for OvrC-backed outlet status.
- Added `POST /api/rooms/{room_id}/wattbox/outlets/{outlet_num}/cycle` with outlet-number validation and audit logging.
- The endpoints inject `WATTBOX_OVRC_API_KEY` server-side and keep the key out of browser responses.
- Expanded offline API contracts to cover missing OvrC config and invalid outlet-cycle input without live WattBox access.
- Updated connector docs to describe the implemented WattBox endpoints and validation path.

### Next

- After real OvrC credentials are available, test one low-risk room outlet status call before enabling cycle actions in technician workflows.

## 2026-06-24 - 25Live schedule endpoint scaffold

- Added `GET /api/campus/{campus_id}/schedule`.
- The endpoint returns seeded mock schedule data from `rooms.active_event` when 25Live credentials are missing.
- With `LIVE25_BASE_URL`, `LIVE25_USERNAME`, and `LIVE25_PASSWORD`, the backend calls 25Live server-side with Basic Auth and returns the upstream schedule payload without exposing credentials.
- Expanded offline API contracts to cover mock schedule output and unknown campus handling without live 25Live access.
- Updated connector docs to describe the implemented endpoint and validation path.

### Next

- After real 25Live credentials are available, compare one room's live schedule payload with the seeded dashboard event display before wiring the frontend to this endpoint.

## 2026-06-24 - ServiceNow incident create endpoint

- Added `POST /api/rooms/{room_id}/servicenow/incident`.
- The endpoint returns a mock draft and writes an audit row when ServiceNow credentials are missing.
- With `SN_INSTANCE` plus OAuth or Basic Auth credentials, the backend creates incidents server-side and returns only minimal ticket identifiers.
- Expanded offline API contracts to cover mock draft creation and missing-room behavior without live ServiceNow access.
- Updated connector docs to describe the implemented endpoint and current `SN_*` environment variable names.

### Next

- After real ServiceNow credentials are available, create one controlled test incident from a non-production room context before wiring the dashboard submit button to this endpoint.
