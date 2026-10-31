"""Truth tables and native semantics; synthetic vectors are NOT economic outcomes."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy
import json
import subprocess
import sys
import unittest
import numpy as np
import pandas as pd
sys.path[:0]=['/lab/scripts','/lab/user_data/strategies']
from PlaybookRiskV1 import session_features, geometry, stake_for, COST_ALLOWANCE
from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
from freqtrade.strategy import merge_informative_pair
from freqtrade.persistence import LocalTrade
from freqtrade.enums import CandleType
CFG={'candle_type_def':CandleType.FUTURES}
from guard import validate
ROOT=Path('/lab')


def vector(n=600):
    x=np.arange(n); c=100+np.sin(x/8)+x*.005
    return pd.DataFrame({'date':pd.date_range('2026-01-01',periods=n,freq='15min',tz='UTC'),
      'open':c-.1,'high':c+1,'low':c-1,'close':c,'volume':1.+(x%5)})


def features():
    d=vector(4)
    d['date']=pd.date_range('2026-01-01 02:00',periods=4,freq='15min',tz='UTC')
    for k,v in {'atr14':1.2,'atr_ratio':.012,'ema20':101.,'ema50':100.,'rvol':2.,
                'ema20_1h':101.,'ema50_1h':100.,'adx_1h':25.,'context_valid_1h':True,
                'contiguous':True,'session_bars':10,'same_session':True,'vwap_valid':True,'vwap':100.,
                'prior_low':99.5,'prior_high':100.5}.items():d[k]=v
    d['date_1h']=(d.date+pd.Timedelta(minutes=15)).dt.floor('1h')-pd.Timedelta(hours=1)
    return d


class Features(unittest.TestCase):
    def test_vwap_weight_reset_and_no_future_volume(self):
        d=vector(4);d['date']=pd.date_range('2026-01-01 23:30',periods=4,freq='15min',tz='UTC')
        for k in ['open','high','low','close']:d[k]=[100.,110.,90.,90.]
        d['volume']=[1.,3.,5.,2.]
        r=session_features(d)
        self.assertEqual(list(r.vwap),[100.,107.5,90.,90.])
        d.loc[3,'volume']=1000000
        pd.testing.assert_series_equal(r.vwap.iloc[:3],session_features(d).vwap.iloc[:3])
        self.assertEqual(list(r.session_bars),[1,2,1,2])
    def test_prior_range_and_prior_volume(self):
        d=vector(40);d['volume']=10.;d.loc[25,'volume']=1000.;d.loc[25,'high']=1000.;d.loc[25,'low']=1.
        r=session_features(d)
        self.assertEqual(r.rvol.iloc[25],100.)
        self.assertEqual(r.prior_high.iloc[25],d.high.iloc[5:25].max())
        self.assertEqual(r.prior_low.iloc[25],d.low.iloc[5:25].min())
        self.assertEqual(r.prior_high.iloc[26],1000.)
    def test_native_hour_alignment(self):
        d=vector(12);h=pd.DataFrame({'date':pd.date_range('2026-01-01',periods=3,freq='1h',tz='UTC'),'known':[10,20,30]})
        r=merge_informative_pair(d,h,'15m','1h',ffill=True)
        self.assertTrue(pd.isna(r.known_1h.iloc[2]))
        self.assertEqual(r.known_1h.iloc[3],10) # 00:45 signal closes01:00
        self.assertEqual(r.known_1h.iloc[6],10)
        self.assertEqual(r.known_1h.iloc[7],20)
    def test_future_append_signals_and_missing_data(self):
        d=vector(900)
        def calculate(cls,df):
            s=cls(CFG);h=df.set_index('date').resample('1h').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).reset_index()
            h=s.populate_indicators_1h(h,{})
            f=merge_informative_pair(df,h,'15m','1h',ffill=True)
            return s.populate_entry_trend(s.populate_indicators(f,{}),{})
        for cls in [VWAPTrendContinuationV1,LiquiditySweepReversalV1]:
            a=calculate(cls,d.iloc[:800].copy());b=calculate(cls,d.copy())
            pd.testing.assert_frame_equal(a,b.iloc[:800])
            pd.testing.assert_frame_equal(a,calculate(cls,d.iloc[:800].copy()))
        d.loc[100,'date']+=pd.Timedelta(minutes=1)
        self.assertFalse(session_features(d).contiguous.iloc[101])


class Signals(unittest.TestCase):
    def test_vwap_long_short_and_no_trade(self):
        s=VWAPTrendContinuationV1(CFG);d=features()
        d['close']=[99.9,100.1,100.1,99.9];d['low']=99.5;d['high']=100.5
        d.loc[2:,'ema20']=99.;d.loc[2:,'ema20_1h']=99.
        r=s.populate_entry_trend(d,{})
        self.assertEqual(list(r.enter_long),[0,1,0,0]);self.assertEqual(list(r.enter_short),[0,0,0,1])
        for col,val in [('volume',0.),('atr14',np.nan),('rvol',.1),('context_valid_1h',False),('same_session',False),('vwap_valid',False),('session_bars',7)]:
            bad=d.copy();bad[col]=val
            r=s.populate_entry_trend(bad,{})
            self.assertEqual(r.enter_long.sum()+r.enter_short.sum(),0)
    def test_sweep_bull_bear_and_reclaim_timing(self):
        s=LiquiditySweepReversalV1(CFG);d=features()
        d['atr14']=1.;d['atr_ratio']=.01
        d['open']=[100.2,99.8,100.2,100.2];d['close']=[100.1,99.9,99.4,100.1]
        d['low']=[99.,99.7,99.,99.];d['high']=[100.3,101.,100.3,100.3]
        d.loc[3,'rvol']=.5
        r=s.populate_entry_trend(d,{})
        self.assertEqual(list(r.enter_long),[1,0,0,0]);self.assertEqual(list(r.enter_short),[0,1,0,0])
        for col,val in [('volume',0.),('atr_ratio',0.),('adx_1h',31.),('prior_low',np.nan)]:
            bad=d.copy();bad[col]=val
            r=s.populate_entry_trend(bad,{})
            self.assertEqual(r.enter_long.sum(),0)


class Callbacks(unittest.TestCase):
    def setUp(self):
        self.s=VWAPTrendContinuationV1(CFG)
        d=features();d['close']=100.;d['low']=99.;d['high']=101.;d['enter_long']=1;d['enter_short']=1
        self.row=d.iloc[-1];self.now=self.row.date.to_pydatetime()+timedelta(minutes=15)
        self.s.dp=SimpleNamespace(get_analyzed_dataframe=lambda *args:(d,None))
    def test_closed_fresh_signal_price_and_expiry(self):
        self.assertIsNotNone(self.s.signal_row('X',self.now,'long'))
        self.assertIsNone(self.s.signal_row('X',self.now-timedelta(seconds=1),'long'))
        self.assertIsNone(self.s.signal_row('X',self.now+timedelta(minutes=5),'long'))
        self.assertEqual(self.s.custom_entry_price('X',None,self.now,101.,None,'long'),100.)
        order=SimpleNamespace(order_date_utc=self.now)
        trade=SimpleNamespace(is_short=False)
        self.assertFalse(self.s.check_entry_timeout('X',trade,order,self.now))
        self.assertTrue(self.s.check_entry_timeout('X',trade,order,self.now+timedelta(minutes=5)))
        self.assertEqual(self.s.adjust_entry_price(None,None,'X',self.now,110.,100.,None,'long'),100.)
    def test_geometry_sides_prices_atr_and_fee_sizing(self):
        for side in ['long','short']:
            g=geometry(self.row,side,100.,.2)
            self.assertIsNotNone(g)
            self.assertTrue(g['stop']<100 if side=='long' else g['stop']>100)
            self.assertAlmostEqual(g['modeled_loss_per_notional'],g['risk_fraction']+COST_ALLOWANCE)
            self.assertEqual(stake_for(g,1.,1000.),25.)
            self.assertEqual(stake_for(g,26.,1000.),0.)
            self.assertEqual(stake_for(g,1.,float('nan')),0.)
            self.assertIsNone(geometry(self.row,side,101.,.2))
        row=self.row.copy();row['atr14']=np.nan
        self.assertIsNone(geometry(row,'long',100.,.2));self.assertEqual(stake_for(None,1.,100.),0.)
    def confirm(self,rate=100.,amount=.25):
        return self.s.confirm_trade_entry('X','limit',amount,rate,'GTC',self.now,None,'long')
    def test_capacity_symbol_fallback_and_daily_utc(self):
        with patch('PlaybookRiskV1.Trade.get_open_trades',return_value=[]),patch('PlaybookRiskV1.Trade.get_trades_proxy',return_value=[]):
            self.assertTrue(self.confirm());self.assertFalse(self.confirm(101.));self.assertFalse(self.confirm(amount=.26))
        for open_trades in [[SimpleNamespace(pair='X',stake_amount=25.)],[SimpleNamespace(pair='Y',stake_amount=25.),SimpleNamespace(pair='Z',stake_amount=25.)]]:
            with patch('PlaybookRiskV1.Trade.get_open_trades',return_value=open_trades):self.assertFalse(self.confirm())
        def closed(dt,pnl):return SimpleNamespace(close_date_utc=dt,close_profit_abs=pnl)
        with patch('PlaybookRiskV1.Trade.get_trades_proxy',return_value=[closed(self.now,-10.)]):
            self.assertFalse(self.s.daily_allowed(self.now))
            self.assertTrue(self.s.daily_allowed(self.now+timedelta(days=1)))
        with patch('PlaybookRiskV1.Trade.get_trades_proxy',side_effect=RuntimeError('unavailable')):
            self.assertFalse(self.s.daily_allowed(self.now))
        with patch('PlaybookRiskV1.Trade.get_open_trades',side_effect=RuntimeError('unavailable')):
            self.assertFalse(self.confirm())
    def test_safe_stake_missing_not_exception_fallback(self):
        self.s.dp=SimpleNamespace(get_analyzed_dataframe=lambda *args:(pd.DataFrame(),None))
        self.assertEqual(self.s.custom_stake_amount('X',self.now,100.,25.,1.,100.,1.,None,'long'),0.)
    def test_native_stop_rounding_roi_hold_and_fill(self):
        for short in [False,True]:
            t=LocalTrade(pair='X',open_rate=100.,amount=.25,stake_amount=25.,is_short=short,leverage=1.,
                open_date=self.now.replace(tzinfo=None),fee_open=.0006,fee_close=.0006,price_precision=.1,precision_mode_price=4)
            store={};t.get_custom_data=lambda k:store.get(k);t.set_custom_data=lambda k,v:store.update({k:v})
            order=SimpleNamespace(ft_order_side=t.entry_side)
            self.s.order_filled('X',t,order,self.now)
            self.assertIn('initial_geometry',store)
            self.s._ft_stop_uses_after_fill=True
            self.s.ft_stoploss_adjust(100.,t,self.now,0.,0.,after_fill=True)
            self.assertTrue(t.stop_loss>100 if short else t.stop_loss<100)
            self.assertAlmostEqual(t.stop_loss/.1,round(t.stop_loss/.1))
            self.assertAlmostEqual(self.s.custom_roi('X',t,self.now,0,None,'short' if short else 'long'),store['initial_geometry']['risk_fraction']*2)
            self.assertEqual(self.s.custom_exit('X',t,self.now+timedelta(hours=8),100.,0.),'max_hold_8h')
            self.assertIsNone(self.s.custom_exit('X',t,self.now+timedelta(hours=7),100.,0.))
    def test_native_stop_precedes_roi_same_bar(self):
        # Direct official should_exit exercises native ambiguity ordering, no invented trade result.
        from freqtrade.enums import ExitType
        s=VWAPTrendContinuationV1(CFG);s.minimal_roi={0:.01};s.use_custom_roi=False;s.use_custom_stoploss=False
        t=LocalTrade(pair='X',open_rate=100.,amount=1.,stake_amount=100.,is_short=False,leverage=1.,
          open_date=(self.now-timedelta(minutes=15)).replace(tzinfo=None),fee_open=.0006,fee_close=.0006,price_precision=.01,precision_mode_price=4)
        t.get_custom_data=lambda k:{'stop':99.,'target_roi':.01}
        s.dp=SimpleNamespace(runmode=SimpleNamespace(value='backtest'))
        exits=s.should_exit(t,100.,self.now,enter=False,exit_=False,low=96.,high=104.)
        types=[x.exit_type for x in exits]
        self.assertIn(ExitType.STOP_LOSS,types);self.assertIn(ExitType.ROI,types)
        self.assertLess(types.index(ExitType.STOP_LOSS),types.index(ExitType.ROI))


class Registration(unittest.TestCase):
    def test_new_configs_and_forbidden_parameters(self):
        for filename in ['research-vwap.json','research-sweep.json']:
            c=json.loads((ROOT/'configs'/filename).read_text());validate(c)
            for key,val in [('leverage',2),('strategy_path','/tmp'),('trailing_stop',True),('use_custom_stoploss',False)]:
                bad=copy.deepcopy(c);bad[key]=val
                with self.assertRaises(ValueError):validate(bad)
    def test_challenger_cannot_start_paper_or_override_config(self):
        for extra in [[],['-s','LiquiditySweepReversalV1'],['--strategy-path','/tmp']]:
            r=subprocess.run([sys.executable,'/lab/scripts/guard.py','trade','-c','/lab/configs/research-vwap.json']+extra,capture_output=True,text=True)
            self.assertEqual(r.returncode,2)
    def test_original_freeze_unchanged(self):
        import hashlib
        for line in (ROOT/'evidence/session-1/freeze.sha256').read_text().splitlines():
            sha,path=line.split(maxsplit=1);self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),sha)

if __name__=='__main__':unittest.main()
