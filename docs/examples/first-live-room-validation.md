# BeaverView First Live-Room Validation

Use this checklist for the first non-critical room after OSU provides the secure Hardware IP export and the first approved connector credentials. Do not paste secrets, raw device IPs, screenshots containing private addresses, or ticket details into Git.

## Validation Record

Complete these fields in a private deployment note, not in this committed file:

- Validation date:
- Technician:
- Non-critical room ID:
- Campus/building/room:
- Connector validated first:
- Approved maintenance window:
- Rollback owner:

## Required Preconditions

- Ubuntu VM exists and BeaverView is deployed behind nginx/systemd.
- Windows test client can open `https://beaverview`.
- Azure/Entra login works for one technician and one admin.
- Ignored `api/.env` has the connector values for the first connector only.
- Ignored `api/.env` has `FIRST_LIVE_ROOM_ID` and `FIRST_LIVE_CONNECTOR` set for this validation target.
- Ignored `api/hardware_ips.csv` contains the selected room and the first connector device type.
- Ignored `api/hardware_ips.csv` has exactly one row for each selected `room_id` / `device_type` pair.
- Device IP rows are private or link-local unless public addressing has been explicitly reviewed and `--allow-public` is intentionally used.
- VLAN route from the Ubuntu VM to the AV device network is confirmed.
- Room is empty or the test is explicitly read-only.
- `python3 scripts/check_pilot_readiness.py` passes locally before live testing.

## Preflight Commands

Run from `/home/beaverview/app` on the VM unless noted:

```bash
python3 scripts/check_pilot_readiness.py --markdown
scripts/check_first_live_room_preflight.py --list-candidates
scripts/check_first_live_room_preflight.py --list-candidates --connector xpanel
scripts/check_hardware_ip_import.sh
scripts/check_first_live_room_preflight.py
cd api && venv/bin/python import_device_ips.py hardware_ips.csv
sudo systemctl status beaverview --no-pager
sudo nginx -t
```

Use `--list-candidates --json` when the selected room and connector need to be reviewed by another tool or pasted into a private deployment note. Add `--connector <name>` to filter the shortlist to one first connector. Device-backed connector filters such as `xpanel`, `wattbox`, and `ptz` require imported Hardware IP device-type rows before they return matching rooms. The candidate list is built from sanitized SQLite room data and Hardware IP device types only; it does not print raw IP addresses.

Expected result: local checks pass, the candidate list identifies non-critical room IDs and eligible connector hints, the selected non-critical room and first connector pass preflight, imported Hardware IP records include the selected non-critical room, duplicate or unreviewed public rows are rejected, and only unrelated external prerequisites remain pending.

## Connector Order

Validate only one connector first. Recommended order:

1. XPanel launch/proxy, because it proves Hardware IP lookup plus backend credential injection.
2. 25Live schedule, because it is read-only and validates room ID mapping.
3. ServiceNow draft/create, because it validates ticket workflow without device control.
4. ScreenConnect or SharePoint launch URL, because each depends on OSU browser-session auth.
5. PTZ command, only after confirming the camera is non-critical.
6. WattBox/OvrC outlet status, then outlet cycle only in an approved empty-room maintenance window.

## Browser Validation

In the dashboard:

- Open the selected room.
- Confirm Overview diagnostics match the known room state.
- Confirm guarded buttons stay pending for connectors that are not configured.
- Exercise only the first approved connector.
- Confirm no raw device IP address appears in the browser URL, page text, or devtools network response body.
- Confirm the room action appears in the admin audit log.

In the admin panel:

- Open `/admin/connectors.html`.
- Run `Test` for the first connector.
- Confirm the result is `live`, `pending`, or a clear error that does not expose secrets or raw IP addresses.

## Pass Criteria

- `python3 scripts/check_pilot_readiness.py --markdown` passes after the test.
- The first connector has a documented live result.
- Other connectors remain guarded or pending.
- No secret, raw IP, or private ticket detail is committed.
- Rollback path is known: set connector mode back to `mock`, remove the imported Hardware IP rows if needed, and restart BeaverView.

## Capture Evidence Privately

Store evidence outside Git:

- readiness report
- connector test result
- admin audit log row
- technician notes
- screenshots with raw IPs redacted

After validation, update `PROJECT-LOG.md` with a sanitized summary only, such as the connector name, room ID class, and pass/fail outcome.
