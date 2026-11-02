"""Meaningful signed decisions, economic geometry, profile units and flow clocks."""
import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'research/intelligence'),str(ROOT/'research/bonus'),str(ROOT/'research/session3'),str(ROOT/'research/master_audit'),str(ROOT/'research/foundation'),str(ROOT/'user_data/strategies')]
from intelligence_features import COST,match,research_plan,profiles,executable_contract
from intelligence_profile import volume_profile_v2
from orderflow import normalize
from intelligence_orderflow import normalize_gate_rest,qualified_flow


class IntelligenceTests(unittest.TestCase):
    def row(self,side='long',**kwargs):
        values=dict(close=100.,open=99.,high=101.,low=98.,atr14=1.,adx_1h=26.,vwap_valid=True,
            prior_low=99.,prior_high=101.,prior_swing_low=99.,prior_swing_high=105.,prior_day_low=95.,prior_day_high=110.,
            vp2_poc=100.5,vp2_val=98.,vp2_vah=104.,date=pd.Timestamp('2026-10-10',tz='UTC'),
            struct_direction_1h='UP' if side=='long' else 'DOWN',struct_direction='UP' if side=='long' else 'DOWN',struct_event=None)
        values.update(kwargs); return pd.Series(values)

    def test_consistent_new_cost(self): self.assertAlmostEqual(COST,.0038)

    def test_net_geometry_not_gross_rr(self):
        self.assertIsNone(research_plan(self.row(low=99.5),'vwap','long'))
        g=research_plan(self.row(low=98.),'vwap','long'); self.assertIsNotNone(g)
        self.assertAlmostEqual(g['after_cost_rr'],(.044-.0038)/(.022+.0038))

    def test_near_obstacle_caution_and_veto_differ(self):
        row=self.row(low=98.)
        self.assertIsNone(research_plan(row,'sweep','long','nearest'))
        g=research_plan(row,'sweep','long','target')
        self.assertEqual(g['target_origin'],'FIXED_2R'); self.assertTrue(g['cautions'])

    def test_long_short_mirror(self):
        long=research_plan(self.row(),'vwap','long')
        short=research_plan(self.row(side='short',low=99.,high=102.),'vwap','short')
        self.assertAlmostEqual(long['risk_fraction'],short['risk_fraction'])
        self.assertAlmostEqual(long['after_cost_rr'],short['after_cost_rr'])
        self.assertAlmostEqual(long['target']+short['target'],200.)

    def test_reversal_opposing_trend_requires_failure_shift(self):
        r=self.row(struct_direction_1h='DOWN')
        self.assertIn('CONTINUATION_DANGER',match(r,'sweep','long'))
        r['struct_event']='CHOCH'; self.assertEqual(match(r,'sweep','long'),'MATCH')

    def test_structure_is_separate_hypothesis(self):
        r=self.row(struct_direction_1h='DOWN')
        self.assertEqual(match(r,'vwap','long'),'MATCH')
        self.assertIn('NOT_ALIGNED',match(r,'vwap','long',True))

    def test_profile_preserves_gaps_and_base_volume(self):
        p=volume_profile_v2([100,110],[9,1],'OBSERVED_TRADES',width=.01)
        self.assertGreater(p['empty_bins'],0); self.assertEqual(p['total_base_volume'],10)
        self.assertLess(p['vah'],110); self.assertEqual(p['fidelity'],'OBSERVED_TRADES')

    def test_profile_fidelity_mandatory(self):
        with self.assertRaises(ValueError): volume_profile_v2([100],[1],'EXCHANGE_CONFIRMED')

    def test_profile_excludes_signal_candle_and_future(self):
        dates=pd.date_range('2026-10-01',periods=100,freq='15min',tz='UTC')
        d=pd.DataFrame(dict(date=dates,open=100.,high=101.,low=99.,close=100.,volume=1.))
        original=profiles(d); d.loc[99,['high','close','volume']]=[1000,900,999999]
        revised=profiles(d)
        pd.testing.assert_series_equal(original.vp2_poc,revised.vp2_poc)
        truncated=profiles(d.iloc[:98]); pd.testing.assert_series_equal(revised.vp2_poc.iloc[:98],truncated.vp2_poc)

    def trade(self,id='1',at=1000,received=1100,size=2,price=100):
        return normalize(dict(id=id,contract='BTC_USDT',create_time_ms=at,size=size,price=price),received,'BTC_USDT',.01)

    def cov(self,**kwargs):
        c=dict(source='WEBSOCKET',subscribed_ms=0,connected_until_ms=5000,disconnects=0,invalid_events=0,out_of_order=0,server_clock_offset_ms=0)
        c.update(kwargs); return c

    def test_native_flow_units_and_receipt_cutoff(self):
        rows=[self.trade(),self.trade('2',1500,1600,-1,101),self.trade('3',1700,4500,100,102)]
        f=qualified_flow(rows,0,2000,3000,self.cov(),1.)
        self.assertEqual(f['trade_count'],2); self.assertAlmostEqual(f['buy_base'],.02)
        self.assertAlmostEqual(f['sell_base'],.01); self.assertAlmostEqual(f['delta_base'],.01)
        self.assertEqual(f['coverage_status'],'COMPLETE_OBSERVED_CONNECTION')

    def test_rest_many_trades_never_complete(self):
        f=qualified_flow([self.trade()],0,2000,3000,self.cov(source='REST'),1.)
        self.assertEqual(f['confirmation'],'UNKNOWN')

    def test_duplicate_trade_is_not_double_counted(self):
        with self.assertRaises(ValueError): qualified_flow([self.trade(),self.trade()],0,2000,3000,self.cov(),1.)

    def test_future_window_and_events_rejected(self):
        with self.assertRaises(ValueError): qualified_flow([],0,4000,3000,self.cov(),1.)
        with self.assertRaises(ValueError): self.trade(at=3000,received=1000)

    def test_incomplete_connection_remains_unknown(self):
        for change in [dict(disconnects=1),dict(out_of_order=1),dict(invalid_events=1),dict(server_clock_offset_ms=2000),dict(connected_until_ms=2000)]:
            f=qualified_flow([self.trade()],0,2000,3000,self.cov(**change),1.)
            self.assertEqual(f['confirmation'],'UNKNOWN')

    def test_absorption_requires_predefined_location(self):
        f=qualified_flow([self.trade(size=-2),self.trade('2',1500,1600,1,101)],0,2000,3000,self.cov(),1.)
        self.assertEqual(f['divergence'],'PRICE_UP_SELL_DELTA');self.assertIsNone(f['flow_at_boundary'])

    def test_internal_trade_excluded(self):
        with self.assertRaises(ValueError): normalize(dict(is_internal=True),1000,'BTC_USDT',.01)

    def test_gate_rest_seconds_and_contract_units_differ_from_ws(self):
        raw=dict(id='7',contract='BTC_USDT',create_time=1793638039.776,create_time_ms=1793638039.776,size='-2',price='100')
        parsed=dict(info=raw,timestamp=1793638039776,amount=2.,side='sell')
        row=normalize_gate_rest(parsed,1793638040000,'BTC_USDT',.001)
        self.assertAlmostEqual(row['amount'],.002); self.assertEqual(row['event_ms'],1793638039776)
        self.assertAlmostEqual(row['latency_ms'],224.)
        with self.assertRaises(ValueError): normalize_gate_rest(parsed|dict(timestamp=1793638039),1793638040000,'BTC_USDT',.001)

    def test_executable_contract_checks_lots_and_minimums(self):
        market=dict(contractSize=.001,precision=dict(amount=1),limits=dict(amount=dict(min=1,max=10000),cost=dict(min=5)))
        r=executable_contract(market,10000)
        self.assertEqual(r['contracts'],2);self.assertEqual(r['base_amount'],.002)
        self.assertEqual(r['modeled_notional_usdt'],20)
        self.assertEqual(executable_contract(market,100000)['status'],'REJECT')
        self.assertEqual(executable_contract(market|dict(contractSize=None),10000)['status'],'UNKNOWN')

    def test_signed_schedule_has_no_reversal_without_actual_failure(self):
        path=ROOT/'evidence/additional-2/intelligence-001/signed-market-ranking.csv'
        if not path.exists(): self.skipTest('Requires actual registered signed schedule')
        rows=pd.read_csv(path)
        eligible=rows.loc[(rows.recipe=='sweep')&rows.eligible]
        self.assertTrue(eligible.failed_boundary_confirmed.all())
        self.assertTrue(rows.loc[(rows.recipe=='vwap')&rows.eligible].side.isin(['long','short']).all())

    def test_native_price_recheck_uses_same_cost_and_expiry(self):
        import json
        from types import SimpleNamespace
        from IntelligenceRouterV2 import IntelligenceRegimeV2
        from freqtrade.enums import CandleType
        s=IntelligenceRegimeV2({'candle_type_def':CandleType.FUTURES,'runmode':'dry_run'})
        row=self.row();row['enter_long']=1;row['enter_short']=0
        row['bonus_plan']=json.dumps(research_plan(row,'vwap','long'))
        s.dp=SimpleNamespace(get_analyzed_dataframe=lambda *a:(pd.DataFrame([row]),None),ticker=lambda *a:dict(bid=100.,ask=100.))
        now=row.date+pd.Timedelta(minutes=15)
        self.assertAlmostEqual(s.row_plan('BTC',now,'long',100.)['modeled_loss_per_notional'],.022+.0038)
        self.assertIsNone(s.row_plan('BTC',now,'long',101.))
        order=SimpleNamespace(order_date_utc=now);trade=SimpleNamespace(is_short=False)
        self.assertFalse(s.check_entry_timeout('BTC',trade,order,now))
        self.assertTrue(s.check_entry_timeout('BTC',trade,order,now+pd.Timedelta(minutes=5)))


if __name__=='__main__': unittest.main()
