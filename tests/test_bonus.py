"""Meaningful causal, native callback, risk and genuine-flow mechanics tests."""
import json
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
ROOT=Path('/lab')
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'research/bonus'),str(ROOT/'research/session3'),str(ROOT/'user_data/strategies')]
from test_playbooks import vector,features,CFG
from advanced_features import advanced,volume_profile,qualifiers,plan
from PlaybookRiskV1 import session_features
from OpportunityRouterV1 import IntegratedM1V1,IntegratedM0V1
from futures_risk import evaluate
from orderflow import normalize,features as flow_features,confirmation,shadow
from freqtrade.persistence import LocalTrade


class Causality(unittest.TestCase):
    def test_every_prefix_and_append_future(self):
        d=vector(180);batch=advanced(session_features(d))
        for n in [97,99,100,107,127,150,179]:
            a=advanced(session_features(d.iloc[:n].copy()))
            assert_frame_equal(a,batch.iloc[:n])
        altered=d.copy();altered.loc[150:,['high','volume']]*=1000
        assert_frame_equal(batch.iloc[:150],advanced(session_features(altered)).iloc[:150])

    def test_prior_day_session_and_fvg_known_at(self):
        d=vector(300);f=advanced(session_features(d))
        i=100;day=d.date.iloc[i].floor('D');prior=d.loc[(d.date>=day-pd.Timedelta(days=1))&(d.date<day)]
        self.assertEqual(f.prior_day_high.iloc[i],prior.high.max())
        self.assertEqual(f.vp_known_at.iloc[i],d.date.iloc[i])
        self.assertEqual(f.vp_anchor.iloc[i],d.date.iloc[i-96])
        self.assertFalse(f.vp_poc.iloc[:96].notna().any())
        gap=d.drop(index=110).reset_index(drop=True)
        out=advanced(session_features(gap))
        self.assertTrue(out.vp_poc.iloc[111:205].isna().all())

    def test_profile_units_value_area_and_trade_not_proxy(self):
        p=volume_profile([99.,100.,100.,101.],[1.,5.,5.,1.])
        self.assertEqual(p['total_base_volume'],12.)
        self.assertTrue(99.9<p['poc']<100.1)
        self.assertGreaterEqual(p['value_fraction_actual'],.7)
        self.assertLess(p['val'],p['vah'])
        self.assertIsNone(volume_profile([1.],[0.]))

    def test_equal_liquidity_needs_two_distinct_confirmed_pivots(self):
        f=advanced(session_features(vector(160)))
        for side in ['high','low']:
            events=f['swing_'+side].where(f['swing_'+side].ne(f['swing_'+side].shift())).dropna()
            self.assertGreaterEqual(len(events),2)
            first,second=events.index[:2]
            self.assertFalse(f['equal_'+side].iloc[first:second].any())
            expected=abs(events.iloc[1]-events.iloc[0])<=.1*f.atr14.iloc[second]
            self.assertEqual(bool(f['equal_'+side].iloc[second]),bool(expected))

    def test_cross_section_rank_is_causal_and_both_directions(self):
        from bonus_pipeline import ranking
        d=vector(200);bases={'BTC/USDT:USDT':d,'ETH/USDT:USDT':d.copy(),'SOL/USDT:USDT':d.copy(),'XRP/USDT:USDT':d.copy()}
        for k,b in bases.items():b['volume']=1e7
        bases['ETH/USDT:USDT'].loc[160:,'close']*=1.1
        bases['SOL/USDT:USDT'].loc[160:,'close']*=.9
        a,sa=ranking({k:b.iloc[:170] for k,b in bases.items()});b,sb=ranking(bases)
        self.assertEqual(sa,{k:v for k,v in sb.items() if k in sa})
        at=list(sa)[-1];self.assertIn('ETH/USDT:USDT',sa[at]['selected']);self.assertIn('SOL/USDT:USDT',sa[at]['selected'])


class Flow(unittest.TestCase):
    def trade(self,id='1',size=2,at=1000,receipt=1100):
        return normalize({'id':id,'contract':'BTC_USDT','size':size,'price':'100.','create_time_ms':at},receipt,'BTC_USDT',.01)
    def test_signed_multiplier_quote_duplicate_future_cutoff(self):
        buy=self.trade();sell=self.trade('2',-1,1200,1300)
        self.assertEqual(buy['amount'],.02);self.assertEqual(sell['side'],'sell');self.assertEqual(buy['quote_usdt'],2.)
        cov={'subscribed_ms':0,'connected_until_ms':3000,'disconnects':0,'invalid_events':0,'out_of_order':0}
        o=flow_features([buy,sell],0,2000,2000,cov,1)
        self.assertEqual(o['delta_base'],.01);self.assertEqual(o['coverage_status'],'COMPLETE_OBSERVED_CONNECTION')
        early=flow_features([buy,sell],0,1200,1200,cov,1);self.assertEqual(early['trade_count'],1)
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):flow_features([buy,buy],0,2000,2000,cov,1)
        with self.assertRaisesRegex(ValueError,'UNOBSERVED'):flow_features([buy],0,2001,2000,cov,1)
        with self.assertRaises(ValueError):self.trade(at=5000)
        with self.assertRaises(ValueError):self.trade(size=0)
    def test_missing_coverage_unknown_for_both_recipes_and_sides(self):
        obs={'coverage_status':'PARTIAL','trade_count':10,'imbalance':.5,'price_return':.01}
        for recipe in ['vwap','sweep']:
            for side in ['long','short']:self.assertEqual(confirmation(obs,recipe,side),'UNKNOWN')
        obs['coverage_status']='COMPLETE_OBSERVED_CONNECTION'
        self.assertEqual(confirmation(obs,'vwap','long'),'CONFIRM')
        self.assertEqual(confirmation(obs,'sweep','long'),'CONTRADICT')
        obs['imbalance']=-.5
        self.assertEqual(confirmation(obs,'sweep','long'),'CONFIRM')
        obs['price_return']=-.01
        self.assertEqual(confirmation(obs,'vwap','short'),'CONFIRM')
    def test_shadow_expiry_and_no_economic_labels(self):
        obs={'coverage_status':'PARTIAL','trade_count':0,'end_ms':1000}
        p={'decision_id':'a','decision_ms':1000,'expires_ms':2000,'recipe':'vwap','side':'long'}
        self.assertEqual(shadow(p,obs,2000)['confirmation'],'EXPIRED')
        self.assertEqual(shadow(p,obs,1100)['economic_outcome'],'UNMEASURED')


class Risk(unittest.TestCase):
    def args(self,side='long',lev=10):
        return dict(side=side,price=100.,stop=99. if side=='long' else 101.,equity=1000.,day_start_equity=1000.,
                    available_margin=100.,unrealized_pnl=0.,leverage=lev,contract_size=.01,min_contracts=1,step_contracts=1,
                    tiers=[{'min_notional':0,'max_notional':100000,'max_leverage':20,'maintenance_rate':.005}])
    def test_1_10_20_same_notional_price_risk_and_stop_conversion(self):
        for side in ['long','short']:
            rs=[evaluate(**self.args(side,l)) for l in [1,10,20]]
            self.assertTrue(all(r['status']=='PASS' for r in rs))
            self.assertEqual(len({r['notional'] for r in rs}),1)
            self.assertEqual(len({r['planned_risk'] for r in rs}),1)
            self.assertAlmostEqual(rs[0]['margin']/rs[-1]['margin'],20)
            self.assertAlmostEqual(rs[-1]['native_stop_ratio'],-.2)
    def test_mtm_pending_correlated_and_missing_tier_fail_closed(self):
        for update,reason in [({'unrealized_pnl':-11.},'MARK_TO_MARKET'),({'pending_risk':6.},'PENDING'),
                              ({'correlated_notional':500.},'CORRELATED'),({'tiers':None},'TIER_UNKNOWN')]:
            a=self.args();a.update(update);r=evaluate(**a)
            self.assertEqual(r['status'],'REJECT');self.assertIn(reason,r['reason'])
        a=self.args(lev=20);a['stop']=95.
        self.assertEqual(evaluate(**a)['reason'],'BUFFERED_LIQUIDATION_CLEARANCE')


class FundingBoundary(unittest.TestCase):
    def test_partial_at_funding_time_is_bounded_without_double_charge(self):
        from bonus_funding_audit import event_bounds
        trade={'is_short':False,'open_timestamp':0,'close_timestamp':3000,'orders':[
            {'amount':.01,'ft_is_entry':True,'order_filled_timestamp':0},
            {'amount':.005,'ft_is_entry':False,'order_filled_timestamp':2000},
            {'amount':.005,'ft_is_entry':False,'order_filled_timestamp':3000}]}
        lo,hi,rows=event_bounds(trade,[{'timestamp_ms':2000,'rate':.00005,'mark_open':2278.794}])
        self.assertAlmostEqual(lo,-.001139397);self.assertAlmostEqual(hi,-.0005696985)
        self.assertTrue(rows[0]['clock_priority_ambiguous'])
        self.assertLess(-.002278794,lo)

    def test_recorded_native_partial_funding_defect_is_exposed(self):
        p=ROOT/'evidence/bonus/source-funding-audit.json'
        obj=json.loads(p.read_text())
        self.assertEqual(obj['variants']['RouterOnlyM1V1']['outside_bounds_trades'],2)
        self.assertEqual(obj['variants']['RouterOnlyV1']['outside_bounds_trades'],0)
        self.assertFalse(obj['native_results_modified'])


class Management(unittest.TestCase):
    def setup_trade(self,short=False):
        self.now=pd.Timestamp('2026-08-25T01:00Z').to_pydatetime()
        s=IntegratedM1V1(CFG.copy())
        t=LocalTrade(pair='X',open_rate=100.,amount=1.,stake_amount=100.,is_short=short,leverage=1.,
                     open_date=(self.now-timedelta(minutes=15)).replace(tzinfo=None),fee_open=.0006,fee_close=.0006,
                     price_precision=.01,precision_mode_price=4)
        store={'bonus_plan':{'stop':101. if short else 99.,'risk_fraction':.01,'target':97. if short else 103.,
                             'max_hold_hours':4},'bonus_partial_done':False}
        t.get_custom_data=lambda key:store.get(key);t.set_custom_data=lambda k,v:store.update({k:v})
        s.dp=SimpleNamespace(get_analyzed_dataframe=lambda *a:(pd.DataFrame(),None))
        return s,t,store
    def adjust(self,s,t,rate):
        return s.adjust_trade_position(t,self.now,rate,0.,1.,1000.,rate,rate,0.,0.)
    def test_native_long_short_partial_pending_minimum_and_duplicate_fill(self):
        from unittest.mock import PropertyMock
        for short in [False,True]:
            s,t,state=self.setup_trade(short);rate=98.5 if short else 101.5
            self.assertEqual(self.adjust(s,t,rate),(-50.,'partial_1R_v1'))
            with patch.object(LocalTrade,'has_open_orders',new_callable=PropertyMock,return_value=True):
                self.assertIsNone(self.adjust(s,t,rate))
            self.assertIsNone(s.adjust_trade_position(t,self.now,rate,0.,60.,1000.,rate,rate,0.,0.))
            # Native exit fill count is represented by a successful order in production.
            with patch.object(LocalTrade,'nr_of_successful_exits',new_callable=PropertyMock,return_value=1):
                order=SimpleNamespace(ft_order_side=t.exit_side)
                s.order_filled('X',t,order,self.now);s.order_filled('X',t,order,self.now)
                self.assertTrue(state['bonus_partial_done']);self.assertIsNone(self.adjust(s,t,rate))
    def test_native_stop_tightening_and_restart_state(self):
        for short in [False,True]:
            s,t,state=self.setup_trade(short);state['bonus_partial_done']=True
            rate=98. if short else 102.
            ratio=s.custom_stoploss('X',t,self.now,rate,0.)
            self.assertGreater(ratio,0.)
            old=state['bonus_tight_stop']
            restored=json.loads(json.dumps(state))
            t.get_custom_data=lambda k:restored.get(k);t.set_custom_data=lambda k,v:restored.update({k:v})
            s2=IntegratedM1V1(CFG.copy());s2.dp=s.dp
            s2.custom_stoploss('X',t,self.now,rate,0.)
            self.assertEqual(restored['bonus_tight_stop'],old)
    def test_m0_no_partials_and_max_hold(self):
        s,t,state=self.setup_trade();s.position_adjustment_enable=False
        self.assertIsNone(self.adjust(s,t,101.5))
        self.assertEqual(s.custom_exit('X',t,self.now+timedelta(hours=4),100.,0.),'max_hold_4h')

    def test_after_fill_cannot_loosen_persisted_stop(self):
        for short in [False,True]:
            s,t,state=self.setup_trade(short);state['bonus_partial_done']=True
            state['bonus_tight_stop']=99.65 if short else 100.35
            crossed=99.8 if short else 100.2
            self.assertIsNone(s.custom_stoploss('X',t,self.now,crossed,0.,after_fill=True))
            self.assertEqual(state['bonus_tight_stop'],99.65 if short else 100.35)

    def test_native_partially_filled_pending_order_blocks_repeat(self):
        from freqtrade.persistence import Order
        s,t,state=self.setup_trade()
        order=Order(ft_order_side=t.exit_side,side=t.exit_side,order_type='limit',
                    order_id='fixture',status='open',filled=.25,amount=.5,ft_is_open=True,
                    ft_pair='X')
        t.orders=[order]
        self.assertTrue(t.has_open_orders)
        self.assertIsNone(self.adjust(s,t,101.5))
        self.assertFalse(state['bonus_partial_done'])

    def test_native_roi_uses_frozen_target_on_both_sides(self):
        from freqtrade.enums import ExitType
        for short in [False,True]:
            s,t,state=self.setup_trade(short)
            s.minimal_roi={0:100.} # native strategy resolver normally normalizes JSON keys
            s.dp.runmode=SimpleNamespace(value='backtest')
            self.assertAlmostEqual(s.custom_roi('X',t,self.now,15,None,'short' if short else 'long'),
                                   t.calc_profit_ratio(state['bonus_plan']['target']))
            exits=s.should_exit(t,100.,self.now,enter=False,exit_=False,
                                low=96. if short else 99.5,high=100.5 if short else 104.)
            self.assertIn(ExitType.ROI,[e.exit_type for e in exits])

    def test_mark_to_market_admission_veto_and_missing_state(self):
        s,t,state=self.setup_trade()
        s.wallets=SimpleNamespace(get_total_stake_amount=lambda:1000.)
        g={'modeled_loss_per_notional':.02}
        now=self.now
        confirm=lambda:s.confirm_trade_entry('NEW','limit',.25,100.,'GTC',now,None,'long')
        with patch.object(s,'row_plan',return_value=g),patch('OpportunityRouterV1.Trade.get_open_trades',return_value=[]),patch('OpportunityRouterV1.Trade.get_trades_proxy',return_value=[]):
            self.assertTrue(confirm())
        row=pd.DataFrame([{'date':pd.Timestamp(now)-pd.Timedelta(minutes=15),'close':90.}])
        s.dp=SimpleNamespace(get_analyzed_dataframe=lambda *a:(row,None))
        t.stake_amount=25.;t.calc_profit=lambda rate:-11.
        with patch.object(s,'row_plan',return_value=g),patch('OpportunityRouterV1.Trade.get_open_trades',return_value=[t]),patch('OpportunityRouterV1.Trade.get_trades_proxy',return_value=[]):
            self.assertFalse(confirm())
        s.wallets=SimpleNamespace(get_total_stake_amount=lambda:float('nan'))
        with patch.object(s,'row_plan',return_value=g),patch('OpportunityRouterV1.Trade.get_open_trades',return_value=[]),patch('OpportunityRouterV1.Trade.get_trades_proxy',return_value=[]):
            self.assertFalse(confirm())


if __name__=='__main__':unittest.main()
