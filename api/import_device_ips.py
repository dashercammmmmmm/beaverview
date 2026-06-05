"""
Import hardware IP spreadsheet into the device_ips table.
Run from the api/ folder:  python3 import_device_ips.py hardware_ips.csv

Expected CSV columns (header row required):
    room_id, device_type, ip_address

  room_id      — matches rooms.id format: campus-building-number  (e.g. corvallis-kad-101)
  device_type  — xpanel | wattbox | ptz | display | etc.
  ip_address   — IPv4 address of the device

Safe to re-run — clears and reloads the device_ips table on each run.
Does NOT touch any other table.
"""
import csv, os, sqlite3, sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'beaverview.db')


def import_ips(csv_path: str) -> None:
    if not os.path.exists(csv_path):
        print(f'Error: file not found: {csv_path}')
        sys.exit(1)

    rows = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        required = {'room_id', 'device_type', 'ip_address'}
        if not required.issubset(set(reader.fieldnames or [])):
            missing = required - set(reader.fieldnames or [])
            print(f'Error: CSV missing required columns: {missing}')
            sys.exit(1)
        for line in reader:
            room_id     = line['room_id'].strip().lower()
            device_type = line['device_type'].strip().lower()
            ip_address  = line['ip_address'].strip()
            if room_id and device_type and ip_address:
                rows.append((room_id, device_type, ip_address))

    con = sqlite3.connect(DB_PATH)
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
    if len(sys.argv) < 2:
        default = os.path.join(os.path.dirname(__file__), 'hardware_ips.csv')
        if os.path.exists(default):
            import_ips(default)
        else:
            print('Usage: python3 import_device_ips.py hardware_ips.csv')
            sys.exit(1)
    else:
        import_ips(sys.argv[1])
