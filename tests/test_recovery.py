"""Causality, actual settlement-clock accounting and research-only mode regressions."""
import sys
import unittest
from pathlib import Path
from datetime import timedelta
from types import SimpleNamespace
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from recovery_common import *
from recovery_funding import EventClockFunding,install
from recovery_features import augment
from RecoveryPolicyR1 import RecoveryPolicyR1
from freqtrade.exchange.exchange import Exchange
from freqtrade.enums import TradingMode,RunMode,CandleType

class RecoveryRegression(unittest.TestCase):
    def test_seconds_after_hour_funding_survives_preexit_checkpoint_once_both_sides(self):
        # Isolated native accounting regression,NOT a market return experiment.
        install();a=pd.Timestamp('2026-08-01T12:00:00Z');event=a+pd.Timedelta(seconds=3)
        f=pd.DataFrame({'date':[event],'funding_rate':[.001]});m=pd.DataFrame({'date':[a],'open':[100.]})
        joined=Exchange.combine_funding_and_mark(f,m)
        self.assertEqual(joined.date.iloc[0],event)
        for short in [False,True]:
            data={}
            class Position:
                pair='ETH/USDT:USDT';amount=2.;is_short=short;entry_side='sell' if short else 'buy';funding_fee_running=0.
                orders=[SimpleNamespace(ft_order_side=entry_side,filled=2.,order_filled_utc=a)]
                def get_custom_data(self,k,default=None):return data.get(k,default)
                def set_custom_data(self,k,v):data[k]=v
                def set_funding_fees(self,v):self.funding_fee_running=v
            engine=EventClockFunding();engine.trading_mode=TradingMode.FUTURES;engine.futures_data={Position.pair:joined}
            engine.exchange=SimpleNamespace(calculate_funding_fees=Exchange.calculate_funding_fees.__get__(object(),Exchange))
            t=Position()
            engine._run_funding_fees(t,a)
            self.assertEqual(t.funding_fee_running,0)
            # The checkpoint precedes native exit-order funding snapshot at12:45.
            engine._run_funding_fees(t,a+pd.Timedelta(minutes=45))
            expected=.2 if short else -.2
            self.assertAlmostEqual(t.funding_fee_running,expected)
            engine._run_funding_fees(t,a+pd.Timedelta(minutes=45),force=True)
            self.assertAlmostEqual(t.funding_fee_running,expected)
            self.assertEqual(len(data['v3_funding_events']),1)

    def test_no_persistent_or_live_activation(self):
        for mode in [RunMode.DRY_RUN,RunMode.LIVE]:
            s=RecoveryPolicyR1({'runmode':mode,'dry_run':True,'candle_type_def':CandleType.FUTURES})
            with self.assertRaisesRegex(ValueError,'historical research only'):s.bot_start()

    def test_short_held_path_extremes_keep_direction_before_aggregation(self):
        from recovery_report import path_extremes
        q=pd.DataFrame({'high':[101.,95.],'low':[90.,92.]})
        mfe,mae=path_extremes(q,100.,-1)
        self.assertAlmostEqual(mfe,1000.)
        self.assertAlmostEqual(mae,-100.)

    def test_new_features_are_prefix_causal_on_real_sources(self):
        for pair in pairs():
            f=pd.read_pickle(WORK/'development/features'/(slug(pair)+'.pkl'))
            cut=1537
            prefix=augment(f.iloc[:cut].copy())
            for key in ['return24h','expanding','hour_atr_fraction']:
                pd.testing.assert_series_equal(prefix[key].reset_index(drop=True),f[key].iloc[:cut].reset_index(drop=True),check_names=False)

    def test_frozen_momentum_plans_use_completed_clocks_and_legal_geometry(self):
        for window,step in [('development',pd.Timedelta(minutes=15)),('hourly-development',pd.Timedelta(hours=1)),('hourly-independent',pd.Timedelta(hours=1))]:
            plans=read(WORK/window/'plans/momentum.json')
            for pair,items in plans.items():
                f=pd.read_pickle(WORK/window/'features'/(slug(pair)+'.pkl')).set_index('date')
                for at,g in items.items():
                    clock=pd.Timestamp(at);row=f.loc[clock-step]
                    self.assertEqual(clock.hour,0);self.assertTrue(bool(row.eligible))
                    self.assertAlmostEqual(g['risk_fraction'],max(.006,2*row.hour_atr_fraction))
                    self.assertLessEqual(g['risk_fraction'],.025)
                    self.assertEqual(pd.Timestamp(g['expires_at'])-clock,pd.Timedelta(minutes=5))
                    self.assertEqual(g['max_hold_hours'],24)

if __name__=='__main__':unittest.main()
