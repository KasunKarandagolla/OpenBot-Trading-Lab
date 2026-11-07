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
    root = Path(root).expanduser().resolve()
    if str(root).startswith('/mnt/'):
        raise ValueError('Choose a local Linux filesystem for SQLite WAL, not /mnt')
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / 'watchlist.sqlite3', isolation_level=None, timeout=10)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version not in (0, 1):
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
    return db


def create(db, data):
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
        db.execute('INSERT OR IGNORE INTO setups VALUES (?,?)', (sid, definition))
        db.execute('INSERT OR IGNORE INTO events(setup_id,event_key,at_ms,state,body) VALUES (?,?,?,?,?)',
                   (sid, 'discovery', cutoff, 'DISCOVERED', encode({'research_only': True})))
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK')
        raise
    return sid


def observe(db, sid, bars, source_hash, *, as_of_ms, mode):
    """Process strictly contiguous, completed 5-minute bars; never infer an entry."""
    if mode == 'LIVE':
        raise ValueError('Live monitoring is unavailable until source identity and freshness are verified')
    if (not re.fullmatch('[0-9a-f]{64}', source_hash) or not bars or type(as_of_ms) is not int
            or mode != 'HISTORICAL'):
        raise ValueError('Missing source or bars')
    db.execute('BEGIN IMMEDIATE')
    try:
        row = db.execute('SELECT definition FROM setups WHERE id=?', (sid,)).fetchone()
        if not row:
            raise ValueError('Unknown setup')
        data = json.loads(row[0])
        prior = db.execute('SELECT at_ms,state FROM events WHERE setup_id=? ORDER BY seq DESC LIMIT 1', (sid,)).fetchone()
        previous_open = None
        for bar in bars:
            if (not isinstance(bar, list) or len(bar) != 12 or type(bar[0]) is not int or type(bar[6]) is not int
                    or bar[0] % 300000 or bar[6] != bar[0] + 299999
                    or (previous_open is not None and bar[0] != previous_open + 300000)):
                raise ValueError('Malformed, duplicate or gapped bars')
            previous_open = bar[0]
            op, high, low, close = map(float, bar[1:5])
            if not all(math.isfinite(x) and x > 0 for x in (op, high, low, close)) or high < max(op, low, close) or low > min(op, high, close):
                raise ValueError('Invalid OHLC')
            at = bar[6] + 1
            if at > as_of_ms:
                raise ValueError('Incomplete or future bar')
            if at <= data['source_cutoff_ms']:
                raise ValueError('Bar does not follow discovery')
            key = 'bar:' + str(at)
            bar_hash = hashlib.sha256(encode(bar).encode()).hexdigest()
            old = db.execute('SELECT body FROM events WHERE setup_id=? AND event_key=?', (sid, key)).fetchone()
            if old:
                if json.loads(old[0])['bar_sha256'] != bar_hash:
                    raise ValueError('Completed bar changed')
                continue
            if prior[1] in ('EXPIRED', 'INVALIDATED') or at != prior[0] + 300000:
                raise ValueError('Terminal state or missing bar')
            if at >= data['expires_ms']:
                state = 'EXPIRED'
            elif ((data['direction'] == 'LONG' and close <= float(data['invalidation'])) or
                  (data['direction'] == 'SHORT' and close >= float(data['invalidation']))):
                state = 'INVALIDATED'
            elif abs(close / float(data['level']) - 1) <= .005:
                state = 'APPROACHING_ZONE'
            else:
                state = 'WATCHING'
            body = encode({'bar_sha256': bar_hash, 'source_sha256': source_hash, 'close': close, 'mode': mode,
                           'note': 'Monitoring observation only; no trade trigger.'})
            db.execute('INSERT INTO events(setup_id,event_key,at_ms,state,body) VALUES (?,?,?,?,?)',
                       (sid, key, at, state, body))
            prior = (at, state)
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='Dedicated local filesystem runtime directory')
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('init')
    actions.add_parser('list')
    add = actions.add_parser('add'); add.add_argument('definition', type=Path)
    tick = actions.add_parser('tick'); tick.add_argument('setup_id'); tick.add_argument('bars', type=Path)
    tick.add_argument('--as-of-ms', required=True, type=int); tick.add_argument('--mode', required=True, choices=['HISTORICAL', 'LIVE'])
    history = actions.add_parser('history'); history.add_argument('setup_id')
    backup = actions.add_parser('backup'); backup.add_argument('destination', type=Path)
    args = parser.parse_args()
    db = connect(args.root)
    try:
        if args.action == 'init':
            result = {'schema': 1, 'status': 'INITIALIZED'}
        elif args.action == 'add':
            result = {'setup_id': create(db, json.loads(args.definition.read_text()))}
        elif args.action == 'tick':
            raw = args.bars.read_bytes()
            observe(db, args.setup_id, json.loads(raw), hashlib.sha256(raw).hexdigest(), as_of_ms=args.as_of_ms, mode=args.mode)
            result = {'status': 'PROCESSED'}
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
