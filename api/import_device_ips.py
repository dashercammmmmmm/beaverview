"""
Import hardware IP spreadsheet into the device_ips table.
Run from the api/ folder:  python3 import_device_ips.py hardware_ips.csv
Dry-run validation:       python3 import_device_ips.py --dry-run hardware_ips.csv

Expected CSV columns (header row required):
    room_id, device_type, ip_address

  room_id      — matches rooms.id format: campus-building-number  (e.g. corvallis-kad-101)
  device_type  — xpanel | wattbox | ptz | display | etc.
  ip_address   — IPv4 address of the device

Safe to re-run — clears and reloads the device_ips table on each run.
Does NOT touch any other table.
Private/link-local IP addresses are required by default. Use --allow-public
only after explicit network review.
"""
import argparse
import os
import sqlite3
import sys

from hardware_ip_csv import HardwareCsvError, load_hardware_rows

DB_PATH = os.path.join(os.path.dirname(__file__), 'beaverview.db')
SUPPORTED_PROXY_TYPES = {'xpanel', 'wattbox', 'ptz'}


def load_rows(csv_path: str, allow_public: bool = False) -> list[tuple[str, str, str]]:
    try:
        return load_hardware_rows(csv_path, allow_public=allow_public)
    except HardwareCsvError as exc:
        print(f'Error: {exc}')
        sys.exit(1)


def validate_room_ids(con: sqlite3.Connection, rows: list[tuple[str, str, str]]) -> None:
    room_ids = {row[0] for row in rows}
    placeholders = ','.join('?' for _ in room_ids)
    found = {
        row[0]
        for row in con.execute(
            f'SELECT id FROM rooms WHERE id IN ({placeholders})',
            tuple(sorted(room_ids))
        ).fetchall()
    }
    missing = sorted(room_ids - found)
    if missing:
        preview = ', '.join(missing[:8])
        if len(missing) > 8:
            preview += f', ... ({len(missing)} total)'
        print(f'Error: CSV references unknown room_id values: {preview}')
        print('Run python3 migrate_data.py first, or fix the room_id values.')
        sys.exit(1)


def import_ips(csv_path: str, dry_run: bool = False, allow_public: bool = False) -> None:
    rows = load_rows(csv_path, allow_public=allow_public)

    from main import init_db
    init_db()

    con = sqlite3.connect(DB_PATH)
    validate_room_ids(con, rows)

    proxy_count = sum(1 for _, device_type, _ in rows if device_type in SUPPORTED_PROXY_TYPES)

    if dry_run:
        con.close()
        print(f'Dry run OK. {len(rows)} device IP records validated ({proxy_count} proxy-capable).')
        return

    con.execute('DELETE FROM device_ips')
    con.executemany(
        'INSERT INTO device_ips(room_id,device_type,ip_address) VALUES(?,?,?)',
        rows
    )
    con.commit()

    count = con.execute('SELECT COUNT(*) FROM device_ips').fetchone()[0]
    con.close()

    print(f'Import complete. {count} device IP records loaded.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import or validate BeaverView hardware IP CSV data.')
    parser.add_argument('csv_path', nargs='?', default=os.path.join(os.path.dirname(__file__), 'hardware_ips.csv'))
    parser.add_argument('--dry-run', action='store_true', help='Validate only; do not replace device_ips rows.')
    parser.add_argument(
        '--allow-public',
        action='store_true',
        help='Allow public IP addresses after explicit network review. Private/link-local is required by default.',
    )
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        print(f'Usage: python3 import_device_ips.py [--dry-run] hardware_ips.csv')
        print(f'Error: file not found: {args.csv_path}')
        sys.exit(1)

    import_ips(args.csv_path, dry_run=args.dry_run, allow_public=args.allow_public)
