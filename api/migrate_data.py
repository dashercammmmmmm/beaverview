"""
One-time migration: imports data.js room inventory into SQLite.
Run once from the api/ folder:  python3 migrate_data.py
Safe to re-run — clears existing rows first (does NOT touch audit_log or user_roles).
"""
import sqlite3, json, re, os

DB_PATH   = os.path.join(os.path.dirname(__file__), 'beaverview.db')
DATA_PATH = os.path.join(os.path.dirname(__file__), '../dashboard/data.js')


def extract_json(js_text):
    match = re.search(r'window\.dashboardData\s*=\s*(\{.*\})', js_text, re.DOTALL)
    if not match:
        raise ValueError('Could not find window.dashboardData in data.js')
    json_str = match.group(1)
    # Replace JS booleans/null so json.loads accepts the string
    json_str = re.sub(r'\btrue\b',  'true',  json_str)
    json_str = re.sub(r'\bfalse\b', 'false', json_str)
    json_str = re.sub(r'\bnull\b',  'null',  json_str)
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # strip trailing commas
    return json.loads(json_str)


def migrate():
    with open(DATA_PATH) as f:
        data = extract_json(f.read())

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Clear existing data (preserves audit_log and user_roles)
    for tbl in ['devices', 'incidents', 'rooms', 'buildings', 'campuses', 'connector_config']:
        cur.execute(f'DELETE FROM {tbl}')

    for campus in data['campuses']:
        cid = campus['id']
        cur.execute(
            'INSERT INTO campuses(id,name,subtitle) VALUES(?,?,?)',
            (cid, campus['name'], campus.get('subtitle', ''))
        )

        # Seed connector_config from campus.connectors (or default to mock)
        for conn_name in ['crestron', 'live25', 'screenconnect', 'wattbox',
                          'servicenow', 'sharepoint', 'ptz']:
            mode = campus.get('connectors', {}).get(conn_name, 'mock')
            if isinstance(mode, dict):
                mode = mode.get('mode', 'mock')
            cur.execute(
                'INSERT INTO connector_config(campus_id,connector_name,mode) VALUES(?,?,?)',
                (cid, conn_name, mode)
            )

        for bldg in campus.get('buildings', []):
            cur.execute(
                'INSERT INTO buildings(campus_id,code,name) VALUES(?,?,?) RETURNING id',
                (cid, bldg['code'], bldg['name'])
            )
            bldg_id = cur.fetchone()[0]

            for room in bldg.get('rooms', []):
                room_id = f"{cid}-{bldg['code'].lower()}-{room['number']}".lower()
                room_id = re.sub(r'[^a-z0-9]+', '-', room_id).strip('-')
                cur.execute(
                    'INSERT INTO rooms(id,building_id,number,type,status,health,'
                    '  active_event,processor,display,screenconnect,wattbox,hybrid,stale)'
                    ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (room_id, bldg_id,
                     room['number'],
                     room.get('type', ''),
                     room.get('status', 'offline'),
                     room.get('health', 0),
                     room.get('activeEvent', ''),
                     room.get('processor', 'mock'),    # renamed from fusion
                     room.get('display', 'unknown'),
                     int(room.get('screenconnect', False)),
                     int(room.get('wattbox', False)),
                     int(room.get('hybrid', False)),
                     int(room.get('stale', False)))
                )

                for i, dev in enumerate(room.get('devices', [])):
                    cur.execute(
                        'INSERT INTO devices(room_id,device_type,manufacturer,model,connection,sort_order)'
                        ' VALUES(?,?,?,?,?,?)',
                        (room_id,
                         dev[0] if len(dev) > 0 else '',
                         dev[1] if len(dev) > 1 else '',
                         dev[2] if len(dev) > 2 else '',
                         dev[3] if len(dev) > 3 else '',
                         i)
                    )

                for inc in room.get('incidents', {}).get('open', []):
                    cur.execute(
                        'INSERT INTO incidents(room_id,ticket,status) VALUES(?,?,?)',
                        (room_id, inc, 'open')
                    )
                for inc in room.get('incidents', {}).get('closed', []):
                    cur.execute(
                        'INSERT INTO incidents(room_id,ticket,status) VALUES(?,?,?)',
                        (room_id, inc, 'closed')
                    )

    con.commit()
    con.close()

    print('Migration complete.')
    con2 = sqlite3.connect(DB_PATH)
    for tbl in ['campuses', 'buildings', 'rooms', 'devices']:
        n = con2.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]
        print(f'  {tbl}: {n} rows')
    con2.close()


if __name__ == '__main__':
    migrate()
