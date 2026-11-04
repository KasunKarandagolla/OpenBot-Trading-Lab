"""Trading behavior, causal timing and native lifecycle. Fixtures are SYNTHETIC."""
import sys,json,math,hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_common import *
from setup_features import scan_pair,make_plan,features,thesis_failed,_arm,merge_candidate
from setup_profile import verified_profile
from SetupPolicyV1 import SetupPolicyV1
from policy_features import execution_plan
from policy_risk import size
from freqtrade.enums import RunMode,CandleType
from causal_structure import structure,closed_merge
from test_policy import account,contract,NativeLifecycleFixture

CLOCK=pd.Timestamp('2026-10-01T00:00:00Z');PAIR='ETH/USDT:USDT'

def row(i=0,**kw):
    at=CLOCK+pd.Timedelta(minutes=15*i)
    d=dict(date=at,open=100.2,high=100.8,low=99.9,close=100.4,volume=10.,atr14=1.,rvol=1.5,
        setup_valid=True,eligible=True,regime='TREND_UP',struct_direction='UP',struct_direction_1h='UP',
        adx_1h=25.,bias4h=1.,session_bars=49+i,vwap_valid=True,same_session=True,prior_vwap=100.,
        previous_close=101.,previous_high=100.8,previous_low=99.5,pull_low=99.5,pull_high=103.,
        swing_low_1h=95.,swing_low_known_at_1h=CLOCK-pd.Timedelta(hours=2),
        swing_high_1h=106.5,swing_high_known_at_1h=CLOCK-pd.Timedelta(hours=2),
        prior_swing_low=95.,prior_swing_low_known_at=CLOCK-pd.Timedelta(hours=1),
        prior_swing_high=106.5,prior_swing_high_known_at=CLOCK-pd.Timedelta(hours=1),
        prior_day_low=90.,prior_day_high=115.,prior_day_known_at=CLOCK.floor('D'),
        prior_session_low=92.,prior_session_high=112.,prior_session_known_at=CLOCK.floor('8h'),
        range_low_1h=90.,range_high_1h=110.,balance_1h=False,date_1h=CLOCK.floor('h')-pd.Timedelta(hours=1))
    d.update(kw);return pd.Series(d)

class SetupBehavior(unittest.TestCase):
    def test_competing_playbooks_abstain_even_when_direction_agrees(self):
        for side in ['long','short']:
            a=dict(recipe='continuation',side='long');b=dict(recipe='reversal',side=side)
            self.assertTrue(merge_candidate(merge_candidate(None,a),b)['conflict'])

    def test_gap_invalidation_consumes_the_old_reference(self):
        d=pd.DataFrame([row(),row(1,setup_valid=False),row(2),row(3,close=101.5,low=100.2)])
        events=scan_pair(d,PAIR)
        self.assertEqual(sum(x['state']=='ARMED' and x['playbook']=='continuation' for x in events),1)

    def test_defended_continuation_requires_later_confirmation(self):
        d=pd.DataFrame([row(),row(1,close=101.5,open=100.4,low=100.2,high=101.8)])
        events=scan_pair(d,PAIR);plans=[x['plan'] for x in events if x['plan']]
        self.assertEqual(len(plans),1);g=plans[0]
        self.assertEqual(g['recipe'],'continuation');self.assertLess(g['setup_armed_at'],g['confirmation_at'])
        self.assertEqual(g['target'],106.5);self.assertLess(g['stop'],99.5)
        self.assertFalse([x for x in scan_pair(d.iloc[:1],PAIR) if x['plan']])

    def test_failed_hourly_structure_cannot_be_continuation(self):
        d=pd.DataFrame([row(struct_direction_1h='DOWN'),row(1,struct_direction_1h='DOWN',close=102.)])
        self.assertFalse([x for x in scan_pair(d,PAIR) if x['playbook']=='continuation'])

    def test_external_sweep_then_shift_is_a_reversal(self):
        d=pd.DataFrame([row(low=98.8,high=100.,open=99.3,close=99.6,previous_close=100.,prior_day_low=99.,prior_vwap=97.,prior_swing_high=100.5),
            row(1,low=99.4,close=101.,open=100.,high=101.2,previous_close=99.6,prior_day_low=99.,prior_vwap=97.,prior_swing_high=110.)])
        p=[x['plan'] for x in scan_pair(d,PAIR) if x['plan'] and x['playbook']=='reversal']
        self.assertEqual(len(p),1);self.assertEqual(p[0]['boundary'],99.)
        self.assertEqual(p[0]['confirmation'],'FROZEN_PRE_SWEEP_STRUCTURE_BREAK')

    def test_arbitrary_wick_without_external_reference_is_not_sweep(self):
        d=pd.DataFrame([row(low=98.8,close=99.6,prior_vwap=97.),row(1,close=101.,open=99.5)])
        self.assertFalse([x for x in scan_pair(d,PAIR) if x['playbook']=='reversal'])

    def test_breakout_acceptance_retest_and_failed_break(self):
        a=row(balance_1h=True,range_high_1h=100.,previous_close=99.5,prior_vwap=97.,low=99.8)
        b=row(1,balance_1h=True,range_high_1h=100.,close=100.8,open=100.3,low=100.1,prior_vwap=97.)
        p=[x for x in scan_pair(pd.DataFrame([a,b]),PAIR) if x['playbook']=='breakout' and x['plan']]
        self.assertEqual(len(p),1);self.assertEqual(p[0]['plan']['boundary'],100.)
        b['close']=99.;b['low']=98.8
        ev=scan_pair(pd.DataFrame([a,b]),PAIR)
        self.assertFalse([x for x in ev if x['playbook']=='breakout' and x['plan']])
        self.assertTrue([x for x in ev if x['playbook']=='breakout' and x['state']=='INVALIDATED'])

    def test_nearest_obstacle_veto_cannot_skip_to_farther_target(self):
        r=row(close=101.,prior_swing_high=101.2)
        a=_arm(PAIR,r,'continuation','long',100.,'SESSION_VWAP',r.date,99.5);a['confirmation']='fixture'
        p,reason=make_plan(r,a)
        self.assertIsNone(p);self.assertIn('FIRST_OBSTACLE',reason)

    def test_bad_logical_stop_not_compressed_to_force_trade(self):
        r=row(close=101.)
        a=_arm(PAIR,r,'continuation','long',100.,'fixture',r.date,95.);a['confirmation']='fixture'
        self.assertEqual(make_plan(r,a)[1],'LOGICAL_STOP_OUTSIDE_0.3_2.5_PERCENT')
        v=size(account(pending_risk=5),clock=CLOCK.timestamp(),side='long',entry=100,stop=99,leverage=1,contract=contract(),cap=25)
        self.assertEqual(v['status'],'REJECT')

    def test_profile_missing_is_unknown_and_proxy_cannot_activate_rotation(self):
        self.assertEqual(verified_profile([],{},CLOCK)['status'],'UNKNOWN')
        d=pd.DataFrame([row(balance_1h=True,low=98.8,close=99.6),row(1,balance_1h=True,close=101.)])
        profile={CLOCK.floor('D').isoformat():dict(known_at=CLOCK.isoformat(),val=99.,vah=110.,poc=105.,fidelity='OHLCV_PROXY')}
        self.assertFalse([x for x in scan_pair(d,PAIR,profiles=profile) if x['playbook']=='rotation'])

    def test_verified_profile_contract_and_rotation_sequence(self):
        # Exact synthetic executed-price vectors test mechanics, no economic claim.
        trades=[dict(id=str(i),event_ms=(CLOCK-pd.Timedelta(hours=1)).timestamp()*1000+i,received_ms=CLOCK.timestamp()*1000,price=p,amount=v) for i,(p,v) in enumerate([(99.,1.),(105.,10.),(110.,1.)])]
        receipt=dict(source='SYNTHETIC_MECHANICS',venue='gate',pair=PAIR,fidelity='EXECUTED_TRADES',coverage='COMPLETE_VERIFIED',start=(CLOCK-pd.Timedelta(hours=8)).isoformat(),end=CLOCK.isoformat(),known_at=CLOCK.isoformat(),sha256=hashlib.sha256(json.dumps(trades,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        p=verified_profile(trades,receipt,CLOCK);self.assertEqual(p['status'],'READY');self.assertEqual(p['total_base_volume'],12.)
        with self.assertRaises(ValueError):verified_profile(trades,receipt,CLOCK-pd.Timedelta(seconds=1))
        p.update(val=99.,vah=110.,poc=106.)
        a=row(balance_1h=True,low=98.8,close=99.6,previous_close=100.,prior_vwap=97.,prior_day_low=90.)
        b=row(1,balance_1h=True,low=99.4,open=99.6,close=100.5,previous_close=99.6,prior_vwap=97.)
        ps=[x['plan'] for x in scan_pair(pd.DataFrame([a,b]),PAIR,profiles={CLOCK.floor('D').isoformat():p}) if x['playbook']=='rotation' and x['plan']]
        self.assertEqual(len(ps),1);self.assertEqual(ps[0]['target'],106.)
        self.assertTrue(thesis_failed(ps[0],pd.DataFrame([row(close=98.),row(1,close=98.2)])))

    def test_repeated_reclaim_does_not_retrade_same_unresolved_anchor(self):
        d=pd.DataFrame([row(),row(1,close=101.5,low=100.2),row(2),row(3,close=101.5,low=100.2)])
        self.assertEqual(len([x for x in scan_pair(d,PAIR) if x['playbook']=='continuation' and x['plan']]),1)

    def test_long_short_geometry_symmetry_and_expiry(self):
        for side,s in [('long',1),('short',-1)]:
            r=row(close=100.,low=99.5,high=100.5,prior_swing_high=106.,prior_swing_low=94.,swing_high_1h=106.,swing_low_1h=94.,prior_vwap=95.)
            a=_arm(PAIR,r,'continuation',side,100.,'fixture',r.date,99.5 if s==1 else 100.5);a['confirmation']='fixture'
            p,_=make_plan(r,a);self.assertIsNotNone(p)
            self.assertAlmostEqual(abs(p['stop']-100),.7)
            self.assertIsNotNone(execution_plan(p,100,pd.Timestamp(p['available_at'])))
            self.assertIsNone(execution_plan(p,100,pd.Timestamp(p['expires_at'])))

    def test_distant_real_objective_rejected_without_manufactured_nearer_target(self):
        r=row(close=100.,prior_swing_high=110.,swing_high_1h=110.)
        a=_arm(PAIR,r,'continuation','long',100.,'fixture',r.date,99.5);a['confirmation']='fixture'
        self.assertEqual(make_plan(r,a)[1],'FIRST_OBJECTIVE_BEYOND_EXISTING_6ATR_BOUND')

    def test_pivot_and_hour_availability(self):
        f=pd.DataFrame(dict(date=pd.date_range(CLOCK,periods=7,freq='15min'),high=[11,12,16,13,12,11,12],low=[8]*7,open=[9]*7,close=[10]*7,volume=[1]*7))
        d=structure(f);self.assertTrue(pd.isna(d.swing_high.iloc[3]));self.assertEqual(d.swing_high.iloc[4],16.)
        self.assertEqual(d.swing_high_known_at.iloc[4],f.date.iloc[4]+pd.Timedelta(minutes=15))
        h=pd.DataFrame(dict(date=[CLOCK],value=[7]))
        m=closed_merge(f,h);self.assertTrue(pd.isna(m.value_1h.iloc[2]));self.assertEqual(m.value_1h.iloc[3],7)

    def test_mode_refusal_and_hard_hold_without_store(self):
        for mode in [RunMode.LIVE,RunMode.DRY_RUN,RunMode.HYPEROPT]:
            s=SetupPolicyV1(dict(runmode=mode,dry_run=True,candle_type_def=CandleType.FUTURES))
            with self.assertRaisesRegex(ValueError,'historical research only'):s.bot_start()
        t=Mock();t.is_short=False;t.open_date_utc=CLOCK.to_pydatetime();g=dict(side='long',stop=99,target=110,max_hold_hours=24,recipe='continuation',boundary=100,atr_at_signal=1)
        t.get_custom_data.side_effect=lambda k,default=None:g if k=='policy_plan' else {}
        s=SetupPolicyV1(dict(candle_type_def=CandleType.FUTURES))
        self.assertEqual(s.custom_exit(PAIR,t,(CLOCK+pd.Timedelta(hours=15)).to_pydatetime(),100,0),'max_hold_15h')

class SetupNativeLifecycle(NativeLifecycleFixture):
    """Run inherited real native SQLite/order/funding regressions on NEW callbacks."""
    def setUp(self):
        super().setUp();self.s._store.close()
        self.cfg.update(runmode=RunMode.BACKTEST,dry_run=True,policy_leverage=1,setup_management=True)
        self.s=SetupPolicyV1(self.cfg);self.s.bot_start();self.s.dp=Mock();self.s.dp.get_analyzed_dataframe.return_value=(pd.DataFrame(),None)
    def make_trade(self,short=False,lev=1):
        t,g=super().make_trade(short,lev)
        g.update(setup_id='fixture:'+str(short),boundary=100,recipe='continuation',atr_at_signal=.6,
            first_objective=dict(price=98. if short else 102.),second_objective=dict(price=96. if short else 104.))
        t.set_custom_data('policy_plan',g)
        return t,g

    def test_native_objective_partial_cancel_restart_final_both_sides(self):
        from freqtrade.persistence import Trade
        for short in [False,True]:
            t,g=self.make_trade(short);e=self.order(t,'entry-'+str(short),t.entry_side,1,100)
            self.terminal(t,e,.6,100,'canceled');self.assertAlmostEqual(t.amount,.6)
            count=self.s._store.db.execute('SELECT count(*) FROM events').fetchone()[0]
            self.s.order_filled(t.pair,t,e,CLOCK.to_pydatetime())
            self.assertEqual(self.s._store.db.execute('SELECT count(*) FROM events').fetchone()[0],count)
            price=98. if short else 102.
            out=self.s.adjust_trade_position(t,CLOCK,price,0,1,100,price,price,0,0)
            self.assertIsNotNone(out);self.assertAlmostEqual(-out[0],t.stake_amount/3)
            x=self.order(t,'partial-'+str(short),t.exit_side,.2,price)
            self.terminal(t,x,.1,price,'canceled');self.assertAlmostEqual(t.amount,.5)
            ident=t.id;Trade.session.expire_all();t=Trade.session.get(Trade,ident)
            out=self.s.adjust_trade_position(t,CLOCK,price,0,1,100,price,price,0,0)
            self.assertIsNotNone(out);self.assertAlmostEqual(-out[0],10.) # remaining0.1 base, no repeated whole third
            final=self.order(t,'final-'+str(short),t.exit_side,.5,price)
            self.terminal(t,final,.5,price);self.assertFalse(t.is_open)

    def test_native_stop_persists_never_widens_and_no_premature_breakeven(self):
        for short in [False,True]:
            t,g=self.make_trade(short);e=self.order(t,'entry-'+str(short),t.entry_side,1,100);self.terminal(t,e,1,100)
            t.adjust_stop_loss(100,-.025,initial=True);self.s._ft_stop_uses_after_fill=True
            self.s.ft_stoploss_adjust(100,t,CLOCK,0,0,after_fill=True);initial=t.stop_loss
            price=98. if short else 102.
            self.s.ft_stoploss_adjust(price,t,CLOCK,0,0,after_fill=True)
            sign=-1 if short else 1
            self.assertGreaterEqual(sign*(t.stop_loss-initial),-1e-10)
            self.assertLessEqual(abs(t.stop_loss-initial),.011);initial=t.stop_loss
            x=self.order(t,'partial-'+str(short),t.exit_side,.3,price);self.terminal(t,x,.3,price)
            # No postfill confirmed swing: partial itself cannot force BE.
            self.s.ft_stoploss_adjust(price,t,CLOCK,0,0,after_fill=True);self.assertGreaterEqual(sign*(t.stop_loss-initial),-1e-10);initial=t.stop_loss
            t.set_custom_data('policy_plan',dict(g,stop=102. if short else 98.))
            self.s.ft_stoploss_adjust(price,t,CLOCK,0,0,after_fill=True);self.assertGreaterEqual(sign*(t.stop_loss-initial),-1e-10)

    def test_pending_partial_entry_and_exit_expiry(self):
        t,g=self.make_trade();o=self.order(t,'pending',t.entry_side,1,100)
        self.assertTrue(self.s.check_entry_timeout(t.pair,t,o,CLOCK+pd.Timedelta(minutes=5)))
        self.assertTrue(self.s.check_exit_timeout(t.pair,t,o,CLOCK+pd.Timedelta(minutes=5)))

    def test_consumed_setup_persists_across_reopen(self):
        from policy_state import StateStore
        self.s._store.put('consumed:idea',True);path=self.cfg['policy_state'];self.s._store.close();self.s._store=StateStore(path)
        with patch.object(self.s,'row_plan',return_value=dict(setup_id='idea')):
            self.assertFalse(self.s.confirm_trade_entry(pair=PAIR,order_type='limit',amount=.1,rate=100,time_in_force='GTC',current_time=CLOCK,entry_tag='',side='long'))

    def test_stop_advances_only_when_new_confirmed_structure_supports_cost_breakeven(self):
        for short in [False,True]:
            t,g=self.make_trade(short);e=self.order(t,'entry-'+str(short),t.entry_side,1,100);self.terminal(t,e,1,100)
            price=97.5 if short else 102.5
            x=self.order(t,'partial-'+str(short),t.exit_side,.3,price);self.terminal(t,x,.3,price)
            key='swing_high' if short else 'swing_low'
            r=dict(date=CLOCK+pd.Timedelta(minutes=15),atr14=.6)
            r[key]=98.8 if short else 101.2;r[key+'_known_at']=CLOCK+pd.Timedelta(minutes=15)
            self.s.dp.get_analyzed_dataframe.return_value=(pd.DataFrame([r]),None)
            self.s.custom_stoploss(PAIR,t,CLOCK+pd.Timedelta(minutes=30),price,0,True)
            tight=t.get_custom_data('policy_state')['tight_stop']
            self.assertGreater((tight-g['stop'])*(-1 if short else 1),0)
            self.assertGreater((tight-100)*(-1 if short else 1),0)

class RealSourceCausality(unittest.TestCase):
    def test_real_executed_profile_sample_reconciles_complete_session(self):
        p=DATA/'verified-profile-sample-trades.json';receipt=DATA/'verified-profile-sample-receipt.json'
        if not p.exists():self.skipTest('optional verified tape sample not restored')
        data=read(p);r=read(receipt);profile=verified_profile(data,r,r['known_at'])
        self.assertEqual(profile['status'],'READY')
        self.assertAlmostEqual(profile['total_base_volume'],sum(t['amount'] for t in data),places=6)
        self.assertLessEqual(pd.Timestamp(profile['anchor_end']),pd.Timestamp(profile['known_at']))

    def test_future_append_preserves_every_earlier_feature_and_decision(self):
        root=DATA/'development/gate/futures'
        if not root.exists():self.skipTest('owner must restore source archive')
        for pair in pairs():
            b=pd.read_feather(root/(slug(pair)+'-15m-futures.feather')).iloc[:1200]
            h=pd.read_feather(root/(slug(pair)+'-1h-futures.feather')).iloc[:300]
            full=features(b,h);n=1103
            prefix=features(b.iloc[:n],h.loc[h.date<b.date.iloc[n-1]+pd.Timedelta(minutes=15)])
            pd.testing.assert_frame_equal(full.iloc[:n].reset_index(drop=True),prefix.reset_index(drop=True))
            self.assertEqual(scan_pair(full.iloc[:n],pair),scan_pair(prefix,pair))
