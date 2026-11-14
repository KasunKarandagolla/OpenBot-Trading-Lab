"""Independent controlled oracles (SYNTHETIC) + retained authentic receipts.

No live network. Numeric expected answers and chronological counterexamples
are specified separately from the algorithms. No profitability/source claims.
"""
from dataclasses import replace, asdict
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest
from unittest.mock import patch

from researcher.contracts import ContractError, utc, encode, digest
from researcher.numerics import (Bar, true_ranges, wilder_atr, compression,
    anchored_value, confirmed_swings, lag_trained_beta)
from researcher.observations import iso_seconds, WIDTHS
from researcher.structures import Reference, swing_references, gap_lifecycle
from researcher.measurements import (tick_price,value_extension,flow_divergence,
    persistent_residual,sector_strength,oi_decomposition,funding_basis,catalyst)
from researcher.specialists import (Trade,TapeWindow,adapt_tape,true_profile,profile_nodes,
    first_profile_revisit,footprint,aggression_attempts,liquidations,trade_value,trade_delta,SpecialistEnvelope,adapt_specialist)
from researcher.family_engine import (boundary_family,continuation,compression_family,
    balance_references,value_reversion,profile_rotation,relative_family,shock_family,evaluate_families,closed_prefix)
from researcher.method_engine import (zone_lifecycle,order_blocks,ote,crt,amd,
    TimingDefinition,timed_subclass,auction,depth_walls,evaluate_methods,specialist_method,analyze_specialist_envelope)
from researcher.pack_contracts import (CORE_COLUMNS,OPTIONAL_COLUMNS,Expr,Column,
    compile_expr,compile_columns,evaluate_expr,evaluate_core,contracts,registered,make_remote_pack,
    scenario_budget,EARLY,early_oracle,quiet_near_oracle,CORRECTIONS,correction_oracle)
from researcher.engine_capabilities import analyze_selected,manifest,qualified_route_a
from researcher.settings import ROOT,load_config,validate_config

START=1793059200  # 2026-10-27 00:00 UTC; divisible by 1H/15M/4H.
TICK=D('.01')


def bars(rows,*,name='TESTUSDT',tf='1h',start=START):
    out=[];width=WIDTHS[tf]
    for i,row in enumerate(rows):
        o,h,l,c=map(D,map(str,row));end=iso_seconds(start+(i+1)*width)
        out.append(Bar(name,tf,(start+i*width)*1000,o,h,l,c,D(10),c*10,D(5),c*5,10,
            'SYNTHETIC_CONTROLLED_VECTOR',end,available_at=end))
    return out


def flat(n=40,price=100,span=1,**kw):
    return bars([(price,price+span,price-span,price)]*n,**kw)


def ref(source,*,lo=100,hi=100,side=1,kind='RANGE_TOP',known=0,atr=2):
    b=source[known]
    return Reference(b.native_symbol,b.timeframe,kind,D(str(lo)),D(str(hi)),D(str(atr)),TICK,side,
        b.end,b.end,b.end,(utc(b.end)+timedelta(days=7)).isoformat(),(b.id,),
        'SYNTHETIC_PREDECLARED_REFERENCE')


def mirror(source):
    return [replace(b,open=200-b.open,high=200-b.low,low=200-b.high,close=200-b.close,
        quote_volume=(200-b.close)*10,buy_quote=(200-b.close)*5) for b in source]


def tape(volumes=None,*,start=START,prices=None,aggressor='BUY',symbol='TESTUSDT',duration=60):
    volumes=volumes or [1,1,1]
    prices=prices or list(range(100,100+len(volumes)))
    trades=tuple(Trade('T'+str(i),iso_seconds(start+i),D(str(p)),D(str(v)),aggressor)
        for i,(p,v) in enumerate(zip(prices,volumes)))
    return TapeWindow(symbol,'BINANCE_USDM','LINEAR_USDT_PERPETUAL',iso_seconds(start),
        iso_seconds(start+duration),iso_seconds(start+duration),iso_seconds(start+duration),
        'SYNTHETIC_EXECUTED_TAPE','COMPLETE',D(1),trades,'SYNTHETIC')


class MeasurementOracles(unittest.TestCase):
    def test_previous_close_seed_units_and_tick_alignment(self):
        b=bars([(10,12,9,11),(20,21,19,20)]+[(20,21,19,20)]*13)
        self.assertEqual(true_ranges(b)[1],D(10))
        self.assertEqual(wilder_atr(b)[14],D(36)/14)
        self.assertEqual(tick_price(D('.000012349'),D('.00000001')),D('.00001234'))
        with self.assertRaises(ContractError):tick_price('NaN',TICK)

    def test_exact_qv_reset_and_close_residual_second_moment_distinction(self):
        b=bars([(100+i,101+i,99+i,100+i) for i in range(18)],tf='15m')
        b=[replace(x,quote_volume=D(1000)+(D(20)*i)) for i,x in enumerate(b)]
        v=anchored_value(b,anchor_ms=b[0].open_ms,anchor_known_at=iso_seconds(START))
        self.assertEqual(v['vwap_whole_bars'],D(117))
        x=value_extension(b,anchor_ms=b[0].open_ms,anchor_known_at=iso_seconds(START),atr_ref=2)
        self.assertIsNone(x['trade_weighted_variance'])
        self.assertEqual(x['distance_atr'],D(0))
        future=[*b,replace(b[-1],open_ms=b[-1].end_ms,received_at=iso_seconds(START+19*900),available_at=iso_seconds(START+19*900))]
        self.assertEqual(x,value_extension(future[:-1],anchor_ms=b[0].open_ms,anchor_known_at=iso_seconds(START),atr_ref=2))
        with self.assertRaises(ContractError):anchored_value(b,anchor_ms=b[0].open_ms,anchor_known_at=b[0].end)

    def test_confirmed_same_anchor_cvd_divergence_and_negative(self):
        prices=[101,100,99,95,99,100,99,98,94,99,100]
        b=bars([(p,p+1,p-1,p) for p in prices])
        b=[replace(x,buy_quote=D(0) if i<5 else x.quote_volume) for i,x in enumerate(b)]
        args={'anchor_ms':b[0].open_ms,'anchor_known_at':iso_seconds(START)}
        r=flow_divergence(b,**args)
        self.assertEqual(len(r),1);self.assertEqual(r[0]['direction'],1)
        self.assertEqual(r[0]['known_at'],b[10].end)
        self.assertEqual(flow_divergence(b[:10],**args),[])
        self.assertEqual(flow_divergence([replace(x,buy_quote=D(0)) for x in b],**args),[])

    def test_lag_beta_oos_and_persistent_two_sided_residual(self):
        bp=[D(100)];ap=[D(50)]
        rs=[D('.01'),D('-.02'),D('.03'),D('-.01')]*10
        for i,r in enumerate(rs):
            bp.append(bp[-1]*r.exp());ap.append(ap[-1]*(2*r+(D('.004') if i>=36 else D(0))).exp())
        b=bars([(p,p,p,p) for p in bp],name='BTCUSDT');a=bars([(p,p,p,p) for p in ap])
        x=lag_trained_beta(a[:38],b[:38],n=32)
        self.assertLess(abs(x['beta']-2),D('1e-20'))
        self.assertEqual(x['training_end'],a[36].end)
        self.assertGreater(x['residual'],0)
        self.assertEqual(persistent_residual(a,b)['direction'],1)
        self.assertEqual(persistent_residual(a,flat(len(a),name='BTCUSDT'))['direction'],0)
        with self.assertRaises(ContractError):persistent_residual(a,[replace(x,timeframe='15m') for x in b])

    def test_sector_dated_memberships_and_minimum(self):
        at=iso_seconds(START+100)
        names=['TESTUSDT']+[f'P{i}USDT' for i in range(5)]
        rows=[{'native_symbol':n,'venue':'BINANCE_USDM','contract_type':'PERPETUAL','quote':'USDT',
            'sector':'S','known_at':iso_seconds(START),'valid_from':iso_seconds(START),
            'valid_until':iso_seconds(START+1000)} for n in names]
        residuals={n:D(i) for i,n in enumerate(names)}
        self.assertEqual(sector_strength('TESTUSDT',residuals,rows,at=at)[0]['residual_from_peer_median'],D(-3))
        self.assertEqual(sector_strength('TESTUSDT',residuals,rows[:-1],at=at)[0]['status'],'SOURCE_UNKNOWN')
        self.assertEqual(sector_strength('TESTUSDT',residuals,[],at=at)[0]['status'],'SOURCE_CAPABILITY_REQUIRED')

    def test_oi_mark_contribution_no_side_and_units_rejection(self):
        a={'venue':'BINANCE_USDM','native_symbol':'1000PEPEUSDT','contract_type':'LINEAR_USDT_PERPETUAL',
            'native_units':'CONTRACTS','at':iso_seconds(START),'mark_at':iso_seconds(START),'native':100,'mark':2}
        b={**a,'at':iso_seconds(START+60),'mark_at':iso_seconds(START+60),'native':110,'mark':3}
        r=oi_decomposition(a,b,multiplier=1000)
        self.assertEqual((r['delta_native'],r['delta_base'],r['delta_usdt']),(D(10),D(10000),D(130000)))
        self.assertLess(abs(r['log_usdt_change']-r['log_base_contribution']-r['log_mark_contribution']),D('1e-25'))
        self.assertIsNone(r['opening_side'])
        with self.assertRaises(ContractError):oi_decomposition(a,{**b,'mark_at':a['at']},multiplier=1000)
        base_a={**a,'native_units':'BASE_ASSET'};base_b={**b,'native_units':'BASE_ASSET'}
        self.assertEqual(oi_decomposition(base_a,base_b)['delta_base'],D(10))
        self.assertEqual(oi_decomposition(base_a,base_b)['delta_usdt'],D(130))
        with self.assertRaises(ContractError):oi_decomposition(base_a,base_b,multiplier=1000)
        notional_a={**a,'native_units':'USDT_NOTIONAL','native':200}
        notional_b={**b,'native_units':'USDT_NOTIONAL','native':330}
        self.assertEqual(oi_decomposition(notional_a,notional_b)['delta_base'],D(10))

    def test_funding_prediction_settlement_and_interval(self):
        r={'rate_kind':'NEXT_PREDICTED','units':'PERCENT','interval_seconds':14400,'mark_at':iso_seconds(START),
            'index_at':iso_seconds(START),'settlement_at':iso_seconds(START+14400),'mark':101,'index':100,'rate':'.1'}
        x=funding_basis(r);self.assertEqual(x['rate_fraction'],D('.001'));self.assertIsNone(x['settled_carry'])
        self.assertEqual(funding_basis({**r,'rate_kind':'SETTLED'})['settled_carry'],D('.001'))
        with self.assertRaises(ContractError):funding_basis({**r,'interval_seconds':None})

    def test_catalyst_exact_identity_and_first_known(self):
        t=iso_seconds(START)
        r={'source_url':'https://publisher.example/controlled-test','publisher':'SYNTHETIC_PUBLISHER',
            'response_hash':'SYNTHETIC','kind':'ANNOUNCEMENT','published_at':t,'first_known_at':t,'received_at':t,
            'contracts':[{'native_symbol':'我踏马来了USDT','venue':'BINANCE_USDM','contract_type':'PERPETUAL',
                'quote':'USDT','mapping_known_at':t}]}
        self.assertEqual(catalyst(r,native_symbol='我踏马来了USDT',at=t)['status'],'SUPPORTED')
        self.assertEqual(catalyst(r,native_symbol='PEPEUSDT',at=t)['status'],'SOURCE_UNKNOWN')
        with self.assertRaises(ContractError):catalyst({**r,'first_known_at':iso_seconds(START-1)},native_symbol='TESTUSDT',at=t)


class ExecutedSpecialistOracles(unittest.TestCase):
    def test_profile_and_tape_ids_freeze_content_not_retrieval_time(self):
        t=tape([4,4,2]);p=true_profile(t,width=D(1))
        later=replace(t,received_at=iso_seconds(START+120),available_at=iso_seconds(START+90),source_hash='RETRIEVED_LATER_SAME_TRADES')
        self.assertEqual(t.id,later.id);self.assertEqual(p['id'],true_profile(later,width=D(1))['id'])
        changed=replace(t,trades=(replace(t.trades[0],base=D(5)),*t.trades[1:]))
        self.assertNotEqual(t.id,changed.id);self.assertNotEqual(p['id'],true_profile(changed,width=D(1))['id'])

    def test_strict_specialist_envelope_scope_and_time_before_reduction(self):
        t=tape([4,4,2])
        e=SpecialistEnvelope('TESTUSDT','BINANCE_USDM','LINEAR_USDT_PERPETUAL','EXECUTED_BASE',
            t.start,t.end,t.end,t.end,t.end,'SYNTHETIC','COMPLETE','SYNTHETIC',{'tape':t,'width':D(1)})
        self.assertEqual(analyze_specialist_envelope('M17',e,as_of=t.end)['value']['total_volume'],D(10))
        with self.assertRaises(ContractError):analyze_specialist_envelope('M17',replace(e,native_symbol='OTHERUSDT'),as_of=t.end)
        with self.assertRaises(ContractError):adapt_specialist({'source':'UNKNOWN'})
        self.assertEqual(analyze_specialist_envelope('M17',replace(e,coverage='PARTIAL'),as_of=t.end)['status'],'SOURCE_CAPABILITY_REQUIRED')

    def test_executed_weighted_second_moment_and_strict_string_adapter(self):
        t=tape([1,3],prices=[100,104]);x=trade_value(t)
        self.assertEqual(x['vwap_executed'],D(103));self.assertEqual(x['trade_weighted_variance'],D(3))
        raw=json.loads(encode(asdict(t)))
        self.assertEqual(trade_value(adapt_tape(raw))['vwap_executed'],D(103))
        with self.assertRaises(ContractError):trade_value(replace(t,coverage='PARTIAL'))

    def test_true_profile_poc_va_ties_and_partial_rejection(self):
        t=tape([4,4,2]);p=true_profile(t,width=D(1))
        self.assertEqual((p['poc_bin'],p['val'],p['vah'],p['value_volume']),(100,D(100),D(102),D(8)))
        p2=true_profile(tape([2,6,2]),width=D(1));self.assertEqual((p2['val'],p2['vah']),(D(100),D(102)))
        with self.assertRaises(ContractError):true_profile(replace(t,coverage='SAMPLED'),width=D(1))
        with self.assertRaises(ContractError):adapt_tape({'open':100,'high':102,'volume':10})
        with self.assertRaises(ContractError):true_profile(t,width=D('.5'))

    def test_versioned_nodes_and_naked_poc_first_revisit(self):
        p=true_profile(tape([1,2,9,4,1,1,2,9,3,1]),width=D(1))
        nodes=profile_nodes(p)
        self.assertEqual([n['bin'] for n in nodes if n['kind']=='HVN'],[102,107])
        self.assertEqual([n['bin'] for n in nodes if n['kind']=='LVN'],[105])
        later=tape([1,1],prices=[110,102],start=START+60)
        self.assertEqual(first_profile_revisit(p,later)['status'],'FIRST_REVISIT')
        self.assertEqual(first_profile_revisit(p,tape([1,1],prices=[110,111],start=START+60))['status'],'NAKED_THROUGH_COMPLETE_WINDOW')
        with self.assertRaises(ContractError):first_profile_revisit(p,replace(later,start=iso_seconds(START+61)))

    def test_footprint_diagonal_stacks_zero_denominator_and_minimum(self):
        r=footprint(tape([4,4,4,4]),width=D(1),minimum=D(3))
        self.assertEqual(r['rows'][0]['stacks'],[(101,102,103)])
        self.assertEqual(footprint(tape([1,1,1,1]),width=D(1),minimum=D(3))['rows'][0]['stacks'],[])
        with self.assertRaises(ContractError):footprint(replace(tape(),coverage='PARTIAL'),width=D(1))

    def test_absorption_requires_actual_aggression_limited_progress_later_response(self):
        aa=[tape([5,5],prices=[100,101]),tape([5,5],prices=[100,101],start=START+60)]
        response=tape([1,1],prices=[100,99],start=START+120)
        r=aggression_attempts(aa,response,direction=1,lo=99,hi=102,max_progress=1,minimum_aggression=8)
        self.assertTrue(r['absorption_candidate']);self.assertFalse(r['exhaustion_candidate'])
        self.assertFalse(aggression_attempts(aa,tape([1,1],prices=[102,103],start=START+120),
            direction=1,lo=99,hi=102,max_progress=1,minimum_aggression=8)['absorption_candidate'])

    def test_exhaustion_requires_declining_flow_and_progress(self):
        aa=[tape([10,10],prices=[100,103]),tape([5,5],prices=[100,102],start=START+60),
            tape([2,2],prices=[100,101],start=START+120)]
        response=tape([1,1],prices=[100,99],start=START+180)
        args={'direction':1,'lo':99,'hi':104,'max_progress':1,'minimum_aggression':2}
        self.assertTrue(aggression_attempts(aa,response,**args)['exhaustion_candidate'])
        aa[1]=tape([5,5],prices=[100,104],start=START+60)
        self.assertFalse(aggression_attempts(aa,response,**args)['exhaustion_candidate'])

    def test_sampled_liquidations_never_modeled_totals(self):
        args={'native_symbol':'TESTUSDT','venue':'BINANCE_USDM','start':iso_seconds(START),
            'end':iso_seconds(START+60),'coverage':'SAMPLED','source_hash':'SYNTHETIC'}
        row={'id':'F1','native_symbol':'TESTUSDT','venue':'BINANCE_USDM','at':iso_seconds(START+1),
            'kind':'OBSERVED_FORCED_EXECUTION','price':100,'base':2}
        r=liquidations([row],**args);self.assertEqual(r['observed_notional_usdt'],D(200));self.assertIsNone(r['market_total_estimate'])
        self.assertIsNone(liquidations([],**{**args,'coverage':'MODELED'})['observed_notional_usdt'])
        with self.assertRaises(ContractError):liquidations([row,{**row}],**args)

    def test_depth_displayed_scope_and_crossed_negative(self):
        s={'venue':'BINANCE_USDM','units':'PRICE_USDT_PER_BASE; QUANTITY_NATIVE_BASE',
            'received':iso_seconds(START),'time':iso_seconds(START),
            'levels':{'bids':[(D(99),D(10))],'asks':[(D(101),D(5))]}}
        r=depth_walls(s,bps=D(200));self.assertEqual(r['displayed_usdt'],{'bids':D(990),'asks':D(505)})
        self.assertIsNone(r['spoofing']);self.assertIsNone(r['iceberg'])
        with self.assertRaises(ContractError):depth_walls({**s,'levels':{'bids':[(D(101),D(1))],'asks':[(D(100),D(1))]}})


class FamilyChronologyOracles(unittest.TestCase):
    def test_f6_true_profile_branch_requires_complete_exact_venue_and_later_rotation(self):
        b=flat(21)+bars([(101,102,100,101),(100,102,98,101),(101,105,100,104)],start=START+21*3600)
        p=true_profile(tape([4,4,2],start=START+20*3600,duration=3600),width=D(1))
        branches=profile_rotation(p,b,TICK,as_of=b[-1].end)
        self.assertTrue(all(h['details']['true_profile'] for h in branches))
        self.assertTrue(any(e['kind']=='ROTATION' for h in branches for e in h['timeline']))
        with self.assertRaises(ContractError):profile_rotation({**p,'venue':'SPOT'},b,TICK,as_of=b[-1].end)
        with self.assertRaises(ContractError):profile_rotation({**p,'coverage':'SAMPLED'},b,TICK,as_of=b[-1].end)

    def test_f7_causal_event_anchor_whole_bar_window_and_post_hoc_rejection(self):
        prices=[100,103,105,103,100,97,95,97]*4+[100]*12+[110,109,107,104]
        b=bars([(p,p+.5,p-.5,p) for p in prices],tf='15m',start=START+3600)
        balance=balance_references(b,TICK,baseline_end=32)
        x=value_reversion(b,TICK,balance,anchor_ms=b[0].open_ms,anchor_known_at=iso_seconds(START+3600))
        self.assertEqual(x['reference']['kind'],'EVENT_VWAP_ANCHOR')
        self.assertTrue(any(e['kind']=='FAILED_FURTHER_PROGRESS_RETURN' for e in x['timeline']))
        with self.assertRaises(ContractError):value_reversion(b,TICK,balance,
            anchor_ms=b[0].open_ms,anchor_known_at=b[0].end)

    def test_f9_only_witnessed_scoped_liquidations_can_add_observed_subclass(self):
        b=flat(40)+bars([(100,112,99,111),(110,111,105,108),(108,110,106,109)],start=START+40*3600)
        start=iso_seconds(START+40*3600);end=b[40].end
        row={'id':'SYNTHETIC_FORCE','native_symbol':'TESTUSDT','venue':'BINANCE_USDM',
            'kind':'OBSERVED_FORCED_EXECUTION','at':iso_seconds(START+40*3600+5),'price':110,'base':2}
        args={'native_symbol':'TESTUSDT','venue':'BINANCE_USDM','start':start,'end':end,'coverage':'SAMPLED','source_hash':'SYNTHETIC'}
        observed=liquidations([row],**args)
        x=shock_family(b,TICK,liquidation=observed)
        self.assertEqual(x['details']['classification'],'POST_SHOCK_WITH_OBSERVED_LIQUIDATIONS')
        self.assertEqual(x['details']['observed_liquidation_coverage'],'SAMPLED')
        modeled=liquidations([],**{**args,'coverage':'MODELED'})
        self.assertEqual(shock_family(b,TICK,liquidation=modeled)['details']['classification'],'POST_SHOCK')
        with self.assertRaises(ContractError):shock_family(b,TICK,liquidation={**observed,'native_symbol':'OTHERUSDT'})

    def boundary(self,which):
        prefix=[(96,97,95,96),(99,100,99,99.8),(97,98,96,97),(99,100,99,99.8)]
        if which=='F2':tail=[(100,102,100,101),(101,103,101,102),(102,104,102,103)]
        elif which=='F4':tail=[(100,102,99,101),(99,99.5,98,99),(99,99,95,95.5)]
        else:tail=[(100,102,99,101),(99,99.5,98,99),(99,99,95,95.5),
                   (100,102,100,101),(101,103,101,102),(102,104,102,103)]
        return bars(prefix+tail)

    def test_f2_early_before_break_later_acceptance_and_no_f5_without_reclaim(self):
        b=self.boundary('F2');r=ref(b)
        early=boundary_family('F2',r,b[:4],as_of=b[-1].end)
        self.assertEqual(early['stage'],'APPROACHING_DECISION')
        self.assertFalse(early['details']['acceptance_verified'])
        done=boundary_family('F2',r,b,as_of=b[-1].end)
        self.assertTrue(done['details']['acceptance_verified'])
        self.assertEqual(done['timeline'][-1]['known_at'],b[-1].end)
        f5=boundary_family('F5',r,b,as_of=b[-1].end)
        self.assertFalse(f5['details']['acceptance_verified'])
        self.assertFalse(any(e['kind']=='REVERSAL_FAILED_REBREAK_SAME_REFERENCE' for e in f5['timeline']))
        short=boundary_family('F2',ref(mirror(b),side=-1),mirror(b),as_of=b[-1].end)
        self.assertTrue(short['details']['acceptance_verified']);self.assertEqual(short['direction'],-1)

    def test_f4_reclaim_then_later_opposing_initiative_and_acceptance_rival(self):
        b=self.boundary('F4');r=ref(b)
        x=boundary_family('F4',r,b,as_of=b[-1].end)
        self.assertTrue(x['details']['opposing_initiative_verified'])
        kinds=[e['kind'] for e in x['timeline']]
        self.assertLess(kinds.index('RECLAIM'),kinds.index('OPPOSING_INITIATIVE'))
        self.assertFalse(boundary_family('F4',r,b[:-1],as_of=b[-1].end)['details']['opposing_initiative_verified'])
        f2=self.boundary('F2')
        self.assertEqual(boundary_family('F4',ref(f2),f2,as_of=f2[-1].end)['stage'],'INVALIDATED')
        short=boundary_family('F4',ref(mirror(b),side=-1),mirror(b),as_of=b[-1].end)
        self.assertTrue(short['details']['opposing_initiative_verified']);self.assertEqual(short['direction'],1)

    def test_f5_same_reference_attempt_rebreak_hold_and_missing_reclaim_negative(self):
        b=self.boundary('F5');r=ref(b)
        x=boundary_family('F5',r,b,as_of=b[-1].end)
        self.assertTrue(x['details']['acceptance_verified'])
        kinds=[e['kind'] for e in x['timeline']]
        required=['RECLAIM','OPPOSING_REVERSAL_ATTEMPT','REVERSAL_FAILED_REBREAK_SAME_REFERENCE','LATER_OUTSIDE_ACCEPTANCE']
        self.assertEqual([k for k in kinds if k in required],required)
        self.assertTrue(all(e['reference_id']==r.id for e in x['timeline']))
        bad=self.boundary('F2')
        self.assertFalse(boundary_family('F5',ref(bad),bad,as_of=bad[-1].end)['details']['acceptance_verified'])
        self.assertTrue(boundary_family('F5',ref(mirror(b),side=-1),mirror(b),as_of=b[-1].end)['details']['acceptance_verified'])

    def continuation_sample(self):
        prices=[100]*20+[99,95,98,101,103,104,105,104,103,102,101,100,102,104,106,108,110,108,107,105,104,105]
        return bars([(p,p+D('.5'),p-D('.5'),p) for p in map(D,prices)])

    def test_f1_ladder_controlled_pullback_defended_response_and_failure(self):
        b=self.continuation_sample();x=continuation(b,TICK)
        self.assertEqual(x['stage'],'DEVELOPING');self.assertEqual(x['direction'],1)
        self.assertEqual(x['details']['ladder'],'HH_HL')
        self.assertEqual(x['timeline'][0]['kind'],'CONTROLLED_COUNTERLEG')
        fail=bars([(105,106,94,95)],start=b[-1].end_ms//1000)
        self.assertEqual(continuation([*b,*fail],TICK)['stage'],'INVALIDATED')
        self.assertEqual(continuation(flat(50),TICK)['stage'],'UNKNOWN')
        self.assertEqual(continuation(mirror(b),TICK)['direction'],-1)

    def test_f3_past_only_quiet_at_reference_before_displacement_and_retention(self):
        old=[(100,105,95,100)]*159
        quiet=[(100,100.2,99.8,100)]*20
        b=bars(old+quiet+[(100,105,100,104.8),(104,105,103,104)])
        r=ref(b,known=158,atr=2)
        early=compression_family(b[:-2],TICK,(r,))
        self.assertEqual(early['stage'],'EARLY')
        done=compression_family(b,TICK,(r,))
        self.assertEqual(done['timeline'][-1]['kind'],'RETAINED_PROGRESS')
        self.assertEqual(compression_family(b,TICK,())['stage'],'UNKNOWN')
        news=bars(old+[(100,120,99,100)])
        self.assertEqual(compression_family(news,TICK,(r,))['stage'],'UNKNOWN')

    def balance_sample(self):
        prices=[100,103,105,103,100,97,95,97]*4
        return bars([(p,p+.5,p-.5,p) for p in prices]+[(97,98,96,97),(95,95.5,94.8,95.2),
            (96,99,95.5,98),(98,101,97,100)])

    def test_f6_separated_balance_edges_rejection_rotation_vs_acceptance(self):
        b=self.balance_sample();refs=balance_references(b,TICK)
        self.assertEqual(len(refs),2)
        lower=refs[0];x=boundary_family('F6',lower,b,as_of=b[-1].end,balance=True)
        self.assertEqual(x['stage'],'DEVELOPING')
        self.assertTrue(any(e['kind']=='ROTATION' for e in x['timeline']))
        outside=bars([(94,94.2,92,93)]*3,start=b[-1].end_ms//1000)
        self.assertEqual(boundary_family('F6',lower,[*b,*outside],as_of=outside[-1].end,balance=True)['stage'],'INVALIDATED')
        self.assertEqual(balance_references(flat(40),TICK),())
        self.assertFalse(boundary_family('F6',lower,b,as_of=b[-1].end,balance=False)['details']['balance_established'])

    def test_f7_session_mean_extension_then_return_and_missing_regime(self):
        # 15M: first 32 bars establish prior balance; later session extension.
        b=self.balance_sample()
        prices=[100,103,105,103,100,97,95,97]*4+[100]*12+[110,109,107,104]
        source=bars([(p,p+.5,p-.5,p) for p in prices],tf='15m')
        refs=balance_references(source,TICK,baseline_end=32)
        x=value_reversion(source,TICK,refs)
        self.assertEqual(x['direction'],-1)
        self.assertEqual(x['timeline'][0]['kind'],'CONDITIONAL_VALUE_EXTENSION')
        self.assertTrue(any(e['kind']=='FAILED_FURTHER_PROGRESS_RETURN' for e in x['timeline']))
        self.assertEqual(value_reversion(source,TICK,())['stage'],'UNKNOWN')
        self.assertIsNone(x['details']['trade_weighted_variance'])

    def test_f8_residual_requires_local_decision_not_rank(self):
        b=flat(41,name='BTCUSDT');b=[replace(x,close=D(100)+(i%4),high=D(104),low=D(99)) for i,x in enumerate(b)]
        a=flat(41);a=[replace(x,close=D(100)+(i%4)+max(0,i-35),high=D(110),low=D(99)) for i,x in enumerate(a)]
        r=ref(a,lo=104,hi=104,known=33)
        x=relative_family(a,b,(r,))
        self.assertEqual(x['direction'],1);self.assertEqual(x['stage'],'DEVELOPING')
        self.assertEqual(relative_family(a,b,())['stage'],'UNKNOWN')
        self.assertEqual(relative_family(a,None,(r,))['status'],'SOURCE_CAPABILITY_REQUIRED')

    def test_f9_historical_shock_stabilization_second_leg_without_fake_liquidations(self):
        b=flat(40)+bars([(100,112,99,111),(110,111,105,108),(108,110,106,109)],start=START+40*3600)
        x=shock_family(b,TICK)
        self.assertEqual(x['details']['classification'],'POST_SHOCK')
        self.assertFalse(x['details']['confirmed_liquidation'])
        self.assertTrue(any(e['kind']=='STABILIZATION_CANDIDATE' for e in x['timeline']))
        extra=bars([(111,115,110,114)],start=b[-1].end_ms//1000)
        y=shock_family([*b,*extra],TICK)
        self.assertEqual(y['timeline'][-1]['kind'],'RENEWED_EXTREME_SECOND_LEG')
        self.assertEqual(shock_family(flat(50),TICK)['status'],'NO_EVENT_IN_COMPLETE_WINDOW')
        self.assertEqual(shock_family(mirror(b),TICK)['direction'],-1)

    def test_noisy_touches_do_not_manufacture_pressure_and_expiry(self):
        b=bars([(99,100,99,99.8)]*8)
        r=ref(b)
        self.assertEqual(boundary_family('F2',r,b,as_of=b[-1].end)['details']['touch_episodes'],1)
        expired=replace(r,valid_until=b[4].end)
        self.assertEqual(boundary_family('F2',expired,b,as_of=b[-1].end)['stage'],'INVALIDATED')
        with self.assertRaises(ContractError):boundary_family('F2',r,[replace(x,native_symbol='OTHERUSDT') for x in b],as_of=b[-1].end)

    def test_append_future_cutoff_prefix_invariance_all_families(self):
        b=self.continuation_sample();cutoff=b[-1].end;at=cutoff
        refs=swing_references(b,TICK,as_of=at)
        before=evaluate_families(b,TICK,cutoff=cutoff,as_of=at,references=refs)
        future=bars([(105,130,80,100)]*5,start=b[-1].end_ms//1000)
        after=evaluate_families([*b,*future],TICK,cutoff=cutoff,as_of=at,references=refs)
        self.assertEqual(before,after)
        self.assertEqual({x['family'] for x in before},{'F'+str(i) for i in range(1,10)})

    def test_missing_bar_publication_delay_and_tf_mismatch_reject(self):
        b=flat(40)
        with self.assertRaises(ContractError):closed_prefix(b[:5]+b[6:],cutoff=b[-1].end,as_of=b[-1].end)
        delayed=[*b[:-1],replace(b[-1],available_at=iso_seconds(START+41*3600),received_at=iso_seconds(START+41*3600))]
        with self.assertRaises(ContractError):closed_prefix(delayed,cutoff=b[-1].end,as_of=b[-1].end)
        for tf in ('15m','4h'):
            with self.assertRaises(ContractError):closed_prefix([replace(x,timeframe=tf) for x in b],cutoff=b[-1].end,as_of=b[-1].end)


class NamedMethodOracles(unittest.TestCase):
    def test_m21_true_trade_delta_and_cvd_keep_bar_and_tape_scopes_separate(self):
        t=tape([1,2,1],prices=[100,101,102])
        t=replace(t,trades=(t.trades[0],replace(t.trades[1],aggressor='SELL'),t.trades[2]))
        r=trade_delta(t)
        self.assertEqual(r['delta_base'],D(0));self.assertEqual(r['delta_quote'],D(0))
        self.assertEqual([x['cvd_base'] for x in r['path']],[D(1),D(-1),D(0)])
        self.assertEqual(specialist_method('M21',tape=t)['value']['scope'],'EXACT_EXECUTED_TAPE_NOT_BAR_DELTA')
        with self.assertRaises(ContractError):trade_delta(replace(t,coverage='PARTIAL'))

    def test_m02_mss_needs_prior_sweep_opposing_context_and_displacement(self):
        b=FamilyChronologyOracles().continuation_sample()
        tail=bars([(110,113,108,109),(109,110,106,107),(107,108,94,95)],start=b[-1].end_ms//1000)
        source=[*b,*tail];refs=swing_references(source,TICK,as_of=source[-1].end)
        m=evaluate_methods(source,TICK,cutoff=source[-1].end,as_of=source[-1].end,references=refs)[1]['value']
        self.assertTrue(any(e['kind']=='CHOCH_CANDIDATE' for e in m['breaks']))
        self.assertTrue(m['mss'])
        no_break=[*source[:-1],replace(source[-1],close=D(107),open=D(107))]
        negative=evaluate_methods(no_break,TICK,cutoff=no_break[-1].end,as_of=no_break[-1].end,references=refs)[1]['value']
        self.assertEqual(negative['mss'],[])

    def test_m01_m02_m03_m04_ladder_breaks_levels_equal_clusters(self):
        b=FamilyChronologyOracles().continuation_sample()
        refs=swing_references(b,TICK,as_of=b[-1].end)
        x=evaluate_methods(b,TICK,cutoff=b[-1].end,as_of=b[-1].end,references=refs)
        methods={r['method_id']:r for r in x}
        self.assertEqual(methods['M01']['value']['ladder'],'HH_HL')
        self.assertTrue(methods['M03']['value']['horizontal'])
        self.assertTrue(all(r['status'] in {'COMPUTED','SOURCE_CAPABILITY_REQUIRED','DEFINITION_PENDING'} for r in x))
        y=evaluate_methods(flat(45),TICK,cutoff=iso_seconds(START+45*3600),as_of=iso_seconds(START+45*3600))
        self.assertEqual(y[0]['value']['swings'],[])
        # Actual confirmed equal highs separated by a deep retreat, not a plateau.
        eq=flat(20)+bars([(100,103,99,102),(100,101,99,100),(100,101,98,100),
            (100,101,99,100),(100,103,99,102),(100,101,99,100),(100,101,99,100)],start=START+20*3600)
        r=evaluate_methods(eq,TICK,cutoff=eq[-1].end,as_of=eq[-1].end)[3]['value']
        self.assertTrue(any(x.origin.startswith('EQH_EQL') for x in r))
        self.assertEqual(evaluate_methods(eq[:-1],TICK,cutoff=eq[-2].end,as_of=eq[-2].end)[3]['value'],[])

    def test_m06_ob_requires_base_displacement_then_later_bos_birth(self):
        b=FamilyChronologyOracles().continuation_sample()
        tail=bars([(106,106,104,105),(105,110,104.5,109.5),(110,115,109,114)],start=b[-1].end_ms//1000)
        source=[*b,*tail];obs=order_blocks(source,TICK,as_of=source[-1].end)
        self.assertTrue(obs)
        latest=next(o for o in obs if o['born_at']==source[-1].end)
        self.assertEqual((latest['reference'].lo,latest['reference'].hi),(D(104),D(106)))
        self.assertLess(utc(latest['displacement_at']),utc(latest['born_at']))
        self.assertFalse(any(o['reference'].origin==latest['reference'].origin for o in order_blocks(source[:-1],TICK,as_of=source[-2].end)))
        self.assertIsNone(latest['institutional_order'])

    def test_m07_m10_same_zone_breach_then_later_retest_and_mitigation(self):
        b=bars([(103,104,103,103),(103,103,101,102),(99,100,98,99),
                (99,100,98,99),(99,101,98,99),(104,105,103,104)])
        r=ref(b,lo=100,hi=102,side=1,kind='ORDER_BLOCK_CANDIDATE')
        x=zone_lifecycle(r,b,as_of=b[-1].end)
        self.assertTrue(x['accepted_breach']);self.assertTrue(x['breaker_candidate'])
        self.assertEqual(x['reference_id'],r.id)
        kinds=[e['kind'] for e in x['events']]
        self.assertLess(kinds.index('ZONE_ACCEPTED_THROUGH'),kinds.index('BREAKER_OPPOSITE_SIDE_RETEST'))
        self.assertEqual(kinds[-1],'BREAKER_INVALIDATED')
        self.assertFalse(zone_lifecycle(r,b[:3],as_of=b[-1].end)['breaker_candidate'])
        self.assertEqual(x['mitigation_fraction_bar_overlap'],D('.5'))

    def test_m08_m09_gap_birth_mitigation_and_inverse_no_fake_color_flip(self):
        b=bars([(100,101,99,100),(102,104,101,103),(105,106,104,105),
            (100,100.5,99,100),(100,100.5,99,100),(100,102,99,100)])
        g=next(x for x in gap_lifecycle(b,TICK,as_of=b[-1].end) if x['reference'].known_at==b[2].end)
        self.assertEqual((g['reference'].lo,g['reference'].hi),(D(101),D(104)))
        self.assertEqual(g['status'],'IFVG_CANDIDATE')
        self.assertFalse(any(e['kind']=='IFVG_OPPOSITE_SIDE_RETEST' for e in gap_lifecycle(b[:4],TICK,as_of=b[-1].end)[0]['events']))
        overlap=bars([(100,103,99,100),(101,104,100,102),(102,105,102,104)])
        self.assertEqual(gap_lifecycle(overlap,TICK,as_of=overlap[-1].end),[])

    def test_m11_contextual_ote_is_not_a_standalone_fibonacci_signal(self):
        b=flat();r=ref(b,lo=95,hi=97,known=15)
        a={'kind':'SWING_LOW','index':3,'known_at':b[5].end,'price':D(90),'id':'SYNTHETIC_A'}
        z={'kind':'SWING_HIGH','index':10,'known_at':b[12].end,'price':D(110),'id':'SYNTHETIC_B'}
        args={'start':a,'end':z,'known_at':b[12].end,'at':b[-1].end,'zones':(r,)}
        self.assertTrue(ote(price=96,**args)['contextual_candidate'])
        self.assertFalse(ote(price=100,**args)['contextual_candidate'])
        self.assertFalse(ote(price=96,**{**args,'zones':()})['contextual_candidate'])
        with self.assertRaises(ContractError):ote(price=96,**{**args,'known_at':b[10].end})

    def test_m12_preselected_crt_and_m13_predeclared_session_amd(self):
        b=FamilyChronologyOracles().boundary('F4');r=ref(b,kind='CRT_CANDLE')
        self.assertTrue(crt(r,b,as_of=b[-1].end)['details']['opposing_initiative_verified'])
        with self.assertRaises(ContractError):crt(ref(b),b,as_of=b[-1].end)
        source=FamilyChronologyOracles().balance_sample()
        args={'session_start':iso_seconds(START),'balance_end':source[31].end,'as_of':source[-1].end}
        x=amd(source,TICK,**args)
        self.assertEqual(x['status'],'COMPUTED');self.assertIsNone(x['institutional_manipulation'])
        self.assertEqual(len(x['branches']),2)
        with self.assertRaises(ContractError):amd(source[1:],TICK,**args)

    def test_m14_timing_dst_only_does_not_qualify_silver_bullet_m15_pending(self):
        d=TimingDefinition('https://primary.example/SYNTHETIC_TEST','TEST_ONLY_WINDOW_NOT_CANONICAL',
            'America/New_York',10,11)
        summer=timed_subclass('2026-07-01T14:30:00+00:00',d)
        winter=timed_subclass('2026-12-01T15:30:00+00:00',d)
        self.assertTrue(summer['inside_declared_window']);self.assertTrue(winter['inside_declared_window'])
        self.assertNotEqual(summer['utc_offset_seconds'],winter['utc_offset_seconds'])
        self.assertFalse(summer['method_enabled'])
        b=flat();m={x['method_id']:x for x in evaluate_methods(b,TICK,cutoff=b[-1].end,as_of=b[-1].end)}
        self.assertEqual(m['M14']['status'],'DEFINITION_PENDING');self.assertEqual(m['M15']['status'],'DEFINITION_PENDING')
        self.assertFalse(m['M15']['implemented_code'])

    def test_m16_price_auction_vs_true_value_migration(self):
        b=FamilyChronologyOracles().balance_sample();refs=balance_references(b,TICK)
        x=auction(refs,b,as_of=b[-1].end)
        self.assertEqual(x['profile_fidelity'],'PRICE_ONLY_AUCTION')
        self.assertIsNone(x['true_value_migration'])
        p=true_profile(tape([4,4,2]),width=D(1))
        q=true_profile(tape([1,2,9],start=START+60),width=D(1))
        self.assertEqual(auction(refs,b,as_of=b[-1].end,profiles=(p,q))['true_value_migration'],D(2))
        with self.assertRaises(ContractError):auction(refs,b,as_of=b[-1].end,profiles=(p,{**q,'venue':'OTHER'}))

    def test_m17_through_m31_source_adapters_present_no_fake_support(self):
        specs=manifest(load_config());self.assertEqual(len(specs['methods']),31)
        for m in specs['methods']:
            self.assertFalse(m['production_enabled']);self.assertFalse(m['whole_universe_coverage'])
            self.assertFalse(m['empirically_useful']);self.assertFalse(m['source_supported'])
        for mid in ('M17','M18','M22','M23','M24','M25','M26','M27','M28','M31'):
            self.assertEqual(specialist_method(mid)['status'],'SOURCE_CAPABILITY_REQUIRED')
        positive=specialist_method('M17',tape=tape([4,4,2]),width=D(1))
        self.assertEqual(positive['status'],'COMPUTED');self.assertFalse(positive['source_supported'])


class RemotePackAndRuntimeOracles(unittest.TestCase):
    def test_two_finite_core_contracts_optional_isolated_and_shared_dag(self):
        c=contracts()
        self.assertEqual(c['CORE_1H']['timeframe'],'1h');self.assertEqual(c['CORE_15M']['timeframe'],'15m')
        self.assertNotIn('quote_rvol32',[x['id'] for x in c['CORE_1H']['columns']])
        self.assertEqual(c['CORE_1H']['dependency_order'][:3],['close','tr','atr14'])
        for k in ('METHOD_AUCTION_VALUE','RELATIONSHIP','DERIV_SPECIALIST'):
            self.assertEqual(c[k]['capability_status'],'SOURCE_CAPABILITY_REQUIRED')
        flatbars=flat(160,span=0)
        out=evaluate_core(flatbars)
        self.assertEqual(out['atr14']['value'],D(0))
        self.assertIsNone(out['efficiency16']['value']);self.assertIsNone(out['displacement']['value'])
        self.assertEqual(out['quiet_percentile']['value'],D('.5'))
        zeros=[replace(b,base_volume=D(0),quote_volume=D(0),buy_base=D(0),buy_quote=D(0)) for b in flatbars]
        self.assertIsNone(evaluate_core(zeros,optional=True)['quote_rvol32']['value'])
        self.assertEqual(evaluate_core(zeros)['close']['value'],D(100))

    def test_core_independent_arithmetic_and_past_window_exclusion(self):
        b=bars([(100+i,102+i,99+i,101+i) for i in range(180)])
        x=evaluate_core(b)
        self.assertEqual(x['tr']['value'],D(3));self.assertEqual(x['atr14']['value'],D(3))
        self.assertEqual(x['efficiency16']['value'],D(1))
        self.assertEqual(x['width16']['value'],D(18)/280)
        self.assertEqual(x['quiet_percentile']['value'],compression(b)['past_percentile'])
        expected={'close':D(280),'tr':D(3),'atr14':D(3),'width16':D(18)/280,
            'quiet_percentile':D(0),'efficiency16':D(1),'progress16':D(280)/264,
            'prior_high16':D(280),'prior_low16':D(262),'tr_fraction':D(3)/279,
            'displacement':D(1),'body_fraction':D(1)/3}
        self.assertEqual({k:v['value'] for k,v in x.items()},expected)
        self.assertEqual(evaluate_core(b,optional=True)['quote_rvol32']['value'],D(560)/527)
        for c in CORE_COLUMNS:
            if len(b)>=c.history:self.assertIsNotNone(evaluate_expr(c.expr,b)[-1])
        short=evaluate_core(b[:5]);self.assertEqual(short['quiet_percentile']['status'],'INSUFFICIENT_HISTORY')

    def test_restricted_compiler_injection_and_cycle_rejection(self):
        with self.assertRaises(ContractError):compile_expr(Expr('eval',('import os',)))
        with self.assertRaises(ContractError):compile_expr(Expr('if',(CORE_COLUMNS[0].expr,)))
        with self.assertRaises(ContractError):compile_expr(Expr('field',('close; malicious()',)))
        with self.assertRaises(ContractError):compile_expr(Expr('lag',(CORE_COLUMNS[0].expr,0)))
        with self.assertRaises(ContractError):compile_columns((
            Column('a',CORE_COLUMNS[0].expr,'X',1,dependencies=('b',)),
            Column('b',CORE_COLUMNS[0].expr,'X',1,dependencies=('a',))))
        p=make_remote_pack('CORE_1H',('TESTUSDT','我踏马来了USDT'))
        self.assertTrue(all(registered(x[1]) for x in p.columns));self.assertFalse(p.full_core_qualified)
        self.assertFalse(registered('close; arbitrary()'))
        self.assertEqual(len(EARLY),12)

    def test_remote_early_approach_pressure_positive_negative_and_no_event(self):
        source=flat(180)
        def setbar(age,o,h,l,c):
            source[-1-age]=replace(source[-1-age],open=D(str(o)),high=D(str(h)),low=D(str(l)),close=D(str(c)))
        setbar(8,104,105,103,104)
        setbar(5,104,105,104,104);setbar(4,100,101,99,100)
        setbar(3,104,105,104,104);setbar(2,103,104,102,103)
        setbar(1,104,104.5,103,104);setbar(0,104,105,104,104.8)
        x=early_oracle(source)
        self.assertEqual(x['approach_8_upper'],D(1));self.assertEqual(x['pressure_8_upper'],D(1))
        self.assertEqual(early_oracle(mirror(source))['pressure_8_lower'],D(1))
        self.assertEqual(quiet_near_oracle(source)['quiet_near_8_upper'],D(0))
        self.assertTrue(all(v is None for v in early_oracle(source[:10]).values()))
        self.assertTrue(all(v==0 for v in early_oracle(flat(180)).values()))
        setbar(0,106,107,106,106)
        self.assertEqual(early_oracle(source)['approach_8_upper'],D(0))
        self.assertTrue(all('[0]' not in expression for expression in EARLY.values()))

    def test_every_registered_pivot_age_and_direction_has_early_and_quiet_positive_negative(self):
        for age in (8,12,16):
            source=flat(180)
            raw={age:(104,105,103,104),5:(104,105,104,104),4:(100,101,99,100),
                 3:(104,105,104,104),2:(103,104,102,103),1:(104,104.5,103,104),0:(104,105,104,104.8)}
            for k,row in raw.items():
                o,h,l,c=map(D,map(str,row));source[-1-k]=replace(source[-1-k],open=o,high=h,low=l,close=c)
            quiet=bars([(100,110,90,100)]*158+[(104.5,105,104,104.5)]*22)
            quiet[-1-age]=replace(quiet[-1-age],high=D('105.5'))
            quiet[-1]=replace(quiet[-1],close=D(105))
            for suffix,series,qseries in [('upper',source,quiet),('lower',mirror(source),mirror(quiet))]:
                label=f'{age}_{suffix}'
                self.assertEqual(early_oracle(series)['approach_'+label],D(1))
                self.assertEqual(early_oracle(series)['pressure_'+label],D(1))
                self.assertEqual(quiet_near_oracle(qseries)['quiet_near_'+label],D(1))
                self.assertEqual(quiet_near_oracle(flat(180))['quiet_near_'+label],D(0))
                bad=list(series);c=D(106) if suffix=='upper' else D(94)
                bad[-1]=replace(bad[-1],open=c,high=c+1,low=c-1,close=c)
                self.assertEqual(early_oracle(bad)['approach_'+label],D(0))
                self.assertEqual(early_oracle(bad)['pressure_'+label],D(0))

    def test_remote_controlled_correction_pre_response_symmetric(self):
        source=flat(80)
        # Fixed ages: low20 -> high16 -> higher low12 -> higher high8.
        overrides={20:(96,97,95,96),16:(103,105,102,104),12:(99,100,98,99),
            8:(108,110,107,109),7:(107,108,106,107),6:(105,106,104,105),
            5:(104,105,103,104),4:(103,104,102,103),3:(103,104,102,103),
            2:(102,103,101,102),1:(102,103,101,102),0:(102,103,101,102)}
        # Surround the lower swing by higher neighboring lows.
        for age in (11,13,14):overrides[age]=(101,102,100,101)
        for age in (18,19,21,22):overrides[age]=(99,100,98,99)
        for age,row in overrides.items():
            o,h,l,c=map(D,map(str,row));source[-1-age]=replace(source[-1-age],open=o,high=h,low=l,close=c)
        self.assertEqual(correction_oracle(source)['controlled_correction_long'],D(1))
        self.assertEqual(correction_oracle(mirror(source))['controlled_correction_short'],D(1))
        self.assertEqual(correction_oracle(flat(80))['controlled_correction_long'],D(0))
        self.assertTrue(all(registered(e) for e in CORRECTIONS.values()))

    def test_optional_source_failure_preserves_runtime_price_coverage(self):
        from test_session5 import FakeAPI,FakeClient,fake_pack,AT
        from researcher.discovery import scan_market_research
        import tempfile
        def optional_fault(engine,inventory,pack,cutoff):
            x=fake_pack(engine,inventory,pack,cutoff)
            if len(pack.columns)==1 and pack.column_id=='quote_rvol32':
                x['observations']=[];x['evaluated_symbols']=[];x['returned_symbols']=[]
                x['failed_symbols']={n:'MCP_TOOL_ERROR' for n in inventory.symbols}
            return x
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as temp,patch('researcher.screening.PartitionEngine.run',optional_fault):
            output=scan_market_research(api=FakeAPI(),client=FakeClient(),ledger_path=temp+'/ledger.sqlite',clock=lambda:AT,mode='SYNTHETIC')
        self.assertEqual([p['evaluated'] for p in output['packs']],[4,4])
        self.assertEqual([p['per_formula']['quote_rvol32']['evaluated'] for p in output['packs']],[0,0])
        self.assertEqual(len(output['optional_packs']),2)
        self.assertFalse(any('quote_rvol32' in p['column_ids'] for p in output['packs']))

    def test_local_probe_requires_explicit_local_declaration_before_any_io(self):
        from researcher.analytical_probe import qualify_selected
        with patch('researcher.analytical_probe.OfficialResearchAPI') as api:
            with self.assertRaisesRegex(ContractError,'LOCAL_ONLY_ANALYTICAL_PROBE'):
                qualify_selected(environment=None)
            api.assert_not_called()

    def test_all_method_results_are_invariant_to_unseen_future_and_foreign_references_fail(self):
        b=FamilyChronologyOracles().continuation_sample();at=b[-1].end
        refs=swing_references(b,TICK,as_of=at)
        old=evaluate_methods(b,TICK,cutoff=at,as_of=at,references=refs)
        future=bars([(105,130,70,110)]*5,start=b[-1].end_ms//1000)
        self.assertEqual(old,evaluate_methods([*b,*future],TICK,cutoff=at,as_of=at,references=refs))
        foreign=replace(ref(b),native_symbol='1000PEPEUSDT')
        with self.assertRaises(ContractError):evaluate_methods(b,TICK,cutoff=at,as_of=at,references=(foreign,))

    def test_budget_scenario_not_quota_claim_or_31_scans(self):
        b=scenario_budget();self.assertEqual(b['partitions'],11)
        self.assertEqual(b['all_three_layers'],66);self.assertEqual(b['quota_charges'],'UNKNOWN')
        self.assertFalse(b['compulsory_broad_local_history'])

    def test_selected_runtime_registry_all_families_methods_and_gated_route_a(self):
        b=FamilyChronologyOracles().boundary('F2');r=ref(b)
        bundle=analyze_selected(b,TICK,cutoff=b[-1].end,as_of=b[-1].end,references=(r,))
        self.assertEqual({x['family'] for x in bundle['families']},{'F'+str(i) for i in range(1,10)})
        self.assertEqual(len(bundle['methods']),31)
        self.assertEqual(qualified_route_a(bundle,None,native_symbol='TESTUSDT',timeframe='1h',cutoff=b[-1].end),[])
        cap={'production_enabled':True,'qualification':'QUALIFIED','venue':'BINANCE_USDM',
            'exact_contracts':['TESTUSDT'],'timeframes':['1h'],'cutoff':b[-1].end,
            'formula_version':'families-6a.1','source_oracle_receipt_hash':'SYNTHETIC_QUALIFICATION_CONTRACT_TEST_ONLY','families':['F2']}
        nominated=qualified_route_a(bundle,cap,native_symbol='TESTUSDT',timeframe='1h',cutoff=b[-1].end)
        self.assertEqual(nominated[0]['family'],'F2')
        with self.assertRaises(ContractError):qualified_route_a(bundle,{**cap,'venue':'SPOT'},native_symbol='TESTUSDT',timeframe='1h',cutoff=b[-1].end)

    def test_actual_scan_consumes_capability_registered_selected_analyzers(self):
        from test_session5 import FakeAPI,FakeClient,fake_pack,AT
        from researcher.discovery import scan_market_research
        import tempfile
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as temp,patch('researcher.screening.PartitionEngine.run',fake_pack):
            output=scan_market_research(api=FakeAPI(),client=FakeClient(),ledger_path=temp+'/ledger.sqlite',clock=lambda:AT,mode='SYNTHETIC')
        self.assertTrue(output['selected_research'])
        for row in output['selected_research']:
            self.assertIn('analytical_engine',row);self.assertEqual(len(row['analytical_engine']['methods']),31)
        self.assertEqual(len(output['method_coverage']['analytical_engine']['families']),9)
        self.assertEqual(output['coverage']['full_core_evaluated'],0)
        self.assertEqual(output['new_orders_created'],0)

    def test_retained_schema_and_authentic_historical_prefixes_are_offline_only(self):
        p=json.loads((ROOT/'evidence/external-first/session55/provider-schema.json').read_text())
        schema=p['tools']['screener_run']['inputSchema']
        self.assertTrue({'manualSymbols','lookback','rules','limit'}<=set(schema['properties']))
        # Genuine retained selected bars, no new Binance HTTP or fabricated data.
        report=json.loads((ROOT/'evidence/external-first/session55/causal-qualification.json').read_text())
        def find_series(obj):
            if isinstance(obj,dict):
                for k,v in obj.items():
                    if k=='bars' and isinstance(v,list):yield v
                    else:yield from find_series(v)
            elif isinstance(obj,list):
                for v in obj:yield from find_series(v)
        series=list(find_series(report))
        self.assertTrue(series)
        numeric={'open','high','low','close','base_volume','quote_volume','buy_base','buy_quote'}
        for raw in series[:2]:
            b=[Bar(**{k:D(v) if k in numeric else v for k,v in row.items()}) for row in raw]
            x=evaluate_core(b)
            self.assertEqual(x['atr14']['value'],wilder_atr(b)[-1])
        validate_config(load_config())

    def test_all_14_authentic_selected_histories_reach_integrated_engine_without_backdated_availability(self):
        p=json.loads((ROOT/'evidence/external-first/session55/causal-qualification.json').read_text())
        metadata=json.loads((ROOT/'evidence/external-first/session5/core-qualification.json').read_text())
        ticks={i['native_symbol']:D(i['tick_size']) for i in metadata['inventory']['selected_instruments']}
        self.assertEqual(len(p['selected_samples']),14)
        numeric={'open','high','low','close','base_volume','quote_volume','buy_base','buy_quote'}
        for sample in p['selected_samples']:
            b=[Bar(**{k:D(v) if k in numeric else v for k,v in row.items()}) for row in sample['bars']]
            at=b[-1].received_at;tick=ticks[b[0].native_symbol]
            refs=swing_references(b,tick,as_of=at)
            value=analyze_selected(b,tick,cutoff=b[-1].end,as_of=at,references=refs)
            self.assertEqual(len(value['methods']),31)
            self.assertEqual({x['family'] for x in value['families']},{'F'+str(i) for i in range(1,10)})
            self.assertFalse(value['production_enabled'])
            for h in value['families']:
                if h['available_at']:self.assertLessEqual(utc(h['available_at']),utc(at))
        # Historical prices fetched after a shock's declared TTL are STALE,
        # never a newly available live stabilization or an illegal reference.
        b=flat(40)+bars([(100,112,99,111)],start=START+40*3600)
        received=(utc(b[-1].end)+timedelta(days=8)).isoformat()
        late=[replace(x,received_at=received,available_at=received) for x in b]
        self.assertEqual(shock_family(late,TICK)['status'],'STALE')
