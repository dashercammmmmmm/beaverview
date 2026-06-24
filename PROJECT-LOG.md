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
