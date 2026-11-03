"""V3 source identities and the active candidate's execution boundary."""
import os
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from policy_common import ROOT,read,verify,sha

RUN=os.environ.get('POLICY_RUN_ID','policy-session3-001')

class PolicyEvidenceTests(unittest.TestCase):
    def test_current_source_seal(self):
        out,data,spec=verify(RUN)
        self.assertFalse(spec['persistent_paper_allowed']);self.assertFalse(spec['orders_allowed'])
        self.assertEqual(spec['candidate'],'PolicyManagedV3')
    def test_private_sources_are_exact_or_explicitly_unavailable(self):
        out,_,_=verify(RUN);m=read(out/'data-manifest.json')
        if any(not (ROOT/r['path']).exists() for r in m['files']):self.skipTest('New private dataset not restored; source identity cannot be checked')
        self.assertEqual(len(m['files']),20)
        for r in m['files']:self.assertEqual(sha(ROOT/r['path']),r['sha256'])
    def test_reserved_future_never_acquired(self):
        out,_,_=verify(RUN);m=read(out/'data-manifest.json')
        self.assertEqual(m['timerange'],'20260726-20261102')
        for r in m['files']:self.assertLess(r['last'],'2026-11-17')
    def test_candidate_remains_outside_persistent_paper_guard(self):
        from guard import validate
        cfg=read(ROOT/'configs/research.json');cfg['strategy']='PolicyManagedV3'
        with self.assertRaisesRegex(ValueError,'unknown strategy'):validate(cfg)
    def test_stopped_smoke_has_no_paper_or_exchange_orders(self):
        out,_,_=verify(RUN);r=read(out/'native-dryrun-smoke.json')
        self.assertTrue(r['passed']);self.assertEqual(r['db_orders'],0);self.assertFalse(r['forward_paper_fill_observed'])

    def test_release_export_has_exact_size_hash_and_read_only_schema(self):
        import jsonschema
        from foundation_report import validate_reader_content
        out,_,_=verify(RUN);p=out/'openbot-release/research-snapshot.json';m=read(out/'openbot-release/manifest.json')
        self.assertEqual(p.stat().st_size,m['bytes']);self.assertLessEqual(p.stat().st_size,1000000);self.assertEqual(sha(p),m['sha256'])
        obj=read(p);jsonschema.validate(obj,read(ROOT/'research/foundation/openbot.schema.json'));validate_reader_content(obj)
    def test_release_decision_trade_event_outcome_ids_join(self):
        out,_,_=verify(RUN);obj=read(out/'openbot-release/research-snapshot.json')
        ids={c['decision_id'] for c in obj['candidates']}
        self.assertEqual(obj['policy_contract']['strategy'],'PolicyFixedV3')
        self.assertFalse(obj['policy_contract']['persistent_paper_allowed'])
        outcomes={r['trade_uid']:r for r in obj['trade_outcomes']}
        for e in obj['position_events']:
            if e.get('decision_id'):self.assertIn(e['decision_id'],ids)
            if e.get('trade_uid'):self.assertIn(e['trade_uid'],outcomes)
        for r in outcomes.values():
            self.assertIn(r['decision_id'],ids);self.assertEqual(r['environment'],'NATIVE_BACKTEST_RESEARCH')
