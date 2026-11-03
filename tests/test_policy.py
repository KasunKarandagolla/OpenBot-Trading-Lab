"""Native long/short lifecycle, causal signal and leveraged account contracts."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'research/policy')]
import policy_common
import unittest
import tempfile
from decimal import Decimal as D
import json
import math
import numpy as np
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock,patch
import pandas as pd
from policy_risk import Account,size,health,liquidation
from policy_state import StateStore
from policy_features import plan,execution_plan,features
from PolicyV3 import PolicyManagedV3,PolicyFixedV3
from freqtrade.persistence import Trade,Order,init_db
from freqtrade.enums import TradingMode,MarginMode,CandleType
from freqtrade.freqtradebot import FreqtradeBot
from ccxt import TICK_SIZE

CLOCK=datetime(2026,10,1,tzinfo=timezone.utc)

def contract():
    return dict(verified=True,contract_size=.01,step_contracts=1,min_contracts=1,min_notional=1,taker=.00075,
        tiers=[dict(min_notional=0,max_notional=100000,maintenance_rate=.005,max_leverage=20,maintenance_deduction=0)])

def account(**kwargs):
    d=dict(cash=1000,unrealized_net=0,free_collateral=1000,posted_margin=0,pending_margin=0,open_risk=0,pending_risk=0,
        gross_notional=0,correlated_notional=0,positions=0,day_start_equity=1000,peak_equity=1000,asof=CLOCK.timestamp())
    d.update(kwargs);return Account(**d)

class RiskTests(unittest.TestCase):
    def size(self,a=None,**kwargs):
        k=dict(clock=CLOCK.timestamp(),side='long',entry=100,stop=99,leverage=10,contract=contract(),cap=100)
        k.update(kwargs);return size(a or account(),**k)
    def test_leverage_holds_notional_and_loss_constant(self):
        cases=[self.size(leverage=l) for l in [1,10,20]]
        self.assertTrue(all(r['status']=='PASS' for r in cases))
        self.assertEqual(len({r['planned_loss'] for r in cases}),1)
        self.assertAlmostEqual(cases[0]['margin'],cases[2]['margin']*20)
    def test_long_short_liquidation_symmetric_clearance(self):
        l=self.size();s=self.size(side='short',stop=101)
        self.assertTrue(l['liquidation_price']<99);self.assertTrue(s['liquidation_price']>101)
    def test_20x_never_compresses_stop(self):
        r=self.size(stop=97.5,leverage=20,contract=contract()|dict(tiers=[dict(min_notional=0,max_notional=1e5,maintenance_rate=.02,max_leverage=20,maintenance_deduction=0)]))
        self.assertEqual(r['reason'],'STOP_LIQUIDATION_CLEARANCE_UNDER_1_PERCENT')
    def test_missing_tiers_only_fully_collateralized_1x(self):
        c=contract()|dict(tiers=[])
        self.assertEqual(self.size(contract=c)['status'],'REJECT')
        self.assertEqual(self.size(contract=c,leverage=1)['status'],'PASS')
    def test_pending_entries_consume_risk_and_margin(self):
        self.assertEqual(self.size(account(pending_risk=5))['status'],'REJECT')
        self.assertEqual(self.size(account(pending_margin=1000))['status'],'REJECT')
    def test_open_losses_halt_even_without_closed_losses(self):
        self.assertEqual(self.size(account(unrealized_net=-11))['reason'],'DAILY_MARK_TO_MARKET_LOSS')
    def test_peak_drawdown_correlation_and_missing_state(self):
        for a in [account(peak_equity=1100),account(correlated_notional=500),account(complete=False),account(asof=0),account(positions=2)]:
            self.assertEqual(self.size(a)['status'],'REJECT')
    def test_loss_streak_cooldown(self):
        self.assertEqual(self.size(account(loss_streak=3,cooldown_until=CLOCK.timestamp()+1))['status'],'REJECT')
    def test_lot_rounding_cannot_exceed_budget(self):
        r=self.size(cap=99.999);self.assertLessEqual(r['notional'],99.999);self.assertAlmostEqual(r['contracts']%1,0)
    def test_minimum_order_and_tier_ceiling(self):
        self.assertEqual(self.size(contract=contract()|dict(min_contracts=1000))['status'],'REJECT')
        c=contract();c['tiers'][0]['max_leverage']=5
        self.assertEqual(self.size(contract=c)['reason'],'CONTRACT_TIER_LEVERAGE_LIMIT')

class GeometryTests(unittest.TestCase):
    def row(self,**kwargs):
        d=dict(date=pd.Timestamp(CLOCK),close=100.,low=99.5,high=100.5,atr14=.6,pullback_low=99.,pullback_high=101.,prior_low=99.4,prior_high=100.6)
        d.update(kwargs);return pd.Series(d)
    def test_logical_long_short_geometry(self):
        l,_=plan(self.row(),'continuation','long');s,_=plan(self.row(),'continuation','short')
        self.assertIsNotNone(l);self.assertAlmostEqual(l['stop']+s['stop'],200);self.assertAlmostEqual(l['target']+s['target'],200)
    def test_retrace_keeps_stop_and_target(self):
        l,_=plan(self.row(),'continuation','long');r,_=plan(self.row(),'continuation','long',True)
        self.assertEqual(l['stop'],r['stop']);self.assertEqual(l['target'],r['target']);self.assertLess(r['reference'],l['reference'])
    def test_no_blind_cost_or_horizon_relaxation(self):
        self.assertIsNone(plan(self.row(pullback_low=99.9,low=99.95,atr14=.1),'continuation','long')[0])
        self.assertIsNone(plan(self.row(pullback_low=98),'continuation','long')[0])
    def test_execution_expiry_and_deviation(self):
        g,_=plan(self.row(),'continuation','long');at=pd.Timestamp(g['available_at'])
        self.assertIsNotNone(execution_plan(g,g['reference'],at))
        self.assertIsNone(execution_plan(g,g['reference'],at+pd.Timedelta(minutes=5)))
        self.assertIsNone(execution_plan(g,g['reference']*1.01,at))
    def test_objectives_no_universal_near_obstacle_veto(self):
        g,_=plan(self.row(prior_swing_high=100.2),'continuation','long',objective=True)
        self.assertIsNotNone(g);self.assertEqual(g['target_origin'],'FIXED_3R_FROM_SIGNAL_CLOSE')

class StateTests(unittest.TestCase):
    def test_restart_preserves_baseline_peak_and_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.sqlite';s=StateStore(p);a=s.checkpoint(CLOCK.timestamp(),1000,[],True)
            self.assertTrue(s.event('x',dict(v=1)));s.close();s=StateStore(p)
            self.assertFalse(s.event('x',dict(v=2)));self.assertEqual(s.get('account')['day_start'],1000)
            self.assertEqual(s.checkpoint(CLOCK.timestamp()+60,990,[],True)['peak'],1000);s.close()
    def test_missing_midnight_with_open_position_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            s=StateStore(Path(d)/'s.sqlite');s.checkpoint(CLOCK.timestamp(),1000,[],True)
            with self.assertRaises(ValueError):s.checkpoint(CLOCK.timestamp()+86400+61,900,[],False)
            s.close()

class NativeLifecycleFixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        init_db('sqlite:///'+str(self.root/'native.sqlite'))
        (self.root/'contracts.json').write_text(json.dumps({'ETH/USDT:USDT':contract()}))
        self.cfg=dict(candle_type_def=CandleType.FUTURES,policy_state=str(self.root/'risk.sqlite'),policy_contracts=str(self.root/'contracts.json'),policy_events=str(self.root/'events.jsonl'))
        self.s=PolicyManagedV3(self.cfg);self.s.bot_start();self.s.dp=Mock();self.s.dp.get_analyzed_dataframe.return_value=(pd.DataFrame(),None)
    def tearDown(self):
        self.s._store.close();Trade.session.remove();Trade.session.bind.dispose();self.tmp.cleanup()
    def make_trade(self,short=False,lev=10):
        g,_=plan(pd.Series(dict(date=pd.Timestamp(CLOCK)-pd.Timedelta(minutes=15),close=100.,low=99.5,high=100.5,atr14=.6,pullback_low=99.,pullback_high=101.,prior_low=99.4,prior_high=100.6)),'continuation','short' if short else 'long')
        g['decision_id']='fixture:'+str(short)
        self.s._store.plan(g['decision_id'],'ETH/USDT:USDT',g['side'],CLOCK.timestamp(),CLOCK.timestamp()+300,g)
        t=Trade(pair='ETH/USDT:USDT',exchange='gate',open_rate=100,open_date=CLOCK,stake_amount=10,amount=0,amount_requested=1,
            fee_open=.00075,fee_close=.00075,is_open=True,is_short=short,leverage=lev,trading_mode=TradingMode.FUTURES,
            amount_precision=1,price_precision=.01,precision_mode=TICK_SIZE,precision_mode_price=TICK_SIZE,contract_size=.01,orders=[])
        Trade.session.add(t);Trade.commit();return t,g
    def order(self,t,id,side,amount,price):
        o=Order(ft_trade_id=t.id,ft_pair=t.pair,order_id=id,ft_order_side=side,side=side,order_type='limit',status='open',
            ft_is_open=True,ft_amount=amount,order_date=CLOCK,price=price,ft_price=price,amount=amount,filled=0,remaining=amount,cost=amount*price)
        t.orders.append(o);Trade.commit();return o
    def terminal(self,t,o,filled,price,status='closed'):
        o.filled=filled;o.remaining=o.amount-filled;o.average=price;o.price=price;o.status=status;o.ft_is_open=False;o.order_filled_date=CLOCK+timedelta(seconds=30)
        t.update_trade(o);self.s.order_filled(t.pair,t,o,CLOCK+timedelta(seconds=30));Trade.commit()

class NativeLifecycleTests(NativeLifecycleFixture):
    def test_native_partial_fill_cancel_restart_partial_exit_final_long_short(self):
        for short in [False,True]:
            t,g=self.make_trade(short);e=self.order(t,'entry-'+str(short),t.entry_side,1,100)
            # Native terminal canceled partial crystallizes the 0.6 filled lot.
            self.terminal(t,e,.6,100,'canceled');self.assertAlmostEqual(t.amount,.6)
            state=t.get_custom_data('policy_state');self.assertEqual(state['entry_amount'],.6)
            count=self.s._store.db.execute('SELECT count(*) FROM events').fetchone()[0]
            self.s.order_filled(t.pair,t,e,CLOCK+timedelta(seconds=31))
            self.assertEqual(self.s._store.db.execute('SELECT count(*) FROM events').fetchone()[0],count)
            price=102 if not short else 98
            x=self.order(t,'partial-'+str(short),t.exit_side,.2,price)
            self.assertIsNone(self.s.adjust_trade_position(t,CLOCK,price,0,1,100,price,price,0,0))
            self.terminal(t,x,.1,price,'canceled');self.assertAlmostEqual(t.amount,.5)
            trade_id=t.id;Trade.session.expire_all();reloaded=Trade.session.get(Trade,trade_id)
            self.assertEqual(reloaded.get_custom_data('policy_plan')['stop'],g['stop'])
            self.assertAlmostEqual(reloaded.get_custom_data('policy_state')['exited_amount'],.1)
            stop=self.s.custom_stoploss(t.pair,t,CLOCK+timedelta(minutes=1),price,0,True)
            tight=t.get_custom_data('policy_state')['tight_stop'];self.assertGreater((tight-g['stop'])*(-1 if short else 1),0)
            self.s.custom_stoploss(t.pair,t,CLOCK+timedelta(minutes=2),100.5 if not short else 99.5,0,True)
            self.assertEqual(t.get_custom_data('policy_state')['tight_stop'],tight)
            final=self.order(t,'final-'+str(short),t.exit_side,.5,price)
            self.terminal(t,final,.5,price)
            self.assertFalse(t.is_open);self.assertEqual(t.nr_of_successful_exits,2)
    def test_native_bot_cancel_pending_partial_exit(self):
        t,g=self.make_trade();e=self.order(t,'entry',t.entry_side,1,100);self.terminal(t,e,1,100)
        o=self.order(t,'exit',t.exit_side,.3,102)
        bot=FreqtradeBot.__new__(FreqtradeBot);bot.strategy=self.s;bot.config={'stake_currency':'USDT','dry_run':True};bot.margin_mode=MarginMode.ISOLATED
        bot.exchange=Mock();bot.wallets=Mock();bot.handle_order_fee=Mock();bot.order_close_notify=Mock();bot._notify_exit_cancel=Mock();bot.cancel_stoploss_on_exchange=Mock(side_effect=lambda t:t)
        bot.exchange.get_min_pair_stake_amount.return_value=1;bot.exchange.check_order_canceled_empty.return_value=False
        bot.exchange.dry_run_liquidation_price.return_value=90;bot.exchange.get_liquidation_price.return_value=90;bot.exchange.get_rate.return_value=102
        bot.exchange.get_maintenance_ratio_and_amt.return_value=(.005,0);bot.exchange.get_option.return_value=False
        ccxt=dict(id='exit',symbol=t.pair,type='limit',side=t.exit_side,status='open',amount=.3,filled=.1,remaining=.2,price=102,average=102,cost=10.2,timestamp=CLOCK.timestamp()*1000)
        bot.exchange.cancel_order_with_result.return_value=ccxt|dict(status='canceled')
        self.assertTrue(bot.handle_cancel_exit(t,ccxt,o,'fixture_timeout'))
        self.assertAlmostEqual(t.amount,.9);self.assertFalse(o.ft_is_open)
        # A replacement can only request the outstanding one-third allocation.
        out=self.s.adjust_trade_position(t,CLOCK+timedelta(minutes=1),102,0,1,100,102,102,0,0)
        self.assertIsNotNone(out);self.assertLessEqual(-out[0],t.stake_amount)
    def test_pending_timeout_does_not_block_protective_management(self):
        t,g=self.make_trade();e=self.order(t,'entry',t.entry_side,1,100);self.terminal(t,e,1,100)
        o=self.order(t,'pending',t.exit_side,.3,110)
        self.assertTrue(self.s.check_exit_timeout(t.pair,t,o,CLOCK+timedelta(minutes=5)))
        self.assertIsNotNone(self.s.custom_stoploss(t.pair,t,CLOCK,100,0,True))

class FundingTests(NativeLifecycleFixture):
    def test_event_once_funding_across_partial_exit_and_restart(self):
        from policy_native import PersistentFunding
        from freqtrade.exchange import Exchange
        t,g=self.make_trade();e=self.order(t,'entry',t.entry_side,1,100);self.terminal(t,e,1,100)
        class Engine(PersistentFunding):pass
        engine=Engine();engine.trading_mode=TradingMode.FUTURES;engine.funding_fee_timeframe_secs=3600
        engine.futures_data={t.pair:pd.DataFrame(dict(date=pd.to_datetime([CLOCK+timedelta(hours=1),CLOCK+timedelta(hours=2)],utc=True),open_fund=[.001,.001],open_mark=[100,100]))}
        engine.exchange=Mock();engine.exchange._add_funding_columns=Exchange._add_funding_columns;engine.exchange.calculate_funding_fees=Exchange.calculate_funding_fees.__get__(engine.exchange,Exchange)
        at=CLOCK+timedelta(hours=1);engine._run_funding_fees(t,at,True);self.assertAlmostEqual(t.funding_fee_running,-.1)
        # A same-clock reduction owns the already-observed event once.
        x=self.order(t,'partial',t.exit_side,.3,102);self.terminal(t,x,.3,102)
        self.assertAlmostEqual(x.funding_fee,-.1)
        Trade.commit();Trade.session.expire_all();t=Trade.session.get(Trade,t.id)
        fresh=Engine();fresh.trading_mode=engine.trading_mode;fresh.funding_fee_timeframe_secs=3600;fresh.futures_data=engine.futures_data;fresh.exchange=engine.exchange
        fresh._run_funding_fees(t,at,True);self.assertAlmostEqual(t.funding_fee_running,0)
        fresh._run_funding_fees(t,CLOCK+timedelta(hours=2),True);self.assertAlmostEqual(t.funding_fee_running,-.07)
        self.assertEqual(len(t.get_custom_data('v3_funding_events')),2)

class CausalTests(unittest.TestCase):
    def test_append_future_does_not_change_closed_policy_features(self):
        n=60;dates=pd.date_range(CLOCK,periods=n,freq='15min')
        close=pd.Series(np.linspace(100,103,n))
        d=pd.DataFrame(dict(date=dates,open=close-.1,high=close+.3,low=close-.3,close=close,volume=1.,ema20=close-.1,ema50=close-.2,vwap=close-.15,atr14=.5))
        full=features(d);short=features(d.iloc[:50]);pd.testing.assert_frame_equal(full.iloc[:50],short)

class NativeAccountTests(NativeLifecycleFixture):
    def boot_account(self):
        self.s._store.checkpoint(CLOCK.timestamp(),1000,[],True)
        self.s.wallets=Mock();self.s.wallets.get_total.return_value=1000;self.s.wallets.get_free.return_value=990
        self.s.mark=lambda pair,now:105.
    def test_uncrystallized_partial_entry_is_in_equity_and_pending_risk(self):
        self.boot_account();t,g=self.make_trade();e=self.order(t,'entry',t.entry_side,1,100)
        e.filled=.4;e.remaining=.6;Trade.commit()
        a=self.s.account(CLOCK+timedelta(minutes=1))
        self.assertAlmostEqual(a.unrealized_net,.4*5-.4*(100*.00075+105*.00075))
        self.assertAlmostEqual(a.pending_margin,6);self.assertGreater(a.pending_risk,0);self.assertGreater(a.open_risk,0)
        self.assertTrue(self.s.check_entry_timeout(t.pair,t,e,CLOCK+timedelta(minutes=1)))
    def test_pending_exit_fill_retains_risk_but_does_not_inflate_equity(self):
        self.boot_account();t,g=self.make_trade();e=self.order(t,'entry',t.entry_side,1,100);self.terminal(t,e,1,100)
        x=self.order(t,'exit',t.exit_side,.3,102);x.filled=.2;x.remaining=.1;Trade.commit()
        a=self.s.account(CLOCK+timedelta(minutes=1))
        expected_realized=.2*2-.2*(100*.00075+102*.00075)
        expected_unrealized=.8*5-.8*(100*.00075+105*.00075)
        self.assertAlmostEqual(a.equity,1000+expected_realized+expected_unrealized)
        self.assertAlmostEqual(a.gross_notional,105)  # conservative until native reconciliation


class ConfigTests(unittest.TestCase):
    def test_baseline_and_native_emergency_settings_do_not_inherit_vwap_overrides(self):
        from policy_common import config,read
        b=read(config('policy-session3-001','TrendPullbackBaselineV1','config-test'))
        self.assertNotIn('stoploss',b);self.assertNotIn('minimal_roi',b)
        p=read(config('policy-session3-001','PolicyManagedV3','config-test'))
        self.assertEqual(p['stoploss'],-.99);self.assertEqual(p['policy_notional_cap'],25.)

class NativePaperFundingTests(NativeLifecycleFixture):
    def exchange(self,t,clock):
        from freqtrade.exchange import Exchange
        from policy_paper_funding import install
        ex=Mock();ex._config={'dry_run':True};ex._ft_has=dict(mark_ohlcv_timeframe='1h',funding_fee_timeframe='8h',mark_ohlcv_price='mark')
        dates=pd.to_datetime([CLOCK+timedelta(hours=8),CLOCK+timedelta(hours=16)],utc=True)
        ex.refresh_latest_ohlcv.return_value={(t.pair,'1h',CandleType.MARK):pd.DataFrame(dict(date=dates,open=100)),
            (t.pair,'8h',CandleType.FUNDING_RATE):pd.DataFrame(dict(date=dates,funding_rate=.001))}
        ex.combine_funding_and_mark=Exchange.combine_funding_and_mark;ex._add_funding_columns=Exchange._add_funding_columns
        ex.calculate_funding_fees=Exchange.calculate_funding_fees.__get__(ex,Exchange)
        install(ex,{t.pair:dict(funding_interval_seconds=28800)},clock=lambda:clock[0])
        return ex
    def test_scoped_native_paper_event_once_survives_partial_and_restart(self):
        t,g=self.make_trade();e=self.order(t,'entry',t.entry_side,1,100);self.terminal(t,e,1,100)
        clock=[CLOCK+timedelta(hours=8)];ex=self.exchange(t,clock)
        fee=ex.get_funding_fees(t.pair,1,False,t.open_date_utc);self.assertAlmostEqual(fee,-.1)
        self.assertAlmostEqual(ex.get_funding_fees(t.pair,1,False,t.open_date_utc),-.1)
        # Native closes a same-clock partial and resets its running funding.
        x=self.order(t,'partial',t.exit_side,.3,102);x.filled=.3;x.remaining=0;x.status='closed';x.ft_is_open=False;x.order_filled_date=clock[0];t.update_trade(x)
        self.assertAlmostEqual(x.funding_fee,-.1);self.assertAlmostEqual(t.amount,.7)
        Trade.commit();Trade.session.expire_all();t=Trade.session.get(Trade,t.id)
        fresh=self.exchange(t,clock)
        self.assertAlmostEqual(fresh.get_funding_fees(t.pair,.7,False,t.date_last_filled_utc),0)
        clock[0]=CLOCK+timedelta(hours=16)
        self.assertAlmostEqual(fresh.get_funding_fees(t.pair,.7,False,t.date_last_filled_utc),-.07)
        self.assertEqual(len(t.get_custom_data('policy_paper_funding_events')),2)
        self.assertEqual(t.get_custom_data('policy_funding_health')['status'],'CHECKED_NATIVE_DRY_RUN')
    def test_outage_preserves_known_fees_and_marks_unknown(self):
        t,g=self.make_trade();e=self.order(t,'entry',t.entry_side,1,100);self.terminal(t,e,1,100)
        clock=[CLOCK+timedelta(hours=8)];ex=self.exchange(t,clock)
        ex.refresh_latest_ohlcv.side_effect=OSError('controlled source outage')
        t.set_funding_fees(-.02)
        self.assertAlmostEqual(ex.get_funding_fees(t.pair,1,False,t.open_date_utc),-.02)
        self.assertEqual(t.get_custom_data('policy_funding_health')['status'],'UNKNOWN')
    def test_source_missing_scheduled_event_does_not_become_zero(self):
        t,g=self.make_trade();e=self.order(t,'entry',t.entry_side,1,100);self.terminal(t,e,1,100)
        clock=[CLOCK+timedelta(hours=8)];ex=self.exchange(t,clock)
        ex.refresh_latest_ohlcv.return_value={}
        ex.get_funding_fees(t.pair,1,False,t.open_date_utc)
        self.assertEqual(t.get_custom_data('policy_funding_health')['status'],'UNKNOWN')

class NativePrecisionTests(unittest.TestCase):
    def test_native_entry_round_trip_preserves_approved_lots_at_all_leverages(self):
        from policy_risk import native_entry_margin
        from freqtrade.exchange import amount_to_contract_precision
        fixtures=[(1.1055,22.,10.,.1),(1.4805,16.,10.,.1),(.08401,290.,10.,1.),(1800.3,.013,.01,.1),(67543.1,.0003,.0001,1.)]
        for price,amount,mult,precision in fixtures:
            c=dict(contract_size=mult,step_contracts=precision)
            v=dict(contracts=float(D(str(amount))/D(str(mult))))
            for lev in [1,10,20]:
                stake=native_entry_margin(v,price,lev,c,1000)
                actual=amount_to_contract_precision(stake/price*lev,precision,TICK_SIZE,mult)
                self.assertAlmostEqual(actual,amount,places=9)
                self.assertLessEqual(actual*price,amount*price+1e-9)
    def test_native_partial_round_trip_preserves_requested_lot(self):
        from policy_risk import native_exit_reduction
        from freqtrade.exchange import amount_to_contract_precision
        from freqtrade.util import FtPrecise
        from types import SimpleNamespace
        for lev in [1,10,20]:
            t=SimpleNamespace(stake_amount=290*.08401/lev,amount=290.,contract_size=10.,amount_precision=1.,precision_mode=TICK_SIZE)
            reduction=native_exit_reduction(90.,t)
            actual=amount_to_contract_precision(abs(float(FtPrecise(-reduction)*FtPrecise(t.amount)/FtPrecise(t.stake_amount))),1.,TICK_SIZE,10.)
            self.assertEqual(actual,90.)
    def test_native_rounding_cannot_exceed_available_margin(self):
        from policy_risk import native_entry_margin
        self.assertEqual(native_entry_margin(dict(contracts=22),1.1055,10,dict(contract_size=1.,step_contracts=1.),.1),0.)

class NativeFundingChronologyTests(NativeLifecycleFixture):
    def test_pending_entry_before_funding_is_not_held_quantity(self):
        from policy_native import PersistentFunding
        from freqtrade.exchange import Exchange
        t,g=self.make_trade();e=self.order(t,'entry',t.entry_side,1,100);self.terminal(t,e,1,100)
        class Engine(PersistentFunding):pass
        engine=Engine();engine.trading_mode=TradingMode.FUTURES;engine.funding_fee_timeframe_secs=3600
        engine.futures_data={t.pair:pd.DataFrame(dict(date=pd.to_datetime([CLOCK,CLOCK+timedelta(hours=1)],utc=True),open_fund=.001,open_mark=100.))}
        engine.exchange=Mock();engine.exchange._add_funding_columns=Exchange._add_funding_columns
        engine.exchange.calculate_funding_fees=Exchange.calculate_funding_fees.__get__(engine.exchange,Exchange)
        engine._run_funding_fees(t,CLOCK+timedelta(seconds=30),True)
        self.assertAlmostEqual(t.funding_fee_running,0.)
        engine._run_funding_fees(t,CLOCK+timedelta(hours=1),True)
        self.assertAlmostEqual(t.funding_fee_running,-.1)
        self.assertEqual(len(t.get_custom_data('v3_funding_events')),1)
