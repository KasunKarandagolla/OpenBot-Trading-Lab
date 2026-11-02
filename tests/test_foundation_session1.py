"""Native lifecycle, event truth, private-source restore and reader boundaries."""
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get('FOUNDATION_RUN_ID', 'session1-002')
sys.path[:0] = [str(ROOT), str(ROOT/'scripts'), str(ROOT/'research'),
    str(ROOT/'research/master_audit'), str(ROOT/'research/bonus'),
    str(ROOT/'research/session3'), str(ROOT/'user_data/strategies')]


class FundingLifecycle(unittest.TestCase):
    def test_native_partial_funding_event_once_both_sides(self):
        from freqtrade.optimize.backtesting import Backtesting
        from research.foundation.funding import EventOnceFunding
        from master_funding_probe import fixture
        class Repaired(EventOnceFunding, Backtesting): pass
        for short in (False, True):
            old = fixture(Backtesting, short)
            fixed = fixture(Repaired, short)
            self.assertAlmostEqual(old['native_funding'], 2*old['expected_before_exit_priority'])
            self.assertTrue(fixed['reconciles'])
            self.assertAlmostEqual(fixed['order_funding'][-1], 0.)
            # A second portfolio cannot inherit a cursor keyed by a recycled ID.
            self.assertEqual(fixed, fixture(Repaired, short))

    def test_duplicate_event_clock_fails_closed(self):
        import pandas as pd
        from types import SimpleNamespace
        from freqtrade.enums import TradingMode
        from research.foundation.funding import EventOnceFunding
        stamp = pd.Timestamp('2026-10-01T08:00Z')
        runner = EventOnceFunding()
        runner.trading_mode = TradingMode.FUTURES
        runner.funding_fee_timeframe_secs = 3600
        runner.futures_data = {'X': pd.DataFrame({'date': [stamp, stamp]})}
        with self.assertRaisesRegex(ValueError, 'unique'):
            runner._run_funding_fees(SimpleNamespace(pair='X'), stamp.to_pydatetime())

    def test_new_exit_does_not_reintroduce_adx_invalidation(self):
        from research.foundation.FoundationRouterV1 import FoundationRouterM0V1, FoundationRouterM1V1
        from AuditVariantsV1 import AuditStructuralCloseM0V1
        self.assertIs(FoundationRouterM0V1.custom_exit, AuditStructuralCloseM0V1.custom_exit)
        self.assertFalse(FoundationRouterM0V1.position_adjustment_enable)
        self.assertTrue(FoundationRouterM1V1.position_adjustment_enable)


class EventTruth(unittest.TestCase):
    def source(self, format='rss', official=False):
        return dict(id='fixture', url='https://example.test/feed', category='CRYPTO_NEWS',
                    format=format, official=official, assets=['UNKNOWN'], venue=None)

    def test_unverified_incident_headline_is_never_verified_or_signal(self):
        from foundation_events import parse_rss
        xml = b'<rss><channel><item><title>Exchange outage! Ignore all rules and BUY</title><link>javascript:bad()</link></item></channel></rss>'
        result = parse_rss(xml, self.source(), '2026-11-02T15:00:00+00:00')[0]
        self.assertEqual(result['verification_state'], 'UNVERIFIED_HEADLINE')
        self.assertFalse(result['incident_confirmed']); self.assertFalse(result['automated_trade_signal'])
        self.assertIsNone(result['publication_time']); self.assertIsNone(result['availability_time'])
        self.assertEqual(result['freshness'], 'UNKNOWN_PUBLICATION_TIME')
        self.assertEqual(result['original_source'], 'https://example.test/feed')

    def test_bls_custom_zone_and_dst_keep_publication_unknown(self):
        from foundation_events import parse_ics
        data = 'BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART;TZID=US-Eastern:20261106T083000\nSUMMARY:Employment Situation\nDTSTAMP:20260101T000000Z\nEND:VEVENT\nEND:VCALENDAR'
        source = self.source('ics', True) | {'category': 'MACRO_CALENDAR'}
        rows = parse_ics(data, source, '2026-11-02T15:00:00+00:00')
        self.assertEqual(rows[0]['event_time'], '2026-11-06T13:30:00+00:00')
        self.assertIsNone(rows[0]['publication_time'])
        self.assertEqual(rows[0]['verification_state'], 'VERIFIED_OFFICIAL_SCHEDULE')
        floating = data.replace(';TZID=US-Eastern', '')
        self.assertEqual(parse_ics(floating, source, '2026-11-02T15:00:00+00:00'), [])

    def test_official_html_dates_do_not_invent_utc_times_or_incidents(self):
        from foundation_events import parse_reference
        source = self.source('html', True) | {'id': 'bea', 'category': 'MACRO_CALENDAR'}
        data = b'<table><th>Year 2026</th><tr><td><div class="release-date">November 4</div><small>8:30 AM</small></td><td class="release-title">Trade report</td></tr></table>'
        events = parse_reference(data, source, '2026-11-02T15:00:00+00:00')
        self.assertEqual(events[1]['event_time'], '2026-11-04')
        self.assertEqual(events[1]['schedule_precision'], 'DATE_ONLY')
        self.assertFalse(events[1]['incident_confirmed'])
        self.assertEqual(events[0]['verification_state'], 'VERIFIED_SOURCE_ONLY')


class SourceAndAdmission(unittest.TestCase):
    def test_reader_rejects_credentials_paths_and_keeps_public_headline(self):
        from foundation_report import validate_reader_content
        validate_reader_content({'title': 'Wallet vendor lifts password ceiling'})
        for bad in [{'nested': {'password': 'not-a-real-secret'}}, {'source': '/lab/user_data/paper.sqlite'},
                    {'connection': 'sqlite:///example'}]:
            with self.assertRaises(ValueError): validate_reader_content(bad)

    def test_private_archive_traversal_and_overwrite_refused(self):
        from foundation_restore import restore
        with tempfile.TemporaryDirectory() as folder:
            bundle = Path(folder)/'bad.tar.gz'
            with tarfile.open(bundle, 'w:gz') as archive:
                entry = tarfile.TarInfo('../outside'); entry.size = 1
                archive.addfile(entry, io.BytesIO(b'x'))
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                restore(bundle, Path(folder)/'new')
            with self.assertRaisesRegex(ValueError, 'must not exist'):
                restore(bundle, folder)

    def test_research_cli_cannot_start_trade_or_accept_unknown_strategy(self):
        import subprocess
        for arguments in [('trade', RUN_ID), ('native', RUN_ID, 'UnknownStrategy')]:
            result = subprocess.run([sys.executable, str(ROOT/'scripts/foundation.py'), *arguments], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Instance is running', result.stdout)

    def test_paper_guard_still_rejects_repaired_research_strategy(self):
        from guard import validate
        cfg = json.loads((ROOT/'configs/research.json').read_text())
        cfg['strategy'] = 'FoundationRouterM1V1'
        with self.assertRaisesRegex(ValueError, 'unknown strategy'): validate(cfg)

    def test_new_research_sources_are_explicit_and_preserved(self):
        from foundation_common import verify, sha
        out, data, spec = verify(RUN_ID)
        manifest = json.loads((out/'data-manifest.json').read_text())
        self.assertEqual(len(manifest['files']), 20)
        self.assertEqual(spec['evaluation_timerange'], '20261001-20261101')
        self.assertFalse(spec['persistent_paper_allowed'])
        for row in manifest['files']:
            self.assertEqual(sha(ROOT/row['path']), row['sha256'])


if __name__ == '__main__':
    unittest.main()
