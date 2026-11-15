"""Operating regressions; controlled responses are explicitly not live proof."""
import copy
import json
import tempfile
import unittest
from decimal import Decimal as D
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from researcher.contracts import ContractError,utc,encode
from researcher.screening import PartitionEngine,RequestBudget
from researcher.candidate_review import (review_card,conditional_research,
    native_review_selection,apply_native_research_advice)
from researcher.agent_review import exchange
from researcher.numerics import validate_bars
from researcher.settings import ROOT
from researcher.handoff import make_export,decode_export
from researcher.transport import ProviderError
from test_session2 import Source,provisional,pack,response,metadata,CUTOFF
from test_session4 import case


class OperatingAcceptance(unittest.TestCase):
    def test_first_source_response_can_freeze_after_slow_start_but_later_cannot_move_it(self):
        names=('AUSDT','BUSDT','CUSDT')
        class Crosses(Source):
            def screen(self,names,spec):
                self.calls.append(names)
                data=response(names,spec.timeframe)
                advance=3600 if len(self.calls)<3 else 7200
                for r in data['results']:r['observationTime']+=advance
                return data,{**metadata(),'received_at_utc':'2026-11-13T07:17:00+00:00'}
        r=PartitionEngine(Crosses(),RequestBudget(3,retry_calls=0,interval_seconds=0),
            partition_size=1,transient_recovery=True,anchor_first_response=True).run(
                provisional(names),replace(pack(),supported_symbols=names),CUTOFF)
        self.assertEqual(utc(r['cutoff_utc']),utc(CUTOFF)+timedelta(hours=1))
        self.assertEqual(r['evaluated_symbols'],['AUSDT','BUSDT'])
        self.assertEqual(r['rejected_after_cutoff'],['CUSDT'])
        self.assertFalse(r['snapshot_anchor']['historical_asof_query_supported'])

    def test_provider_future_bar_never_anchors_a_snapshot(self):
        class Future(Source):
            def screen(self,names,spec):
                data=response(names,spec.timeframe)
                for r in data['results']:r['observationTime']+=3600
                return data,metadata()
        r=PartitionEngine(Future(),RequestBudget(1,retry_calls=0,interval_seconds=0),
            anchor_first_response=True).run(provisional(),pack(),CUTOFF)
        self.assertEqual(r['evaluated_symbols'],[])
        self.assertIsNone(r['snapshot_anchor']);self.assertEqual(r['cutoff_utc'],CUTOFF)

    def test_native_selection_uses_a_real_conditional_finalist(self):
        c,f,refs,b=case(qualification='TRIAL',current=100)
        r=review_card(c,f,refs,as_of=b[-1].end)
        ids,selection=native_review_selection([r],[c],f,refs,as_of=b[-1].end,max_cards=2)
        self.assertEqual(ids,[c.id]);self.assertEqual(selection['selected'][0]['relationship'],'PROVISIONAL_FINALIST')

    def test_explicit_finalist_order_survives_exchange_stage_and_hash_sort(self):
        a,fa,_,b=case(family='F4');z,fz,_,zb=case(family='F5',name='OTHERUSDT')
        mapping={i:'OTHER_'+i for i in fz if len(i)!=64}
        fz={mapping.get(i,i):replace(f,id=mapping.get(i,i)) for i,f in fz.items()}
        z=replace(z,evidence_ids=tuple(mapping.get(i,i) for i in z.evidence_ids))
        wanted=sorted([a.id,z.id],reverse=True)
        self.assertNotEqual(a.id,z.id)
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
            result=exchange(tmp,[a,z],{**fa,**fz},as_of=max(b[-1].end,zb[-1].end,key=utc),
                max_cards=1,ordered_card_ids=wanted)
            request=json.loads((Path(tmp)/result['request_file']).read_text())
        self.assertEqual(request['cards'][0]['card_id'],wanted[0])

    def test_native_decline_can_defer_research_but_expired_advice_cannot(self):
        c,f,refs,b=case(qualification='TRIAL',current=100)
        r=review_card(c,f,refs,as_of=b[-1].end)
        candidates,decisions=conditional_research([r],[c],f,refs,as_of=b[-1].end)
        advice={'status':'VALIDATED_ADVISORY_ONLY','request_created_at_utc':b[-1].end,'material_sha256':'a'*64,
            'reply':{'interpretations':[{'card_id':c.id,'priority':'DECLINE','interpretation':'NULL',
                'strongest_rival':'NULL','falsifying_question':'FIRST_OBSTACLE','supporting_evidence_ids':['seq'],
                'contradicting_ids':[],'missed_traps':[],'null_hypothesis':True}]}}
        picked,why,comparison=apply_native_research_advice(candidates,decisions,advice,as_of=b[-1].end)
        self.assertFalse(picked);self.assertEqual(why[-1]['disposition'],'DEFER_NATIVE_RIVAL_CHALLENGE')
        self.assertFalse(comparison['hard_gates_changed'])
        late=(utc(b[-1].end)+timedelta(seconds=601)).isoformat()
        picked,why,comparison=apply_native_research_advice(candidates,decisions,advice,as_of=late)
        self.assertEqual(len(picked),1);self.assertFalse(comparison['accepted_current_advice'])

    def test_cached_intrinsic_bar_validation_never_caches_cutoff_or_changed_prices(self):
        _,_,_,bars=case();validate_bars(bars);validate_bars(bars)
        with self.assertRaisesRegex(ContractError,'FUTURE_BAR'):
            validate_bars(bars,cutoff=bars[-2].end)
        malformed=[*bars[:-1],replace(bars[-1],high=bars[-1].low)]
        with self.assertRaisesRegex(ContractError,'OHLC_INCONSISTENT'):validate_bars(malformed)

    def test_export_hash_remains_valid_after_report_coverage_and_review_updates(self):
        c,f,refs,b=case();r=review_card(c,f,refs,as_of=b[-1].end)
        report={'shortlist':[r],'mode':'SYNTHETIC','completed_at_utc':b[-1].end,
            'coverage':{'source_observed':1},'method_coverage':{}}
        export=make_export(report,[c],f,refs)
        report['coverage']['new_field']=['later'];r['late_annotation']='changed'
        self.assertEqual(len(decode_export(export)),1)
        self.assertNotIn('new_field',export['capabilities'])

    def test_f5_reclaim_without_failed_reversal_stays_a_watch(self):
        c,f,refs,b=case(family='F5',qualification='TRIAL',current=100)
        # Keep the authentic controlled prefix through the reclaim; its label
        # alone must not establish the later F5 failure/continuation sequence.
        events=tuple(e for e in c.events if e['kind'] not in
            {'REBREAK_SAME_REFERENCE','FAILED_RECLAIM','LATER_HOLD','LATER_OUTSIDE_ACCEPTANCE'})
        ids={e['id'] for e in events};reclaim=next(e['id'] for e in events if e['kind']=='RECLAIM')
        hypotheses=tuple(replace(h,supporting_ids=(reclaim,) if h.family=='F5' else tuple(i for i in h.supporting_ids if i in ids),
            contradicting_ids=tuple(i for i in h.contradicting_ids if i in ids)) for h in c.hypotheses)
        c=replace(c,events=events,hypotheses=hypotheses)
        r=review_card(c,f,refs,as_of=b[-1].end)
        # Exercise the conditional-specific gate after independently isolating
        # this partial case; strict admission remains unchanged.
        r={**r,'stage':'DEVELOPING','historical_significance':'HIGH'}
        c=replace(c,hypotheses=tuple(replace(h,contradicting_ids=()) if h.family=='F5' else h for h in c.hypotheses))
        picked,why=conditional_research([r],[c],f,refs,as_of=b[-1].end)
        self.assertFalse(picked);self.assertIn('F5_FAILURE_NOT_OBSERVED',why[0]['disposition'])

    def test_unchanged_post_shock_recovery_does_not_refresh_an_old_directional_event(self):
        from test_session6a import flat,bars,START,TICK
        from researcher.family_engine import shock_family
        source=flat(40)+bars([(100,112,99,111)]+[(105,106,103,104)]*6,start=START+40*3600)
        state=shock_family(source,TICK,latest=True)
        kinds=[e['kind'] for e in state['timeline']]
        self.assertEqual(kinds.count('SHOCK_MIDPOINT_RECLAIM'),1)
        self.assertEqual(kinds.count('STABILIZATION_CANDIDATE'),1)
        self.assertEqual(state['details']['current_response'],'RECOVERY_AGAINST_SHOCK')

    def test_remote_time_slice_leaves_next_pack_budget_available(self):
        now=[0]
        class Slow(Source):
            def screen(self,names,spec):
                now[0]+=2
                return super().screen(names,spec)
        names=('AUSDT','BUSDT','CUSDT');source=Slow()
        budget=RequestBudget(2,retry_calls=0,interval_seconds=0,clock=lambda:now[0])
        engine=PartitionEngine(source,budget,partition_size=1,max_pack_seconds=1,transient_recovery=True)
        spec=replace(pack(),supported_symbols=names)
        first=engine.run(provisional(names),spec,CUTOFF);second=engine.run(provisional(names),spec,CUTOFF)
        self.assertEqual(first['evaluated_symbols'],['AUSDT']);self.assertEqual(second['evaluated_symbols'],['AUSDT'])
        self.assertEqual(len(source.calls),2);self.assertIsNone(budget.stopped_reason)
        self.assertEqual(set(first['deferred_symbols']),{'BUSDT','CUSDT'})

    def test_broad_subset_order_includes_quiet_tail_and_never_drops_an_eligible_coin(self):
        from researcher.audit import broad_order
        names=[f'ALT{j}USDT' for j in range(100)]
        ticks={n:{'values':{'quoteVolume':j+1}} for j,n in enumerate(names)}
        order,proof=broad_order(names,ticks,CUTOFF)
        self.assertEqual(set(order),set(names));self.assertEqual(len(order),100)
        self.assertEqual(proof['excluded_by_liquidity'],0)
        for group in range(4):self.assertEqual(sum(n in names[group*25:(group+1)*25] for n in order[:20]),5)

    def test_slow_optional_depth_refreshes_quote_and_cannot_poison_every_watch(self):
        from researcher.admission_facts import refresh_selected
        c,f,refs,b=case(current=100)
        at=b[-1].end;later=(utc(at)+timedelta(seconds=40)).isoformat()
        def book(stamp):return {'native_symbol':c.native_symbol,'values':{'bid':D(100),'ask':D('100.1'),'spread_bps':D(2)},
            'source_time_utc':stamp,'received_at_utc':stamp,'source_response_sha256':stamp}
        pulses=iter([[{'kind':'book','observations':[book(at)]}],[{'kind':'book','observations':[book(later)]}]])
        api=SimpleNamespace(pulse=lambda *a,**kw:next(pulses))
        old_depth={'native_symbol':c.native_symbol,'time':at,'received':at,'source_hash':'old'}
        with patch('researcher.economic_sources.depth_snapshot',return_value=old_depth):
            cards,depths,faults,asof=refresh_selected([c],f,refs,api,
                SimpleNamespace(instruments=[next(iter(f.values())).instrument]),{},clock=lambda:later,max_depth=1)
        review=review_card(cards[0],f,refs,as_of=asof)
        self.assertNotEqual(review['stage'],'UNKNOWN')
        self.assertTrue(any(x['code']=='CURRENT_DEPTH_EXPIRED_DURING_COLLECTION' for x in faults))
        self.assertNotIn(review['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'})

    def test_inventory_retries_one_transport_failure_and_never_a_denial(self):
        from researcher.binance import OfficialResearchAPI
        with patch('researcher.binance.OfficialBinanceInventory') as source:
            source.return_value.load.side_effect=[ProviderError('NETWORK_OR_TLS_FAILURE'),'snapshot']
            self.assertEqual(OfficialResearchAPI().inventory(),'snapshot')
            self.assertEqual(source.return_value.load.call_count,2)
        with patch('researcher.binance.OfficialBinanceInventory') as source:
            source.return_value.load.side_effect=ProviderError('HTTP_451')
            with self.assertRaisesRegex(ProviderError,'HTTP_451'):OfficialResearchAPI().inventory()
            self.assertEqual(source.return_value.load.call_count,1)

    def test_m16_uses_the_measured_f6_balance_instead_of_an_unrelated_empty_default(self):
        from test_session6a import FamilyChronologyOracles,TICK
        from researcher.family_engine import evaluate_families
        from researcher.method_engine import evaluate_methods
        bars=FamilyChronologyOracles().balance_sample();at=bars[-1].end
        families=evaluate_families(bars,TICK,cutoff=at,as_of=at,current_episodes=True)
        known={h['reference_id'] for h in families if h['family']=='F6' and h['reference']}
        self.assertTrue(known)
        with patch('researcher.method_engine.balance_references',return_value=()):
            methods=evaluate_methods(bars,TICK,cutoff=at,as_of=at,families=families)
        auction=next(m for m in methods if m['method_id']=='M16')
        self.assertEqual({h['reference_id'] for h in auction['value']['price_only_branches']},known)
        self.assertIsNone(auction['value']['true_value_migration'])

    def test_saved_conditional_results_and_watches_render_after_json_decimal_roundtrip(self):
        from researcher.discovery import research_summary,watch_summary
        from researcher.candidate_review import active_coin_watches
        c,f,refs,b=case(qualification='TRIAL',current=100);at=b[-1].end
        review=review_card(c,f,refs,as_of=at)
        candidates,_=conditional_research([review],[c],f,refs,as_of=at)
        report={'release_status':'PARTIAL','mode':'SYNTHETIC','coverage':{'eligible_contracts':1},
            'shortlist':[],'conditional_research_candidates':candidates,'packs':[],'watches':[],
            'near_misses':[],'invalidations':[],'not_reviewed_budget':[],'time_gaps':[],
            'active_coin_watchlist':active_coin_watches([review],as_of=at),'completed_at_utc':at,
            'source_faults':[],'costs':{'http_requests':0,'response_bytes':0,'wall_ms':1}}
        saved=json.loads(encode(report))
        self.assertIn(c.native_symbol,research_summary(saved))
        self.assertIn(c.native_symbol,watch_summary(saved))

    def test_missing_nearest_obstacle_history_cannot_substitute_a_farther_target(self):
        c,f,refs,b=case(qualification='TRIAL',current=100)
        near=replace(refs[1],lo=D(105),hi=D(105),origin='NEAREST_OLD_REFERENCE',source_ids=('old-raw-outside-window',))
        review=review_card(c,f,[*refs,near],as_of=b[-1].end)
        self.assertEqual(review['room']['status'],'ROOM_UNKNOWN')
        self.assertEqual(review['room']['first_obstacle_id'],near.id)
        picked,why=conditional_research([review],[c],f,[*refs,near],as_of=b[-1].end)
        self.assertTrue(picked,why)
        self.assertEqual(picked[0]['research_room']['first_obstacle_id'],near.id)
        self.assertEqual(picked[0]['research_room']['status'],'ROOM_UNKNOWN')
        self.assertIn('OUTSIDE_SELECTED_HISTORY',picked[0]['research_room']['reason'])

    def test_changed_analyzer_revision_invalidates_a_same_cutoff_cache(self):
        from test_session5 import FakeAPI,FakeClient,fake_pack,AT
        from researcher.discovery import scan_market_research
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp,patch('researcher.screening.PartitionEngine.run',fake_pack):
            path=Path(tmp)/'version.sqlite'
            with patch('researcher.discovery.implementation_revision',return_value='a'*64):
                scan_market_research(api=FakeAPI(),client=FakeClient(),clock=lambda:AT,ledger_path=path)
            api=FakeAPI();client=FakeClient()
            with patch('researcher.discovery.implementation_revision',return_value='b'*64):
                report=scan_market_research(api=api,client=client,clock=lambda:AT,ledger_path=path)
        self.assertFalse(report['costs']['cached_snapshot_reused'])
        self.assertGreater(api.sample_calls,0);self.assertEqual(client.connections,1)

    def test_a_stale_provider_cannot_move_a_restart_behind_its_prior_snapshot(self):
        cutoff=(utc(CUTOFF)+timedelta(hours=1)).isoformat()
        r=PartitionEngine(Source(),RequestBudget(1,retry_calls=0,interval_seconds=0),
            anchor_first_response=True,minimum_anchor_cutoff=cutoff).run(provisional(),pack(),cutoff)
        self.assertEqual(r['cutoff_utc'],cutoff);self.assertIsNone(r['snapshot_anchor'])
        self.assertEqual(r['evaluated_symbols'],[])


if __name__=='__main__':unittest.main()
