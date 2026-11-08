"""Native Freqtrade callback/guard checks; unit fixtures are explicitly synthetic."""
from pathlib import Path
import sys
import tempfile
import hashlib
import json
import unittest
from types import SimpleNamespace
import pandas as pd
from freqtrade.enums import RunMode
from freqtrade.persistence import LocalTrade
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/session3_v3'))
from BreakoutAcceptanceRetest import BreakoutAcceptanceRetest
from SweepReclaimReversal import SweepReclaimReversal


class NativeV3Callbacks(unittest.TestCase):
    def sample(self,family='BREAKOUT_RETEST',side='long'):
        sign=1 if side=='long' else -1
        return dict(decision_id='fixture',symbol='FILUSDT',side=side,family=family,variant='retest',
                    feature_version='multi-playbook-v3.0.2',entry=100.,stop=100-sign*1.,target=100+sign*3.,
                    decision_at='2026-08-01T00:05Z',earliest_order_at='2026-08-01T00:05Z',expires_at='2026-08-01T00:10Z',
                    boundary_known_at='2026-07-31T23:00Z',max_hold_minutes=480 if family=='BREAKOUT_RETEST' else 240,
                    boundary=100.,atr15=1.,admission_cost_allowance=.0033,max_deviation=.0015,leverage=1,
                    notional_cap=25,execution_authority='NONE',diagnostics='GEOMETRY_PASS_RESEARCH_ONLY')

    def strategy(self,book='BREAKOUT_RETEST',side='long'):
        strategy=BreakoutAcceptanceRetest({}) if book=='BREAKOUT_RETEST' else SweepReclaimReversal({})
        strategy.plans={'fixture':self.sample(book,side)}
        return strategy

    def test_long_short_confirm_expiry_notional_and_no_chase(self):
        for book in ['BREAKOUT_RETEST','SWEEP_RECLAIM']:
            for side in ['long','short']:
                s=self.strategy(book,side);at=pd.Timestamp('2026-08-01T00:05Z').to_pydatetime()
                args=('FIL/USDT:USDT','limit',.25,100.,'GTC',at,'fixture',side)
                self.assertTrue(s.confirm_trade_entry(*args))
                self.assertFalse(s.confirm_trade_entry('FIL/USDT:USDT','limit',.25,101.,'GTC',at,'fixture',side))
                self.assertFalse(s.confirm_trade_entry('FIL/USDT:USDT','limit',.26,100.,'GTC',at,'fixture',side))
                self.assertFalse(s.confirm_trade_entry('FIL/USDT:USDT','limit',.25,100.,'GTC',at+pd.Timedelta(minutes=5),'fixture',side))
                self.assertTrue(s.check_entry_timeout('',SimpleNamespace(enter_tag='fixture'),None,at+pd.Timedelta(minutes=5)))

    def test_native_fixed_stop_roi_and_hold_callbacks(self):
        for side in ['long','short']:
            s=self.strategy(side=side);at=pd.Timestamp('2026-08-01T00:05Z').to_pydatetime()
            t=LocalTrade(pair='FIL/USDT:USDT',open_rate=100.,amount=.25,stake_amount=25.,is_short=side=='short',leverage=1.,
                         open_date=at,enter_tag='fixture',fee_open=.0005,fee_close=.0005)
            value=s.custom_stoploss(t.pair,t,at,100.,0.)
            self.assertAlmostEqual(value,.01)
            self.assertAlmostEqual(s.custom_roi(t.pair,t,at,0,'fixture',side),t.calc_profit_ratio(s.plans['fixture']['target']))
            s.dp=SimpleNamespace(get_analyzed_dataframe=lambda *_:(pd.DataFrame({'date':[pd.Timestamp(at)-pd.Timedelta(minutes=5)],'close':[100.]}),None))
            self.assertEqual(s.custom_exit(t.pair,t,at+pd.Timedelta(hours=8),100.,0.),'TIME_CAP')
            self.assertEqual(s.custom_exit(t.pair,t,at+pd.Timedelta(hours=4),100.,-.001),'NO_PROGRESS_TIMEOUT')
            self.assertEqual(s.leverage(),1.)

    def test_offline_guard_and_plan_tampering(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'plans.json';path.write_text(json.dumps([self.sample()]))
            cfg=dict(runmode=RunMode.BACKTEST,dry_run=True,recovery_plans=str(path),plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            s=BreakoutAcceptanceRetest(cfg);s.bot_start()
            path.write_text('[]')
            with self.assertRaisesRegex(ValueError,'INTEGRITY'):s.bot_start()
            cfg['runmode']=RunMode.DRY_RUN
            with self.assertRaisesRegex(ValueError,'OFFLINE'):s.bot_start()

    def test_signal_row_precedes_native_execution_bar(self):
        s=self.strategy();d=pd.DataFrame({'date':pd.date_range('2026-08-01T00:00Z',periods=3,freq='5min')})
        out=s.populate_entry_trend(d,{'pair':'FIL/USDT:USDT'})
        self.assertEqual(out.enter_long.tolist(),[1,0,0])
        self.assertEqual(s.custom_stake_amount('',None,100.,25.,1.,100.,1.,'fixture','long'),25.)
        self.assertEqual(s.custom_stake_amount('',None,100.,25.,1.,100.,20.,'fixture','long'),0.)

if __name__=='__main__':unittest.main()
