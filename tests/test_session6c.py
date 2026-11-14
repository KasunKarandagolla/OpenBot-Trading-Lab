"""Regressions from genuine Local provider failures; network stays opt-in."""
from types import SimpleNamespace
from dataclasses import replace
from decimal import Decimal as D
import unittest
from unittest.mock import patch

from researcher.analytical_probe import qualify_selected,independent_column
from researcher.pack_contracts import CORE_COLUMNS,OPTIONAL_COLUMNS,EARLY,QUIET_NEAR,CORRECTIONS,compile_expr,Expr
from researcher.contracts import Instrument,ContractError
from researcher.transport import ProviderError
from researcher.observations import candle_observation,iso_seconds
from researcher.market import normalize_market
from researcher.screening import normalize_screen
from researcher.pack_contracts import make_remote_pack
from researcher.basis import BasisMCP,rpc_result
from researcher.transport import Response
import json
from test_session6a import flat,START


class LocalOracleRegression(unittest.TestCase):
    def test_actual_http200_busy_text_becomes_cooldown_and_stops_same_client(self):
        payload={'jsonrpc':'2.0','id':1,'result':{'isError':True,'content':[{'type':'text','text':
            'Basis is reading a lot of exchange data right now, so this exchange read is waiting. Try again in about a minute. Calls with a free key keep going for longer: https://www.basischarts.com/mcp#key'}]}}
        with self.assertRaisesRegex(ProviderError,'PROVIDER_BUSY_COOLDOWN'):rpc_result(json.dumps(payload).encode(),1)
        class HTTP:
            def __init__(self):self.calls=0
            def request(self,*args,**kwargs):
                self.calls+=1
                return Response(json.dumps(payload).encode(),{}, {'http_status':200,'response_sha256':'actual-error-shape'})
        http=HTTP();client=BasisMCP(http)
        with self.assertRaises(ProviderError) as error:client._rpc('tools/call',{})
        self.assertEqual(error.exception.receipt['provider_advised_wait_seconds'],60)
        with self.assertRaisesRegex(ProviderError,'PROVIDER_BUSY_COOLDOWN'):client.call('market_candles',{})
        self.assertEqual(http.calls,1)

    def test_busy_stops_oracle_without_spending_on_later_fields(self):
        api,client,at,calls,_=self.setup_probe(code='PROVIDER_BUSY_COOLDOWN')
        r=qualify_selected(environment='CODEX_LOCAL',native_symbol='TESTUSDT',api=api,client=client,clock=lambda:at)
        self.assertEqual(calls[-1],'quiet_percentile');self.assertFalse(r['numeric_passed'])
        self.assertIn('controlled_correction_short',r['not_evaluated_columns'])

    def setup_probe(self,*,fail='quiet_percentile',code='MCP_TOOL_ERROR',future=False):
        b=flat(300,name='TESTUSDT');at=b[-1].end
        receipt={'received_at_utc':at,'response_sha256':'controlled-receipt','http_status':200}
        api=SimpleNamespace(http=SimpleNamespace(receipts=[]))
        api.inventory=lambda:SimpleNamespace(instruments=(Instrument('TESTUSDT','BINANCE_USDM'),),
            content_sha256='inventory',eligible_symbols=('TESTUSDT',),mode='VERIFIED_INVENTORY',captured_at_utc=at)
        api.klines=lambda *args,**kwargs:(b,{'source_response_sha256':'controlled-reference'})
        columns={c.id:c.expression for c in (*CORE_COLUMNS,*OPTIONAL_COLUMNS)}|EARLY|QUIET_NEAR|CORRECTIONS
        names={v:k for k,v in columns.items()};calls=[]
        candle={'ref':'controlled.300','symbol':'TESTUSDT','exchange':'binance','market':'futures','timeframe':'1h',
            'from':b[0].open_ms//1000,'to':b[-1].open_ms//1000,'closedBars':300,'lastClose':D(100),
            'lastClosedCandle':{'time':b[-1].open_ms//1000,'open':100,'high':101,'low':99,'close':100},
            'evidence':{'barSeconds':3600,'asOfUtc':at,'loadedAtUtc':iso_seconds(START+301*3600) if future else at,'lastClose':100}}
        client=SimpleNamespace(http=SimpleNamespace(receipts=[]),tools={'market_candles':{'inputSchema':{}}})
        client.connect=lambda:None
        def call(tool,args):
            client.http.receipts.append(dict(receipt))
            if tool=='market_candles':return candle
            name=names[args['expression']];calls.append(name)
            if name==fail:raise ProviderError(code)
            return {'symbol':'TESTUSDT','exchange':'binance','market':'futures','timeframe':'1h','bars':300,
                'tailTimes':[b[-1].open_ms//1000],'tail':[independent_column(name,b)]}
        client.call=call
        return api,client,at,calls,candle

    def test_http200_tool_failure_isolated_and_later_core_still_checked(self):
        api,client,at,calls,_=self.setup_probe()
        with patch('researcher.pack_contracts.evaluate_expr',side_effect=AssertionError('compiler is not an oracle')):
            r=qualify_selected(environment='CODEX_LOCAL',native_symbol='TESTUSDT',api=api,client=client,clock=lambda:at)
        self.assertIn('body_fraction',[x['column'] for x in r['checks']])
        self.assertIn('controlled_correction_short',calls)
        self.assertEqual(r['not_evaluated_columns'],['quiet_percentile'])
        self.assertFalse(r['sample_passed']);self.assertFalse(r['numeric_passed'])
        self.assertEqual(r['failures'][0]['receipt']['http_status'],200)

    def test_denial_stops_remaining_operations_instead_of_trying_other_columns(self):
        api,client,at,calls,_=self.setup_probe(code='HTTP_451')
        r=qualify_selected(environment='CODEX_LOCAL',native_symbol='TESTUSDT',api=api,client=client,clock=lambda:at)
        self.assertEqual(calls[-1],'quiet_percentile')
        self.assertNotIn('efficiency16',calls);self.assertFalse(r['sample_passed'])
        self.assertIn('efficiency16',r['not_evaluated_columns'])

    def test_clock_fault_preserves_numeric_diagnostics_but_cannot_qualify(self):
        api,client,at,_,_=self.setup_probe(fail=None,future=True)
        r=qualify_selected(environment='CODEX_LOCAL',native_symbol='TESTUSDT',api=api,client=client,clock=lambda:at)
        self.assertTrue(r['numeric_passed']);self.assertFalse(r['sample_passed'])
        self.assertEqual(r['time_integrity'],'UNQUALIFIED_NO_CAUSAL_OR_LIVE_PROMOTION')
        self.assertEqual(r['failures'][0]['code'],'CLOSED_BAR_CUTOFF_MISMATCH')
        self.assertEqual(len(r['checks']),33)

    def test_300_bar_validation_is_explicit_default_narrow_bound_preserved(self):
        _,_,at,_,candle=self.setup_probe()
        kwargs=dict(requested_symbol='TESTUSDT',timeframe='1h',received_at=at,schema_hash='schema',response_hash='response')
        with self.assertRaisesRegex(ContractError,'CLOSED_HISTORY_REQUIRED'):candle_observation(candle,**kwargs)
        self.assertEqual(candle_observation(candle,max_bars=300,**kwargs).temporal_status,'CLOSED_CURRENT')
        with self.assertRaises(ContractError):candle_observation(candle,max_bars=301,**kwargs)

    def test_independent_flat_zero_and_tie_semantics(self):
        b=flat(180,span=0)
        self.assertEqual(independent_column('quiet_percentile',b),D('.5'))
        self.assertEqual(independent_column('efficiency16',b),0)
        self.assertEqual(independent_column('displacement',b),0)
        self.assertEqual(independent_column('body_fraction',b),0)
        self.assertEqual(independent_column('controlled_correction_short',b),0)
        self.assertIn('/if(amp>0,amp,1)',CORRECTIONS['controlled_correction_short'])
        self.assertEqual(independent_column('quote_rvol32',[replace(x,base_volume=D(0),quote_volume=D(0),buy_base=D(0),buy_quote=D(0)) for x in b]),0)

    def test_registered_percentile_stays_below_observed_provider_nesting_limit(self):
        expression=next(c.expression for c in CORE_COLUMNS if c.id=='quiet_percentile')
        depth=peak=0
        for c in expression:
            depth+=1 if c=='(' else -1 if c==')' else 0;peak=max(peak,depth)
        self.assertLess(peak,128);self.assertEqual(depth,0)
        self.assertLess(len(expression),10000);self.assertIn('let v0=',expression)
        exported=next(c[1] for c in make_remote_pack('CORE_1H',('TESTUSDT',)).columns if c[0]=='quiet_percentile')
        self.assertTrue(exported.startswith('let v0='));self.assertNotIn('(let ',exported)
        self.assertEqual(next(c.expression for c in CORE_COLUMNS if c.id=='atr14'),'rma(max((high-low),max(abs((high-(close)[1])),abs((low-(close)[1])))),14)')
        self.assertTrue(all('let e=' not in x for x in CORRECTIONS.values()))
        with self.assertRaises(ContractError):compile_expr(Expr('field',('close; unsafe()',)))

    def test_genuine_short_rolling_window_retains_exact_interval_and_no_bar_claim(self):
        at=iso_seconds(1794665848)
        inv=SimpleNamespace(symbols=('ACUUSDT',),mode='VERIFIED_INVENTORY')
        row={'symbol':'ACUUSDT','closeTime':1794665840612,'openTime':1794579480000,
            'priceChangePercent':'1','quoteVolume':'1381698.3829000','volume':'100','lastPrice':'2'}
        result=normalize_market([row],kind='ticker',inventory=inv,captured_at=at,response_hash='genuine-source-shape')
        self.assertEqual(result['observations'][0]['values']['window_seconds'],86360.612)
        self.assertFalse(result['synchronized_closed_bar_cross_section'])
        row['openTime']-=3600000
        self.assertEqual(len(normalize_market([row],kind='ticker',inventory=inv,captured_at=at,response_hash='x')['failed_symbols']),1)

    def test_versioned_new_core_decodes_small_values_and_zero_unknowns(self):
        pack=make_remote_pack('CORE_1H',('TESTUSDT',));inst=Instrument('TESTUSDT','BINANCE_USDM')
        rules=[{'id':str(i),'left':{'kind':'formula','expression':c[1]},'operator':'atOrAbove',
            'right':{'kind':'constant','value':0}} for i,c in enumerate(pack.columns)]
        encoded={'close':10000000000,'tr':200000000,'atr14':200000000,'width16':2000000,
            'quiet_percentile':50000000,'efficiency16':0,'progress16':100000000,
            'prior_high16':10100000000,'prior_low16':9900000000,'tr_fraction':2000000,
            'displacement':200000000,'body_fraction':0}
        data={'exchange':'binance','market':'futures','quote':'USDT','timeframe':'1h',
            'screened':1,'evaluated':1,'returned':1,'matched':1,'couldNotEvaluate':0,'truncated':False,
            'rules':rules,'results':[{'symbol':'TESTUSDT','last':100,'observationTime':START,
                'values':[{'left':encoded[c[0]],'right':0,'matched':True,'ruleId':str(i)} for i,c in enumerate(pack.columns)]}]}
        cutoff=iso_seconds(START+3600)
        _,values=normalize_screen(('TESTUSDT',),data,{'received_at_utc':cutoff,'schema_sha256':'s',
            'response_sha256':'r','response_bytes':1,'elapsed_ms':1},pack=pack,instruments={'TESTUSDT':inst},cutoff=cutoff)
        by={r['measurement_id']:r['value'] for r in values}
        self.assertEqual(by['quiet_percentile'],D('.5'));self.assertEqual(by['width16'],D('.02'))
        self.assertIsNone(by['efficiency16']);self.assertEqual(by['body_fraction'],0)
        self.assertEqual(by['displacement'],1)
