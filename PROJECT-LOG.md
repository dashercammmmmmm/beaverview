# BeaverView Project Log

This is the durable local work log for BeaverView v2. Add an entry every time the project changes materially so the Mac Mini checkout remains the source of truth between assistant sessions.

## 2026-06-24 - Source-of-truth stabilization

- Confirmed canonical local repo: `/Users/benjaminfranklinautomation/projects/beaverview`.
- Confirmed GitHub remote: `https://github.com/dashercammmmmmm/beaverview`.
- Confirmed local `main` is five commits ahead of `origin/main`; latest local commit is `9a4cb4f fix: allow maplibre and osm tiles via relaxed CSP header`.
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
- Push the five local v2 commits plus this stabilization commit to GitHub once Cam approves syncing `main`.

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

- Attempted `git push origin main`; remote had not advanced, but push failed because this environment has no GitHub HTTPS credentials configured.
- Replaced the `/api/rooms/{room_id}/proxy/{tool}/{path}` 501 stub with a conservative GET-only proxy foundation for `xpanel`, `wattbox`, and `ptz`.
- Proxy now looks up device IPs from `device_ips`, validates proxyable IP addresses, injects backend-only credentials, disables redirects, sets a short timeout, and returns `Cache-Control: no-store`.
- Added private/link-local IP enforcement by default; `DEVICE_PROXY_ALLOW_PUBLIC=true` is available only for reviewed deployments.
- Fixed ServiceNow env compatibility so `SN_INSTANCE`, `SN_CLIENT_ID`, and `SN_CLIENT_SECRET` from `.env.example` are honored by `main.py`.
- Fixed ServiceNow launch URL construction for documented full instance domains such as `oregonstate.service-now.com`.
- Hardened `api/import_device_ips.py` to initialize schema and reject invalid/non-proxyable IP rows.

### Next

- Configure GitHub credentials or switch the remote to SSH, then push local `main`.
- Load the real secure `hardware_ips.csv` and device credentials, then test one actual XPanel or WattBox path on the AV network.
