"""Session 4 adversarial synthetic contracts and authentic recorded regressions.

Synthetic READY cases establish engine invariants, never live qualification.
"""
from dataclasses import replace,asdict
from decimal import Decimal as D
import json
import unittest
from unittest.mock import patch
from researcher.contracts import ContractError,Instrument,encode,utc,Evidence,Fidelity
from researcher.research import Fact,fact_id
from researcher.context import (build_context,ContextCard,investigation_order,matched_budget_study,benchmark_fact)
from researcher.candidate_review import (boundary_card,review_card,shortlist,union_cards,remaining_room,
    STAGE_REQUIREMENTS)
from researcher.query_planner import QueryPlanner,Question,Query
from researcher.precursors import (FEATURES,expected_feature,compare_feature,reproduce_atr_failures,
                                   verify_retained_precursors,precursor_questions)
from researcher.structures import boundary_events
from researcher.session4 import authentic_session3,replay_session3
from researcher.screening import closed_cutoff
from researcher.settings import load_config,ROOT
from researcher.nominations import Nomination,NominationRouter
from test_session3 import bars_from,ref_for,iso,BASE
from test_session2 import provisional,AT,CUTOFF


def instrument(name='TESTUSDT'):
    return Instrument(name,'BINANCE_USDM',quote='USDT',settlement='USDT',contract_type='PERPETUAL',
        tick_size=D('.1'),quantity_rules={'minQty':'1'},metadata_hash='SYNTHETIC',identity_status='EXCHANGE_VERIFIED',
        trading_status='TRADING',underlying_class='CRYPTO',source_id='SYNTHETIC',captured_at_utc=iso(BASE-7200000))


def fact(key,value,units,at,*,name='TESTUSDT',tf='1h',measurement=None,age=86400,qualification='QUALIFIED'):
    return Fact(key,instrument(name),measurement or key,value,units,tf,at,at,at,at,'SYNTHETIC_SOURCE',
        'SYNTHETIC_HASH','EXACT_REPORTED',True,qualification,'SYNTHETIC',age)


def case(*,family='F2',name='TESTUSDT',current=106,qualification='QUALIFIED'):
    pressure=[(99,100,98,99),(92,94,90,92),(99,100,98,99)]
    rows=pressure+[(100,105,99,104),(104,106,103,105),(105,107,104,106)]
    if family=='F4':rows=pressure+[(100,105,95,97),(97,98,82,84)]
    if family=='F5':rows=pressure+[(100,105,95,97),(97,98,90,92),(99,105,98,104),(104,106,103,105),(105,107,104,106)]
    bars=bars_from(rows,name=name);r=ref_for(bars);result=boundary_events(r,bars,as_of=bars[-1].end)
    card=boundary_card(r,result,cutoff=bars[-1].end,evidence_ids=('seq',),primary_family=family,
                       origins=('A_REMOTE_STRUCTURE',),qualification=qualification,mode='SYNTHETIC')
    facts={}
    by_id={b.id:b.end for b in bars}
    raw=set(r.source_ids)|{i for e in card.events for i in e['source_ids']}
    for i in raw:facts[i]=fact(i,True,'BOOLEAN',by_id.get(i,r.known_at),name=name)
    at=bars[-1].end
    facts['seq']=fact('seq',True,'BOOLEAN',at,name=name,measurement='CAUSAL_SEQUENCE',qualification=qualification)
    roles={'DECISION_PRICE':(100,'USDT_PER_BASE',card.window_start),
        'RESEARCH_PRICE':(current,'USDT_PER_BASE',at),'REFERENCE_SIGNIFICANCE':('HIGH','ORDINAL',r.known_at),
        'DECISION_PROXIMITY':(True,'BOOLEAN',at),'SPREAD_BPS':(D(2),'BPS',at),
        'DEPTH_USDT_WITHIN_ROOM':(10000,'USDT',at),'ROUND_TRIP_FEE_BPS':(D(8),'BPS',at),
        'SLIPPAGE_BOUND_BPS':(D(3),'BPS',at),'FUNDING_BOUND_BPS':(D(1),'BPS',at),
        'HORIZON_SECONDS':(3600,'SECONDS',at),'HORIZON_RELEVANT':(True,'BOOLEAN',at)}
    for k,(v,u,t) in roles.items():facts[k]=fact(k,v,u,t,name=name)
    # F4 side is bearish; first obstacle below original decision reference.
    obstacle=replace(r,lo=D(80 if family=='F4' else 110),hi=D(80 if family=='F4' else 110),
        kind='RANGE_BOTTOM' if family=='F4' else 'RANGE_TOP',direction=-1 if family=='F4' else 1,
        origin='PREKNOWN_OBSTACLE',source_ids=('OBSTACLE_SOURCE',))
    facts['OBSTACLE_SOURCE']=fact('OBSTACLE_SOURCE',True,'BOOLEAN',r.known_at,name=name)
    if family=='F4':facts['RESEARCH_PRICE']=replace(facts['RESEARCH_PRICE'],value=D(84))
    card=replace(card,evidence_ids=tuple(['seq',*roles]))
    return card,facts,[r,obstacle],bars


def context(labels=(),eth=None):
    at=iso(BASE+6*3600000);facts={}
    for n,ls in [('BTCUSDT',labels),('ETHUSDT',labels if eth is None else eth)]:
        for tf in ['1h','4h']:
            k=n+tf;t=closed_cutoff(at,tf)
            facts[k]=fact(k,{'labels':list(ls)},'STRUCTURE',t,name=n,tf=tf,measurement='BENCHMARK_STRUCTURE')
    return build_context(facts,as_of=at,benchmark_ids=tuple(facts))


class EvidenceAndContext(unittest.TestCase):
    def test_unknown_context_preserves_all_four_htf_slots(self):
        c=build_context({},as_of=iso(BASE),eligible_symbols=('BTCUSDT','ETHUSDT'),eligible_known=True)
        self.assertEqual(len([x for x in c.claims if x.name.endswith(('_1h','_4h'))]),4)
        self.assertEqual(c.agenda,())
        self.assertTrue(all(x.status=='UNKNOWN' for x in c.claims))

    def test_mixed_btc_eth_is_explicit(self):
        c=context(['TREND_UP'],['TREND_DOWN'])
        self.assertTrue(next(x for x in c.claims if x.name=='BTC_ETH_DISAGREEMENT').value)
        self.assertIn('F1',c.agenda)

    def test_htf_stale_and_after_cutoff_never_becomes_current(self):
        at=iso(BASE+6*3600000)
        f=fact('b',{'labels':['TREND_UP']},'STRUCTURE',iso(BASE),name='BTCUSDT',tf='4h',measurement='BENCHMARK_STRUCTURE')
        c=build_context({'b':f},as_of=at,benchmark_ids=('b',))
        self.assertEqual(c.claims[0].status,'UNKNOWN')
        f=replace(f,window_end=iso(BASE+8*3600000),known_at=iso(BASE+8*3600000),available_at=iso(BASE+8*3600000),received_at=iso(BASE+8*3600000))
        self.assertEqual(build_context({'b':f},as_of=at,benchmark_ids=('b',)).agenda,())

    def test_rolling_ticker_cannot_be_htf_structure_or_breadth(self):
        f=fact('b',D(5),'PERCENT',iso(BASE),name='BTCUSDT',measurement='ROLLING_TICKER_RETURN')
        c=build_context({'b':f},as_of=iso(BASE),eligible_symbols=('BTCUSDT',),eligible_known=True,benchmark_ids=('b',),return_ids=('b',))
        self.assertEqual(c.claims[0].status,'UNKNOWN')
        self.assertEqual(next(x for x in c.claims if x.name=='BREADTH_1H_16').evaluated,0)

    def test_breadth_has_exact_evaluable_denominator_and_mad(self):
        at=iso(BASE)
        fs={n:fact(n,D(v),'LOG_RETURN',at,name=n,measurement='CLOSED_LOG_RETURN_16') for n,v in [('BTCUSDT','.01'),('ALTUSDT','.03'),('DOWNUSDT','-.02')]}
        c=build_context(fs,as_of=at,eligible_symbols=(*fs,'MISSINGUSDT'),eligible_known=True,return_ids=tuple(fs))
        b=next(x for x in c.claims if x.name=='BREADTH_1H_16')
        self.assertEqual((b.eligible,b.evaluated,b.missing),(4,3,('MISSINGUSDT',)))
        self.assertEqual(b.value['up_fraction'],D(2)/3);self.assertEqual(b.value['outperform_btc_fraction'],D('.5'))
        self.assertEqual(b.value['median'],D('.01'));self.assertEqual(b.value['mad'],D('.02'))

    def test_sector_mapping_text_is_not_qualified_taxonomy(self):
        c=build_context({},as_of=iso(BASE),sector_mapping={'BTC':'AI'})
        self.assertEqual(next(x for x in c.claims if x.name=='SECTOR_HEAT').status,'UNKNOWN')

    def test_bullish_btc_bearish_alt_survives_research_admission(self):
        card,fs,refs,b=case(family='F4');ctx=context(['TREND_UP'])
        self.assertEqual(investigation_order([card],ctx),[card])
        r=review_card(card,fs,refs,as_of=b[-1].end)
        self.assertIn(r['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'});self.assertEqual(r['side_hypothesis'],'BEARISH')

    def test_falling_btc_independent_bullish_alt_survives(self):
        card,fs,refs,b=case();ctx=context(['TREND_DOWN'])
        self.assertEqual(investigation_order([card],ctx),[card])
        self.assertIn(review_card(card,fs,refs,as_of=b[-1].end)['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'})

    def test_shock_keeps_independent_range_question_in_union(self):
        c,*_=case();r=replace(c,primary_family='F6')
        for ctx in [context(['SHOCK']),context(['RANGE']),context([])]:
            self.assertEqual({x.id for x in investigation_order([r],ctx)},{r.id})

    def test_equal_budget_context_and_neutral_preserve_unreviewed(self):
        a,*_=case(name='AUSDT');b,*_=case(name='BUSDT');c,*_=case(name='CUSDT')
        study=matched_budget_study([a,b,c],context(['SHOCK']),1)
        for k in ['neutral','context']:
            self.assertEqual(len(study[k]['reviewed']),1);self.assertEqual(len(study[k]['not_reviewed']),2)
            self.assertEqual(set(study[k]['reviewed'])|set(study[k]['not_reviewed']),set(study['union_ids']))

    def test_4h_source_clocks_and_future_append_stability(self):
        b=bars_from([100+(j%6) for j in range(45)],name='BTCUSDT')
        b=[replace(x,timeframe='4h',open_ms=BASE+j*14400000,received_at=iso(BASE+(j+1)*14400000),available_at=iso(BASE+(j+1)*14400000)) for j,x in enumerate(b)]
        a=benchmark_fact(b[:40],instrument('BTCUSDT'),as_of=b[39].end,mode='SYNTHETIC')
        same=benchmark_fact(b,instrument('BTCUSDT'),as_of=b[39].end,mode='SYNTHETIC')
        self.assertEqual(a,same)


class PlannerPolicy(unittest.TestCase):
    def setUp(self):
        self.card,self.facts,self.refs,self.bars=case();c=self.card
        self.question=Question('RECLAIM_VS_HOLD',0,'BOOLEAN',('WATCH','READY_FOR_DEEP'))
        self.query=Query('SYNTHETIC_SOURCE','formula_evaluate',c.native_symbol,c.venue,c.timeframe,c.window_start,c.cutoff,
            self.question.fact,self.question.units,'targeted',1,10,100,True,True,True,True)
        self.at=self.bars[-1].end

    def test_only_a_decision_changing_question_can_query(self):
        p=QueryPlanner()
        self.assertEqual(p.next(self.card,[replace(self.question,changes=('WATCH',))],[self.query],{},as_of=self.at)['status'],'STOP_NO_DECISION_CHANGING_QUERY')

    def test_point_quote_keeps_its_real_clock_instead_of_closed_bar_time(self):
        at=iso(self.bars[-1].end_ms+10000)
        q=replace(self.query,operation='binance_book',timeframe='CURRENT',start=iso(self.bars[-1].end_ms-20000),
                  end=at,fact='SPREAD_BPS',units='BPS')
        question=Question('SPREAD_BPS',0,'BPS',('WATCH','READY_FOR_DEEP'))
        p=QueryPlanner()
        fs,_=p.investigate(self.card,[question],[q],{},as_of=at,adapters={('SYNTHETIC_SOURCE','binance_book'):
            lambda q:fact('quote',D(2),'BPS',iso(self.bars[-1].end_ms+9000),tf='CURRENT',measurement='SPREAD_BPS',age=30)})
        self.assertIn('quote',fs)
        self.assertNotEqual(utc(fs['quote'].window_end),utc(self.card.cutoff))
        stale=replace(q,start=iso(self.bars[-1].end_ms-30000))
        self.assertEqual(QueryPlanner().next(self.card,[question],[stale],{},as_of=at)['status'],'UNKNOWN')

    def test_necessary_contradiction_precedes_optional_facts(self):
        q=replace(self.question,priority=99,contradiction=True)
        optional=Question('DECORATION',0,'BOOLEAN',('X','Y'),necessary=False)
        p=QueryPlanner()
        self.assertEqual(p.next(self.card,[optional,q],[self.query],{},as_of=self.at)['question'],q)

    def test_unavailable_specialist_retains_unknown(self):
        p=QueryPlanner();plan=p.next(self.card,[self.question],[],{},as_of=self.at)
        self.assertEqual(plan['status'],'UNKNOWN');self.assertEqual(p.audit[-1]['reason'],'NO_QUALIFIED_SOURCE')

    def test_scope_units_rights_history_and_stale_are_rejected(self):
        for changes in [{'native_symbol':'WRONGUSDT'},{'venue':'SPOT'},{'timeframe':'15m'},
                {'units':'PERCENT'},{'authorized':False},{'qualified':False},{'complete_window':False},
                {'source_current':False},{'operation':'create_order'}]:
            with self.subTest(changes=changes):
                self.assertEqual(QueryPlanner().next(self.card,[self.question],[replace(self.query,**changes)],{},as_of=self.at)['status'],'UNKNOWN')

    def test_budget_pools_do_not_steal_audit_or_watch_reserve(self):
        p=QueryPlanner(budgets={'broad':0,'targeted':0,'exception':1,'watch':1})
        self.assertEqual(p.next(self.card,[self.question],[self.query],{},as_of=self.at)['status'],'NOT_REVIEWED_BUDGET')
        self.assertEqual(p.next(self.card,[self.question],[replace(self.query,pool='exception')],{},as_of=self.at)['status'],'QUERY')

    def test_equivalent_qualified_query_prefers_lower_cost(self):
        cheap=replace(self.query,quota=0,latency_ms=20)
        self.assertEqual(QueryPlanner().next(self.card,[self.question],[self.query,cheap],{},as_of=self.at)['query'],cheap)

    def test_validated_cache_avoids_repeat_network_and_unchanged_watch(self):
        p=QueryPlanner();called=[]
        def adapter(q):
            called.append(q);return fact('answer',True,'BOOLEAN',q.end,measurement=q.fact)
        fs,plans=p.investigate(self.card,[self.question],[self.query],{},as_of=self.at,adapters={('SYNTHETIC_SOURCE','formula_evaluate'):adapter})
        self.assertIn('answer',fs);self.assertEqual(len(called),1)
        self.assertEqual(p.next(self.card,[self.question],[self.query],{},as_of=self.at)['status'],'CACHED')
        self.assertEqual(p.budgets['targeted'],3)

    def test_response_identity_mismatch_is_unknown_and_not_retried(self):
        p=QueryPlanner()
        fs,_=p.investigate(self.card,[self.question],[self.query],{},as_of=self.at,
            adapters={('SYNTHETIC_SOURCE','formula_evaluate'):lambda q:fact('bad',True,'BOOLEAN',q.end,name='WRONGUSDT',measurement=q.fact)})
        self.assertEqual(fs,{})
        self.assertEqual(p.next(self.card,[self.question],[self.query],{},as_of=self.at)['status'],'UNKNOWN')
        self.assertEqual(p.audit[-1]['rejections'][0]['reason'],'UNCHANGED_WATCH_ALREADY_QUERIED')

    def test_existing_exact_fact_stops_unnecessary_query(self):
        f=fact('cached',True,'BOOLEAN',self.query.end,measurement=self.question.fact)
        self.assertEqual(QueryPlanner().next(self.card,[self.question],[self.query],{f.id:f},as_of=self.at)['status'],'STOP_NO_DECISION_CHANGING_QUERY')


class ShortlistContracts(unittest.TestCase):
    def test_f2_f4_f5_each_reach_only_their_own_sequence_contract(self):
        for family in ['F2','F4','F5']:
            c,f,refs,b=case(family=family);r=review_card(c,f,refs,as_of=b[-1].end)
            self.assertIn(r['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'},(family,r))
            self.assertTrue(r['necessary_sequence_event_ids'])
            self.assertTrue(any(h['family']=='NULL' for h in r['hypotheses']))

    def test_f2_cannot_become_f5_without_reclaim_and_opposing_attempt(self):
        c,f,refs,b=case();c=replace(c,primary_family='F5')
        self.assertNotIn(review_card(c,f,refs,as_of=b[-1].end)['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'})

    def test_trial_and_unverified_identity_cannot_be_ready(self):
        c,f,refs,b=case(qualification='TRIAL')
        self.assertNotIn(review_card(c,f,refs,as_of=b[-1].end)['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'})
        c,f,refs,b=case();f={k:replace(v,instrument=replace(v.instrument,identity_status='UNVERIFIED')) for k,v in f.items()}
        self.assertNotIn(review_card(c,f,refs,as_of=b[-1].end)['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'})

    def test_room_unknown_and_economics_unknown_are_distinct(self):
        c,f,refs,b=case();r=review_card(c,f,refs[:1],as_of=b[-1].end)
        self.assertEqual(r['room']['status'],'ROOM_UNKNOWN')
        c=replace(c,evidence_ids=tuple(i for i in c.evidence_ids if i!='ROUND_TRIP_FEE_BPS'))
        r=review_card(c,f,refs,as_of=b[-1].end)
        self.assertEqual(r['room']['status'],'ROOM_OBSERVED');self.assertEqual(r['economics']['status'],'ECONOMICS_UNKNOWN')

    def test_first_obstacle_is_frozen_even_after_price_passes_it(self):
        c,f,refs,b=case(current=111)
        farther=replace(refs[1],lo=D(120),hi=D(120),origin='FARTHER')
        r=review_card(c,f,refs+[farther],as_of=b[-1].end)
        self.assertEqual(r['room']['first_obstacle_id'],refs[1].id)
        self.assertEqual(r['stage'],'LATE');self.assertEqual(r['room']['gross_room'],0)

    def test_future_obstacle_does_not_create_room(self):
        c,f,refs,b=case();refs[1]=replace(refs[1],known_at=b[-1].end,available_at=b[-1].end)
        self.assertEqual(review_card(c,f,refs,as_of=b[-1].end)['room']['status'],'ROOM_UNKNOWN')

    def test_actual_unfavorable_economics_and_horizon_block_ready(self):
        c,f,refs,b=case();f['SLIPPAGE_BOUND_BPS']=replace(f['SLIPPAGE_BOUND_BPS'],value=D(1000))
        r=review_card(c,f,refs,as_of=b[-1].end)
        self.assertEqual(r['economics']['status'],'ECONOMICS_UNFAVORABLE');self.assertNotIn(r['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'})
        f['HORIZON_SECONDS']=replace(f['HORIZON_SECONDS'],value=16*3600)
        self.assertEqual(review_card(c,f,refs,as_of=b[-1].end)['economics']['status'],'HORIZON_UNCERTAIN')

    def test_stale_or_after_cutoff_necessary_sequence_blocks_admission(self):
        c,f,refs,b=case();f['seq']=replace(f['seq'],window_end=b[-2].end,known_at=b[-2].end,available_at=b[-2].end,received_at=b[-2].end)
        self.assertNotIn(review_card(c,f,refs,as_of=b[-1].end)['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'})

    def test_distance_alone_cannot_promote_missing_sequence(self):
        c,f,refs,b=case();c=replace(c,primary_family='F6')
        self.assertNotIn(review_card(c,f,refs,as_of=b[-1].end)['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'})

    def test_source_citations_and_opposing_null_rivals_are_required(self):
        c,f,refs,b=case();del f[c.reference.source_ids[0]]
        with self.assertRaises(ContractError):review_card(c,f,refs,as_of=b[-1].end)
        with self.assertRaises(ContractError):replace(c,hypotheses=tuple(h for h in c.hypotheses if h.family!='NULL'))

    def test_dedupe_preserves_independent_initiators(self):
        c,*_=case();d=replace(c,origins=('B_QUALIFIED_SPECIALIST',),method_ids=('M26',))
        u=union_cards([c,d]);self.assertEqual(len(u),1)
        self.assertEqual(set(u[0].origins),{'A_REMOTE_STRUCTURE','B_QUALIFIED_SPECIALIST'})
        self.assertIn('M26',u[0].method_ids)

    def test_shortlist_zero_to_five_and_preserves_audit(self):
        rows=[]
        for j in range(7):
            c,f,refs,b=case(name=f'SYNTH{j}USDT');rows.append(review_card(c,f,refs,as_of=b[-1].end))
        result=shortlist(rows,coverage={'eligible':519},not_reviewed=[{'id':'unreviewed','reason':'NOT_REVIEWED_BUDGET'}])
        self.assertEqual(len(result['shortlist']),5);self.assertEqual(len(result['near_misses']),2)
        self.assertEqual(len(result['not_reviewed']),1);self.assertTrue(result['pairwise_comparison'])
        self.assertEqual(shortlist([],coverage={'eligible':None})['shortlist'],[])
        with self.assertRaises(ContractError):shortlist(rows,coverage={},max_count=6)

    def test_output_contains_no_executable_trade_instructions(self):
        c,f,refs,b=case();r=shortlist([review_card(c,f,refs,as_of=b[-1].end)],coverage={})
        def keys(x):
            if isinstance(x,dict):
                for k,v in x.items():yield k;yield from keys(v)
            elif isinstance(x,(list,tuple)):
                for v in x:yield from keys(v)
        self.assertFalse(set(keys(r))&{'entry','stop','stop_loss','take_profit','position_size','win_probability'})
        self.assertEqual(r['new_orders_created'],0);self.assertEqual(r['llm_calls'],0)

    def test_every_stage_has_explicit_requirements(self):
        from researcher.nominations import STAGES
        self.assertEqual(set(STAGE_REQUIREMENTS),STAGES)
        self.assertTrue(all(STAGE_REQUIREMENTS.values()))


class SourceRegressions(unittest.TestCase):
    def test_exact_remote_atr_seed_and_recurrence_use_independent_retained_hlc(self):
        from researcher.precursors import verify_seed_capture
        capture=json.loads((ROOT/'evidence/external-first/session4/atr-seed-experiment.json').read_text())
        original,_=authentic_session3()
        for check in capture['checks']:
            oracle=next(o for o in original['oracles'] if o['native_symbol']=='BTCUSDT' and o['timeframe']==check['timeframe'])
            fields={o['formula']:{r['open_seconds']:r['independent'] for r in o['comparisons']} for o in oracle['outcomes']}
            for row in check['independent_hlc']:
                for field in ['high','low','close']:self.assertEqual(D(row[field]),D(fields[field][row['open_seconds']]))
            result=verify_seed_capture(check)
            explicit=next(x for x in result if x['label']=='explicit_tr_rma')
            native=next(x for x in result if x['label']=='native_atr')
            self.assertEqual(len(explicit['comparisons']),6);self.assertTrue(explicit['passed'])
            self.assertTrue(explicit['comparisons'][0]['seed_point']);self.assertFalse(native['passed'])
            self.assertTrue(all(x['alternative_first_hl_seed_passed'] for x in native['comparisons']))
            self.assertTrue(all(x['production_enabled'] is False for x in result))

    def test_remote_seed_history_start_mismatch_is_rejected(self):
        from researcher.precursors import verify_seed_capture
        capture=json.loads((ROOT/'evidence/external-first/session4/atr-seed-experiment.json').read_text())
        check=capture['checks'][0];check['source_window']['from']+=3600
        with self.assertRaises(ContractError):verify_seed_capture(check)

    def test_new_live_remote_values_match_only_retained_independent_times(self):
        q=json.loads((ROOT/'evidence/external-first/session4/qualification.json').read_text())
        old,_=authentic_session3();checks=verify_retained_precursors(old,q['outcomes'])
        self.assertEqual(json.loads(encode(checks)),q['independent_comparisons'])
        self.assertEqual(sum(len(c['comparisons']) for c in checks),98)
        self.assertTrue(all(row['passed'] for c in checks for row in c['comparisons']))
        self.assertEqual(sum(c['status']=='NO_RETAINED_INDEPENDENT_INPUTS' for c in checks),4)
        self.assertTrue(all(c['production_enabled'] is False for c in checks))

    def test_unicode_targeted_failure_and_filler_counts_survive_curation(self):
        q=json.loads((ROOT/'evidence/external-first/session4/qualification.json').read_text())
        self.assertEqual(q['unicode_targeted_alternative']['status'],'MCP_TOOL_ERROR')
        self.assertEqual(q['unicode_targeted_alternative']['receipt']['http_status'],200)
        self.assertEqual(q['unicode_targeted_alternative']['label'],'unicode_formula_1h')
        self.assertEqual(sum(x['excluded_fillers'] for x in q['coverage']),26)
        self.assertEqual(sum(x['evaluated'] for x in q['coverage']),214)
        self.assertTrue(all(x['qualified_methods']==0 for x in q['coverage']))

    def test_quiet_questions_are_independent_incomplete_precursors(self):
        q=json.loads((ROOT/'evidence/external-first/session4/qualification.json').read_text())
        questions=precursor_questions(q['scans'])
        self.assertEqual(len(questions),24)
        self.assertTrue(all(x['nomination'].direction=='UNDETERMINED' for x in questions))
        self.assertTrue(all(x['nomination'].stage=='PREMATURE' and not x['formation_supported'] for x in questions))
        self.assertTrue(all(x['disposition']=='UNKNOWN' for x in questions))

    def test_same_price_evidence_is_one_dependency_cluster(self):
        c,f,refs,b=case();r=review_card(c,f,refs,as_of=b[-1].end)
        self.assertEqual(r['evidence_clusters'],('PRICE_PATH',))
        self.assertIsNone(r['independent_confirmation_count'])

    def test_stale_book_and_old_inventory_block_ready(self):
        c,f,refs,b=case();f['SPREAD_BPS']=replace(f['SPREAD_BPS'],window_end=iso(b[-1].end_ms-31000),
            known_at=iso(b[-1].end_ms-31000),available_at=iso(b[-1].end_ms-31000),received_at=iso(b[-1].end_ms-31000))
        self.assertEqual(review_card(c,f,refs,as_of=b[-1].end)['economics']['status'],'ECONOMICS_UNKNOWN')
        f['seq']=replace(f['seq'],instrument=replace(f['seq'].instrument,captured_at_utc=iso(BASE-2*86400000)))
        self.assertNotIn(review_card(c,f,refs,as_of=b[-1].end)['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM'})

    def test_configuration_refuses_unqualified_provider_or_llm_promotion(self):
        from researcher.settings import validate_config
        for key,value in [('default_llm_calls',1),('full_core_enabled',True),('specialist_runtime_sources',{'unproven':{}})]:
            cfg=load_config();cfg['session4'][key]=value
            with self.assertRaisesRegex(ContractError,'SESSION4_CAPABILITY_BOUNDARY'):validate_config(cfg)

    def test_exact_four_authentic_atr_failures_remain_failures(self):
        report,_=authentic_session3();r=reproduce_atr_failures(report)
        self.assertEqual(len(r['failures']),4)
        self.assertEqual(sum(len(x['comparisons']) for x in r['failures']),80)
        self.assertTrue(all(not c['recomputed_passed'] for x in r['failures'] for c in x['comparisons']))
        self.assertTrue(all(x['first_bar_hl_seed_passed'] for x in r['failures']))

    def test_explicit_tr_rma_semantics_against_selected_oracle(self):
        b=bars_from([100]*14+[120]*26)
        self.assertNotEqual(expected_feature('atr_explicit',b[:15]),D(2))
        self.assertEqual(expected_feature('base_rvol32',b),1)

    def test_quiet_baseline_excludes_measured_window_and_handles_ties(self):
        b=bars_from([100]*180)
        self.assertEqual(expected_feature('quiet_percentile',b),D('.5'))
        self.assertEqual(expected_feature('quiet_ratio',b),1)
        with self.assertRaises(ContractError):expected_feature('quiet_percentile',b[:158])

    def test_remote_feature_identity_and_tail_clock_contract(self):
        b=bars_from([100+j%7 for j in range(180)])
        values=[expected_feature('width16',b[:j+1]) for j in range(160,180)]
        data={'symbol':'TESTUSDT','exchange':'binance','market':'futures','timeframe':'1h','bars':180,
            'tail':values,'tailTimes':[x.open_ms//1000 for x in b[-20:]]}
        self.assertTrue(compare_feature('width16',data,b)['passed'])
        data['tailTimes'][-1]+=3600
        with self.assertRaises(ContractError):compare_feature('width16',data,b)

    def test_authentic_replay_produces_cited_watches_not_fictitious_ready(self):
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('replay must be offline')):
            r=replay_session3()
        self.assertEqual(r['mode'],'AUTHENTIC_REPLAY');self.assertEqual(r['shortlist'],[])
        self.assertEqual(len(r['watches'])+len(r['invalidations']),40)
        self.assertEqual(len(r['method_coverage']['methods']),31)
        self.assertEqual(r['resources']['http_requests'],0)
        for card in r['watches']+r['invalidations']:
            self.assertTrue(set(card['supporting_evidence_ids'])<=set(r['facts']))

    def test_specialist_independent_route_checks_actual_scope(self):
        inv=provisional();e=Evidence('special',inv.instruments[0],'OI_CHANGE',D(1),'BASE_OI','1h',
            '2026-11-13T04:00:00Z',CUTOFF,AT,None,AT,'specialist','BINANCE_USDM_PERPETUAL','schema','receipt',None,
            True,'SUPPORTED',Fidelity.EXACT_REPORTED,'CLOSED_CURRENT')
        n=Nomination('BTCUSDT','SPECIALIST',('F9',),('M26',),'specialist',('special',),CUTOFF,AT,AT,
            'EXACT_REPORTED','TARGETED_ONLY','Does covered OI shock change the research question?')
        cap={'qualification':'QUALIFIED','exact_contracts':['BTCUSDT'],'method_ids':['M26'],
            'venue':'BINANCE_USDM','authorized_read_only':True,'units':['BASE_OI'],'timeframes':['1h']}
        router=NominationRouter(load_config(),inv,specialist_capabilities={'specialist':cap})
        router.add(n,{'special':e});self.assertEqual(len(router.union()),1)
        with self.assertRaises(ContractError):router.add(n,{'special':replace(e,units='USD_OI')})
        with self.assertRaises(ContractError):NominationRouter(load_config(),inv).add(n,{'special':e})
