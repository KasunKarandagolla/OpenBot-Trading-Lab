"""Integrated ordinary-runtime controls. All controls are explicitly offline.

Authentic reconstruction preserves captured data, never prospective recall.
"""
import copy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from researcher.contracts import ContractError, Instrument, digest, encode, utc
from researcher.discovery import scan_market_research
from researcher.replay import synthetic_6b, retained_session5, decode_bars
from researcher.resource_planner import plan_resources
from researcher.query_planner import ResearchSources, QueryPlanner, Query, Question
from researcher.candidate_review import formation_cards, review_card, shortlist, union_cards
from researcher.engine_capabilities import analyze_selected
from researcher.structures import swing_references
from researcher.research import Fact, fact_id
from researcher.handoff import replay_export
from researcher.persistence import read_latest_report, RunLedger
from researcher.settings import ROOT, load_config
from researcher.observations import WIDTHS, iso_seconds
from researcher.specialists import SpecialistEnvelope
from researcher.context import build_context
from researcher.audit import allocate


class IntegratedControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'work').mkdir(exist_ok=True)
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'work')
        cls.db=Path(cls.temp.name)/'control.sqlite'
        cls.api,cls.client,cls.sources,cls.at,cls.provenance=synthetic_6b()
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('NETWORK_FORBIDDEN')):
            cls.result=scan_market_research(api=cls.api,client=cls.client,sources=cls.sources,
                clock=lambda:cls.at,mode='SYNTHETIC',ledger_path=cls.db)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_positive_ordinary_pipeline_not_prebuilt_cards(self):
        r=self.result
        self.assertEqual(r['source_faults'],[])
        self.assertTrue(0<len(r['shortlist'])<=5)
        self.assertTrue(all(p['evaluated']==3 for p in r['packs']))
        self.assertTrue(all(c['primary_family']=='F4' and c['formation_contract'] for c in r['shortlist']))
        for c in r['shortlist']:
            self.assertEqual(c['stage'],'CONDITIONAL_FOR_DEEP')
            self.assertTrue(c['necessary_sequence_event_ids'])
            self.assertIsNotNone(c['strongest_rival']);self.assertEqual(c['null_rival']['family'],'NULL')
            self.assertGreater(D(c['room']['room_bps']),D(c['economics']['observed_friction_bound_bps']))
            self.assertTrue(c['economics']['assumption_evidence_ids'])
            self.assertTrue(c['next_deep_analyst_question'])
        self.assertEqual(r['evidence_mode'],'SYNTHETIC_TEST');self.assertEqual(r['costs']['http_requests'],0)

    def test_source_chain_and_export_replay_resolve(self):
        packet=json.loads(encode(self.result['handoff_export']))
        reviews=replay_export(packet,as_of=self.at)
        self.assertEqual([r['stage'] for r in reviews],[r['stage'] for r in self.result['shortlist']])
        for p in packet['research_handoffs']:
            ids=set(p['card']['evidence_ids'])|set(p['card']['reference']['source_ids'])
            ids.update(i for e in p['card']['events'] for i in e['source_ids'])
            self.assertTrue(ids<=set(p['evidence']))
            self.assertTrue(p['obstacles'])

    def test_versioned_report_hash_and_atomic_saved_read_only_views(self):
        report=self.result['research_shortlist'];body={k:v for k,v in report.items() if k!='payload_sha256'}
        self.assertEqual(digest(encode(body).encode()),report['payload_sha256'])
        before=self.db.read_bytes();saved=read_latest_report(self.db)
        latest=saved['research_shortlist'];latest_body={k:v for k,v in latest.items() if k!='payload_sha256'}
        self.assertEqual(latest['payload_sha256'],digest(encode(latest_body).encode()))
        import sqlite3,zlib
        db=sqlite3.connect(self.db.as_uri()+'?mode=ro',uri=True)
        try:
            raw=db.execute('SELECT body FROM run_snapshot WHERE run_key=?',(self.result['run_key'],)).fetchone()[0]
            original=json.loads(zlib.decompress(raw))
        finally:db.close()
        self.assertEqual(original['research_shortlist']['payload_sha256'],report['payload_sha256'])
        self.assertEqual(before,self.db.read_bytes())

    def test_all_nine_and_31_methods_remain_independently_accounted(self):
        for tf,rows in self.result['research_coverage']['by_timeframe'].items():
            self.assertEqual(set(rows['families']),{f'F{i}' for i in range(1,10)})
            self.assertEqual(set(rows['methods']),{f'M{i:02d}' for i in range(1,32)})
            self.assertEqual(rows['methods']['M14']['code_state'],'DEFINITION_PENDING')
            self.assertEqual(rows['methods']['M15']['code_state'],'DEFINITION_PENDING')
        self.assertFalse(self.result['coverage']['all_market_structurally_covered'])
        self.assertTrue(all(not m['production_enabled'] for m in self.result['method_coverage']['analytical_engine']['methods']))

    def test_same_source_warm_repeat_preserves_admission_reference_event_and_watch_counts(self):
        api,client,sources,at,_=synthetic_6b()
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('NETWORK_FORBIDDEN')):
            repeat=scan_market_research(api=api,client=client,sources=sources,clock=lambda:at,
                mode='SYNTHETIC',ledger_path=self.db)
        self.assertTrue(repeat['costs']['cached_snapshot_reused'])
        self.assertEqual(repeat['costs']['targeted_kline_calls'],0)
        self.assertEqual([x['card_id'] for x in repeat['shortlist']],[x['card_id'] for x in self.result['shortlist']])
        for k in ('reference','event','hypothesis','watch_revisions'):
            self.assertEqual(self.result['persistence'][k],repeat['persistence'][k])
        # A later manual invocation refreshes point evidence, without repeating
        # history or dropping otherwise valid admissions solely due to a cache.
        later=(utc(at)+timedelta(seconds=10)).isoformat()
        api,client,sources,_,_=synthetic_6b();api.at=later
        advanced=scan_market_research(api=api,client=client,sources=sources,clock=lambda:later,
            mode='SYNTHETIC',ledger_path=self.db)
        self.assertTrue(advanced['costs']['cached_snapshot_reused'])
        self.assertEqual(advanced['costs']['targeted_kline_calls'],0)
        self.assertEqual([x['card_id'] for x in repeat['shortlist']],[x['card_id'] for x in advanced['shortlist']])
        self.assertTrue(advanced['reuse']['admission_revalidated_from_frozen_export'])
        for packet in advanced['handoff_export']['research_handoffs']:
            quotes=[f for f in packet['evidence'].values() if f['measurement']=='RESEARCH_PRICE']
            self.assertTrue(any(f['window_end']==later for f in quotes))
        # A witnessed first-obstacle crossing remains a late near miss.
        crossed=(utc(at)+timedelta(seconds=15)).isoformat()
        api,client,sources,_,_=synthetic_6b();api.at=crossed;api.prices['CONTROLUSDT']=D(94)
        late=scan_market_research(api=api,client=client,sources=sources,clock=lambda:crossed,
            mode='SYNTHETIC',ledger_path=self.db)
        self.assertEqual(late['shortlist'],[]);self.assertTrue(late['consumed_obstacles'])
        self.assertTrue(late['late']);self.assertEqual(late['costs']['targeted_kline_calls'],0)

    def test_source_certificates_cannot_leak_into_live_mode(self):
        with self.assertRaisesRegex(ContractError,'SOURCE_QUALIFICATION_CONTRACT'):
            ResearchSources(mode='LIVE',certificates=self.sources.certificates)

    def test_disabled_model_and_no_execution_connection(self):
        self.assertEqual(self.result['consultant']['calls'],0)
        self.assertFalse(self.result['trade_authorization']);self.assertEqual(self.result['new_orders_created'],0)
        self.assertIsNone(self.result['handoff_export']['execution_connection'])

    def test_cli_same_function_positive_and_readonly_show(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
            db=Path(tmp)/'cli.sqlite';out=Path(tmp)/'cli.json'
            run=subprocess.run([sys.executable,'-m','researcher','scan','now','--replay','synthetic-6b',
                '--db',str(db),'--output',str(out)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            r=json.loads(out.read_text());self.assertTrue(r['shortlist']);self.assertEqual(r['costs']['http_requests'],0)
            before=db.read_bytes()
            for action in ('results','watches','coverage'):
                show=subprocess.run([sys.executable,'-m','researcher','show',action,'--db',str(db)],
                    cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(show.returncode,0,show.stdout+show.stderr);json.loads(show.stdout)
            self.assertEqual(db.read_bytes(),before)


class ResourcePlans(unittest.TestCase):
    def test_exact_519_core_optional_conflict_and_partitions(self):
        names=tuple(f'C{i}USDT' for i in range(519))
        plan=plan_resources(names,qualified_packs=['CORE_1H','CORE_15M','PARTICIPATION_1H','PARTICIPATION_15M','METHOD_STRUCTURE_1H','METHOD_STRUCTURE_15M'])
        self.assertEqual((plan['partitions'],plan['mandatory_core_calls'],plan['three_layers_calls']),(11,22,66))
        self.assertEqual(sum(r['logical_calls_planned'] for r in plan['packs']),26)
        self.assertTrue(plan['full_core_planned']);self.assertFalse(plan['coverage_certified'])
        self.assertEqual(sum(r['logical_calls_planned'] for r in plan['packs'] if r['pack_id'].startswith('PARTICIPATION')),4)
        self.assertTrue(any(r['not_evaluated_budget'] for r in plan['packs']))
        self.assertIsNone(plan['quota'])
        requested=[n for r in plan['packs'] if r['pack_id']=='CORE_1H' for p in r['selected_partitions'] for n in p]
        self.assertEqual(tuple(requested),names)

    def test_insufficient_quota_cannot_certify_full_core(self):
        names=tuple(f'C{i}USDT' for i in range(519))
        for cap,quota in ((10,None),(26,19),(26,0)):
            p=plan_resources(names,cap=cap,remaining_quota=quota,qualified_packs=['CORE_1H','CORE_15M'])
            self.assertFalse(p['full_core_planned']);self.assertFalse(p['coverage_certified'])
            self.assertTrue(any(r['not_evaluated_budget'] for r in p['packs'] if r['required']))

    def test_disabled_new_packs_still_have_executable_degraded_plan(self):
        names=tuple(f'C{i}USDT' for i in range(519));p=plan_resources(names,fallback_qualified=True)
        self.assertEqual(sum(x['calls'] for x in p['effective_degraded_plan']),26)
        self.assertFalse(p['full_core_planned']);self.assertEqual(p['actual_fallback'],'QUALIFIED_LEGACY_PRICE_SCALARS')
        self.assertEqual(p['selected_reserves']['watch_exception_audit'],'PROTECTED_ROTATING_REVIEW_LANE')

    def test_estimates_bound_to_retained_receipts_and_versioned_hash(self):
        p=plan_resources(('AUSDT',),qualified_packs=['CORE_1H','CORE_15M'],samples=[{'response_bytes':200,'elapsed_ms':10}])
        self.assertEqual(p['estimates']['response_bytes'],400)
        self.assertEqual(p['estimates']['serial_latency_ms'],20)
        self.assertEqual(p['plan_sha256'],digest(encode({k:v for k,v in p.items() if k!='plan_sha256'}).encode()))

    def test_positive_audit_capacity_and_unreviewed_names_with_opposing_context(self):
        nominees=[{'native_symbol':n,'timeframe':'1h','families':['F4'],'routes':[route]}
            for n,route in [('AUSDT','A_REMOTE_CAUSAL'),('BUSDT','B_SPECIALIST'),('CUSDT','C_STRATIFIED_AUDIT')]]
        reached=set()
        for j in range(8):
            cutoff=iso_seconds(1794650400+j*900)
            for agenda in (['F1'],['F9'],[]):
                context=type('Context',(),{'agenda':agenda})()
                chosen,receipts,p=allocate(nominees,context,{'15m':cutoff})
                self.assertEqual(len(chosen),2);self.assertIn('AUSDT',chosen)
                self.assertEqual(len(p['neutral']),len(p['context']));reached.update(chosen)
        self.assertEqual(reached,{'AUSDT','BUSDT','CUSDT'})


class GraphAndPlanner(unittest.TestCase):
    def synthetic_graph(self, family='F4'):
        from test_session6a import FamilyChronologyOracles,ref,TICK,bars as make_bars,flat,START
        fixture=FamilyChronologyOracles()
        benchmark=None
        if family=='F1':bars=fixture.continuation_sample();refs=swing_references(bars,TICK,as_of=bars[-1].end)
        elif family=='F3':
            bars=make_bars([(100,105,95,100)]*159+[(100,100.2,99.8,100)]*20+[(100,105,100,104.8),(104,105,103,104)])
            refs=[ref(bars,known=158,atr=2)]
        elif family=='F6':bars=fixture.balance_sample();refs=swing_references(bars,TICK,as_of=bars[-1].end)
        elif family=='F7':
            prices=[100,103,105,103,100,97,95,97]*4+[100]*12+[110,109,107,104]
            bars=make_bars([(p,p+.5,p-.5,p) for p in prices],tf='15m')
            refs=swing_references(bars,TICK,as_of=bars[-1].end)
        elif family=='F8':
            benchmark=[replace(x,close=D(100)+(j%4),high=D(104),low=D(99)) for j,x in enumerate(flat(41,name='BTCUSDT'))]
            bars=[replace(x,close=D(100)+(j%4)+max(0,j-35),high=D(110),low=D(99)) for j,x in enumerate(flat(41))]
            refs=[ref(bars,lo=104,hi=104,known=33)]
        elif family=='F9':
            bars=flat(40)+make_bars([(100,112,99,111),(110,111,105,108),(108,110,106,109),(111,115,110,114)],start=START+40*3600)
            refs=swing_references(bars,TICK,as_of=bars[-1].end)
        else:bars=fixture.boundary(family);refs=[ref(bars)]
        at=bars[-1].end
        i=Instrument(bars[0].native_symbol,'BINANCE_USDM',quote='USDT',settlement='USDT',contract_type='PERPETUAL',
            tick_size=TICK,quantity_rules={'minQty':'1'},metadata_hash='SYNTHETIC',identity_status='EXCHANGE_VERIFIED',
            trading_status='TRADING',underlying_class='CRYPTO',captured_at_utc=at,source_id='SYNTHETIC')
        facts={b.id:Fact(b.id,i,'SELECTED_CLOSED_BAR',{'close':b.close},'USDT_PER_BASE',b.timeframe,
            b.end,b.end,b.received_at,b.received_at,'SYNTHETIC',b.source_hash,'EXACT_REPORTED',True,
            'QUALIFIED','SYNTHETIC',300*WIDTHS[b.timeframe]) for b in bars}
        bundle=analyze_selected(bars,TICK,cutoff=at,as_of=at,references=refs,benchmark=benchmark)
        cards,new_refs,bundles=formation_cards(bundle,i,facts,cutoff=at,as_of=at,mode='SYNTHETIC',
            qualified_families=[family],origins=('A_REMOTE_STRUCTURE',))
        return bars,bundle,cards,facts,[*refs,*new_refs]

    def test_all_nine_engine_timelines_reach_interpreter(self):
        for f in (f'F{i}' for i in range(1,10)):
            with self.subTest(family=f):
                b,bundle,cards,facts,refs=self.synthetic_graph(f)
                c=next(c for c in cards if c.primary_family==f)
                r=review_card(c,facts,refs,as_of=b[-1].end)
                self.assertNotIn('COMPLETE_FAMILY_SEQUENCE',r['missing_necessary_inputs'])
                self.assertTrue(r['necessary_sequence_event_ids']);self.assertEqual(r['primary_family'],f)
                self.assertEqual(r['null_rival']['family'],'NULL');self.assertTrue(r['method_roles'])

    def test_append_future_cannot_change_earlier_card_ids_events_or_reviews(self):
        b,bundle,cards,facts,refs=self.synthetic_graph('F1');at=b[-1].end
        future=replace(b[-1],open_ms=b[-1].end_ms,received_at=iso_seconds(b[-1].end_ms//1000+3600),
            available_at=iso_seconds(b[-1].end_ms//1000+3600))
        appended=analyze_selected([*b,future],b[0].close*0+D('.01'),cutoff=at,as_of=at,references=refs[:len(swing_references(b,D('.01'),as_of=at))])
        self.assertEqual(bundle['families'],appended['families'])
        self.assertEqual(bundle['methods'],appended['methods'])

    def test_no_reclaim_cannot_manufacture_f5_research_admission(self):
        b,bundle,cards,facts,refs=self.synthetic_graph('F2')
        f5=next((c for c in cards if c.primary_family=='F5'),None)
        if f5:
            r=review_card(f5,facts,refs,as_of=b[-1].end)
            self.assertIn('COMPLETE_FAMILY_SEQUENCE',r['missing_necessary_inputs'])
        self.assertFalse(any(h['family']=='F5' and h['details'].get('acceptance_verified') for h in bundle['families']))

    def test_equivalent_query_cache_ignores_budget_pool_and_avoids_duplicate_call(self):
        from test_session4 import case,fact
        c,fs,refs,b=case();at=b[-1].end
        q=Query('SYNTHETIC_SOURCE','formula_evaluate',c.native_symbol,c.venue,c.timeframe,c.window_start,c.cutoff,
            'MISSING_TEST','BOOLEAN','targeted',1,1,100,True,True,True,True)
        other=replace(q,pool='watch',quota=0,latency_ms=2)
        self.assertEqual(q.key,other.key)
        called=[]
        def answer(query):called.append(query.key);return fact('answer',True,'BOOLEAN',at,measurement='MISSING_TEST')
        planner=QueryPlanner();question=Question('MISSING_TEST',0,'BOOLEAN',('WATCH','RIVAL_REBUTTED'))
        first,plans=planner.investigate(c,[question],[q],{},as_of=at,adapters={(q.source_id,q.operation):answer})
        second,plans=planner.investigate(c,[question],[other],{},as_of=at,adapters={})
        self.assertEqual(len(called),1);self.assertEqual(plans[0]['status'],'CACHED');self.assertEqual(first,second)

    def test_nondecisive_query_is_skipped_and_no_unavailable_tool_runs(self):
        from test_session4 import case
        c,fs,refs,b=case();p=QueryPlanner()
        _,decisions=p.investigate(c,[Question('TRIVIA',0,'BOOLEAN',('WATCH',))],[],{},as_of=b[-1].end,adapters={})
        self.assertEqual(decisions[0]['status'],'STOP_NO_DECISION_CHANGING_QUERY')
        _,decisions=p.investigate(c,[Question('TRUE_PROFILE',0,'PROFILE',('PROXY_ONLY','TRUE_PROFILE_REBUTTED'))],[],{},as_of=b[-1].end,adapters={})
        self.assertEqual(decisions[0]['status'],'UNKNOWN');self.assertEqual(p.audit[-1]['reason'],'NO_QUALIFIED_SOURCE')

    def test_early_reference_stays_early_without_requiring_future_trigger(self):
        from test_session6a import flat,bars,ref,TICK
        b=bars([(100,105,95,100)]*159+[(100,100.2,99.8,100)]*20)
        r=ref(b,known=158,atr=2)
        from researcher.family_engine import compression_family
        h=compression_family(b,TICK,(r,));self.assertEqual(h['stage'],'EARLY')
        self.assertNotIn('FIRST_DISPLACEMENT',[e['kind'] for e in h['timeline']])

    def test_quote_units_fees_and_first_obstacle_changes_are_operational(self):
        from test_session4 import case
        c,f,refs,b=case();at=b[-1].end
        f['RESEARCH_PRICE']=replace(f['RESEARCH_PRICE'],units='USDT')
        self.assertEqual(review_card(c,f,refs,as_of=at)['room']['status'],'ROOM_UNKNOWN')
        c,f,refs,b=case();f['ROUND_TRIP_FEE_BPS']=replace(f['ROUND_TRIP_FEE_BPS'],value=D(10000))
        self.assertEqual(review_card(c,f,refs,as_of=b[-1].end)['economics']['status'],'ECONOMICS_UNFAVORABLE')
        f.pop('ROUND_TRIP_FEE_BPS')
        c=replace(c,evidence_ids=tuple(i for i in c.evidence_ids if i!='ROUND_TRIP_FEE_BPS'))
        self.assertEqual(review_card(c,f,refs,as_of=b[-1].end)['economics']['status'],'ECONOMICS_UNKNOWN')


class AuthenticAndSpecialist(unittest.TestCase):
    def test_all_14_retained_histories_enter_interpretation_with_original_hashes(self):
        proof=json.loads((ROOT/'evidence/external-first/session55/causal-qualification.json').read_text())
        meta=json.loads((ROOT/'evidence/external-first/session5/core-qualification.json').read_text())
        members={r['native_symbol']:Instrument(**{**r,'tick_size':D(r['tick_size'])}) for r in meta['inventory']['selected_instruments']}
        count=cards_seen=0
        for s in proof['selected_samples']:
            bars=decode_bars(s['bars']);n=bars[0].native_symbol;tf=bars[0].timeframe;at=s['source']['receipt']['received_at_utc']
            refs=swing_references(bars,members[n].tick_size,as_of=at)
            bundle=analyze_selected(bars,members[n].tick_size,cutoff=bars[-1].end,as_of=at,references=refs)
            facts={b.id:Fact(b.id,members[n],'SELECTED_CLOSED_BAR',{'close':b.close},'USDT_PER_BASE',tf,
                b.end,b.end,b.received_at,b.received_at,'OFFICIAL_RETAINED',b.source_hash,'EXACT_REPORTED',
                True,'QUALIFIED','AUTHENTIC_REPLAY',300*WIDTHS[tf]) for b in bars}
            cards,new_refs,_=formation_cards(bundle,members[n],facts,cutoff=bars[-1].end,as_of=at,mode='AUTHENTIC_REPLAY')
            for c in cards:
                result=review_card(c,facts,[*refs,*new_refs],as_of=at)
                self.assertNotIn(result['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'})
                self.assertTrue(all(f.response_hash in {b.source_hash for b in bars} for f in facts.values() if f.measurement=='SELECTED_CLOSED_BAR'))
            cards_seen+=len(cards);count+=1
        self.assertEqual(count,14);self.assertGreater(cards_seen,0)

    def test_genuine_retained_specialist_can_nominate_independently_without_price_route(self):
        proof=json.loads((ROOT/'evidence/external-first/session55/economic-qualification.json').read_text())
        row=next(o for o in proof['observations'] if 'depth' in o)
        snapshot=copy.deepcopy(row['depth'])
        snapshot['levels']={k:[(D(p),D(q)) for p,q in rows] for k,rows in snapshot['levels'].items()}
        instrument=Instrument(**{**row['instrument'],'tick_size':D(row['instrument']['tick_size'])})
        start=(utc(snapshot['time'])-timedelta(seconds=1)).isoformat();at=snapshot['received']
        e=SpecialistEnvelope(instrument.native_symbol,'BINANCE_USDM','LINEAR_USDT_PERPETUAL','DISPLAYED_NATIVE_BASE',
            start,snapshot['time'],snapshot['time'],at,at,snapshot['source_hash'],'COMPLETE','AUTHENTIC_REPLAY',{'snapshot':snapshot})
        cert={'mode':'AUTHENTIC_REPLAY','venue':'BINANCE_USDM','authorized_read_only':True,'rights_verified':True,
            'oracle_receipt_hash':snapshot['source_hash'],'source_id':'RETAINED_NATIVE_DEPTH','exact_contracts':[instrument.native_symbol],
            'timeframes':['1h'],'families':['F6'],'methods':['M25'],'packs':[],'formation_causality_verified':True,
            'valid_from':start,'valid_until':(utc(at)+timedelta(seconds=60)).isoformat()}
        nominee={'envelope':e,'source_id':'RETAINED_NATIVE_DEPTH','method_id':'M25','family':'F6','timeframe':'1h',
            'question':'Does this displayed-liquidity boundary persist? Snapshot does not establish absorption.'}
        sources=ResearchSources(mode='AUTHENTIC_REPLAY',certificates=[cert],nominations=[nominee])
        accepted,faults=sources.independent(as_of=at,eligible={instrument.native_symbol:instrument})
        self.assertEqual(faults,[]);self.assertEqual(accepted[0]['routes'],['B_SPECIALIST'])
        self.assertTrue(accepted[0]['vendor_score_is_not_certification'])
        denied=ResearchSources(mode='AUTHENTIC_REPLAY',nominations=[nominee])
        self.assertEqual(denied.independent(as_of=at,eligible={instrument.native_symbol:instrument})[0],[])

    def test_partial_or_candle_proxy_specialist_cannot_gain_authority(self):
        from test_session6a import tape
        t=tape();e=SpecialistEnvelope(t.native_symbol,t.venue,t.contract_type,'EXECUTED_BASE',t.start,t.end,t.end,
            t.end,t.end,t.source_hash,'PARTIAL','SYNTHETIC',{'tape':t,'width':D(1)})
        api,client,sources,at,_=synthetic_6b()
        cert={**sources.certificates[0],'exact_contracts':[t.native_symbol],'methods':['M17'],'families':['F6'],
            'valid_from':t.start,'valid_until':iso_seconds(int(utc(t.end).timestamp())+3600)}
        s=ResearchSources(mode='SYNTHETIC',certificates=[cert],nominations=[{'envelope':e,'source_id':cert['source_id'],
            'method_id':'M17','family':'F6','timeframe':'1h','question':'True complete profile?'}])
        accepted,faults=s.independent(as_of=t.end,eligible={t.native_symbol:api.instruments[0]})
        self.assertEqual(accepted,[]);self.assertTrue(faults)
        from researcher.method_engine import analyze_specialist_envelope
        complete=replace(e,coverage='COMPLETE',payload={'tape':t})
        self.assertEqual(analyze_specialist_envelope('M21',complete,as_of=t.end)['status'],'COMPUTED')
        with self.assertRaisesRegex(ContractError,'SPECIALIST_ENVELOPE_SCOPE_OR_TIME'):
            analyze_specialist_envelope('M21',replace(complete,mode='AUTHENTIC_REPLAY'),as_of=t.end)
        # A declared sampled forced-execution feed can initiate a bounded
        # question; it never becomes complete liquidation-market coverage.
        payload={'rows':[{'native_symbol':t.native_symbol,'venue':t.venue,'id':'SYNTHETIC_FORCED_1',
            'at':t.start,'kind':'OBSERVED_FORCED_EXECUTION','price':D(100),'base':D(1)}],
            'native_symbol':t.native_symbol,'venue':t.venue,'start':t.start,'end':t.end,
            'coverage':'SAMPLED','source_hash':t.source_hash}
        sampled=replace(e,units='OBSERVED_FORCED_BASE',coverage='SAMPLED',payload=payload)
        cert={**cert,'methods':['M28'],'families':['F9']}
        src=ResearchSources(mode='SYNTHETIC',certificates=[cert],nominations=[{'envelope':sampled,
            'source_id':cert['source_id'],'method_id':'M28','family':'F9','timeframe':'1h','question':'Did witnessed forced executions coincide with a price shock?'}])
        accepted,faults=src.independent(as_of=t.end,eligible={t.native_symbol:replace(api.instruments[0],native_symbol=t.native_symbol)})
        self.assertFalse(faults);self.assertTrue(accepted)
        observed=src.normalized_inputs[t.native_symbol,'1h']['observed_liquidation']
        self.assertEqual(observed['coverage'],'SAMPLED');self.assertIsNone(observed['market_total_estimate'])

    def test_complete_covered_gap_and_incomplete_interval_are_distinct(self):
        api,client,sources,at,_=synthetic_6b();bars=api.samples['CONTROLUSDT','1h'][0][-10:]
        gap={'scope':'WATCH:sample','timeframe':'1h','symbols':['CONTROLUSDT'],
            'after':bars[0].end,'before_current':bars[-1].end}
        sources.gap_histories=({'mode':'SYNTHETIC','timeframe':'1h','bars':bars},)
        self.assertTrue(sources.covered_gap(gap))
        sources.gap_histories=({'mode':'SYNTHETIC','timeframe':'1h','bars':bars[1:]},)
        self.assertFalse(sources.covered_gap(gap))


class FullPipelineVariants(unittest.TestCase):
    def run_control(self,*,mutate=None,**options):
        api,client,sources,at,_=synthetic_6b()
        if mutate:mutate(api,sources,at)
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
            return scan_market_research(api=api,client=client,sources=sources,clock=lambda:at,
                mode='SYNTHETIC',ledger_path=Path(tmp)/'r.sqlite',**options)

    def test_A_only_and_C_only_reach_positive_admission(self):
        for route in ('A','C'):
            r=self.run_control(route_ablation=[route])
            self.assertTrue(r['shortlist'],r['source_faults'])
            self.assertTrue(all(o.startswith(route+'_') for c in r['shortlist'] for o in c['origins']))
            self.assertTrue(all(x[0]==route for n in r['nominations'] for x in n['routes']))

    def specialist(self,api,sources,at):
        from researcher.economic_sources import depth_snapshot
        i=next(i for i in api.instruments if i.native_symbol=='CONTROLUSDT')
        snap=depth_snapshot(api,i)
        start=(utc(at)-timedelta(seconds=1)).isoformat()
        envelope=SpecialistEnvelope(i.native_symbol,i.venue,'LINEAR_USDT_PERPETUAL','DISPLAYED_NATIVE_BASE',
            start,at,at,at,at,snap['source_hash'],'COMPLETE','SYNTHETIC',{'snapshot':snap})
        sources.certificates=({**sources.certificates[0],'methods':['M25']},)
        sources.nominations=({'envelope':envelope,'source_id':'SYNTHETIC_6B','method_id':'M25','family':'F4',
            'timeframe':'1h','question':'Does the observed displayed boundary support a sourceable current sweep investigation?'},)

    def test_B_only_strict_declared_specialist_reaches_investigation_and_admission(self):
        r=self.run_control(mutate=self.specialist,route_ablation=['B'])
        self.assertTrue(r['shortlist'],r['source_faults'])
        self.assertTrue(all(c['origins']==('B_SPECIALIST',) for c in r['shortlist']))
        self.assertTrue(all('M25' in c['method_ids'] for c in r['shortlist']))
        self.assertGreater(r['route_coverage']['B']['evaluated'],0)

    def test_union_retains_A_B_C_initiators_without_global_AND(self):
        r=self.run_control(mutate=self.specialist)
        c=next(c for c in r['shortlist'] if c['reference']['timeframe']=='1h')
        self.assertEqual({o[0] for o in c['origins']},{'A','B','C'})
        self.assertEqual(len({n['native_symbol']+n['timeframe'] for n in r['nominations']}),len(r['nominations']))

    def test_neutral_and_context_order_keep_identical_alt_nominations_and_allowance(self):
        a=self.run_control(context_prioritized=False);b=self.run_control(context_prioritized=True)
        self.assertEqual(a['nominations'],b['nominations'])
        self.assertEqual(a['context_questions']['verification_allowance'],b['context_questions']['verification_allowance'])
        self.assertEqual(a['costs']['targeted_kline_calls'],b['costs']['targeted_kline_calls'])
        self.assertEqual([c['card_id'] for c in a['shortlist']],[c['card_id'] for c in b['shortlist']])

    def test_qualified_core_uses_actual_partition_engine_without_promoting_real_source(self):
        def qualify(api,sources,at):
            c={**sources.certificates[0],'exact_contracts':[i.native_symbol for i in api.instruments],
                'packs':['CORE_1H','CORE_15M']}
            sources.certificates=(c,)
        r=self.run_control(mutate=qualify)
        self.assertEqual(r['source_faults'],[])
        self.assertEqual(r['coverage']['full_core_evaluated'],3)
        self.assertTrue(r['resource_plan']['full_core_planned'])
        self.assertTrue(all(len(p['column_ids'])==12 and p['evaluated']==3 for p in r['packs']))
        self.assertFalse(r['coverage']['all_market_structurally_covered'])
        self.assertFalse(load_config()['session5']['full_core_enabled'])

    def test_stale_quote_blocks_all_admission_without_erasing_source_watch(self):
        def stale(api,sources,at):
            original=api.pulse
            def pulse(*args,**kwargs):
                rows=original(*args,**kwargs)
                for row in rows:
                    for o in row['observations']:
                        o['source_time_utc']=(utc(at)-timedelta(seconds=60)).isoformat()
                return rows
            api.pulse=pulse
        r=self.run_control(mutate=stale)
        self.assertEqual(r['shortlist'],[]);self.assertTrue(r['watches'])
        self.assertTrue(any('PREKNOWN_FIRST_OBSTACLE_AND_FRESH_PRICE' in m['missing_necessary_inputs'] for m in r['near_misses']))

    def test_source_clock_regression_blocks_ready_preserving_original_times(self):
        def skew(api,sources,at):
            original=api.inventory
            def inventory():return replace(original(),received_at_utc=(utc(at)+timedelta(seconds=6)).isoformat())
            api.inventory=inventory
        r=self.run_control(mutate=skew)
        self.assertEqual(r['shortlist'],[]);self.assertTrue(r['clock_anomalies'])
        self.assertEqual(r['time_integrity_status'],'CLOCK_UNCERTAINTY; NO_READY')

    def test_different_fees_or_no_native_depth_changes_admission(self):
        def no_depth(api,sources,at):
            api.http.request=lambda *a,**k:(_ for _ in ()).throw(ContractError('OFFLINE_SOURCE_UNAVAILABLE'))
        r=self.run_control(mutate=no_depth)
        self.assertEqual(r['shortlist'],[]);self.assertTrue(r['source_faults'])
        self.assertTrue(r['near_misses'])

    def test_realized_impact_and_personal_fee_are_never_invented(self):
        r=self.run_control()
        for c in r['shortlist']:
            self.assertEqual(c['economics']['scope'],'SOURCE_DECLARED_BOUNDS; EXECUTION_NOT_CERTIFIED')
            self.assertIsNone(c['independent_confirmation_count'])
            self.assertIn('UNKNOWN',c['economics']['price_arrival_within_horizon'])

    def test_offline_route_ablation_rejected_before_any_live_source(self):
        with self.assertRaisesRegex(ContractError,'OFFLINE_REPLAY_SCOPE'):
            scan_market_research(mode='LIVE',route_ablation=['A'])

    def test_ordinary_planner_resolves_real_room_question_and_reuses_equivalent_fact(self):
        called=[]
        def prepare(api,sources,at):
            original=api.pulse
            def pulse(*args,**kwargs):
                rows=original(*args,**kwargs)
                for row in rows:
                    if row['kind']=='book':row['observations']=[]
                return rows
            api.pulse=pulse
            sources.certificates=({**sources.certificates[0],'operations':['binance_book'],
                'facts':{'RESEARCH_PRICE':'USDT_PER_BASE'}},)
            q=Query('SYNTHETIC_6B','binance_book','CONTROLUSDT','BINANCE_USDM','CURRENT',
                (utc(at)-timedelta(seconds=30)).isoformat(),at,'RESEARCH_PRICE','USDT_PER_BASE','targeted',1,1,100,
                True,True,True,True)
            i=next(i for i in api.instruments if i.native_symbol=='CONTROLUSDT')
            def answer(query):
                called.append(query.key)
                return Fact(fact_id(query.key,'answer'),i,'RESEARCH_PRICE',api.prices[i.native_symbol],
                    'USDT_PER_BASE','CURRENT',at,at,at,at,'SYNTHETIC_6B',digest(encode(api.prices).encode()),
                    'EXACT_REPORTED',True,'QUALIFIED','SYNTHETIC',30)
            sources.queries=(q,);sources.adapters={(q.source_id,q.operation):answer}
        r=self.run_control(mutate=prepare)
        answered=[p for p in r['planner'] if p['status'] in {'QUERY','CACHED'}]
        self.assertEqual(len(called),1);self.assertTrue(answered)
        self.assertTrue(any(p['rival_or_admission_changed'] for p in answered))
        self.assertTrue(any(p['status']=='CACHED' for p in answered))
        self.assertEqual(r['source_faults'],[])

    def test_source_backed_rising_btc_does_not_veto_bearish_alt_and_opposite_case(self):
        def market(bias,mirror=False,eth_bias=None):
            def prepare(api,sources,at):
                for (n,tf),(bars,source) in list(api.samples.items()):
                    if n=='CONTROLUSDT' and mirror:
                        series=[replace(b,open=200-b.open,high=200-b.low,low=200-b.high,close=200-b.close,
                            quote_volume=(200-b.close)*1000,buy_quote=(200-b.close)*500) for b in bars]
                    elif n in {'BTCUSDT','ETHUSDT'}:
                        slope=D(str(eth_bias if n=='ETHUSDT' and eth_bias is not None else bias))
                        wave=[0,1,2,3,2,1,0,-1,-2,-3,-2,-1]
                        series=[]
                        for j,b in enumerate(bars):
                            p=D(100)+slope*j+D(wave[j%len(wave)])
                            series.append(replace(b,open=p,close=p,high=p+1,low=p-1,
                                quote_volume=p*1000,buy_quote=p*500))
                    else:continue
                    hashed=digest(encode(series).encode())
                    source={**source,'source_response_sha256':hashed,
                        'receipt':{**source['receipt'],'response_sha256':hashed}}
                    api.samples[n,tf]=(series,source)
                    if tf=='1h':api.prices[n]=series[-1].close
            return prepare
        for slope,mirror,side in (('.05',False,'BEARISH'),('-.05',True,'BULLISH')):
            r=self.run_control(mutate=market(slope,mirror))
            self.assertTrue(any(c['side_hypothesis']==side for c in r['shortlist']),r['source_faults'])
            labels=next(c['value']['labels'] for c in r['context']['claims'] if c['name']=='BTCUSDT_1h')
            self.assertIn('TREND_UP' if slope=='.05' else 'TREND_DOWN',labels)
        mixed=self.run_control(mutate=market('.05',False,'-.05'))
        self.assertTrue(next(c['value'] for c in mixed['context']['claims'] if c['name']=='BTC_ETH_DISAGREEMENT'))
        self.assertTrue(mixed['shortlist'])


if __name__=='__main__':unittest.main()
