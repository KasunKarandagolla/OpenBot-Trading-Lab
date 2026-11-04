"""Focused causal and lifecycle regressions. Fixtures do not claim an economic edge."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from integrated_common import ROOT,OUT,read,sha
from market_reader import interpret,objective,reprice,continuation_failure
from integrated_five import first_response
from IntegratedPolicyR1 import IntegratedPolicyR1,IntegratedFiveMinuteR1
from test_setup import row,CLOCK
from freqtrade.enums import RunMode,CandleType

def context(**kw):
    values=dict(close=100.,open=99.8,low=99.5,high=100.2,known4h=CLOCK-pd.Timedelta(hours=4),direction_4h='UP',
        prior_swing_high=103.,swing_high_1h=106.,prior_vwap=100.)
    values.update(kw)
    return row(**values)

def opportunity():
    return dict(side='long',recipe='continuation',setup_id='frozen-1',decision_id='frozen-1',setup_armed_at=CLOCK.isoformat(),
        boundary=100.,stop=99.,target=103.,atr_at_signal=1.,reference=100.,signal_close=100.,available_at=CLOCK.isoformat(),
        expires_at=(CLOCK+pd.Timedelta(minutes=5)).isoformat(),deviation_fraction=.0015,max_hold_hours=8)

def bars():
    return pd.DataFrame([dict(date=CLOCK+pd.Timedelta(minutes=5*i),open=o,high=h,low=l,close=c,previous_high=p,previous_low=99.7)
        for i,(o,h,l,c,p) in enumerate([(99.8,100.1,99.6,99.9,100.2),(99.9,100.4,99.8,100.3,100.1),(100.3,101.,100.2,100.9,100.4)])])

class IntegratedBehavior(unittest.TestCase):
    def test_context_retains_contradicting_ema_without_automatic_veto(self):
        r=context(ema20_1h=98.,ema50_1h=101.)
        result=interpret(r,'long','continuation',100,99,.01)
        self.assertEqual(result['status'],'QUALIFIED_RESEARCH')
        self.assertIn('HOURLY_EMA_CONTRADICTS',result['contradicting'])
        self.assertEqual(result['execution_permission'],'NONE')

    def test_opposed_parent_and_unknown_source_abstain(self):
        self.assertEqual(interpret(context(direction_4h='DOWN'),'long','continuation',100,99)['status'],'NO_TRADE')
        self.assertEqual(interpret(context(setup_valid=False),'long','continuation',100,99)['status'],'UNKNOWN')
        self.assertEqual(interpret(context(known4h=CLOCK+pd.Timedelta(hours=4)),'long','continuation',100,99)['status'],'UNKNOWN')
        self.assertEqual(interpret(context(date_1h=CLOCK),'long','continuation',100,99)['status'],'UNKNOWN')

    def test_missing_boolean_flags_do_not_become_truthy(self):
        for flag in ('setup_valid','map4h_ready'):
            for value in (None,float('nan')):
                self.assertEqual(interpret(context(**{flag:value}),'long','continuation',100,99)['status'],'UNKNOWN')

    def test_local_reversal_is_not_named_parent_trend(self):
        result=interpret(context(struct_direction_1h='DOWN',direction_4h='DOWN'),'long','reversal',100,99)
        self.assertEqual(result['primary_hypothesis'],'reversal')
        self.assertEqual(result['alternative'],'LOCAL_CORRECTION_IN_PARENT_TREND')
        self.assertIn('1H_STRUCTURE_NOT_ALIGNED',result['contradicting'])

    def test_first_obstacle_veto_and_future_pivot_unavailable(self):
        r=context(prior_swing_high=100.2)
        self.assertEqual(objective(r,'long',100,99)[1],'FIRST_OBSTACLE_INSUFFICIENT_AFTER_COST_REWARD')
        r['prior_swing_high_known_at']=CLOCK+pd.Timedelta(hours=1)
        first,_=objective(r,'long',100,99)
        self.assertNotEqual(first['price'],100.2)

    def test_passive_price_keeps_stop_target_and_expiry(self):
        g=opportunity();original=copy.deepcopy(g)
        p=reprice(g,99.85,'PASSIVE')
        self.assertEqual(g,original);self.assertEqual(p['reference'],99.85)
        self.assertEqual((p['stop'],p['target'],p['expires_at']),(99.,103.,g['expires_at']))
        self.assertIsNone(reprice(g,98.9,'INVALID_BEYOND_STOP'))

    def test_first_completed_five_response_and_prefix_invariance(self):
        f=bars();g=opportunity()
        p,_=first_response(f,g)
        self.assertEqual(p['available_at'],(CLOCK+pd.Timedelta(minutes=10)).isoformat())
        self.assertIsNone(first_response(f.iloc[:1],g)[0])
        self.assertEqual(first_response(f.iloc[:2],g)[0],p)
        f.loc[2,'high']=10000.
        self.assertEqual(first_response(f,g)[0],p)
        self.assertEqual(g['boundary'],100.)

    def test_five_source_gap_expiry_and_stop_reject(self):
        self.assertEqual(first_response(bars().iloc[1:],opportunity())[1],'SOURCE_GAP')
        f=bars();f['date']+=pd.Timedelta(hours=2)
        self.assertIsNone(first_response(f,opportunity())[0])
        f=bars();f.loc[0,'low']=98.9
        self.assertEqual(first_response(f,opportunity())[1],'PROTECTED_EXTREME_FAILED')

    def test_thesis_requires_zone_failure_and_opposing_structure(self):
        g=opportunity();q=pd.DataFrame([dict(close=99.7,struct_direction='UP'),dict(close=99.7,struct_direction='UP')])
        self.assertFalse(continuation_failure(g,q));q.loc[1,'struct_direction']='DOWN'
        self.assertTrue(continuation_failure(g,q));q.loc[0,'close']=100.
        self.assertFalse(continuation_failure(g,q))

    def test_hard_protection_without_optional_data_or_store(self):
        s=IntegratedPolicyR1(dict(runmode=RunMode.BACKTEST,dry_run=True,candle_type_def=CandleType.FUTURES,integrated_structural_exit=True))
        t=Mock();t.is_short=False;t.open_date_utc=CLOCK.to_pydatetime()
        g=opportunity();t.get_custom_data.side_effect=lambda key,default=None:g if key=='policy_plan' else {}
        self.assertEqual(s.custom_exit('ETH/USDT:USDT',t,CLOCK.to_pydatetime(),98.,-.02),'protective_level_breach')

    def test_research_mode_and_risk_bound_refusal(self):
        for mode in [RunMode.LIVE,RunMode.DRY_RUN,RunMode.HYPEROPT]:
            s=IntegratedPolicyR1(dict(runmode=mode,dry_run=True,max_open_trades=2,policy_notional_cap=25,candle_type_def=CandleType.FUTURES))
            with self.assertRaisesRegex(ValueError,'historical research only'): s.bot_start()
        s=IntegratedPolicyR1(dict(max_open_trades=3,policy_notional_cap=25,candle_type_def=CandleType.FUTURES))
        with self.assertRaisesRegex(ValueError,'research risk bounds'): s.bot_start()

    def test_true_five_minute_signal_row_clock(self):
        s=IntegratedFiveMinuteR1(dict(candle_type_def=CandleType.FUTURES))
        s.dp=Mock();s.dp.get_analyzed_dataframe.return_value=(pd.DataFrame([dict(date=CLOCK,enter_long=1)]),None)
        self.assertIsNone(s.signal_row('ETH/USDT:USDT',CLOCK+pd.Timedelta(minutes=4),'long'))
        self.assertIsNotNone(s.signal_row('ETH/USDT:USDT',CLOCK+pd.Timedelta(minutes=5),'long'))

    def test_all_frozen_repository_files_unchanged(self):
        for name,digest in read(OUT/'starting-freeze.json')['preexisting_files'].items():
            self.assertEqual(sha(ROOT/name),digest,name)

if __name__=='__main__': unittest.main()
