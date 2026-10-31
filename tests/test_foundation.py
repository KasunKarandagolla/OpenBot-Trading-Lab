"""Synthetic fixtures test mechanics only; never economic evidence."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
import numpy as np
import pandas as pd
sys.path[:0]=['/lab/scripts','/lab/user_data/strategies']
from guard import validate, merge
from scan_export import shortlist
from validate_data import inspect
from report import summarize
from TrendPullbackBaselineV1 import TrendPullbackBaselineV1
ROOT=Path('/lab')


class Safety(unittest.TestCase):
    def setUp(self):self.c=json.loads((ROOT/'configs/research.json').read_text())
    def test_safe_public_config(self):validate(self.c)
    def test_pinned_installed_version(self):
        import freqtrade,ccxt
        self.assertEqual(freqtrade.__version__,'2026.10');self.assertEqual(ccxt.__version__,'4.5.90')
    def test_live_input_refused_before_engine_import(self):
        c=copy.deepcopy(self.c);c['dry_run']=False
        p=ROOT/'user_data/runtime/unsafe-test.json';p.write_text(json.dumps(c))
        try:
            r=subprocess.run([sys.executable,'/lab/scripts/guard.py','trade','--config',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2);self.assertIn('dry_run must be true',r.stderr)
            self.assertNotIn('freqtrade',r.stdout)
        finally:p.unlink()
    def test_keys_and_nested_overrides_refused(self):
        for change in [{'exchange':{'key':'fixture-not-a-key'}},{'add_config_files':['elsewhere']},{'max_open_trades':3},{'stake_amount':'unlimited'},{'force_entry_enable':True},{'position_adjustment_enable':True}]:
            c=merge(copy.deepcopy(self.c),change)
            with self.assertRaises(ValueError):validate(c)
    def test_all_environment_overrides_refused(self):
        import os
        env=dict(os.environ,FREQTRADE__DRY_RUN='false')
        r=subprocess.run([sys.executable,'/lab/scripts/guard.py','--version'],env=env,capture_output=True,text=True)
        self.assertEqual(r.returncode,2)
    def test_unsafe_cli_override_refused(self):
        r=subprocess.run([sys.executable,'/lab/scripts/guard.py','trade','--config','/lab/configs/research.json','--stake-amount','unlimited'],capture_output=True,text=True)
        self.assertEqual(r.returncode,2)
    def test_attached_config_and_strategy_alias_cannot_bypass_guard(self):
        c=copy.deepcopy(self.c);c['dry_run']=False
        p=ROOT/'user_data/runtime/unsafe-test.json';p.write_text(json.dumps(c))
        try:
            for extra in [['-c'+str(p)],['-s','OtherStrategy']]:
                r=subprocess.run([sys.executable,'/lab/scripts/guard.py','trade','--config','/lab/configs/research.json']+extra,capture_output=True,text=True)
                self.assertEqual(r.returncode,2)
        finally:p.unlink()
    def test_loopback_publication_and_digest(self):
        c=json.loads((ROOT/'user_data/runtime/compose-safety.json').read_text())
        for name,svc in c['services'].items():
            self.assertIn('@sha256:',svc['image'])
            for binding in svc.get('ports',[]):self.assertEqual(binding['host_ip'],'127.0.0.1')
            self.assertFalse(any('API_KEY' in k or k.startswith('FREQTRADE__') for k in svc.get('environment',{})))


class Scanner(unittest.TestCase):
    def setUp(self):
        self.rules=json.loads((ROOT/'configs/scan-rules.json').read_text())
        self.markets={s:{'active':True,'swap':True,'linear':True,'settle':'USDT','quote':'USDT','info':{'contract_type':'','in_delisting':False,'is_pre_market':False,'launch_time':-10000000}} for s in ['A/USDT:USDT','B/USDT:USDT','C/USDT:USDT']}
        self.t={s:{'quoteVolume':20000000,'bid':100,'ask':100.1,'timestamp':1000000} for s in self.markets}
    def test_deterministic_deduplicated_bounded(self):
        self.rules['limit']=2
        a=shortlist(self.markets,self.t,self.rules,1000000)
        b=shortlist(dict(reversed(list(self.markets.items()))),self.t,self.rules,1000000)
        self.assertEqual(a,b);self.assertEqual([r['symbol'] for r in a[1]],['A/USDT:USDT','B/USDT:USDT'])
    def test_spot_inverse_inactive_excluded(self):
        self.markets['A/USDT:USDT']['swap']=False
        self.markets['B/USDT:USDT']['linear']=False
        self.markets['C/USDT:USDT']['active']=False
        self.assertEqual(shortlist(self.markets,self.t,self.rules,1000000)[0:2],(0,[]))
    def test_missing_spread_volume_stale_never_pass(self):
        self.t['A/USDT:USDT']['bid']=None
        self.t['B/USDT:USDT']['quoteVolume']=None
        self.t['C/USDT:USDT']['timestamp']=0
        result=shortlist(self.markets,self.t,self.rules,1000000)
        self.assertEqual(result[1],[]);self.assertEqual(len(result[2]),3)
    def test_tradfi_delisting_and_age_unknown_excluded(self):
        self.markets['A/USDT:USDT']['info']['contract_type']='stocks'
        self.markets['B/USDT:USDT']['info']['in_delisting']=True
        self.markets['C/USDT:USDT']['info'].pop('launch_time')
        self.assertEqual(shortlist(self.markets,self.t,self.rules,1000000)[1],[])
    def test_empty_safe(self):self.assertEqual(shortlist({}, {},self.rules,1000000)[1],[])


class DataChecks(unittest.TestCase):
    def setUp(self):
        self.start=pd.Timestamp('2026-07-01',tz='UTC');self.end=self.start+pd.Timedelta(hours=1)
        self.now=self.end+pd.Timedelta(days=1)
        self.df=pd.DataFrame({'date':pd.date_range(self.start,periods=4,freq='15min'),'open':100.,'high':102.,'low':99.,'close':101.,'volume':1.})
    def check(self,df):return inspect(df,900,self.start,self.end,self.now)['errors']
    def test_valid(self):self.assertEqual(self.check(self.df),[])
    def test_gap_duplicate_bad_price_detected(self):
        self.assertIn('MISSING_OR_IRREGULAR_BARS',self.check(self.df.drop(1).reset_index(drop=True)))
        self.assertIn('DUPLICATE_TIMESTAMP',self.check(pd.concat([self.df,self.df.tail(1)],ignore_index=True)))
        df=self.df.copy();df.loc[0,'close']=-1
        self.assertIn('NONPOSITIVE_PRICE',self.check(df))
    def test_incomplete_warmup_and_alignment(self):
        self.now=self.end-pd.Timedelta(minutes=1)
        self.assertIn('INCOMPLETE_CANDLE',self.check(self.df))
        self.assertIn('MISSING_START_OR_WARMUP',self.check(self.df.iloc[1:].reset_index(drop=True)))
        df=self.df.copy();df['date']+=pd.Timedelta(seconds=1)
        self.assertIn('MISALIGNED_TIMESTAMP',self.check(df))
    def test_timezone_and_funding_schema(self):
        df=self.df.copy();df['date']=df.date.dt.tz_localize(None)
        self.assertIn('SOURCE_TIMEZONE_NOT_UTC',self.check(df))
        funding=pd.DataFrame({'date':pd.date_range(self.start,periods=3,freq='8h'),'funding_rate':[-.0001,0.,.0002]})
        self.assertEqual(inspect(funding,28800,self.start,self.end,self.now,True)['errors'],[])
        self.assertIn('SCHEMA_MISMATCH',inspect(funding,28800,self.start,self.end,self.now)['errors'])
    def test_finite_ohlc_range_volume(self):
        for column,value,reason in [('close',np.nan,'NONFINITE_OHLCV'),('high',99.,'INVALID_OHLC_RANGE'),('volume',-1.,'NEGATIVE_VOLUME')]:
            df=self.df.copy();df.loc[0,column]=value
            self.assertIn(reason,self.check(df))


class Strategy(unittest.TestCase):
    def setUp(self):self.s=TrendPullbackBaselineV1({})
    def test_exact_symmetric_signal_fixture(self):
        # SYNTHETIC feature-level truth table; does not claim market performance.
        df=pd.DataFrame({'close':[99.,101.,101.,99.,100.], 'ema20':[100.]*5,'ema50':[98.,98.,102.,102.,100.], 'atr_ratio':[.005]*5,'volume':[1.]*5})
        r=self.s.populate_entry_trend(df,{})
        self.assertEqual(list(r.enter_long),[0,1,0,0,0]);self.assertEqual(list(r.enter_short),[0,0,0,1,0])
    def test_no_volume_or_atr_no_setup(self):
        df=pd.DataFrame({'close':[99.,101.],'ema20':[100.,100.],'ema50':[98.,98.],'atr_ratio':[.005,.005],'volume':[1.,0.]})
        self.assertEqual(self.s.populate_entry_trend(df,{})['enter_long'].sum(),0)
    def test_append_future_and_determinism(self):
        x=np.arange(600);close=100+np.sin(x/9)+x/100
        df=pd.DataFrame({'date':pd.date_range('2025-01-01',periods=600,freq='15min',tz='UTC'),'open':close,'high':close+1,'low':close-1,'close':close,'volume':1.})
        def evaluate(d):return self.s.populate_exit_trend(self.s.populate_entry_trend(self.s.populate_indicators(d.copy(),{}),{}),{})
        a=evaluate(df.iloc[:400]);b=evaluate(df)
        pd.testing.assert_frame_equal(a,b.iloc[:400])
        pd.testing.assert_frame_equal(a,evaluate(df.iloc[:400]))
    def test_risk_and_timeout(self):
        self.assertEqual(self.s.stoploss,-.02);self.assertEqual(self.s.minimal_roi,{'0':.03})
        self.assertFalse(self.s.position_adjustment_enable);self.assertFalse(self.s.trailing_stop)
        self.assertEqual(self.s.leverage('',datetime.now(timezone.utc),100,5,10,None,'long'),1)
        from types import SimpleNamespace
        now=datetime.now(timezone.utc);trade=SimpleNamespace(open_date_utc=now-timedelta(hours=12))
        self.assertEqual(self.s.custom_exit('',trade,now,100,0),'max_hold_12h')


class Backtest(unittest.TestCase):
    def test_zero_trade_report(self):
        s=summarize([]);self.assertEqual(s['trades'],0);self.assertIsNone(s['profit_factor']);self.assertIsNone(s['win_rate'])
    def test_protocol_is_real_futures_explicit_costs(self):
        p=json.loads((ROOT/'research/protocol.json').read_text())
        self.assertEqual(p['exchange'],'gate');self.assertEqual(p['fee_per_side'],.0006)
        self.assertTrue(all(s.endswith('/USDT:USDT') for s in p['pairs']))
    def test_actual_export_and_provenance_when_present(self):
        p=ROOT/'evidence/session-1/market-data-manifest.json'
        if not p.exists():self.skipTest('real download not executed here')
        m=json.loads(p.read_text());self.assertEqual(m['fidelity'],'ACTUAL_PUBLIC_MARKET');self.assertTrue(m['valid_for_backtest'])
        p=ROOT/'evidence/session-1/backtest-summary.json'
        if not p.exists():self.skipTest('native backtest not executed here')
        m=json.loads(p.read_text());self.assertIn('0.0006',m['fees']);self.assertGreaterEqual(len(m['limitations']),4)
        import csv
        with (ROOT/'evidence/session-1/trade-ledger.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),m['summary']['trades'])
        self.assertAlmostEqual(sum(float(r['profit_abs']) for r in rows),m['net_profit_usdt'])
        self.assertTrue(all(float(r['leverage'])==1 and float(r['stake_amount'])<=25 for r in rows))
        self.assertTrue(any(r['is_short']=='True' for r in rows))
        self.assertTrue(any(r['is_short']=='False' for r in rows))

if __name__=='__main__':unittest.main()
