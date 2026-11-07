import json
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from trading_lab.watchlist import connect, create, observe, encode


class WatchlistTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(self.temp.name)
        self.definition = dict(symbol='BTCUSDT', venue='BINANCE_PUBLIC_USDM', direction='LONG',
            family='HTF_REACTION', source_cutoff_ms=300000, source_sha256='a'*64,
            level=100, invalidation=90, expires_ms=1800000, hypothesis='support',
            opposition='breakdown', confirmation='reclaim', feature_version='v1')
        self.sid = create(self.db, self.definition)

    def tearDown(self):
        self.db.close(); self.temp.cleanup()

    def bar(self, start, close):
        return [start, '100', str(max(101, close)), str(min(99, close)), str(close), '1', start+299999, '100', 1, '0.5', '50', '0']

    def update(self, bars, as_of=1500000):
        observe(self.db, self.sid, bars, 'b'*64, as_of_ms=as_of, mode='HISTORICAL')

    def test_restart_idempotence_and_multiple_hypotheses(self):
        self.update([self.bar(300000, 100)])
        self.update([self.bar(300000, 100)])
        other = dict(self.definition, direction='SHORT', invalidation=110, hypothesis='rejection')
        self.assertNotEqual(self.sid, create(self.db, other))
        self.db.close(); self.db = connect(self.temp.name)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM setups').fetchone()[0], 2)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM events WHERE setup_id=?', (self.sid,)).fetchone()[0], 2)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('DELETE FROM events')

    def test_gap_future_and_changed_bar_rollback(self):
        with self.assertRaises(ValueError): self.update([self.bar(300000, 100), self.bar(900000, 100)])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 1)
        with self.assertRaises(ValueError): self.update([self.bar(300000, 100)], as_of=599999)
        self.update([self.bar(300000, 100)])
        with self.assertRaises(ValueError): self.update([self.bar(300000, 99)])

    def test_terminal_and_backup(self):
        self.update([self.bar(300000, 89)])
        with self.assertRaises(ValueError): self.update([self.bar(600000, 100)])
        path = Path(self.temp.name) / 'backup.sqlite3'
        out = sqlite3.connect(path); self.db.backup(out); out.close()
        restored = sqlite3.connect(path)
        self.assertEqual(restored.execute('SELECT state FROM events ORDER BY seq DESC LIMIT 1').fetchone()[0], 'INVALIDATED')
        restored.close()

    def test_existing_sealed_historical_bars_replay_after_restart(self):
        path = Path(__file__).resolve().parents[1] / 'evidence/skills-v2/20261107/casebook/agent-inputs/B01'
        raw = (path / 'input.json').read_bytes()
        seal = json.loads((path / 'decision-seal.json').read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), seal['input_sha256'])
        case = json.loads(raw); evidence = case['numeric']['5m']; bars = evidence['bars']
        self.assertEqual(hashlib.sha256(encode(bars).encode()).hexdigest(), evidence['bars_sha256'])
        past = bars[276:300]; future = bars[300:312]
        definition = dict(self.definition, symbol=case['symbol'], source_cutoff_ms=past[-1][6]+1,
                          source_sha256=evidence['bars_sha256'], level=max(float(b[2]) for b in past),
                          invalidation=min(float(b[3]) for b in past), expires_ms=past[-1][6]+1+13*300000)
        sid = create(self.db, definition)
        observe(self.db, sid, future, 'c'*64, as_of_ms=future[-1][6]+1, mode='HISTORICAL')
        self.db.close(); self.db = connect(self.temp.name)
        states = [r[0] for r in self.db.execute('SELECT state FROM events WHERE setup_id=? ORDER BY seq', (sid,))]
        self.assertEqual(len(states), 13)
        self.assertIn('APPROACHING_ZONE', states)
        self.assertIn('WATCHING', states)

    def test_live_feed_is_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'Live monitoring is unavailable'):
            observe(self.db, self.sid, [self.bar(300000, 100)], 'b'*64, as_of_ms=600000, mode='LIVE')

    def test_recovery_references_match_their_manifest(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / 'integrations/openbot/skills/recovery-reference/mapping.json').read_text())
        self.assertEqual(len(manifest['assignments']), 27)
        for item in manifest['assignments']:
            for path_key, sha_key in [('original', 'original_sha256'), ('v2', 'v2_sha256')]:
                self.assertEqual(hashlib.sha256((root / item[path_key]).read_bytes()).hexdigest(), item[sha_key])
