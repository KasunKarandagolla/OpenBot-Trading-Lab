import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trading_lab.case_monitor import available_bars, create_case_setup, expire, load_case, observe_case
from trading_lab.watchlist import connect, create, observe


class CaseMonitorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(self.temp.name)
        self.case, self.digest = load_case('B01')
        self.bars = self.case['numeric']['5m']['bars']
        self.cutoff = self.bars[299][6] + 1
        self.definition = dict(symbol=self.case['symbol'], venue=self.case['venue'], direction='LONG',
            family='SWEEP_RECLAIM', source_cutoff_ms=self.cutoff,
            source_sha256=self.case['numeric']['5m']['bars_sha256'], level=.716,
            invalidation=.70, expires_ms=self.cutoff+8*300000,
            hypothesis='Reclaim of prior research level', opposition='Acceptance lower',
            confirmation='Close above level after excursion', feature_version='case-monitor-v1')

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_untrusted_raw_bars_cannot_create_observation(self):
        sid = create(self.db, self.definition)
        with self.assertRaisesRegex(ValueError, 'EXISTING_SETUP_HAS_NO_MATCHING_SOURCE_BINDING'):
            create_case_setup(self.db, self.definition, 'B01')
        with self.assertRaisesRegex(ValueError, 'UNVERIFIED_RAW_BARS'):
            observe(self.db, sid, [self.bars[300]], 'a'*64, as_of_ms=self.bars[300][6]+1, mode='HISTORICAL')
        with self.assertRaisesRegex(ValueError, 'UNBOUND_LEGACY_SETUP'):
            observe_case(self.db, sid, as_of_ms=self.bars[300][6]+1)
        with self.assertRaisesRegex(ValueError, 'Live monitoring is unavailable'):
            observe(self.db, sid, [self.bars[300]], 'a'*64, as_of_ms=self.bars[300][6]+1, mode='LIVE')

    def test_wrong_source_symbol_cutoff_and_future_rejected(self):
        for change in (dict(symbol='BTCUSDT'), dict(source_sha256='a'*64),
                       dict(source_cutoff_ms=self.bars[2][6]+1)):
            with self.assertRaises(ValueError):
                create_case_setup(self.db, dict(self.definition, **change), 'B01')
        sid = create_case_setup(self.db, self.definition, 'B01')
        with self.assertRaisesRegex(ValueError, 'CUTOFF'):
            observe_case(self.db, sid, as_of_ms=self.case['cutoff_ms']+1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 1)

    def test_real_case_replay_restart_idempotence_and_expiry_without_bar(self):
        sid = create_case_setup(self.db, self.definition, 'B01')
        observe_case(self.db, sid, as_of_ms=self.bars[300][6]+1)
        observe_case(self.db, sid, as_of_ms=self.bars[300][6]+1)
        self.db.close(); self.db = connect(self.temp.name)
        states = [r[0] for r in self.db.execute('SELECT state FROM events WHERE setup_id=? ORDER BY seq', (sid,))]
        self.assertEqual(states, ['DISCOVERED', 'TRIGGER_CANDIDATE'])
        expire(self.db, sid, self.definition['expires_ms'])
        expire(self.db, sid, self.definition['expires_ms'])
        self.assertEqual(self.db.execute('SELECT state FROM events ORDER BY seq DESC LIMIT 1').fetchone()[0], 'EXPIRED')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 3)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('DELETE FROM events')

    def test_multiple_opposing_hypotheses_and_backup(self):
        a = create_case_setup(self.db, self.definition, 'B01')
        other = dict(self.definition, direction='SHORT', invalidation=.73, hypothesis='Rejection')
        b = create_case_setup(self.db, other, 'B01')
        self.assertNotEqual(a, b)
        observe_case(self.db, a, as_of_ms=self.bars[301][6]+1)
        observe_case(self.db, b, as_of_ms=self.bars[301][6]+1)
        path = Path(self.temp.name) / 'backup.sqlite3'
        output = sqlite3.connect(path); self.db.backup(output); output.close()
        restored = sqlite3.connect(path)
        self.assertEqual(restored.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(restored.execute('SELECT COUNT(*) FROM case_bindings').fetchone()[0], 2)
        restored.close()

    def test_known_pins_cover_casebook(self):
        for i in range(1, 13):
            case, digest = load_case(f'B{i:02d}')
            self.assertEqual(len(digest), 64)
            self.assertEqual(case['execution_authority'], 'NONE')

    def test_changed_case_input_is_rejected_before_replay(self):
        root = Path(self.temp.name) / 'altered'
        target = root / 'evidence/skills-v2/20261107/casebook/agent-inputs/B01'
        target.mkdir(parents=True)
        (target / 'input.json').write_text(json.dumps(self.case))
        with patch('trading_lab.case_monitor.ROOT', root):
            with self.assertRaisesRegex(ValueError, 'CASE_INPUT_HASH_MISMATCH'):
                load_case('B01')

    def test_schema_one_migrates_without_rewriting_legacy_events(self):
        sid = create(self.db, self.definition)
        before = self.db.execute('SELECT seq,setup_id,event_key,at_ms,state,body FROM events').fetchall()
        self.db.close()
        self.db = sqlite3.connect(Path(self.temp.name) / 'watchlist.sqlite3')
        self.db.execute('DROP TRIGGER case_bindings_no_delete')
        self.db.execute('DROP TRIGGER case_bindings_no_update')
        self.db.execute('DROP TABLE case_bindings')
        self.db.execute('PRAGMA user_version=1')
        self.db.commit(); self.db.close()
        self.db = connect(self.temp.name)
        self.assertEqual(self.db.execute('PRAGMA user_version').fetchone()[0], 2)
        self.assertEqual(self.db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(self.db.execute('SELECT seq,setup_id,event_key,at_ms,state,body FROM events').fetchall(), before)
        with self.assertRaisesRegex(ValueError, 'UNBOUND_LEGACY_SETUP'):
            observe_case(self.db, sid, as_of_ms=self.bars[300][6] + 1)

    def test_replay_does_not_examine_later_prices_for_state(self):
        a = create_case_setup(self.db, self.definition, 'B01')
        when = self.bars[301][6] + 1
        observe_case(self.db, a, as_of_ms=when)
        rows = self.db.execute('SELECT at_ms,body FROM events WHERE setup_id=? ORDER BY seq', (a,)).fetchall()
        self.assertTrue(all(at <= when for at, _ in rows))
        self.assertNotIn('bar_sha256', json.loads(rows[0][1]))
        self.assertEqual(len(rows), 3)

    def test_future_bad_candle_does_not_change_prior_prefix_validation(self):
        bars = self.bars[:302] + [[self.bars[302][0], 'bad future']]
        prefix = available_bars(bars, self.bars[301][6] + 1)
        self.assertEqual(len(prefix), 302)
        with self.assertRaises(ValueError):
            available_bars(bars, self.bars[302][6] + 1)


if __name__ == '__main__':
    unittest.main()
