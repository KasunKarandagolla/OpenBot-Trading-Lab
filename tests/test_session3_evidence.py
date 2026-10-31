"""Recorded actual-engine invariants and offline reproduction contracts."""
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
sys.path.insert(0,'/lab/scripts')
from session3_common import *
from economics3 import compare
from opportunity3 import validate_report
from orderflow3 import aggregate

class Recorded(unittest.TestCase):
 def test_actual_native_trades_risk_ledgers_and_common_window(self):
  for cid in ['s3-development-v1','s3-transfer-v1']:
   c=cohort(cid);out=destination(cid)
   for name in NAMES:
    p=out/'native-results'/(name+'.json')
    if not p.exists():self.fail('required actual native result missing: '+cid+' '+name)
    native=read(p)['strategy'][name];trades=native['trades']
    self.assertEqual(sorted(native['pairlist']),sorted(c['pairs']))
    self.assertEqual(pd.Timestamp(native['backtest_start']).strftime('%Y%m%d'),c['evaluation_timerange'].split('-')[0])
    ledger=pd.read_csv(out/'trade-ledgers'/(name+'.csv'))
    self.assertEqual(len(ledger),len(trades));self.assertAlmostEqual(float(ledger.profit_abs.sum()),sum(t['profit_abs'] for t in trades))
    for t in trades:
     self.assertEqual(t['leverage'],1.);self.assertLessEqual(t['stake_amount'],25.);self.assertGreater(t['stake_amount'],0.)
     self.assertAlmostEqual(t['fee_open'],.0006);self.assertAlmostEqual(t['fee_close'],.0006)
     self.assertTrue(t['stop_loss_abs']>t['open_rate'] if t['is_short'] else t['stop_loss_abs']<t['open_rate'])
    active=[t for t in trades if t['trade_duration']>0]
    for t in active:
     concurrent=[r for r in active if pd.Timestamp(r['open_date'])<=pd.Timestamp(t['open_date'])<pd.Timestamp(r['close_date'])]
     self.assertLessEqual(len(concurrent),2);self.assertEqual(len(concurrent),len({r['pair'] for r in concurrent}))
   self.assertGreater(len(read(out/'native-results/StructureAwareSweepV1.json')['strategy']['StructureAwareSweepV1']['trades']),0)
 def test_compare_offline_and_deterministic(self):
  cid='s3-development-v1';path=destination(cid)/'economic-comparison.json'
  with patch('subprocess.run',side_effect=AssertionError('no execution')),patch('pandas.read_feather',side_effect=AssertionError('no candles')):
   a=compare(cid);before=path.read_bytes();b=compare(cid);self.assertEqual(before,path.read_bytes());self.assertEqual(a,b)
  for name,m in a['strategies'].items():self.assertLess(abs(m['reconciliation_residual_usdt']),1e-5)
 def test_actual_asof_accept_reject_bounded_and_unknown(self):
  a=read(OUT/'opportunity-sample.json');self.assertEqual(a['setup']['decision'],'ACCEPT');validate_report(a)
  for r in read(OUT/'opportunity-rejections.json'):self.assertEqual(r['setup']['decision'],'REJECT');validate_report(r)
  bad=copy.deepcopy(a);bad['source']['status']='UNKNOWN'
  with self.assertRaises(ValueError):validate_report(bad)
  bad=copy.deepcopy(a);bad['provenance']['features_known_at_utc']='2099-01-01T00:00:00Z'
  with self.assertRaises(ValueError):validate_report(bad)
 def test_preserved_data_and_warmup(self):
  from data_session3 import verify
  m=verify('s3-development-v1');self.assertEqual(m['total_bytes'],1201184);self.assertTrue(all(r['matches_session2'] for r in m['files']));self.assertEqual(m['warmup_hours'],240)
  from engine3 import arguments
  with self.assertRaisesRegex(ValueError,'preserved'):arguments('download-data','s3-development-v1',NAMES[0])
  from data_session3 import acquire
  with self.assertRaisesRegex(ValueError,'future data'):acquire('s3-prospective-v1')

class Orderflow(unittest.TestCase):
 def test_sign_units_dedup_future_and_unknown(self):
  r={'id':'1','contract':'BTC_USDT','create_time':1767225600,'price':'100','size':'2'};s=r|{'id':'2','size':'-3'};at=pd.Timestamp('2026-01-01T00:00:01Z')
  m=aggregate([r,s,r],.0001,at,True);self.assertAlmostEqual(m['signed_delta_btc'],-.0001);self.assertAlmostEqual(m['buy_aggressor_btc'],.0002);self.assertEqual(m['duplicate_ids'],1)
  self.assertIsNone(aggregate([r,s],.0001,at)['signed_delta_btc'])
  self.assertEqual(aggregate([r|{'create_time':1767225620}],.0001,at)['distinct_available_prints'],0)
  with self.assertRaises(ValueError):aggregate([r,r|{'size':'9'}],.0001,at)
 def test_real_capture_refuses_completeness_or_aggressor_claim(self):
  m=read(OUT/'orderflow-proof.json');self.assertGreater(m['raw_rows'],0);self.assertEqual(m['coverage_status'],'PARTIAL_COVERAGE');self.assertEqual(m['summary']['side_status'],'AGGRESSOR_SIDE_UNKNOWN');self.assertFalse(m['strategy_feature_eligible']);self.assertIsNone(m['summary']['signed_delta_btc'])
if __name__=='__main__':unittest.main()
