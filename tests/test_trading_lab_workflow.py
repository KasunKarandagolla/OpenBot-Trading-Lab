"""Fault tests use explicitly synthetic inputs; acceptance evidence is separate."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from binance_research_data import DataError
from trading_lab.public import PublicFeed, validate_bars, quality
from trading_lab.charts import validate_request, utc_milliseconds
from trading_lab.risk import validate_market_plan
from trading_lab.execution import (SignedServiceStub, ExecutionBlocked, OfflineVenue,
                                   OfflineManager, conditional_confirmed, readiness)
from trading_lab.workflow import Inbox, lock_worker, atomic_reply
import test_openbot_current as inherited_tests


class PublicTests(unittest.TestCase):
    def test_only_allowlisted_get_no_production_signing_route(self):
        with tempfile.TemporaryDirectory() as root, patch('trading_lab.public.HTTPSConnection') as transport:
            feed=PublicFeed(root)
            for endpoint in ['order','leverage','https://evil.test/time','../account']:
                with self.assertRaises(DataError):feed.get('x',endpoint)
            for params in [{'symbol':'ETHUSDT;id','interval':'5m','limit':20,'endTime':1},
                           {'symbol':'ETHUSDT','interval':'7m','limit':20,'endTime':1},
                           {'symbol':'ETHUSDT','interval':'5m','limit':1001,'endTime':1}]:
                with self.assertRaises(DataError):feed.get('x','klines',**params)
            transport.assert_not_called()

    def test_redirect_is_not_followed(self):
        with tempfile.TemporaryDirectory() as root, patch('trading_lab.public.HTTPSConnection') as transport:
            conn=transport.return_value;conn.getresponse.return_value.status=302
            conn.getresponse.return_value.read.return_value=b'{}'
            with self.assertRaises(DataError):PublicFeed(root,demo=True).get('clock','time')
            self.assertEqual(transport.call_args.args[0],'demo-fapi.binance.com')
            self.assertEqual(conn.request.call_count,1)
            self.assertEqual(conn.request.call_args.args[0],'GET')

    def test_bad_ohlcv_future_gap_and_duplicate(self):
        bars=[[i*300000,'10','11','9','10','20',i*300000+299999,'200',4,'10','100','0'] for i in range(24)]
        self.assertEqual(len(validate_bars(bars,'5m',24*300000,24)),24)
        with self.assertRaises(DataError):validate_bars(bars,'5m',23*300000,24)
        for change in ['gap','duplicate','ohlc','proxy']:
            sample=copy.deepcopy(bars)
            if change=='gap':sample.pop(10)
            elif change=='duplicate':sample[10]=sample[9]
            elif change=='ohlc':sample[10][2]='8'
            else:sample[10][10]='300'
            with self.subTest(change=change),self.assertRaises(DataError):validate_bars(sample,'5m',24*300000,23)


class ChartSchemaTests(unittest.TestCase):
    def setUp(self):
        self.identity={'candidate_id':'ETHUSDT-case','symbol':'ETHUSDT','as_of_ms':1000000}
        self.request=dict(request_id='vision-a',candidate_id='ETHUSDT-case',symbol='ETHUSDT',
                          venue='BINANCE_PUBLIC_USDM',cutoff_ms=1000000,timeframe='1h',visible_candles=150,
                          overlays=[],volume=True,purpose='Clean structural context',revision=1)

    def test_supported_clean_request(self):validate_request(self.request,self.identity)

    def test_milliseconds_are_independent_of_pandas_datetime_storage_unit(self):
        import pandas as pd
        from datetime import datetime,timezone
        expected=int(datetime(2026,11,7,tzinfo=timezone.utc).timestamp()*1000)
        for unit in ['ms','us','ns']:
            stamps=pd.Series(pd.to_datetime([expected],unit='ms',utc=True)).dt.as_unit(unit)
            self.assertEqual(utc_milliseconds(stamps).iloc[0],expected)

    def test_reject_paths_urls_future_overload_and_wrong_venue(self):
        cases=[{'path':'/etc/passwd'},{'url':'https://evil.test'},{'request_id':'../../x'},
               {'cutoff_ms':1000001},{'end_ms':1000001},{'timeframe':'7m'},
               {'visible_candles':201},{'overlays':['exec']},{'revision':5},
               {'venue':'GATE'},{'focus_zone':[11,10]}]
        for changes in cases:
            with self.subTest(changes=changes),self.assertRaises((DataError,TypeError)):
                validate_request({**self.request,**changes},self.identity)


class GateTests(unittest.TestCase):
    def setUp(self):
        fixture=inherited_tests.RiskTests();fixture.setUp()
        self.constraints={**fixture.constraints,'as_of_ms':995,'public_symbol_status':'TRADING',
                          'closed_bar_source_sha256':['synthetic-source'],
                          'structural_anchors':[{'source_sha256':'synthetic-source','available_at_ms':900,'low':'99','high':'101'}]}
        self.plan={**fixture.plan,'decision':'LIMIT','engine_mode':'DEMO_READ_ONLY','margin_type':'ISOLATED',
                   'position_side':'BOTH','stop_working_type':'MARK_PRICE','hold_seconds':3600,
                   'invalidation':{'source_sha256':'synthetic-source','available_at_ms':900,'reason':'Synthetic unit level','anchor_price':'99'},
                   'exits':[{'price':'103','quantity':'0.1','reduce_only':True},
                            {'price':'105','quantity':'0.1','reduce_only':True}]}
        self.account={**fixture.demo,'host':'demo-fapi.binance.com','engine_mode':'DEMO_READ_ONLY',
            'authenticated':True,'credential_boundary_verified':True,'position_mode':'ONE_WAY','margin_type':'ISOLATED',
            'multi_assets':False,'demo_quote':{'host':'demo-fapi.binance.com','observed_at_ms':995,'bid':'99.99','ask':'100.02','mark':'100'},
            'bracket':{'notional_floor':'0','notional_cap':'1000','initial_leverage':'25','maintenance_ratio':'0.004','maintenance_deduction_usdt':'0'},
            'configured_leverage':20,'remaining_daily_loss_budget_usdt':'5','correlated_stop_risk_usdt':'0',
            'portfolio_stop_risk_budget_usdt':'5','available_after_reservations_usdt':'25','equity_usdt':'100',
            'next_funding_ms':8000000,'funding_interval_ms':28800000,'adverse_funding_rate_per_event':'0.0001'}
        self.receipts=fixture.receipts

    def evaluate(self,plan=None,constraints=None,account=None,now=1000):
        return validate_market_plan(plan or self.plan,constraints or self.constraints,
                                   account or self.account,now,self.receipts,'fixture')

    def test_complete_math_input_pass_does_not_authorize_orders(self):
        result=self.evaluate();self.assertEqual(result['status'],'PASS',result)
        self.assertFalse(result['order_authorized'])
        self.assertEqual(result['execution_readiness'],'EXECUTION_BLOCKED_CREDENTIAL_BOUNDARY')
        self.assertIn('return_on_margin_stop_percent',result['metrics'])

    def test_no_proposal_skips_without_exchange(self):
        for plan in [None,{'decision':'NO_OPPORTUNITY'}]:
            self.assertEqual(validate_market_plan(plan,{},None,1000)['status'],'SKIPPED_NO_PROPOSAL')

    def test_absent_account_and_malformed_plan(self):
        self.assertEqual(validate_market_plan(self.plan,self.constraints,None,1000,self.receipts,'fixture')['status'],'UNKNOWN')
        self.assertEqual(validate_market_plan([],self.constraints,None,1000)['status'],'VETO')
        self.assertEqual(self.evaluate({**self.plan,'decision':'WATCH'})['status'],'VETO')

    def test_plan_negative_cases(self):
        cases=[({'entry':'100.001'},'PRICE_TICK_MISMATCH'),({'quantity':'0.001'},'BELOW_PUBLIC_MINIMUM_NOTIONAL'),
               ({'engine_mode':'LIVE'},'UNSUPPORTED_MODE_MARGIN_OR_STOP_TRIGGER'),
               ({'hold_seconds':54001},'HOLD_LIMIT_15_HOURS'),
               ({'invalidation':{'reason':'x','source_sha256':'synthetic-source','available_at_ms':1001}},'STOP_STRUCTURAL_EVIDENCE_MISSING_OR_LOOKAHEAD'),
               ({'exits':[{'price':'103','quantity':'0.001','reduce_only':True},{'price':'105','quantity':'0.199','reduce_only':True}]},'EXIT_BELOW_FILTER_OR_NOT_CLOSE_ONLY'),
               ({'decision':'CONDITIONAL','trigger':{'kind':'WAIT_FOR_LLM'}},'CONDITIONAL_TRIGGER_OR_ORDER_TIMING_INVALID')]
        for changes,reason in cases:
            with self.subTest(reason=reason):self.assertIn(reason,self.evaluate({**self.plan,**changes})['reasons'])

    def test_stale_late_ticker_lookahead_and_venue(self):
        self.assertIn('STALE_OR_FUTURE_CANDLES',self.evaluate(now=200000)['reasons'])
        c={**self.constraints,'public_quote':{**self.constraints['public_quote'],'quote_time_ms':999}}
        self.assertIn('TICKER_AFTER_RESEARCH_CUTOFF',self.evaluate(constraints=c)['reasons'])
        self.assertEqual(self.evaluate(account={**self.account,'host':'fapi.binance.com'})['status'],'VETO')

    def test_account_negative_cases(self):
        cases=[({'symbol_has_position':True},'EXISTING_OR_CONFLICTING_SYMBOL_EXPOSURE'),
               ({'symbol_has_algo_orders':True},'EXISTING_OR_CONFLICTING_SYMBOL_EXPOSURE'),
               ({'configured_leverage':10},'LEVERAGE_OR_MAINTENANCE_BRACKET_MISMATCH'),
               ({'bracket':{**self.account['bracket'],'notional_floor':'21'}},'LEVERAGE_OR_MAINTENANCE_BRACKET_MISMATCH'),
               ({'demo_quote':{**self.account['demo_quote'],'observed_at_ms':-20000}},'DEMO_QUOTE_MISSING_STALE_OR_WRONG_VENUE'),
               ({'available_after_reservations_usdt':'0.1'},'INSUFFICIENT_WALLET_AFTER_RESERVES_AND_COSTS'),
               ({'remaining_daily_loss_budget_usdt':'0'},'DAILY_LOSS_BUDGET'),
               ({'correlated_stop_risk_usdt':'5'},'CORRELATED_PORTFOLIO_RISK')]
        for changes,reason in cases:
            with self.subTest(reason=reason):self.assertIn(reason,self.evaluate(account={**self.account,**changes})['reasons'])

    def test_stop_must_match_cited_real_bar_anchor(self):
        result=self.evaluate({**self.plan,'invalidation':{**self.plan['invalidation'],'anchor_price':'98'}})
        self.assertIn('STOP_NOT_OUTSIDE_CITED_BAR_STRUCTURE',result['reasons'])

    def test_liquidation_and_negative_net_reward(self):
        result=self.evaluate({**self.plan,'leverage':25},{**self.constraints},
                            {**self.account,'maintenance_ratio':'0.039'})
        self.assertIn('INSUFFICIENT_LIQUIDATION_BUFFER',result['reasons'])
        self.assertIn('TP1_AFTER_COST_RR_BELOW_1_25',self.evaluate({**self.plan,'tp1':'100.01'})['reasons'])


class ExecutionTests(unittest.TestCase):
    def test_signed_boundary_rejects_hosts_proxies_and_all_operations(self):
        import openbot_demo_readonly as old_reader
        with self.assertRaisesRegex(old_reader.ReadError,'CREDENTIAL_BOUNDARY'):
            old_reader.credentials()
        with patch.object(old_reader,'HTTPSConnection') as transport:
            with self.assertRaisesRegex(old_reader.ReadError,'CREDENTIAL_BOUNDARY'):
                old_reader.get('/fapi/v3/balance',('dummy','dummy'),123)
            transport.assert_not_called()
        for host in ['fapi.binance.com','api.binance.com','demo-fapi.binance.com.evil.test','https://demo-fapi.binance.com']:
            with self.assertRaises(ExecutionBlocked):SignedServiceStub(host)
        with patch.dict('os.environ',{'HTTPS_PROXY':'http://proxy.invalid'},clear=True):
            with self.assertRaises(ExecutionBlocked):SignedServiceStub()
        with patch.dict('os.environ',{},clear=True):
            stub=SignedServiceStub()
            for method,path in [('GET','/fapi/v3/balance'),('POST','/fapi/v1/order'),('POST','/fapi/v1/leverage')]:
                with self.assertRaises(ExecutionBlocked):stub.request(method,path,{})
        self.assertEqual(readiness()['orders_submitted'],0)

    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory();self.addCleanup(self.scratch.cleanup)
        self.path=Path(self.scratch.name)/'offline.db';self.venue=OfflineVenue()
        self.plan={'decision':'LIMIT','symbol':'SYNTHETICUSDT','side':'LONG','entry':'100','quantity':'0.2',
                   'stop':'99','tp1':'103','engine_mode':'OFFLINE_SIMULATION','margin_type':'ISOLATED',
                   'position_side':'BOTH','expires_at_ms':60000,'hold_seconds':3600,'preapproved_emergency_flatten':True}
        self.manager=OfflineManager(self.path,self.venue)
        self.job=self.manager.propose(self.plan,{'status':'PASS'},1000)

    def start(self):
        self.manager.approve_offline(self.job,1100)
        self.manager.step(self.job,1200)

    def test_duplicate_approval_and_restart_ambiguous_submit(self):
        self.venue.timeout_entry=True;self.start()
        with self.assertRaises(ExecutionBlocked):self.manager.approve_offline(self.job,1300)
        self.manager.db.close();self.manager=OfflineManager(self.path,self.venue)
        self.assertEqual(self.manager.step(self.job,1400),'ACKNOWLEDGED')
        self.assertEqual(self.venue.entry_calls,1)

    def test_crash_after_intent_does_not_repeat_opening(self):
        self.manager.approve_offline(self.job,1100)
        self.manager._event(self.job,'SUBMITTED',1200,'SIMULATED_CRASH_BEFORE_NETWORK')
        self.assertEqual(self.manager.step(self.job,1500),'UNKNOWN')
        self.assertEqual(self.venue.entry_calls,0)

    def test_partial_fill_then_full_fill_protected_without_new_entry(self):
        self.start();self.venue.fill(self.job,'.05')
        self.assertEqual(self.manager.step(self.job,1300),'MANAGING')
        self.assertTrue(self.venue.query_stop(self.job)['closePosition'])
        self.venue.fill(self.job,'.2',terminal=True)
        self.assertEqual(self.manager.step(self.job,1400),'MANAGING')
        self.assertEqual(self.venue.entry_calls,1)

    def test_stop_rejection_cancels_remainder_and_flattens_only_owned_fill(self):
        self.start();self.venue.fill(self.job,'.05');self.venue.reject_stop=True
        self.assertEqual(self.manager.step(self.job,1300),'UNKNOWN')
        self.assertEqual(self.venue.position,0)
        self.assertEqual(self.manager.step(self.job,1400),'CLOSED')
        self.assertEqual(self.venue.entries[self.job]['status'],'CANCELED')
        self.assertEqual(self.manager.db.execute('select stop_new from controls').fetchone()[0],1)

    def test_missing_protection_and_ambiguous_close_reconcile(self):
        self.start();self.venue.fill(self.job,'.2',terminal=True);self.manager.step(self.job,1300)
        self.venue.protections.clear();self.venue.timeout_close=True
        self.manager.step(self.job,1400)
        self.manager.db.close();self.manager=OfflineManager(self.path,self.venue)
        self.assertEqual(self.manager.step(self.job,1500),'CLOSED')
        self.assertEqual(len(self.venue.closes),1)

    def test_kill_switch_preserves_close_only_management(self):
        self.start();self.venue.fill(self.job,'.2',terminal=True);self.manager.step(self.job,1300)
        self.manager.stop_new_entries();self.manager.step(self.job,1400,emergency=True)
        self.assertEqual(self.manager.step(self.job,1500),'CLOSED')
        self.assertTrue(self.venue.closes[self.job]['reduceOnly'])

    def test_entry_expiry_and_fifteen_hour_bound(self):
        self.start();self.assertEqual(self.manager.step(self.job,60001),'CANCELED')
        with self.assertRaises(ExecutionBlocked):self.manager.propose({**self.plan,'hold_seconds':54001},{'status':'PASS'},1000)

    def test_pending_symbol_entry_blocks_second_job_and_stop_cancels_remainder(self):
        self.start()
        second=self.manager.propose({**self.plan,'tp1':'104'},{'status':'PASS'},1300)
        self.manager.approve_offline(second,1400)
        self.assertEqual(self.manager.step(second,1500),'FAILED')
        self.assertEqual(self.venue.entry_calls,1)
        self.manager.stop_new_entries()
        self.assertEqual(self.manager.step(self.job,1600),'CANCELED')

    def test_stop_mismatch_never_claimed_confirmed(self):
        self.start();self.venue.fill(self.job,'.1');self.venue.stop(self.job,self.plan)
        self.venue.protections[self.job]['side']='BUY'
        self.manager.step(self.job,1300)
        states=[r[0] for r in self.manager.db.execute('select state from events')]
        self.assertNotIn('PROTECTION_CONFIRMED',states)

    def test_conditional_waits_for_completed_venue_bar(self):
        trigger={'kind':'CLOSED_5M_ABOVE','order_after_confirmation':True,'not_before_ms':300000,'expires_at_ms':900000,'price':'100'}
        bar={'host':'demo-fapi.binance.com','interval_ms':300000,'open_ms':300000,'available_ms':600000,'close':'101'}
        self.assertFalse(conditional_confirmed(trigger,bar,599999))
        self.assertTrue(conditional_confirmed(trigger,bar,600000))
        self.assertFalse(conditional_confirmed(trigger,{**bar,'host':'fapi.binance.com'},600000))


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory();self.addCleanup(self.scratch.cleanup)
        self.inbox=Inbox(Path(self.scratch.name)/'TradingLab-Workflow-v2')

    def request(self,key='request-a',**changes):
        data={'schema':'openbot.shared.request.v2','request_id':key,'kind':'READINESS',
              'created_at_ms':900,'expires_at_ms':2000,'payload':{}}
        data.update(changes);path=self.inbox.root/'requests'/(key+'.json');atomic_reply(path,data)
        return path

    def test_dedup_restart_and_request_id_reuse(self):
        path=self.request();first=self.inbox.handle(path,1000)
        second=Inbox(self.inbox.root).handle(path,3000)
        self.assertEqual(first,second)
        changed=json.loads(path.read_text());changed['expires_at_ms']=2500;atomic_reply(path,changed)
        with self.assertRaises(DataError):self.inbox.handle(path,1000)

    def test_no_shell_path_url_or_signed_account_api(self):
        for i,change in enumerate([{'kind':'SHELL','payload':{'command':'id'}},
                                   {'kind':'CHART','payload':{'path':'/etc/passwd'}},
                                   {'kind':'GATE','payload':{'account':{'key':'not-a-secret'}}},
                                   {'kind':'SCAN','payload':{'url':'https://evil.test'}},
                                   {'expires_at_ms':999},{'created_at_ms':1001}]):
            with self.subTest(change=change),self.assertRaises((DataError,KeyError)):
                self.inbox.handle(self.request(key='request-'+str(i),**change),1000)

    def test_worker_lock_excludes_second_writer(self):
        held=lock_worker(self.inbox.root)
        try:
            with self.assertRaises(DataError):lock_worker(self.inbox.root)
        finally:held.close()
        lock_worker(self.inbox.root).close()

    def test_no_reply_is_not_native_agent_participation(self):
        result=self.inbox.handle(self.request(),1000)
        self.assertEqual(result['native_message_receipt'],'NOT_CREATED_BY_FILE_BRIDGE')


if __name__=='__main__':unittest.main()
