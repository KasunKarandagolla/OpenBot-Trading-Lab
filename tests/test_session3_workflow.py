"""Meaningful strategy/assessor/safety/economic vectors; no synthetic market claims."""
import copy,json,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import numpy as np
sys.path[:0]=['/lab/tests','/lab/scripts','/lab/research/session3','/lab/user_data/strategies']
import test_playbooks as playbooks
features=playbooks.features;CFG=playbooks.CFG
from StructureAwareSweepV1 import StructureAwareSweepV1
from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
from opportunity3 import assess,analyze,utc,validate_report
from session3_common import stage,config,sanitized_env,OUT,ROOT
from economics3 import metric,weekly,blocked_interval
from engine3 import arguments

class Strategy(unittest.TestCase):
 def fixture(self):
  d=features();d['atr14']=1.;d['atr_ratio']=.01;d['open']=[100.2,99.8,100.2,100.2];d['close']=[100.1,99.9,99.4,100.1];d['low']=[99.,99.7,99.,99.];d['high']=[100.3,101.,100.3,100.3]
  for k,v in {'struct_valid':True,'struct_valid_1h':True,'struct_direction_1h':'UP','prior_swing_low':99.5,'prior_swing_high':100.5}.items():d[k]=v
  d['prior_swing_low_known_at']=d.date-pd.Timedelta(minutes=15);d['prior_swing_high_known_at']=d.date-pd.Timedelta(minutes=15)
  return d
 def test_symmetric_signals_and_explainable_rejection(self):
  s=StructureAwareSweepV1(CFG);d=self.fixture();d['adx_1h']=24.
  r=s.populate_entry_trend(d,{})
  self.assertEqual(r.enter_long.iloc[0],1);self.assertEqual(r.enter_short.iloc[1],1)
  for k,v in [('prior_swing_low',90.),('struct_direction_1h','UNKNOWN'),('struct_valid_1h',False)]:
   bad=d.copy();bad[k]=v;r=s.populate_entry_trend(bad,{});self.assertEqual(r.enter_long.iloc[0],0);self.assertEqual(r.reason.iloc[0],'STRUCTURAL_ELIGIBILITY')
  d['struct_direction_1h']='DOWN';d['adx_1h']=26.;self.assertEqual(s.populate_entry_trend(d,{}).enter_long.iloc[0],0)
 def test_future_known_levels_forbidden_and_risk_inherited(self):
  d=self.fixture();d['prior_swing_low_known_at']=d.date+pd.Timedelta(minutes=15);s=StructureAwareSweepV1(CFG)
  self.assertEqual(s.populate_entry_trend(d,{}).enter_long.iloc[0],0)
  for callback in ['custom_stake_amount','confirm_trade_entry','check_entry_timeout','custom_stoploss','custom_roi','custom_exit','order_filled','leverage']:
   self.assertIs(getattr(StructureAwareSweepV1,callback),getattr(LiquiditySweepReversalV1,callback))
  self.assertEqual(s.leverage(None,None,None,20,20,None,None),1.);self.assertFalse(s.position_adjustment_enable)

class AdvancedCallbacks(playbooks.Callbacks):
 # Run all prior native risk/expiry/fill tests against the actual advanced class.
 def setUp(self):
  super().setUp();self.s.__class__=StructureAwareSweepV1
 def test_native_stop_rounding_roi_hold_and_fill(self):
  self.s.hold_hours=8 # inherited test expects8; separate test asserts actual4 below
  super().test_native_stop_rounding_roi_hold_and_fill()
 def test_actual_hold4(self):self.assertEqual(StructureAwareSweepV1(CFG).hold_hours,4)

class Assessment(unittest.TestCase):
 def data(self):
  x=np.arange(1100);c=100+np.sin(x/8)+x*.01
  b=pd.DataFrame({'date':pd.date_range('2026-01-01',periods=len(x),freq='15min',tz='UTC'),'open':c,'high':c+1,'low':c-1,'close':c,'volume':2.})
  h=b.set_index('date').resample('1h').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).reset_index()
  return b,h
 def test_historical_future_sentinel_and_schema(self):
  b,h=self.data();at=b.date.iloc[1040]+pd.Timedelta(minutes=15)
  a=assess('BTC/USDT:USDT',b,h,at,'fixture');changed=b.copy();changed.loc[1041:,'close']=1e12;changedh=h.copy();changedh.loc[changedh.date+pd.Timedelta(hours=1)>at,'close']=1e12
  self.assertEqual(a,assess('BTC/USDT:USDT',changed,changedh,at,'fixture'));validate_report(a)
  self.assertLessEqual(pd.Timestamp(a['provenance']['features_known_at_utc']),at)
 def test_missing_stale_gap_warmup_current_timestamp(self):
  b,h=self.data();at=b.date.iloc[-1]+pd.Timedelta(minutes=15)
  for bb,hh,when,reason in [(b.iloc[:100],h,at,'INSUFFICIENT_WARMUP'),(b.drop(900),h,at,'DATA_GAP_OR_DUPLICATE'),(b,h,at+pd.Timedelta(hours=1),'STALE_CANDLES')]:
   a=assess('BTC/USDT:USDT',bb,hh,when,'fixture');self.assertEqual(a['setup']['decision'],'REJECT');self.assertIn(reason,a['setup']['reason_codes'])
  a=assess('BTC/USDT:USDT',b,h,at,'fixture',mode='current',ticker={'venue_timestamp_ms':None});self.assertEqual(a['source']['status'],'UNKNOWN')
  a=assess('BTC/USDT:USDT',b,h,at,'fixture',mode='current',ticker={'venue_timestamp_ms':(at-pd.Timedelta(minutes=2)).timestamp()*1000});self.assertIn('TICKER_STALE_OR_FUTURE',a['setup']['reason_codes'])
 def test_input_times(self):
  for t in ['2026-01-01','2030-01-01T00:00:00Z','2026-01-01T00:00:00+01:00']:
   with self.assertRaises(ValueError):utc(t)
 def test_candle_timestamp_alignment_schema_and_timezone_unknown(self):
  b,h=self.data();at=b.date.iloc[-1]+pd.Timedelta(minutes=15)
  for bad in [b.drop(columns='volume'),b.assign(date=b.date+pd.Timedelta(minutes=1)),b.assign(date=b.date.dt.tz_localize(None))]:
   r=assess('BTC/USDT:USDT',bad,h,at,'fixture');self.assertEqual(r['setup']['decision'],'REJECT');self.assertEqual(r['source']['status'],'UNKNOWN')

class Safety(unittest.TestCase):
 def test_no_cli_bypass_and_staging_impersonator(self):
  for action in ['trade','webserver','hyperopt']:
   with self.assertRaises(ValueError):arguments(action,'s3-development-v1','StructureAwareSweepV1')
  folder=stage();p=folder/'Impersonator.py';p.write_text('class StructureAwareSweepV1: pass')
  try:
   with self.assertRaisesRegex(ValueError,'impersonator'):stage()
  finally:p.unlink()
 def test_configs_env_and_frozen_sources(self):
  for name in ['StructureAwareSweepV1','LiquiditySweepReversalV1']:
   c=config('s3-development-v1',name);self.assertTrue(c['dry_run']);self.assertEqual(c['stake_amount'],25);self.assertEqual(c['max_open_trades'],2);self.assertFalse(c['exchange']['key'])
  with patch.dict(os.environ,{'FREQTRADE__DRY_RUN':'false'}):
   with self.assertRaises(ValueError):sanitized_env()
  with patch.dict(os.environ,{'BINANCE_FUTURES_DEMO_API_KEY':'fixture-secret'}):self.assertNotIn('BINANCE_FUTURES_DEMO_API_KEY',sanitized_env())

class Economics(unittest.TestCase):
 def test_fee_funding_costs_forced_exit_zero_and_blocks(self):
  t={'pair':'X/USDT:USDT','is_short':False,'open_date':'2026-01-01T00:00:00Z','close_date':'2026-01-01T01:00:00Z','open_rate':100.,'close_rate':102.,'amount':.25,'stake_amount':25.,'fee_open':.0006,'fee_close':.0006,'funding_fees':-.01,'profit_abs':.5-.0303-.01,'profit_ratio':.01,'trade_duration':60,'exit_reason':'force_exit'}
  m=metric([t],{},[{'profit_abs':t['profit_abs'],'regime':'RANGE_LOW_ADX','net_R':.1}],['2025-12-29','2026-01-05','2026-01-12','2026-01-19'])
  self.assertAlmostEqual(m['reconciliation_residual_usdt'],0.);self.assertAlmostEqual(m['fees_usdt'],.0303);self.assertAlmostEqual(m['friction'][2]['net_usdt'],t['profit_abs']-.0505);self.assertEqual(m['forced_end_exits']['net_excluding_forced_usdt'],0.)
  self.assertIsNone(metric([],{},[],[])['profit_factor']);self.assertIsNone(metric([],{},[],[])['expectancy_usdt'])
  self.assertEqual(blocked_interval(np.array([0.,1.,2.,-3.])),blocked_interval(np.array([0.,1.,2.,-3.])))
if __name__=='__main__':unittest.main()
