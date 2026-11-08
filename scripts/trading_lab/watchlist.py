"""Research-only SQLite candidate history; this module cannot place orders."""
import hashlib
import argparse
import json
import math
import re
import sqlite3
from pathlib import Path


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def connect(root):
    root = Path(root).expanduser().absolute()
    if any(p.is_symlink() for p in [root, *root.parents]) or (root / 'watchlist.sqlite3').is_symlink():
        raise ValueError('WATCHLIST_SYMLINK_REJECTED')
    root = root.resolve()
    if str(root).startswith('/mnt/'):
        raise ValueError('Choose a local Linux filesystem for SQLite WAL, not /mnt')
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / 'watchlist.sqlite3', isolation_level=None, timeout=10)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version not in (0, 1, 2, 3):
        raise ValueError('Unsupported watchlist schema')
    if version == 0:
        db.executescript('''BEGIN IMMEDIATE;
            CREATE TABLE setups(id TEXT PRIMARY KEY, definition TEXT NOT NULL);
            CREATE TABLE events(seq INTEGER PRIMARY KEY, setup_id TEXT NOT NULL REFERENCES setups(id),
                event_key TEXT NOT NULL, at_ms INTEGER NOT NULL, state TEXT NOT NULL, body TEXT NOT NULL,
                UNIQUE(setup_id,event_key));
            CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;
            CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;
            CREATE TRIGGER setups_no_update BEFORE UPDATE ON setups BEGIN SELECT RAISE(ABORT,'immutable'); END;
            CREATE TRIGGER setups_no_delete BEFORE DELETE ON setups BEGIN SELECT RAISE(ABORT,'immutable'); END;
            PRAGMA user_version=1; COMMIT;''')
        version = 1
    if version == 1:
        # A legacy setup remains present, but has no trusted case binding.
        db.executescript('''BEGIN IMMEDIATE;
            CREATE TABLE case_bindings(setup_id TEXT PRIMARY KEY REFERENCES setups(id),
                case_id TEXT NOT NULL, input_sha256 TEXT NOT NULL);
            CREATE TRIGGER case_bindings_no_update BEFORE UPDATE ON case_bindings BEGIN SELECT RAISE(ABORT,'immutable'); END;
            CREATE TRIGGER case_bindings_no_delete BEFORE DELETE ON case_bindings BEGIN SELECT RAISE(ABORT,'immutable'); END;
            PRAGMA user_version=2; COMMIT;''')
        version = 2
    if version == 2:
        db.executescript('''BEGIN IMMEDIATE;
            CREATE TABLE source_bindings(setup_id TEXT PRIMARY KEY REFERENCES setups(id),
                source_version TEXT NOT NULL, source_id TEXT NOT NULL, setup TEXT NOT NULL);
            CREATE TRIGGER source_bindings_no_update BEFORE UPDATE ON source_bindings BEGIN SELECT RAISE(ABORT,'immutable'); END;
            CREATE TRIGGER source_bindings_no_delete BEFORE DELETE ON source_bindings BEGIN SELECT RAISE(ABORT,'immutable'); END;
            PRAGMA user_version=3; COMMIT;''')
    return db


def create(db, data, *, _case_binding=None, _panel_binding=None):
    required = {'symbol', 'venue', 'direction', 'family', 'source_cutoff_ms', 'source_sha256',
                'level', 'invalidation', 'expires_ms', 'hypothesis', 'opposition', 'confirmation', 'feature_version'}
    if set(data) != required or data['venue'] != 'BINANCE_PUBLIC_USDM':
        raise ValueError('Invalid definition or venue')
    if not re.fullmatch('[A-Z0-9]{2,32}', data['symbol']) or not re.fullmatch('[0-9a-f]{64}', data['source_sha256']):
        raise ValueError('Invalid symbol or source hash')
    if data['direction'] not in ('LONG', 'SHORT') or data['family'] not in ('TREND_PULLBACK', 'SWEEP_RECLAIM', 'BREAKOUT_RETEST', 'HTF_REACTION'):
        raise ValueError('Invalid direction or family')
    cutoff, expiry = data['source_cutoff_ms'], data['expires_ms']
    level, stop = float(data['level']), float(data['invalidation'])
    if (type(cutoff) is not int or type(expiry) is not int or cutoff % 300000 or cutoff >= expiry
            or not all(math.isfinite(x) and x > 0 for x in (level, stop))
            or (data['direction'] == 'LONG' and stop >= level)
            or (data['direction'] == 'SHORT' and stop <= level)
            or any(not isinstance(data[k], str) or not data[k].strip() for k in ('hypothesis', 'opposition', 'confirmation', 'feature_version'))):
        raise ValueError('Invalid timestamps, levels or research context')
    definition = encode(data)
    sid = hashlib.sha256(definition.encode()).hexdigest()
    db.execute('BEGIN IMMEDIATE')
    try:
        if _case_binding and db.execute('SELECT 1 FROM setups WHERE id=?', (sid,)).fetchone():
            existing = db.execute('SELECT case_id,input_sha256 FROM case_bindings WHERE setup_id=?', (sid,)).fetchone()
            if existing != _case_binding:
                raise ValueError('EXISTING_SETUP_HAS_NO_MATCHING_SOURCE_BINDING')
        if _panel_binding and db.execute('SELECT 1 FROM setups WHERE id=?', (sid,)).fetchone():
            if db.execute('SELECT source_version,source_id,setup FROM source_bindings WHERE setup_id=?', (sid,)).fetchone() != _panel_binding:
                raise ValueError('EXISTING_SETUP_HAS_NO_MATCHING_PANEL_BINDING')
        db.execute('INSERT OR IGNORE INTO setups VALUES (?,?)', (sid, definition))
        if _panel_binding:
            db.execute('INSERT OR IGNORE INTO source_bindings VALUES (?,?,?,?)', (sid, *_panel_binding))

        if _case_binding:
            db.execute('INSERT OR IGNORE INTO case_bindings VALUES (?,?,?)', (sid, *_case_binding))
            if db.execute('SELECT case_id,input_sha256 FROM case_bindings WHERE setup_id=?', (sid,)).fetchone() != _case_binding:
                raise ValueError('Conflicting source binding')
        db.execute('INSERT OR IGNORE INTO events(setup_id,event_key,at_ms,state,body) VALUES (?,?,?,?,?)',
                   (sid, 'discovery', cutoff, 'DISCOVERED', encode({'research_only': True})))
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK')
        raise
    return sid


def observe(db, sid, bars, source_hash, *, as_of_ms, mode):
    """Legacy raw bars cannot establish instrument identity or source provenance."""
    if mode == 'LIVE':
        raise ValueError('Live monitoring is unavailable until source identity and freshness are verified')
    raise ValueError('UNVERIFIED_RAW_BARS: use a pinned historical case')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='Dedicated local filesystem runtime directory')
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('init')
    actions.add_parser('list')
    add = actions.add_parser('add'); add.add_argument('definition', type=Path)
    tick = actions.add_parser('tick'); tick.add_argument('setup_id'); tick.add_argument('bars', type=Path)
    tick.add_argument('--as-of-ms', required=True, type=int); tick.add_argument('--mode', required=True, choices=['HISTORICAL', 'LIVE'])
    verified_add = actions.add_parser('case-add'); verified_add.add_argument('case_id'); verified_add.add_argument('definition', type=Path)
    verified_tick = actions.add_parser('case-tick'); verified_tick.add_argument('setup_id'); verified_tick.add_argument('--as-of-ms', required=True, type=int)
    expiry = actions.add_parser('expire'); expiry.add_argument('setup_id'); expiry.add_argument('--as-of-ms', required=True, type=int)
    history = actions.add_parser('history'); history.add_argument('setup_id')
    backup = actions.add_parser('backup'); backup.add_argument('destination', type=Path)
    args = parser.parse_args()
    db = connect(args.root)
    try:
        if args.action == 'init':
            result = {'schema': db.execute('PRAGMA user_version').fetchone()[0], 'status': 'INITIALIZED'}
        elif args.action == 'add':
            result = {'setup_id': create(db, json.loads(args.definition.read_text()))}
        elif args.action == 'tick':
            raw = args.bars.read_bytes()
            observe(db, args.setup_id, json.loads(raw), hashlib.sha256(raw).hexdigest(), as_of_ms=args.as_of_ms, mode=args.mode)
            result = {'status': 'PROCESSED'}
        elif args.action == 'case-add':
            from trading_lab.case_monitor import create_case_setup
            result = {'setup_id': create_case_setup(db, json.loads(args.definition.read_text()), args.case_id)}
        elif args.action == 'case-tick':
            from trading_lab.case_monitor import observe_case
            observe_case(db, args.setup_id, as_of_ms=args.as_of_ms)
            result = {'status': 'PROCESSED_HISTORICAL_ONLY'}
        elif args.action == 'expire':
            from trading_lab.case_monitor import expire
            expire(db, args.setup_id, args.as_of_ms)
            result = {'status': 'RECONCILED'}
        elif args.action == 'history':
            result = [dict(seq=r[0], at_ms=r[1], state=r[2], body=json.loads(r[3])) for r in db.execute(
                'SELECT seq,at_ms,state,body FROM events WHERE setup_id=? ORDER BY seq', (args.setup_id,))]
        elif args.action == 'list':
            result = [dict(setup_id=r[0], definition=json.loads(r[1]), state=r[2]) for r in db.execute(
                'SELECT s.id,s.definition,e.state FROM setups s JOIN events e ON e.seq='
                '(SELECT MAX(seq) FROM events WHERE setup_id=s.id) ORDER BY s.id')]
        else:
            if args.destination.exists():
                raise ValueError('Backup destination already exists')
            destination = sqlite3.connect(args.destination)
            try:
                db.backup(destination)
            finally:
                destination.close()
            result = {'backup': str(args.destination)}
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == '__main__':
    main()
