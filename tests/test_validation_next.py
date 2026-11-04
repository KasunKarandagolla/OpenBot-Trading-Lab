"""Contract, source, causal and native lifecycle regression tests; no synthetic PnL."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validation_next_common import *
from trade_contract import parent_target,audit,economics
import pandas as pd
from ValidationPolicyR1 import ValidationPolicyR1
from freqtrade.enums import RunMode,CandleType

def plan(side='long'):
 s=1 if side=='long' else -1
 return dict(side=side,recipe='continuation',reference=100.,stop=100-s,target=100+3*s,atr_at_signal=1.,available_at='2026-01-20T12:15:00+00:00',expires_at='2026-01-20T12:20:00+00:00',max_hold_hours=8)
class Contract(unittest.TestCase):
 def test_parent_objective_both_sides_preserves_risk_and_frozen_input(self):
  for side,s in [('long',1),('short',-1)]:
   g=plan(side);original=copy.deepcopy(g);row=pd.Series(dict(date=pd.Timestamp('2026-01-20T12:00Z'),prior_day_high=102.5 if s==1 else 110,prior_day_low=97.5 if s==-1 else 90,prior_session_high=102.7,prior_session_low=97.3))
   out=parent_target(g,row,.01)
   self.assertEqual(g,original);self.assertEqual(out['stop'],g['stop']);self.assertEqual(out['reference'],g['reference']);self.assertEqual(out['target'],100+s*2.5)
   self.assertEqual(audit(out,.01)['errors'],[])
 def test_too_near_or_future_objective_never_invents_net_reward(self):
  g=plan();r=pd.Series(dict(date=pd.Timestamp('2026-01-20T12:00Z'),prior_day_high=101.,prior_session_high=110.))
  self.assertEqual(parent_target(g,r,.01)['target'],103.)
  bad=g|dict(objective_evidence={'known_at':'2026-01-21T00:00Z'})
  self.assertIn('FUTURE_OBJECTIVE',audit(bad,.01)['errors'])
 def test_reprice_stale_rr_is_detected_and_recomputed_without_double_fee(self):
  g=plan();g.update(economics(g));old=g['after_cost_rr'];g['reference']=99.85
  result=audit(g,.01)
  self.assertTrue(result['stored_economics_stale']);self.assertNotEqual(old,result['economics']['after_cost_rr'])
  self.assertAlmostEqual(result['economics']['modeled_loss_per_notional'],(99.85-99)/99.85+.0038)
 def test_invalid_sides_expiry_and_proxy_duplicate_audited(self):
  g=plan();g.update(stop=101,target=99,expires_at=g['available_at'])
  r=audit(g,.01);self.assertIn('STOP_WRONG_SIDE',r['errors']);self.assertIn('TARGET_WRONG_SIDE',r['errors']);self.assertIn('EXPIRY',r['errors'])
  g=plan();g['obstacles']=[dict(price=102.,source='prior_day_high',fidelity='CONFIRMED_CLOSED_BARS'),dict(price=102.001,source='vp2_poc',fidelity='OHLCV_PROXY')]
  self.assertEqual(len(audit(g,.01)['distinct_levels']),1)
 def test_strategy_refuses_other_modes_and_requires_explicit_scenario(self):
  for mode in [RunMode.LIVE,RunMode.DRY_RUN,RunMode.HYPEROPT]:
   s=ValidationPolicyR1(dict(runmode=mode,dry_run=True,validation_fixture_scenario=True,exchange={'name':'binance'},policy_leverage=1,max_open_trades=2,policy_notional_cap=25,candle_type_def=CandleType.FUTURES))
   with self.assertRaisesRegex(ValueError,'historical research only'):s.bot_start()
class Evidence(unittest.TestCase):
 def test_original_sources_and_all_prior_seals_preserved(self):
  self.assertEqual(verify_old()['changed'],[]);verify_sources()
  c=read(OUT/'frozen-control-verification.json');self.assertEqual(c['mismatches'],[]);self.assertEqual(c['missing'],[])
 def test_data_contracts_are_explicitly_unqualified_and_btc_cannot_fit_cap(self):
  m=read(ROOT/'research/validation_next/binance-fixture-markets.json');self.assertGreater(m['BTC/USDT:USDT']['limits']['cost']['min'],25)
  for c in read(OUT/'scenario-contracts.json').values():self.assertFalse(c['economic_qualified']);self.assertEqual(c['verification_scope'],'FIXTURE_SCHEMA_ONLY;NOT_HISTORICAL_VENUE')
 def test_every_target_correction_and_asof_clock_matches_original_opportunity(self):
  for partition in ['development','validation','holdout']:
   reg=WORK/partition/'plans/v4-transfer.json'
   if not reg.exists():continue
   old=read(reg);new=read(WORK/partition/'plans/parent-target.json')
   self.assertEqual(old.keys(),new.keys())
   for pair,rows in old.items():
    self.assertEqual(rows.keys(),new[pair].keys())
    for at,g in rows.items():
     n=new[pair][at];self.assertEqual((g['stop'],g['reference'],g['expires_at']),(n['stop'],n['reference'],n['expires_at']));self.assertEqual(audit(n,.000001)['errors'],[])
 def test_native_removal_is_terminal_at_five_minutes_with_detail(self):
  seen=0
  for p in (OUT/'native').glob('*detail5m*/order-audit.json'):
   for x in read(p)['terminal_events']:
    seen+=1;self.assertGreaterEqual(x['age_minutes'],5);self.assertEqual(x['age_minutes'],5);self.assertEqual(x['native_timeout'],5)
  self.assertGreater(seen,0,'real native timeout events required')
 def test_native_funding_retains_archived_millisecond_clocks(self):
  seen=0
  for p in (OUT/'native').glob('*exactclock/states.json'):
   for st in read(p):
    source=pd.read_feather(DATA/'binance/futures'/(slug(st['pair'])+'-1h-funding_rate.feather'))
    clocks=set(source.date.map(lambda x:x.isoformat()))
    for event in st['funding']:
     seen+=1;self.assertIn(event['at'],clocks)
  self.assertGreater(seen,0)
 def test_native_fills_never_exceed_cap_or_expiry(self):
  seen=0
  for p in (OUT/'native').glob('*/order-audit.json'):
   for o in read(p)['orders']:
    if o['is_entry'] and o['filled']:
     seen+=1;self.assertLessEqual(o['price']*o['filled'],25+1e-8)
     self.assertLess(pd.Timestamp(o['filled_at']),pd.Timestamp(o['plan_expires_at']))
  self.assertGreater(seen,0)
if __name__=='__main__':unittest.main()
