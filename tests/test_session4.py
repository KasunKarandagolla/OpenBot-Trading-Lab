"""Real native dry-order simulation, protection-before-callback and recovery contracts."""
import json
import math
from pathlib import Path
import sys
import tempfile
import os
import unittest
from unittest.mock import Mock,patch
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import session4_common
from session4_common import ROOT,OUT,DATA,STATE
from PaperPolicyV4 import PaperPolicyV4
from freqtrade.exchange.gate import Gate
from freqtrade.persistence import Trade,Order,init_db
from freqtrade.enums import CandleType,TradingMode,RunMode
from ccxt import TICK_SIZE
from policy_features import plan
import pandas as pd

CLOCK=datetime(2026,11,3,12,0,tzinfo=timezone.utc)
PAIR='ETH/USDT:USDT'


class NativeProtection(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);init_db('sqlite:///'+str(self.root/'native.sqlite'))
        contract=dict(verified=True,contract_size=.01,step_contracts=1,min_contracts=1,min_notional=1,taker=.00075,
            price_precision=.01,observed_at=CLOCK.isoformat(),funding_interval_seconds=28800,tiers=[])
        (self.root/'contracts.json').write_text(json.dumps({PAIR:contract}))
        self.cfg=dict(dry_run=True,candle_type_def=CandleType.FUTURES,policy_state=str(self.root/'account.sqlite'),
            policy_events=str(self.root/'events.jsonl'),policy_contracts=str(self.root/'contracts.json'))
        self.s=PaperPolicyV4(self.cfg);self.s.bot_start();self.s.dp=Mock();self.s.dp.get_analyzed_dataframe.return_value=(pd.DataFrame(),None)
        self.s._ft_stop_uses_after_fill=True
    def tearDown(self):
        self.s._store.close();Trade.session.remove();Trade.session.bind.dispose();self.tmp.cleanup()
    def trade(self,short=False,lev=1):
        t=Trade(pair=PAIR,exchange='gate',open_rate=100,open_date=CLOCK,stake_amount=10/lev,amount=.1,amount_requested=.1,
            fee_open=.00075,fee_close=.00075,is_open=True,is_short=short,leverage=lev,trading_mode=TradingMode.FUTURES,
            amount_precision=1,price_precision=.01,precision_mode=TICK_SIZE,precision_mode_price=TICK_SIZE,contract_size=.01,orders=[])
        Trade.session.add(t);Trade.commit();return t
    def test_native_initial_stop_exists_when_callback_raises_at_1_10_20x_both_sides(self):
        for lev in (1,10,20):
            for short in (False,True):
                t=self.trade(short,lev);self.s.stoploss=-.025*lev
                with patch.object(self.s,'custom_stoploss',side_effect=RuntimeError('callback failure')):
                    self.s.ft_stoploss_adjust(100,t,CLOCK,0,0)
                self.assertLessEqual(abs(t.stop_loss/100-1),.025+1e-12)
                self.assertGreaterEqual(abs(t.stop_loss/100-1),.0249-1e-12)
                self.assertAlmostEqual(abs(t.initial_stop_loss_pct),.025*lev)
    def test_outage_and_store_failure_keep_native_stop_and_exit_paths(self):
        for short in (False,True):
            t=self.trade(short,10);self.s.stoploss=-.25
            t.adjust_stop_loss(100,self.s.stoploss,initial=True)
            g=dict(stop=101 if short else 99,target=97 if short else 103,max_hold_hours=4)
            t.set_custom_data('policy_plan',g)
            with patch.object(self.s,'sync_trade',side_effect=RuntimeError('store outage')):
                self.assertIsNone(self.s.custom_stoploss(PAIR,t,CLOCK,100,0))
                self.assertEqual(self.s.custom_exit(PAIR,t,CLOCK,102 if short else 98,0),'protective_level_breach')
                self.assertEqual(self.s.custom_exit(PAIR,t,CLOCK+timedelta(hours=4),100,0),'max_hold_4h')
            self.assertLessEqual(abs(t.stop_loss/100-1),.025+1e-12)
    def test_after_fill_and_restart_cannot_widen_native_stop(self):
        for short in (False,True):
            t=self.trade(short,10);self.s.stoploss=-.25
            t.adjust_stop_loss(100,self.s.stoploss,initial=True)
            t.set_custom_data('policy_plan',dict(stop=101 if short else 99,target=97 if short else 103,max_hold_hours=4,decision_id='recovery'))
            self.s.ft_stoploss_adjust(100,t,CLOCK,0,0,after_fill=True)
            expected=t.stop_loss;Trade.commit();id=t.id;Trade.session.expire_all();t=Trade.session.get(Trade,id)
            t.set_custom_data('policy_plan',dict(stop=102 if short else 98,target=97 if short else 103,max_hold_hours=4,decision_id='recovery'))
            self.s.ft_stoploss_adjust(100,t,CLOCK,0,0,after_fill=True)
            self.assertEqual(t.stop_loss,expected)
    def test_missing_account_and_stale_source_fail_closed(self):
        self.s._source_health='SOURCE_UNAVAILABLE'
        self.assertEqual(self.s.custom_stake_amount(PAIR,CLOCK,100,25,1,100,1,'test','long'),0)
        self.assertFalse(self.s.confirm_trade_entry(PAIR,'market',.1,100,'GTC',CLOCK,'test','long'))


class NativeDryOrderLifecycle(NativeProtection):
    def setUp(self):
        super().setUp()
        cfg=dict(dry_run=True,runmode=RunMode.DRY_RUN,trading_mode='futures',margin_mode='isolated',stake_currency='USDT',
            fee=.00075,exchange=dict(name='gate',key='',secret='',pair_whitelist=[PAIR],enable_ws=False,
            ccxt_config={'has':{'fetchCurrencies':False}}))
        self.exchange=Gate(cfg,validate=False)
        m=json.loads((DATA.parent/'contract-source.json').read_text())[PAIR]['market']
        self.exchange._api.set_markets([m]);self.exchange._api_async.set_markets([m]);self.exchange._markets=self.exchange._api.markets
        self.exchange._api.create_order=Mock(side_effect=AssertionError('EXTERNAL ORDER MUST NEVER BE CALLED'))
        self.exchange.fetch_l2_order_book=Mock(return_value=dict(bids=[[99.99,100]],asks=[[100.01,100]]))
    def tearDown(self):
        self.exchange.close();super().tearDown()
    def native_order(self,kind,side,rate=100):
        result=self.exchange.create_order(pair=PAIR,ordertype=kind,side=side,amount=.1,rate=rate,reduceOnly=False,time_in_force='GTC',leverage=1)
        self.trace('NATIVE_CREATE',result)
        return result
    def trace(self,event,order):
        path=os.environ.get('SESSION4_TEST_EVIDENCE_PATH')
        if path:
            with open(path,'a') as file:file.write(json.dumps(dict(event=event,order=order,classification='ISOLATED_NATIVE_DRY_ORDER_TEST_CONTROLLED_BOOK_NOT_OBSERVED_LIVE_FILL'),default=str)+'\n')
    def persist(self,t,raw):
        o=Order.parse_from_ccxt_object(raw,PAIR,raw['side'],.1,raw['price']);t.orders.append(o);Trade.commit();return o
    def test_native_limit_open_cross_fill_and_sqlite_restart_recovery(self):
        for short in (False,True):
            t=self.trade(short);raw=self.native_order('limit',t.entry_side);self.assertEqual(raw['status'],'open')
            o=self.persist(t,raw);id=raw['id'];self.exchange._dry_run_open_orders.clear()
            # Fetch restores the native order from SQLite, without an exchange order API.
            self.assertEqual(self.exchange.fetch_dry_run_order(id)['status'],'open')
            self.exchange.fetch_l2_order_book.return_value=dict(bids=[[100.02 if short else 99.97,100]],asks=[[100.03 if short else 99.98,100]])
            filled=self.exchange.fetch_dry_run_order(id);self.assertEqual(filled['status'],'closed');self.assertEqual(filled['filled'],.1)
            self.trace('NATIVE_FETCH_AFTER_SQLITE_RECOVERY_AND_CROSS',filled)
            o.update_from_ccxt_object(filled);t.update_trade(o);Trade.commit();self.assertAlmostEqual(t.amount,.1)
            self.exchange.fetch_l2_order_book.return_value=dict(bids=[[99.99,100]],asks=[[100.01,100]])
        self.exchange._api.create_order.assert_not_called()
    def test_native_market_long_short_entries_and_exits_reconcile_fees(self):
        for short in (False,True):
            t=self.trade(short);entry=self.native_order('market',t.entry_side);self.assertEqual(entry['status'],'closed')
            o=self.persist(t,entry);t.update_trade(o)
            self.exchange.fetch_l2_order_book.return_value=dict(bids=[[101.99 if not short else 97.99,100]],asks=[[102.01 if not short else 98.01,100]])
            exit=self.native_order('market',t.exit_side,102 if not short else 98);x=self.persist(t,exit);t.update_trade(x);Trade.commit()
            self.assertFalse(t.is_open);self.assertGreater(t.close_profit_abs,0)
            self.assertEqual(entry['fee']['rate'],.00075);self.assertEqual(exit['fee']['rate'],.00075)
            self.exchange.fetch_l2_order_book.return_value=dict(bids=[[99.99,100]],asks=[[100.01,100]])
        self.exchange._api.create_order.assert_not_called()
    def test_native_cancel_pending_limit(self):
        raw=self.native_order('limit','buy',99)
        self.assertEqual(raw['status'],'open')
        result=self.exchange.cancel_order(raw['id'],PAIR)
        self.trace('NATIVE_CANCEL',result)
        self.assertEqual(result['status'],'canceled');self.assertEqual(result['filled'],0)
        self.exchange._api.create_order.assert_not_called()


class ReviewedGuard(unittest.TestCase):
    def test_exact_modes_and_credentials_exposure_and_override_rejection(self):
        from session4_safety import validate_paper,verify_frozen
        import time
        verify_frozen()
        for mode in ('limit','market'):
            cfg=json.loads((ROOT/'configs'/('paper-policy-'+mode+'.json')).read_text());cfg['session4_deadline']=time.time()+120
            validate_paper(cfg)
            for edit in [dict(dry_run=False),dict(policy_leverage=10),dict(force_entry_enable=True),dict(max_open_trades=3),dict(stoploss=-.99)]:
                with self.assertRaises(ValueError):validate_paper(dict(cfg,**edit))
            bad=json.loads(json.dumps(cfg));bad['exchange']['key']='fixture-forbidden'
            with self.assertRaises(ValueError):validate_paper(bad)
            with self.assertRaises(ValueError):validate_paper(dict(cfg,session4_deadline=time.time()+301))
            from session4_safety import launch
            with self.assertRaisesRegex(ValueError,'CLI override forbidden: fee'):
                launch(['trade'],cfg,dict(fee=0,datadir='/lab/user_data/data/cache/session4/gate'),[str(ROOT/'work/session4'/('runtime-'+mode+'.json'))])


class AtomicPaperAccount(unittest.TestCase):
    def test_failed_checkpoint_rolls_back_consumed_close_and_restart_recovers_streak(self):
        from paper_state import PaperState
        import sqlite3
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.sqlite';s=PaperState(path)
            s.checkpoint(CLOCK.timestamp(),1000,[],True)
            t=Mock(id=1,close_date_utc=CLOCK,close_profit_abs=-1)
            s.db.execute("CREATE TRIGGER fail_checkpoint BEFORE UPDATE ON kv WHEN NEW.k='account' BEGIN SELECT RAISE(ABORT,'injected crash boundary'); END")
            s.db.commit()
            with self.assertRaises(sqlite3.IntegrityError):s.checkpoint(CLOCK.timestamp()+1,999,[t],True)
            self.assertEqual(s.db.execute("SELECT count(*) FROM events").fetchone()[0],0)
            s.db.execute('DROP TRIGGER fail_checkpoint');s.db.commit();s.close();s=PaperState(path)
            self.assertEqual(s.checkpoint(CLOCK.timestamp()+2,999,[t],True)['loss_streak'],1)
            self.assertEqual(s.checkpoint(CLOCK.timestamp()+3,999,[t],True)['loss_streak'],1)
            with self.assertRaises(ValueError):s.checkpoint(CLOCK.timestamp(),999,[t],True)
            s.close()


if __name__=='__main__':unittest.main(verbosity=2)
