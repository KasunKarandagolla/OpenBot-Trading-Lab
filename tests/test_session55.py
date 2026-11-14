"""Authentic selected oracles plus labeled simulated chronology/fault cases."""
import copy
from dataclasses import replace,asdict
from decimal import Decimal as D
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from researcher.contracts import ContractError,encode,digest,utc
from researcher.settings import ROOT,load_config,validate_config
from researcher.remote_structure import DETECTORS,BITS,Detector,oracle_masks,reduction_expression,registered,manifest
from researcher.economic_sources import normalize_depth,book_cost
from researcher.audit import allocate
from researcher.handoff import validate_consultation,consult_changed_cards,make_export,replay_export
from researcher.candidate_review import review_card,shortlist
from researcher.numerics import Bar
from researcher.transport import PublicHTTP,ProviderError
from test_session4 import case

FIELDS={'open','high','low','close','base_volume','quote_volume','buy_base','buy_quote'}


def bars(raw):return [Bar(**{k:D(v) if k in FIELDS else v for k,v in b.items()}) for b in raw]


class AuthenticCausalOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof=json.loads((ROOT/'evidence/external-first/session55/causal-qualification.json').read_text())

    def test_480_live_tail_values_recompute_from_exact_native_closed_prefixes(self):
        samples={(s['source']['native_symbol'],s['source']['timeframe']):bars(s['bars'])[-299:]
            for s in self.proof['selected_samples'][:10]}
        count=positive=0
        for c in self.proof['tail_checks']:
            source=samples[c['symbol'],c['timeframe']];by={b.open_ms//1000:i for i,b in enumerate(source)}
            identity=c['provider_identity']
            self.assertEqual((identity['exchange'],identity['market'],identity['symbol'],identity['timeframe'],identity['bars']),
                ('binance','futures',c['symbol'],c['timeframe'],len(source)))
            for r in c['rows']:
                expected=oracle_masks(source[:by[r['time']]+1])[c['column']]
                self.assertEqual(D(str(r['actual'])) if r['actual'] is not None else None,expected)
                count+=1;positive+=bool(expected)
        self.assertEqual(count,480);self.assertGreater(positive,0)

    def test_all_five_historical_positive_directions_are_real_reductions(self):
        self.assertEqual({c['family'] for c in self.proof['positive_checks']},
            {'F2_LOWER','F4_UPPER','F4_LOWER','F5_UPPER','F5_LOWER'})
        for c in self.proof['positive_checks']:
            sample=next(s for s in self.proof['selected_samples'][10:] if
                s['source']['native_symbol']==c['symbol'] and s['source']['timeframe']==c['timeframe'])
            source=bars(sample['bars'])[-299:];expected=oracle_masks(source[:-c['offset']])[c['column']]
            self.assertEqual(D(str(c['actual'])),expected);self.assertTrue(expected)
        self.assertEqual(self.proof['unqualified_bits'],{'1':'NO_AUTHENTIC_REMOTE_F2_UPPER_POSITIVE_YET'})

    def test_unicode_screens_succeed_while_targeted_tool_remains_unknown(self):
        checks=[c for c in self.proof['screen_checks'] if c['symbol']=='我踏马来了USDT']
        self.assertEqual(len(checks),6);self.assertTrue(all(c['passed'] for c in checks))
        self.assertEqual(len([f for f in self.proof['failures'] if f.get('symbol')=='我踏马来了USDT' and f['code']=='MCP_TOOL_ERROR']),2)

    def test_qualification_cannot_be_enabled_by_changing_manifest_or_evidence(self):
        c=load_config();c['session55']['qualified_bits'].append(1)
        with self.assertRaises(ContractError):validate_config(c)
        c=load_config();c['session55']['qualification_sha256']='bad'
        with self.assertRaises(ContractError):validate_config(c)

    def test_future_append_does_not_rewrite_a_frozen_historical_prefix(self):
        source=bars(self.proof['selected_samples'][3]['bars']);prefix=source[:200]
        before=oracle_masks(prefix);frozen_end=prefix[-1].end
        self.assertEqual(before,oracle_masks([b for b in source if utc(b.end)<=utc(frozen_end)]))

    def test_missing_bars_and_wrong_contract_are_rejected(self):
        source=bars(self.proof['selected_samples'][0]['bars'])
        for malformed in (source[:50]+source[51:],source[:-1]+[replace(source[-1],native_symbol='WRONGUSDT')]):
            with self.assertRaises(ContractError):oracle_masks(malformed)


class RestrictedCompiler(unittest.TestCase):
    def test_compiler_accepts_only_finite_registered_ast_and_bounded_reductions(self):
        for bad in (0,9,200,'8',True):
            with self.assertRaises(ContractError):Detector(bad)
        for bad in (-1,261,'8',True):
            with self.assertRaises(ContractError):reduction_expression('boundary_8',bad)
        self.assertFalse(registered('close; send_order()'))
        self.assertTrue(registered(reduction_expression('boundary_8',158)))

    def test_no_zero_offset_or_rejected_native_atr_and_manifest_has_dependencies(self):
        for detector in DETECTORS.values():
            self.assertNotIn('[0]',detector.expression);self.assertNotIn('atr(14)',detector.expression)
        self.assertEqual(len(manifest()['columns']),3);self.assertTrue(manifest()['dependencies'])

    def sample(self,family):
        # SIMULATED OHLC chronology, independent hand-constructed event cases.
        c,_,_,source=case();base=source[0]
        from researcher.observations import iso_seconds
        result=[replace(base,open_ms=base.open_ms+j*3600000,open=D(100),high=D(101),low=D(99),close=D(100),
            received_at=iso_seconds(base.open_ms//1000+(j+1)*3600),available_at=iso_seconds(base.open_ms//1000+(j+1)*3600)) for j in range(80)]
        def setbar(age,o,h,l,c):result[-1-age]=replace(result[-1-age],open=D(o),high=D(h),low=D(l),close=D(c))
        setbar(8,104,105,103,104)
        if family=='F2':
            setbar(5,104,105,104,104);setbar(4,100,101,99,100);setbar(3,104,105,104,104)
        elif family=='F4':
            setbar(3,105,107,104,106);setbar(2,104,104,102,103);setbar(1,103,103,101,102);setbar(0,102,102,100,101)
        elif family=='F5':
            setbar(5,105,107,104,106);setbar(4,104,104,102,103);setbar(3,103,103,101,102)
        if family in {'F2','F5'}:
            setbar(2,106,108,106,107);setbar(1,107,109,107,108);setbar(0,108,110,108,109)
        return result

    def test_distinct_pressure_break_and_later_acceptance_is_f2_without_f5(self):
        source=self.sample('F2');mask=int(oracle_masks(source)['boundary_8'])
        self.assertTrue(mask&1);self.assertFalse(mask&16)
        source[-2]=replace(source[-2],open=D(104),high=D(105),low=D(103),close=D(104))
        self.assertFalse(int(oracle_masks(source)['boundary_8'])&1)

    def test_f4_and_f5_require_ordered_reclaim_and_actual_opposing_close_progress(self):
        self.assertTrue(int(oracle_masks(self.sample('F4'))['boundary_8'])&4)
        source=self.sample('F5');self.assertTrue(int(oracle_masks(source)['boundary_8'])&16)
        source[-5]=replace(source[-5],open=D(106),low=D(106),high=D(108),close=D(107))
        self.assertFalse(int(oracle_masks(source)['boundary_8'])&16)

    def test_zero_atr_short_history_and_tied_pivots_have_no_false_positive(self):
        source=self.sample('F2')
        self.assertTrue(all(v is None for v in oracle_masks(source[:10]).values()))
        flat=[replace(b,open=D(100),high=D(100),low=D(100),close=D(100)) for b in source]
        self.assertEqual(set(oracle_masks(flat).values()),{D(0)})
        source[-10]=replace(source[-10],high=D(105))
        self.assertFalse(int(oracle_masks(source)['boundary_8'])&1)


class EconomicsAndAdmission(unittest.TestCase):
    def test_authentic_native_depth_walk_and_oi_preserve_units(self):
        proof=json.loads((ROOT/'evidence/external-first/session55/economic-qualification.json').read_text())
        self.assertEqual(proof['failures'],[])
        for o in proof['observations']:
            if 'cost' in o:
                self.assertEqual(o['cost']['status'],'OBSERVED')
                self.assertGreaterEqual(D(o['cost']['round_trip_book_walk_bps']),D(o['cost']['spread_bps']))
            else:
                oi=o['oi'];self.assertEqual(len(oi['times_ms']),12)
                self.assertEqual(D(oi['native_oi'][-1])/D(oi['native_oi'][0])-1,D(oi['native_change_fraction']))

    def test_assumed_fees_can_only_emit_conditional_handoff(self):
        c,f,refs,b=case()
        f={k:replace(v,source_id='DECLARED_RESEARCH_SCENARIO:documented') if v.measurement=='ROUND_TRIP_FEE_BPS' else v for k,v in f.items()}
        r=review_card(c,f,refs,as_of=b[-1].end)
        self.assertEqual(r['stage'],'CONDITIONAL_FOR_DEEP');self.assertTrue(r['economics']['assumption_evidence_ids'])
        self.assertEqual(len(shortlist([r],coverage={})['shortlist']),1)

    def test_cold_historical_origin_receipt_never_claims_prospective_ready(self):
        c,f,refs,b=case()
        f={k:replace(v,available_at=b[-1].end,received_at=b[-1].end) if v.measurement=='DECISION_PRICE' else v for k,v in f.items()}
        r=review_card(c,f,refs,as_of=b[-1].end)
        self.assertEqual(r['room']['reason'],'DECISION_PRICE_NOT_PREKNOWN')
        self.assertNotIn(r['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'})

    def test_nearest_consumed_obstacle_is_not_skipped_after_price_returns(self):
        from researcher.research import Fact,fact_id
        c,f,refs,b=case();at=b[-1].end
        obstacle=refs[1];fid=fact_id('consumed')
        exemplar=next(iter(f.values()))
        f[fid]=replace(exemplar,id=fid,measurement='OBSTACLE_LIFECYCLE',units='REFERENCE_STATE',
            value={'reference_id':obstacle.id,'after':c.window_start,'consumed':True},window_end=c.cutoff,
            known_at=at,available_at=at,received_at=at,max_age_seconds=86400)
        c=replace(c,evidence_ids=(*c.evidence_ids,fid))
        r=review_card(c,f,refs,as_of=at);self.assertEqual(r['stage'],'LATE')
        self.assertEqual(r['room']['first_obstacle_id'],obstacle.id)

    def test_new_endpoints_reject_extra_parameters_and_mutating_operations(self):
        h=PublicHTTP()
        for endpoint,query in (('binance_depth',{'symbol':'BTCUSDT','limit':100,'account':'bad'}),
                ('binance_oi_history',{'symbol':'BTCUSDT','period':'1h','limit':12})):
            with self.assertRaises(ProviderError):h.request(endpoint,query=query)
        with self.assertRaises(ProviderError):h.request('binance_order',query={})


class AllocationAndExport(unittest.TestCase):
    def nominees(self):
        return [{'native_symbol':n+'USDT','timeframe':tf,'families':['F2'], 'routes':[route]}
            for n,route in [('A','A_REMOTE_CAUSAL'),('Q','C_QUIET'),('W','C_SAVED_WATCH'),('R','C_STRATIFIED_AUDIT')]
            for tf in ('1h','15m')]

    def test_causal_lane_cannot_be_starved_by_duplicate_watch_and_quiet_questions(self):
        chosen,receipts,study=allocate(self.nominees(),SimpleNamespace(agenda=['F4']),{'15m':'2026-01-20T12:00:00+00:00'})
        self.assertIn('AUSDT',chosen);self.assertEqual(len(chosen),2)
        self.assertEqual(study['unique_nominated_symbols'],4);self.assertEqual(study['raw_symbol_timeframe_questions'],8)
        self.assertEqual(len(study['neutral']),len(study['context']))

    def test_rotating_protected_lanes_and_btc_context_do_not_delete_questions(self):
        pools=set()
        for minute in ('00','15','30'):
            for agenda in (['F4'],['F2'],[]):
                c,r,s=allocate(self.nominees(),SimpleNamespace(agenda=agenda),{'15m':f'2026-01-20T12:{minute}:00+00:00'})
                pools.update(x['pool'] for x in r);self.assertIn('AUSDT',c)
        self.assertEqual(pools,{'causal','quiet_contrary','watch','audit'})

    def test_consultant_is_disabled_and_rejects_fabricated_citations_or_query(self):
        self.assertEqual(consult_changed_cards([])['calls'],0)
        for reply in ({'evidence_ids':['fake'],'next_question':'FIRST_OBSTACLE'},
                {'evidence_ids':['real'],'next_question':'place_order'},
                {'evidence_ids':['real'],'next_question':'FIRST_OBSTACLE','target':1}):
            with self.assertRaises(ContractError):validate_consultation(reply,['real'])
        with self.assertRaises(ContractError):consult_changed_cards([],provider=object())

    def test_versioned_handoff_is_self_cited_replayable_and_decline_has_no_side_effects(self):
        c,f,refs,b=case();review=review_card(c,f,refs,as_of=b[-1].end)
        report={'mode':'SYNTHETIC','completed_at_utc':b[-1].end,'shortlist':[review]}
        before=encode(report);packet=make_export(report,[c],f,refs)
        self.assertEqual(packet['schema_version'],'openbot.research-handoff.v1')
        self.assertFalse(packet['order_authority']);self.assertEqual(packet['research_handoffs'][0]['decline_side_effects'],[])
        self.assertEqual(encode(report),before)
        cited=set(packet['research_handoffs'][0]['evidence']);self.assertTrue(set(c.evidence_ids)<=cited)
        replay=replay_export(json.loads(encode(packet)),as_of=b[-1].end)
        self.assertEqual(replay[0]['stage'],review['stage'])
        self.assertEqual(replay[0]['necessary_sequence_event_ids'],list(review['necessary_sequence_event_ids']))

    def test_handoff_hash_or_authority_tampering_is_rejected(self):
        c,f,refs,b=case();review=review_card(c,f,refs,as_of=b[-1].end)
        packet=make_export({'mode':'SYNTHETIC','completed_at_utc':b[-1].end,'shortlist':[review]},[c],f,refs)
        for key,value in (('order_authority',True),('payload_sha256','changed'),('execution_connection','live')):
            altered={**packet,key:value}
            with self.assertRaises(ContractError):replay_export(altered,as_of=b[-1].end)


class DeferredRecovery(unittest.TestCase):
    def test_distinct_transient_partitions_each_get_one_deferred_retry(self):
        from test_session2 import Source,response,metadata,provisional,pack,CUTOFF,budget
        from researcher.screening import PartitionEngine
        class Transient(Source):
            def __init__(self):super().__init__(lambda names,p:response(names));self.seen=set()
            def screen(self,names,p):
                if names not in self.seen:
                    self.seen.add(names);raise ProviderError('MCP_TOOL_ERROR',metadata())
                return super().screen(names,p)
        b=budget();r=PartitionEngine(Transient(),b,partition_size=1,deferred_tool_recovery=True).run(provisional(),pack(),CUTOFF)
        self.assertEqual(len(r['evaluated_symbols']),2);self.assertEqual(b.retries,2)
        self.assertEqual(len(r['attempts']),4);self.assertEqual(len(r['failed_symbols']),0)

    def test_persistent_source_fault_remains_unknown_with_original_attempts(self):
        from test_session2 import Source,metadata,provisional,pack,CUTOFF,budget
        from researcher.screening import PartitionEngine
        class Failure(Source):
            def screen(self,names,p):raise ProviderError('MCP_TOOL_ERROR',metadata())
        b=budget();r=PartitionEngine(Failure(lambda *_:None),b,partition_size=1,deferred_tool_recovery=True).run(provisional(),pack(),CUTOFF)
        self.assertEqual(len(r['failed_symbols']),2);self.assertEqual(r['evaluated_symbols'],[])
        self.assertFalse(r['zero_opportunities_established']);self.assertEqual(b.retries,2)

    def test_denial_is_not_deferred_or_retried(self):
        from test_session2 import Source,metadata,provisional,pack,CUTOFF,budget
        from researcher.screening import PartitionEngine
        class Denied(Source):
            def screen(self,names,p):raise ProviderError('HTTP_451',metadata())
        b=budget();r=PartitionEngine(Denied(lambda *_:None),b,partition_size=1,deferred_tool_recovery=True).run(provisional(),pack(),CUTOFF)
        self.assertEqual(b.retries,0);self.assertEqual(b.calls,1);self.assertFalse(r['evaluated_symbols'])


if __name__=='__main__':unittest.main()
