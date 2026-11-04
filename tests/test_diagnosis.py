"""Causal correction mechanics and real-source factor isolation; no synthetic profit claim."""
import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from diagnosis_common import *
from targeted_rules import conditional_entry,expansion,compatible_thesis,relaxed_candidates
from diagnosis_prepare import rank
from session4_features import candidates
from DiagnosisPolicyR1 import DiagnosisPolicyR1
from RecoveryPolicyR1 import RecoveryPolicyR1
from IntegratedPolicyR1 import IntegratedPolicyR1
from freqtrade.enums import RunMode,CandleType

AT=pd.Timestamp('2026-10-01T12:00:00Z')
def plan(side='long'):
    sign=1 if side=='long' else -1
    return dict(side=side,recipe='continuation',reference=100.,signal_close=100.,stop=100-sign,target=100+3*sign,
        available_at=AT.isoformat(),expires_at=(AT+pd.Timedelta(minutes=5)).isoformat(),atr_at_signal=1.,deviation_fraction=.0015,
        max_hold_hours=8,boundary=100-sign*.2,decision_id='immutable')

class Corrections(unittest.TestCase):
    def test_conditional_entry_uses_known_expansion_and_keeps_geometry(self):
        for side,sign in [('long',1),('short',-1)]:
            g=plan(side);old=copy.deepcopy(g)
            strong=pd.Series(dict(open=100.,close=100+sign,atr14=1.25,rvol=1.2))
            weak=pd.Series(dict(open=100.,close=100+sign*.4,atr14=1.,rvol=1.1))
            self.assertTrue(expansion(strong,side));self.assertEqual(conditional_entry(g,strong)['reference'],100.)
            passive=conditional_entry(g,weak)
            self.assertAlmostEqual(passive['reference'],100-sign*.15)
            self.assertEqual((passive['stop'],passive['target'],passive['expires_at']),(old['stop'],old['target'],old['expires_at']))
            self.assertEqual(g,old)

    def test_reversal_uses_its_original_execution_hypothesis(self):
        g=plan();g['recipe']='reversal'
        self.assertEqual(conditional_entry(g,pd.Series(dict(open=100.,close=100.1,atr14=1.,rvol=.5)))['reference'],100.)

    def test_unreachable_thesis_and_tick_buffer_fail_compatibility_both_sides(self):
        for side,sign in [('long',1),('short',-1)]:
            g=plan(side);g['boundary']=g['stop']+sign*.1
            self.assertFalse(compatible_thesis(g,.01))
            g['boundary']=g['stop']+sign*.16
            self.assertFalse(compatible_thesis(g,.011))
            g['boundary']=g['stop']+sign*.2
            self.assertTrue(compatible_thesis(g,.01))
            g['boundary']=None;self.assertFalse(compatible_thesis(g,.01))

    def test_immutable_compatibility_flag_dispatches_to_original_fast_or_structural_rule(self):
        s=DiagnosisPolicyR1(dict(candle_type_def=CandleType.FUTURES,diagnosis_thesis_guard=True))
        t=Mock();t.get_custom_data.return_value={'diagnosis_structural_compatible':False}
        with patch.object(RecoveryPolicyR1,'custom_exit',return_value='fast') as fast:
            self.assertEqual(s.custom_exit('ETH/USDT:USDT',t,AT,100,0),'fast');fast.assert_called_once()
        t.get_custom_data.return_value={'diagnosis_structural_compatible':True}
        with patch.object(IntegratedPolicyR1,'custom_exit',return_value='structural') as structural:
            self.assertEqual(s.custom_exit('ETH/USDT:USDT',t,AT,100,0),'structural');structural.assert_called_once()

    def test_ranking_stable_and_eligibility_separate_from_pool(self):
        def row(bias=1):return pd.Series(dict(eligible=True,return4h=.01,activity=1.,ema20_1h=100+bias,ema50_1h=100.))
        rows={'BTC/USDT:USDT':row(),'A/USDT:USDT':row(-1),'B/USDT:USDT':row(),'C/USDT:USDT':row(),'D/USDT:USDT':row()}
        self.assertNotIn('A/USDT:USDT',rank(rows,'continuation','long',strict=True))
        self.assertIn('A/USDT:USDT',rank(rows,'continuation','long',strict=False))
        self.assertEqual(rank(rows,'continuation','long',qualified={'D/USDT:USDT'}),['D/USDT:USDT'])
        self.assertEqual(rank(rows,'continuation','long'),rank(dict(reversed(list(rows.items()))),'continuation','long'))

    def test_new_class_refuses_live_dry_run_and_hyperopt(self):
        for mode in (RunMode.LIVE,RunMode.DRY_RUN,RunMode.HYPEROPT):
            s=DiagnosisPolicyR1(dict(runmode=mode,dry_run=True,max_open_trades=2,policy_notional_cap=25,candle_type_def=CandleType.FUTURES))
            with self.assertRaisesRegex(ValueError,'historical research only'):s.bot_start()

class RealSourceIsolation(unittest.TestCase):
    def test_putting_only_three_ema_predicates_back_recovers_frozen_continuation_candidates(self):
        for pair in pairs():
            f=pd.read_pickle(PWORK/'features/v4'/(slug(pair)+'.pkl'))
            expected={x['at']+x['side'] for x in candidates(f,'structure') if x['recipe']=='continuation' and x['reason']=='TRADE'}
            actual=set()
            for x in relaxed_candidates(f):
                if x['reason']!='TRADE':continue
                r=f.iloc[x['index']];sign=1 if x['side']=='long' else -1
                if sign*(r.ema20_1h-r.ema50_1h)>0 and sign*(r.ema20-r.ema50)>0 and sign*r.ema20_slope>0:actual.add(x['at']+x['side'])
            self.assertEqual(actual,expected,pair)

    def test_relaxed_signal_prefix_does_not_change_after_future_rows_append(self):
        for pair in pairs():
            f=pd.read_pickle(PWORK/'features/v4'/(slug(pair)+'.pkl')).iloc[:1400]
            cutoff=f.date.iloc[1102]+pd.Timedelta(minutes=15)
            full=[x for x in relaxed_candidates(f) if pd.Timestamp(x['at'])<=cutoff]
            prefix=relaxed_candidates(f.iloc[:1103])
            self.assertEqual(full,prefix,pair)

    def test_every_parent_tracked_file_and_market_seal_remains_unchanged(self):
        self.assertEqual(verify_parent()['changed'],[])

class NativeResultIntegrity(unittest.TestCase):
    def test_exact_control_trade_objects_and_nonmutating_terminal_observers(self):
        for name in ('v4','pr12','passive','structural'):
            parent=next(iter(read(PARENT/'native'/NATIVE_LABELS[name]/'result.json')['strategy'].values()))['trades']
            new=next(iter(read(OUT/'native'/('development-'+name+'-touch-750')/'result.json')['strategy'].values()))['trades']
            self.assertEqual(parent,new,name)
            if name in ('v4','passive'):
                replay=next(iter(read(OUT/'native'/('development-'+name+'-touch-750-lifecycle-audit')/'result.json')['strategy'].values()))['trades']
                self.assertEqual(new,replay,name)

    def test_corrected_expiry_reaches_native_config_and_terminal_lifecycle(self):
        for path in sorted((OUT/'native').glob('*passive-30m*expiry-corrected/provenance.json')):
            p=read(path);cfg=read((ROOT/p['archive']).parent/'config.json')
            self.assertEqual(cfg['unfilledtimeout']['entry'],30)
            self.assertEqual(sha((ROOT/p['archive']).parent/'config.json'),p['config_sha256'])
            events=read(path.parent/'entry-lifecycle.json')['terminal_events']
            for event in events:
                self.assertEqual(event['native_entry_timeout_minutes'],30)
                self.assertGreaterEqual(event['age_minutes'],30)
        full=read(OUT/'native/development-passive-30m-touch-750-expiry-corrected/entry-lifecycle.json')
        self.assertEqual(len(full['terminal_events']),8)
        self.assertTrue(all(e['age_minutes']==30 for e in full['terminal_events']))

    def test_new_sources_are_complete_hash_sealed_and_never_future_holdout(self):
        validation=read(OUT/'data-validation.json')
        for name in ('earlier','later'):
            self.assertTrue(validation[name]['complete']);self.assertEqual(len(validation[name]['files']),56)
            for row in validation[name]['files']:
                self.assertEqual(sha(ROOT/row['path']),row['sha256'])
                self.assertLess(pd.Timestamp(row['last']),pd.Timestamp('2026-11-04T00:00:00Z'))
                self.assertIn(row['gaps'],(0,None))

    def test_every_new_plan_uses_available_closed_candles_and_preserves_stop_target(self):
        from diagnosis_native import verify
        for cohort in ('development','earlier','later'):
            verify(cohort)
            original=read(WORK/cohort/'plans/v4.json')
            for name in ('conditional-entry','passive-30m','thesis-compatible'):
                plans=read(WORK/cohort/'plans'/(name+'.json'))
                for pair,items in plans.items():
                    for at,g in items.items():
                        prior=original[pair][at]
                        self.assertEqual((g['stop'],g['target']),(prior['stop'],prior['target']))
                        self.assertLessEqual(pd.Timestamp(g['available_at']),pd.Timestamp(at))

if __name__=='__main__':unittest.main()
