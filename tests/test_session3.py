"""Deterministic SYNTHETIC counterexamples; these are never live evidence."""
import copy
from dataclasses import replace,asdict
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from researcher.contracts import ContractError,encode,digest,symbol
from researcher.numerics import (Bar,validate_bars,true_ranges,wilder_atr,normalized_width,
    past_percentile,compression,efficiency,overlap,displacement,confirmed_swings,swing_ladder,
    distance,touch_episodes,relative_quote_volume,bar_delta,anchored_value,relative_return,
    lag_trained_beta,parse_klines,first_obstacle)
from researcher.structures import (Reference,StructuralEvent,boundary_events,gap_lifecycle,
    ResearchLedger,swing_references,swing_breaks,formation_candidates)
from researcher.binance import OfficialResearchAPI,CachedPublicHTTP
from researcher.market import normalize_market
from researcher.transport import PublicHTTP,Response,ProviderError,ENDPOINTS
from researcher.settings import load_config,validate_config,ROOT
from researcher.method_registry import capability_coverage
from researcher.live_oracle import compare_formula

BASE=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp()*1000)


def setUpModule():
    (ROOT/'work').mkdir(exist_ok=True)


def iso(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()


def bars_from(rows,*,name='TESTUSDT',tf='1h',start=BASE):
    width=3600000 if tf=='1h' else 900000
    out=[]
    for j,r in enumerate(rows):
        if not isinstance(r,(tuple,list)):r=(r,r+1,r-1,r)
        o,h,l,c=map(lambda x:D(str(x)),r)
        at=start+j*width;end=iso(at+width)
        out.append(Bar(name,tf,at,o,h,l,c,D(10),D(1000),D(6),D(610),10,
                       'SYNTHETIC',end,available_at=end))
    return out


def ref_for(bars,*,direction=1,lo=100,hi=100):
    return Reference(bars[0].native_symbol,bars[0].timeframe,'RANGE_TOP' if direction==1 else 'RANGE_BOTTOM',
        D(lo),D(hi),D(10),D('.1'),direction,iso(bars[0].open_ms-7200000),iso(bars[0].open_ms-3600000),
        iso(bars[0].open_ms-3600000),iso(bars[-1].end_ms+86400000),('SYNTHETIC_PREKNOWN',),'PREDECLARED_TEST')


def hypotheses(result):return {h['family']:h for h in result['hypotheses']}


def result_for(rows,*,direction=1):
    bars=bars_from(rows);ref=ref_for(bars,direction=direction)
    return bars,ref,boundary_events(ref,bars,as_of=bars[-1].end)


class NumericalSemantics(unittest.TestCase):
    def test_true_range_gap_and_wilder_seed(self):
        b=bars_from([100,100,100,110,110])
        self.assertEqual(true_ranges(b),[None,D(2),D(2),D(11),D(2)])
        a=wilder_atr(b,3)
        self.assertEqual(a[:3],[None]*3);self.assertEqual(a[3],D(5));self.assertEqual(a[4],D(4))

    def test_atr_does_not_seed_with_missing_previous_close(self):
        with self.assertRaisesRegex(ContractError,'INSUFFICIENT_HISTORY'):wilder_atr(bars_from([100]*14))

    def test_percentile_ties_sign_and_missing_baseline(self):
        self.assertEqual(past_percentile(D(2),[1,2,2,3],required=4),D('.5'))
        self.assertEqual(past_percentile(D(0),[1,2,3,4],required=4),D(0))
        with self.assertRaises(ContractError):past_percentile(0,[1],required=128)

    def test_compression_needs_excluded_window_warmup(self):
        with self.assertRaisesRegex(ContractError,'INSUFFICIENT_HISTORY'):compression(bars_from([100]*158))
        result=compression(bars_from([100]*159))
        self.assertEqual(result['past_percentile'],D('.5'))
        self.assertTrue(result['measured_window_excluded'])

    def test_efficiency_constant_monotonic_and_churn(self):
        self.assertIsNone(efficiency(bars_from([100]*17)))
        self.assertEqual(efficiency(bars_from(list(range(100,117)))),D(1))
        self.assertEqual(efficiency(bars_from([100,101]*8+[100])),D(0))

    def test_overlap_displacement_and_frozen_distance(self):
        b=bars_from([(100,105,95,100),(100,104,96,103)])
        self.assertEqual(overlap(*b,D('.1')),1)
        self.assertEqual(displacement(*b,D(10),D('.1'))['body_fraction'],D(3)/8)
        self.assertEqual(distance(110,100,105,10),D('.5'))

    def test_pivot_known_only_after_right_confirmation(self):
        b=bars_from([(10,11,9,10),(11,12,10,11),(14,15,13,14),(14,15,13,14),(12,13,11,12),(11,12,10,11)])
        self.assertEqual(confirmed_swings(b[:4]),[])
        s=confirmed_swings(b)
        h=[x for x in s if x['kind']=='SWING_HIGH']
        self.assertEqual(len(h),1);self.assertEqual(h[0]['index'],2)
        self.assertEqual(h[0]['known_at'],b[4].end)

    def test_future_append_does_not_move_confirmed_pivots(self):
        b=bars_from([100,102,106,101,100,99,98,105,100,99])
        old=confirmed_swings(b[:7]);new=confirmed_swings(b)
        self.assertEqual(old,[s for s in new if s['known_index']<7])

    def test_continuous_touch_vs_separated_episode(self):
        b=bars_from([(99,100,98,99)]*5+[(90,92,89,91),(99,100,98,99)])
        self.assertEqual(len(touch_episodes(b[:5],lo=D(100),hi=D(100),atr=D(10),buffer=D(1))),1)
        self.assertEqual(len(touch_episodes(b,lo=D(100),hi=D(100),atr=D(10),buffer=D(1))),2)

    def test_rvol_uses_prior_quote_median(self):
        b=bars_from([100]*33);b[-1]=replace(b[-1],quote_volume=D(2000))
        self.assertEqual(relative_quote_volume(b),2)
        b=[replace(x,base_volume=D(0),quote_volume=D(0),buy_base=D(0),buy_quote=D(0)) for x in b]
        self.assertIsNone(relative_quote_volume(b))

    def test_delta_is_not_candle_color_or_footprint(self):
        b=bars_from([(101,102,99,100)])[0]
        delta=bar_delta(b)
        self.assertEqual(delta['delta_base'],2);self.assertEqual(delta['delta_quote'],220)
        self.assertFalse(delta['footprint'])

    def test_exact_whole_bar_value_and_anchor(self):
        b=bars_from([100,100]);b[1]=replace(b[1],base_volume=D(20),quote_volume=D(2200))
        v=anchored_value(b,anchor_ms=BASE,anchor_known_at=iso(BASE))
        self.assertEqual(v['vwap_whole_bars'],D(3200)/30)
        self.assertFalse(v['true_profile']);self.assertIsNone(v['exact_trade_weighted_variance'])
        with self.assertRaises(ContractError):anchored_value(b,anchor_ms=BASE,anchor_known_at=b[0].end)

    def test_invalid_units_missing_bars_and_stale_tail(self):
        b=bars_from([100]*4)
        for bad in ([b[0],b[2]], [replace(b[0],volume_units='CONTRACTS')],
                    [replace(b[0],buy_base=D(11))], [replace(b[0],quote_volume=D(-1))]):
            with self.assertRaises(ContractError):validate_bars(bad)
        with self.assertRaisesRegex(ContractError,'STALE'):validate_bars(b,cutoff=iso(b[-1].end_ms+3600000),require_current=True)

    def test_bar_availability_and_forming_rejected(self):
        b=bars_from([100])[0]
        with self.assertRaises(ContractError):validate_bars([replace(b,received_at=iso(b.open_ms))])
        with self.assertRaises(ContractError):validate_bars([b],cutoff=iso(b.open_ms))

    def test_independent_kline_clock_schema(self):
        b=bars_from([100])[0]
        r=[BASE,'100','101','99','100','10',b.end_ms-1,'1000',10,'6','610','0']
        receipt={'received_at_utc':b.end,'response_sha256':'SYNTHETIC'}
        parsed=parse_klines([r],native_symbol='TESTUSDT',timeframe='1h',cutoff=b.end,receipt=receipt,requested_bars=1)
        self.assertEqual(parsed[0].end,b.end)
        r[6]-=1
        with self.assertRaises(ContractError):parse_klines([r],native_symbol='TESTUSDT',timeframe='1h',cutoff=b.end,receipt=receipt,requested_bars=1)

    def test_relative_alignment_and_beta_not_correlation(self):
        # Alternating exact exponential returns; asset has slope two.
        returns=[D('.001'),D('-.002'),D('.003'),D('-.001')]*10
        price=D(100);x=[price];y=[price]
        for r in returns:price=price*r.exp();x.append(price);y.append(D(100)*(price/D(100))**2)
        a=bars_from([float(z) for z in y]);b=bars_from([float(z) for z in x],name='BTCUSDT')
        beta=lag_trained_beta(a,b)
        self.assertAlmostEqual(float(beta['beta']),2,places=10)
        self.assertLess(abs(beta['residual']),D('1e-12'))
        self.assertLess(utc_ms(beta['training_end']),utc_ms(beta['evaluation_end']))
        with self.assertRaises(ContractError):relative_return(a,b[1:])

    def test_relative_variance_zero_unknown(self):
        self.assertIsNone(lag_trained_beta(bars_from([100]*34),bars_from([100]*34,name='BTCUSDT')))


def utc_ms(x):return datetime.fromisoformat(x).timestamp()*1000


class CausalSequences(unittest.TestCase):
    pressure=[(99,100,98,99),(92,94,90,92),(99,100,98,99)]

    def test_f2_requires_pressure_and_two_later_outside_closes(self):
        b,r,x=result_for(self.pressure+[(100,105,99,104),(104,106,103,105),(105,107,104,106)])
        self.assertEqual(hypotheses(x)['F2']['current_formation_verdict'],'SUPPORTED')
        self.assertNotEqual(hypotheses(x)['F5']['current_formation_verdict'],'SUPPORTED')
        earlier=boundary_events(r,b[:-1],as_of=b[-2].end)
        self.assertNotEqual(hypotheses(earlier)['F2']['current_formation_verdict'],'SUPPORTED')

    def test_bare_breakout_cannot_claim_full_f2_or_f5(self):
        _,_,x=result_for([(100,105,99,104),(104,106,103,105),(105,107,104,106)])
        self.assertEqual(hypotheses(x)['F2']['current_formation_verdict'],'UNKNOWN')
        self.assertEqual(hypotheses(x)['F5']['current_formation_verdict'],'UNKNOWN')

    def test_wick_reclaim_then_opposite_initiative_supports_f4(self):
        _,_,x=result_for(self.pressure+[(100,105,95,97),(97,98,82,84)])
        self.assertEqual(hypotheses(x)['F4']['current_formation_verdict'],'SUPPORTED')
        self.assertEqual(hypotheses(x)['F2']['current_formation_verdict'],'CONTRADICTED')
        self.assertNotEqual(hypotheses(x)['F5']['current_formation_verdict'],'SUPPORTED')

    def test_f5_genuine_reclaim_attempt_rebreak_and_later_hold(self):
        _,r,x=result_for(self.pressure+[(100,105,95,97),(97,98,90,92),(99,105,98,104),
                                     (104,106,103,105),(105,107,104,106)])
        self.assertEqual(hypotheses(x)['F5']['current_formation_verdict'],'SUPPORTED')
        self.assertEqual(hypotheses(x)['F2']['current_formation_verdict'],'CONTRADICTED')
        kinds=[e['kind'] for e in x['events']]
        for a,b in zip(['RECLAIM','OPPOSING_ATTEMPT','REBREAK_SAME_REFERENCE'],['OPPOSING_ATTEMPT','REBREAK_SAME_REFERENCE','OUTSIDE_HOLD']):
            self.assertLess(kinds.index(a),kinds.index(b))
        self.assertTrue(all(e['reference_id']==r.id for e in x['events']))

    def test_reclaim_without_later_attempt_is_not_f5(self):
        _,_,x=result_for([(100,105,95,97),(99,105,98,104),(104,106,103,105),(105,107,104,106)])
        self.assertEqual(hypotheses(x)['F5']['current_formation_verdict'],'UNKNOWN')

    def test_mirrored_lower_boundary(self):
        rows=self.pressure+[(100,105,95,97),(97,98,90,92),(99,105,98,104),(104,106,103,105),(105,107,104,106)]
        mirrored=[(200-o,200-l,200-h,200-c) for o,h,l,c in rows]
        _,_,x=result_for(mirrored,direction=-1)
        self.assertEqual(hypotheses(x)['F5']['current_formation_verdict'],'SUPPORTED')

    def test_no_future_ref_and_unavailable_ref(self):
        b=bars_from(self.pressure);r=ref_for(b)
        future=replace(r,known_at=b[-1].end,available_at=b[-1].end)
        self.assertEqual(boundary_events(future,b,as_of=b[-1].end)['events'],[])
        unavailable=replace(r,available_at=iso(b[-1].end_ms+3600000))
        self.assertEqual(boundary_events(unavailable,b,as_of=b[-1].end)['status'],'NOT_AVAILABLE')

    def test_expired_reference_not_reused(self):
        b=bars_from(self.pressure+[(100,110,99,108)]);r=replace(ref_for(b),valid_until=b[0].end)
        x=boundary_events(r,b,as_of=b[-1].end)
        self.assertEqual(x['status'],'EXPIRED')
        self.assertNotIn('CLOSE_OUTSIDE',[e['kind'] for e in x['events']])

    def test_append_future_asof_stability_and_timestamp_shift(self):
        b,r,x=result_for(self.pressure+[(100,105,95,97),(97,98,90,92)])
        future=bars_from([(99,105,98,104),(104,106,103,105)],start=b[-1].end_ms)
        self.assertEqual(x,boundary_events(r,b+future,as_of=b[-1].end))
        shift=7*86400000
        shifted=[replace(z,open_ms=z.open_ms+shift,received_at=iso(z.end_ms+shift),available_at=iso(z.end_ms+shift)) for z in b]
        rr=replace(r,created_at=iso(utc_ms(r.created_at)+shift),known_at=iso(utc_ms(r.known_at)+shift),
                   available_at=iso(utc_ms(r.available_at)+shift),valid_until=iso(utc_ms(r.valid_until)+shift))
        xx=boundary_events(rr,shifted,as_of=shifted[-1].end)
        self.assertEqual([e['kind'] for e in x['events']],[e['kind'] for e in xx['events']])
        self.assertEqual([h['current_formation_verdict'] for h in x['hypotheses']],[h['current_formation_verdict'] for h in xx['hypotheses']])

    def test_multiple_events_same_reference_keep_stable_ids(self):
        b,r,x=result_for(self.pressure+[(100,105,95,97),(97,98,90,92),(99,105,98,104)])
        self.assertEqual(len({e['id'] for e in x['events']}),len(x['events']))
        with ResearchLedgerContext() as l:
            l.record(r,x['events'],hypotheses=x['hypotheses'],cutoff=b[-1].end)
            counts=l.counts();l.record(r,x['events'],hypotheses=x['hypotheses'],cutoff=b[-1].end)
            self.assertEqual(counts,l.counts())

    def test_fvg_birth_then_invalidation_and_inverse_later_retest(self):
        b=bars_from([(99,100,98,99),(100,108,99,107),(106,109,105,108),
                     (104,104,98,99),(99,100,97,98),(101,106,98,99)])
        g=gap_lifecycle(b,D('.1'),as_of=b[-1].end)[0]
        self.assertEqual(g['reference'].known_at,b[2].end)
        self.assertEqual(g['status'],'IFVG_CANDIDATE')
        kinds=[e['kind'] for e in g['events']]
        self.assertLess(kinds.index('ZONE_ACCEPTED_THROUGH'),kinds.index('IFVG_OPPOSITE_SIDE_RETEST'))
        born=gap_lifecycle(b,D('.1'),as_of=b[2].end)[0]
        self.assertEqual(born['status'],'BORN')

    def test_fvg_no_gap_is_not_born(self):
        self.assertEqual(gap_lifecycle(bars_from([100]*6),D('.1'),as_of=iso(BASE+6*3600000)),[])

    def test_ledger_rejects_reverse_order_and_cross_reference_atomically(self):
        b,r,x=result_for(self.pressure+[(100,105,95,97),(97,98,90,92)])
        with ResearchLedgerContext() as l:
            with self.assertRaises(ContractError):l.record(r,list(reversed(x['events'])),cutoff=b[-1].end)
            self.assertEqual(l.counts()['event'],0)
            bad=copy.deepcopy(x['events']);bad[0]['reference_id']='WRONG'
            with self.assertRaises(ContractError):l.record(r,bad,cutoff=b[-1].end)
            self.assertEqual(l.counts()['reference'],0)

    def test_lifecycle_consumed_invalidated_not_active_and_persistent_reopen(self):
        b,r,x=result_for(self.pressure)
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
            path=tmp+'/ledger.sqlite';l=ResearchLedger(path)
            l.record(r,x['events'],cutoff=b[-1].end);self.assertEqual(len(l.active_references(b[-1].end)),1)
            l.transition(r,state='CONSUMED',at=b[-1].end);l.close()
            l=ResearchLedger(path);self.assertEqual(l.active_references(b[-1].end),[]);l.close()

    def test_ledger_hypothesis_cannot_invent_event(self):
        b,r,x=result_for(self.pressure);bad=copy.deepcopy(x['hypotheses']);bad[0]['supporting_ids']=['FAKE']
        with ResearchLedgerContext() as l:
            with self.assertRaises(ContractError):l.record(r,x['events'],hypotheses=bad,cutoff=b[-1].end)
            self.assertEqual(l.counts()['event'],0)

    def test_context_is_not_a_detector_eligibility_input(self):
        b,r,x=result_for(self.pressure+[(100,105,95,97),(97,98,82,84)])
        # BTC-up/down/unknown cannot be passed as a veto; same local evidence.
        for context in ['BTC_UP','BTC_DOWN','BTC_UNKNOWN']:
            self.assertEqual(x,boundary_events(r,b,as_of=b[-1].end),context)
        self.assertIn('NULL',hypotheses(x))


class ResearchLedgerContext:
    def __enter__(self):self.ledger=ResearchLedger();return self.ledger
    def __exit__(self,*_):self.ledger.close()


class LiveContracts(unittest.TestCase):
    def test_unicode_identity_preserved_without_multiplier_inference(self):
        self.assertEqual(symbol('币安人生USDT'),'币安人生USDT')
        for n in ['ＡUSDT','BTC\nUSDT','BTC/USDT','币安人生USDT?x=1','btcUSDT']:
            with self.assertRaises(ContractError):symbol(n)

    def test_full_registry_has_all_contract_fields_and_no_fake_specialists(self):
        c=load_config();coverage=capability_coverage(c)
        self.assertEqual(len(coverage['methods']),31);self.assertEqual(len(coverage['families']),9)
        for i in [17,18,22,23,24,26,28,31]:
            self.assertEqual(coverage['methods'][i-1]['state'],'BLOCKED_DATA')
        self.assertEqual(coverage['methods'][14]['state'],'DEFINITION_PENDING')
        altered=copy.deepcopy(c);altered['methods'][0]['implementation']['production_enabled']=True
        with self.assertRaises(ContractError):validate_config(altered)

    def test_public_transport_rejects_arbitrary_urls_queries_auth_and_large_download(self):
        h=PublicHTTP()
        for endpoint,kw in [('https://other.com',{}),('binance_klines',{'query':{'symbol':'BTCUSDT','interval':'1h','limit':301,'endTime':BASE}}),
                            ('binance_inventory',{'query':{'apiKey':'x'}})]:
            with self.assertRaises(ProviderError):h.request(endpoint,**kw)

    def test_cached_api_reads_do_not_repeat_downloads(self):
        class H:
            receipts=[]
            def __init__(self):self.calls=0
            def request(self,*a,**kw):self.calls+=1;return Response(b'{}',{},{} )
        h=H();clock=[0];cached=CachedPublicHTTP(h,clock=lambda:clock[0])
        cached.request('binance_inventory');cached.request('binance_inventory')
        self.assertEqual(h.calls,1);clock[0]=301;cached.request('binance_inventory');self.assertEqual(h.calls,2)

    def test_ticker_minute_rounding_is_explicit_not_synchronized(self):
        from test_session2 import official,AT
        inv=official()
        end=int(datetime.fromisoformat(AT).timestamp()*1000)
        row={'symbol':'BTCUSDT','closeTime':end,'openTime':end-86459000,
             'priceChangePercent':'1','quoteVolume':'1000','volume':'10','lastPrice':'100'}
        result=normalize_market([row],kind='ticker',inventory=inv,captured_at=AT,response_hash='SYNTHETIC')
        self.assertEqual(len(result['observations']),1)
        self.assertEqual(result['observations'][0]['values']['window_seconds'],86459)
        self.assertFalse(result['synchronized_closed_bar_cross_section'])

    def test_independent_formula_oracle_detects_wrong_price_and_seed(self):
        b=bars_from([100+i for i in range(65)])
        times=[z.open_ms//1000 for z in b[-20:]]
        data={'symbol':'TESTUSDT','exchange':'binance','market':'futures','timeframe':'1h','bars':65,
              'tailTimes':times,'tail':[float(z.close) for z in b[-20:]]}
        kwargs=dict(label='close',window_from=b[0].open_ms//1000,window_to=b[-1].open_ms//1000,expected_count=65,tick=D('.1'))
        self.assertTrue(compare_formula(data,b,**kwargs)['passed'])
        data['tail'][-1]+=1;self.assertFalse(compare_formula(data,b,**kwargs)['passed'])

    def test_small_sample_api_rejects_more_than_five_symbols_and_calls(self):
        api=OfficialResearchAPI();api.sample_calls=10
        from researcher.contracts import Instrument
        with self.assertRaises(ContractError):api.klines(Instrument('BTCUSDT','BINANCE_USDM'),timeframe='1h',cutoff=iso(BASE))




class LiveIntegration(unittest.TestCase):
    def test_disjoint_independent_partitions_include_young_and_native_names(self):
        from test_session2 import official,official_row,AT
        from researcher.cohorts import independent_partitions
        names=[f'COIN{i:03d}USDT' for i in range(240)]
        names[0]='币安人生USDT';names[1]='1000TESTUSDT'
        rows=[official_row(n) for n in names]
        rows[0]['onboardDate']=int(datetime.fromisoformat(AT).timestamp()*1000)-86400000
        inv=official(rows)
        ticker={'kind':'ticker','observations':[{'native_symbol':n,'values':{'quoteVolume':str(i+1)},
            'received_at_utc':AT,'source_scope':'OFFICIAL_BINANCE_USDM'} for i,n in enumerate(names)]}
        c=independent_partitions(inv,ticker,as_of=AT)
        self.assertEqual([len(x) for x in c['partitions']],[50,50,7])
        self.assertEqual(len(set(sum(c['partitions'],[]))),107)
        self.assertIn('币安人生USDT',c['verified_young_members'])
        self.assertEqual(c['verified_multiplier_members'],[])
        self.assertFalse(c['provider_top_lists_used'])
        ticker['observations'].pop()
        with self.assertRaisesRegex(ContractError,'DENOMINATOR'):independent_partitions(inv,ticker,as_of=AT)

    def test_end_to_end_live_path_reuses_existing_runtime_and_no_manual_files(self):
        from test_session2 import official,official_row,response,AT
        from researcher.discovery import scan_live
        from types import SimpleNamespace
        c=load_config();names=c['external_discovery']['observed_symbols']
        inv=official([official_row(n) for n in names])
        class API:
            http=SimpleNamespace(receipts=[],cache_hits=0)
            def inventory(self):return inv
            def pulse(self,inventory):
                return [{'kind':'ticker','observations':[{'native_symbol':n} for n in names]}]
        class Client:
            http=SimpleNamespace(receipts=[])
            tools={'screener_run':{'inputSchema':{}}}
            def connect(self):pass
            def call(self,name,args):
                self.http.receipts.append({'received_at_utc':AT,'response_sha256':'SYNTHETIC',
                    'elapsed_ms':1,'response_bytes':100,'http_status':200})
                return response(args['manualSymbols'],args['timeframe'])
        with patch('researcher.discovery.now_utc',return_value=AT):
            r=scan_live(api=API(),client=Client())
        self.assertEqual(r['source_faults'],[])
        self.assertEqual(r['coverage']['eligible_contracts'],5)
        self.assertEqual([len(x['requested_symbols']) for x in r['packs']],[5,5])
        self.assertEqual(r['coverage']['valid_remote_core_evaluated'],0)
        self.assertEqual(r['shortlist'],[]);self.assertFalse(r['trade_authorization'])

    def test_denied_live_api_surfaces_blocker_and_does_not_fabricate_fallback(self):
        from researcher.discovery import scan_live
        from types import SimpleNamespace
        class API:
            http=SimpleNamespace(receipts=[],cache_hits=0)
            def inventory(self):raise ProviderError('HTTP_451')
        r=scan_live(api=API())
        self.assertEqual(r['operation_status'],'BLOCKED_OR_UNQUALIFIED')
        self.assertIsNone(r['coverage']['eligible_contracts'])
        self.assertEqual(r['source_faults'][0]['code'],'HTTP_451')
        self.assertEqual(r['packs'],[])

    def test_index_and_premarket_are_excluded_unknown_class_remains_partial(self):
        from test_session2 import official,official_row
        rows=[official_row('INDEXUSDT'),official_row('PREUSDT'),official_row('UNKNOWNUSDT')]
        for row,kind in zip(rows,['INDEX','PREMARKET','UNRECOGNIZED']):row['underlyingType']=kind
        i=official(rows)
        self.assertEqual(len(i.excluded),2)
        self.assertEqual(i.provisional_symbols,('UNKNOWNUSDT',))
        self.assertEqual(i.mode,'PARTIAL_INVENTORY')
        row=official_row('1000TESTUSDT')
        row['deliveryDate']=4133404800000
        row['filters'].append({'filterType':'MIN_NOTIONAL','notional':'5'})
        saved=official([row]).instruments[0]
        self.assertEqual(saved.exchange_rules[-1]['notional'],'5')
        self.assertEqual(saved.listing_metadata['deliveryDate'],4133404800000)
        self.assertIsNone(saved.contract_multiplier)
        row['filters'][-1]['notional']='999'
        self.assertEqual(saved.exchange_rules[-1]['notional'],'5')


class PersistenceAndCounterexamples(unittest.TestCase):
    def test_reference_identity_and_scale_are_frozen_across_later_fetch(self):
        b,r,x=result_for(CausalSequences.pressure)
        later=replace(r,available_at=b[-1].end,atr=D(99),tick=D('.2'))
        self.assertEqual(r.id,later.id)
        with ResearchLedgerContext() as l:
            l.record(r,x['events'],cutoff=b[-1].end)
            frozen=l.freeze_reference(later)
            self.assertEqual(frozen.atr,D(10));self.assertEqual(frozen.available_at,r.available_at)
            xx=boundary_events(frozen,[replace(v,available_at=None,received_at=b[-1].end) for v in b],as_of=b[-1].end)
            l.record(frozen,xx['events'],cutoff=b[-1].end)
            self.assertEqual(l.counts()['event'],len(x['events']))

    def test_direct_primitives_cannot_ignore_missing_middle_bars(self):
        b=bars_from([100]*40);missing=b[:20]+b[21:]
        for fn in [normalized_width,efficiency,relative_quote_volume]:
            with self.assertRaisesRegex(ContractError,'MISSING'):fn(missing)

    def test_first_obstacle_uses_identity_time_and_near_edge(self):
        b=bars_from([100]*4);r=ref_for(b,lo=110,hi=115)
        self.assertEqual(first_obstacle(100,1,[r],at=b[-1].end,native_symbol='TESTUSDT',timeframe='1h'),(10,r.id))
        stale=replace(r,valid_until=b[0].end)
        self.assertIsNone(first_obstacle(100,1,[stale],at=b[-1].end,native_symbol='TESTUSDT',timeframe='1h'))
        with self.assertRaises(ContractError):first_obstacle(100,1,[r],at=b[-1].end,native_symbol='OTHERUSDT',timeframe='1h')

    def test_atr_oracle_distinguishes_provider_seed_without_promotion(self):
        b=bars_from([100+i for i in range(65)])
        # Alternative n=14 seed includes first H-L, then standard recurrence.
        tr=[D(2)]+true_ranges(b)[1:];values=[None]*65;values[13]=sum(tr[:14],D(0))/14
        for i in range(14,65):values[i]=(13*values[i-1]+tr[i])/14
        data={'symbol':'TESTUSDT','exchange':'binance','market':'futures','timeframe':'1h','bars':65,
              'tailTimes':[z.open_ms//1000 for z in b[-20:]],'tail':[str(x) for x in values[-20:]]}
        # Change first range to ensure the two seeds differ.
        b[0]=replace(b[0],high=D(110),low=D(90))
        tr=[D(20)]+true_ranges(b)[1:];values[13]=sum(tr[:14],D(0))/14
        for i in range(14,65):values[i]=(13*values[i-1]+tr[i])/14
        data['tail']=[str(x) for x in values[-20:]]
        out=compare_formula(data,b,label='atr',window_from=b[0].open_ms//1000,
                            window_to=b[-1].open_ms//1000,expected_count=65,tick=D('.1'))
        self.assertFalse(out['passed']);self.assertTrue(out['first_bar_hl_seed_passed'])
        self.assertTrue(out['conditional_recurrence_passed']);self.assertFalse(out['remote_production_enabled'])

    def test_delayed_middle_bar_cannot_create_fake_adjacent_gap(self):
        from researcher.structures import visible_bars
        b=bars_from([100]*4)
        b[1]=replace(b[1],available_at=iso(b[-1].end_ms+3600000),received_at=iso(b[-1].end_ms+3600000))
        with self.assertRaisesRegex(ContractError,'MISSING'):visible_bars(b,b[-1].end)


class RecordedIndependentEvidence(unittest.TestCase):
    def test_live_source_comparisons_preserve_known_atr_counterexamples(self):
        path=ROOT/'evidence/external-first/session3/live-qualification.json'
        report=json.loads(path.read_text())
        outcomes=[o for sample in report['oracles'] for o in sample['outcomes']]
        passed=failed=0
        for outcome in outcomes:
            self.assertEqual(outcome['classification'],'INDEPENDENT_OFFICIAL_BINANCE_REFERENCE')
            for comparison in outcome['comparisons']:
                error=abs(D(comparison['actual'])-D(comparison['independent']))
                ok=error<=D(comparison['tolerance'])
                self.assertEqual(ok,comparison['passed'])
                passed+=int(ok);failed+=int(not ok)
        self.assertEqual((passed,failed),(840,80))
        mismatches=[o for o in outcomes if not o['passed']]
        self.assertEqual(len(mismatches),4)
        for outcome in mismatches:
            self.assertEqual(outcome['formula'],'atr')
            self.assertTrue(outcome['first_bar_hl_seed_passed'])
            self.assertTrue(outcome['conditional_recurrence_passed'])
            self.assertFalse(outcome['remote_production_enabled'])
        self.assertEqual(len(report['source_faults']),2)
        self.assertTrue(all(x['code']=='MCP_TOOL_ERROR' for x in report['source_faults']))

    def test_recorded_real_metadata_replays_without_rewriting_history(self):
        report=json.loads((ROOT/'evidence/external-first/session3/selected-causal-metadata.json').read_text())
        with ResearchLedgerContext() as ledger:
            for _ in range(2):
                for bundle in report['bundles']:
                    raw=dict(bundle['reference'])
                    for key in ['lo','hi','atr','tick']:raw[key]=D(raw[key])
                    raw['source_ids']=tuple(raw['source_ids']);ref=Reference(**raw)
                    ledger.record(ref,bundle['events'],hypotheses=bundle['hypotheses'],cutoff=bundle['as_of'])
            self.assertEqual(ledger.counts(),{'reference':40,'event':59,'hypothesis':200,'lifecycle':0})


class AdditionalFormationCounterexamples(unittest.TestCase):
    path=[100,101,110,108,105,100,102,105,115,110,108,105,108,110,118,114,111,108,111,112]

    def test_f1_controlled_pullback_is_disconfirmed_by_protected_start_breach(self):
        b=bars_from(self.path)
        f=next(x for x in formation_candidates(b,D('.1'),as_of=b[-1].end) if x['family']=='F1')
        self.assertTrue(f['controlled_range_predicate']);self.assertFalse(f['production_enabled'])
        failed=bars_from([100],start=b[-1].end_ms)
        x=formation_candidates(b+failed,D('.1'),as_of=failed[-1].end)
        f=next(z for z in x if z['family']=='F1')
        self.assertFalse(f['controlled_range_predicate'])

    def test_swing_choch_requires_preknown_confirmed_ladder(self):
        b=bars_from(self.path+[106,102])
        result=swing_breaks(b,D('.1'),as_of=b[-1].end)
        events=[e for e in result['events'] if e.kind=='CHOCH_CANDIDATE']
        self.assertTrue(events)
        refs={r.id:r for r in result['references']}
        for e in events:self.assertLessEqual(utc_ms(refs[e.reference_id].known_at),utc_ms(e.occurred_from))

    def test_isolated_shock_without_prior_quiet_is_not_f3(self):
        b=bars_from([100]*170+[120])
        f=next(x for x in formation_candidates(b,D('.1'),as_of=b[-1].end) if x['family']=='F3')
        self.assertGreater(f['displacement']['tr_atr_previous'],D(2))
        self.assertFalse(f['quiet_then_expansion'])

    def test_fvg_prefix_is_identical_when_future_is_appended(self):
        b=bars_from([(99,100,98,99),(100,108,99,107),(106,109,105,108),
                     (104,104,98,99),(99,100,97,98)])
        prefix=gap_lifecycle(b[:3],D('.1'),as_of=b[2].end)
        self.assertEqual(prefix,gap_lifecycle(b,D('.1'),as_of=b[2].end))


if __name__=='__main__':unittest.main()
