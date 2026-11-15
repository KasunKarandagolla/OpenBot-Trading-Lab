"""Recovery contracts; synthetic positives never qualify live methodology."""
import copy
import json
import unittest
import tempfile
from pathlib import Path
from dataclasses import replace
from decimal import Decimal as D
from types import SimpleNamespace
from unittest.mock import patch

from researcher.audit import investigate
from researcher.basis import BasisMCP
from researcher.candidate_review import review_card,conditional_research,active_coin_watches
from researcher.contracts import ContractError
from researcher.screening import PartitionEngine,RequestBudget
from researcher.transport import ProviderError,Response
from researcher.settings import load_config
from researcher.settings import ROOT
from researcher.admission_facts import attach
from researcher.method_registry import capability_coverage
from test_session2 import Source,provisional,pack,response,metadata,CUTOFF
from test_session4 import case,context


class RecoveryContracts(unittest.TestCase):
    def test_operational_capacity_is_additive_and_cross_tf_deduplicated(self):
        noms=[];rows={'1h':{},'15m':{}}
        for j in range(40):
            n=f'ALT{j}USDT'
            for tf in rows:
                noms.append({'native_symbol':n,'timeframe':tf,'routes':['C_QUIET','C_RELATIVE_EXCEPTION'],
                    'families':['F2','F4'],'evidence_ids':[f'e{j}']})
                rows[tf][n]={'values':{'close':100,'atr_explicit':2,'upper_distance':D('.01'),
                    'lower_distance':D('.02'),'quiet_percentile':D('.1'),'pressure_upper':j%3}}
        names,receipts,study=investigate(noms,context(),{'15m':CUTOFF,'1h':CUTOFF},rows,{},capacity=18)
        self.assertEqual(len(names),20);self.assertEqual(len(set(names)),20)
        self.assertEqual(study['protected_audit_symbol_budget'],2)
        self.assertEqual(study['operational_capacity'],18)
        self.assertFalse(study['context_direction_veto'])
        self.assertTrue(any(r['pool']=='operational_contrary_relative' for r in receipts))

    def test_busy_resumes_once_and_retains_prior_valid_partition(self):
        class Busy(Source):
            resumed=0
            def screen(self,names,spec):
                self.calls.append((names,spec))
                if len(self.calls)==2:raise ProviderError('PROVIDER_BUSY_COOLDOWN',metadata())
                return response(names,spec.timeframe),metadata()
            def resume_after_busy(self):self.resumed+=1;return True
        source=Busy();names=('AUSDT','BUSDT','CUSDT')
        b=RequestBudget(5,retry_calls=1,interval_seconds=0)
        result=PartitionEngine(source,b,partition_size=1,transient_recovery=True).run(
            provisional(names),replace(pack(),supported_symbols=names),CUTOFF)
        self.assertEqual(set(result['evaluated_symbols']),set(names))
        self.assertEqual(len(result['attempts']),4);self.assertEqual(b.retries,1)
        self.assertEqual(source.resumed,1);self.assertFalse(result['failed_symbols'])
        self.assertTrue(result['attempts'][1]['bounded_resume_authorized'])

    def test_boundary_is_rejected_without_future_row_relabeling(self):
        def moved(names,spec):
            data=response(names,spec.timeframe)
            data['results'][-1]['observationTime']+=3600
            return data
        class Moved(Source):
            def screen(self,names,spec):
                return moved(names,spec),{**metadata(),'received_at_utc':'2026-11-13T06:17:00+00:00'}
        r=PartitionEngine(Moved(),RequestBudget(2,interval_seconds=0),transient_recovery=True).run(
            provisional(),pack(),CUTOFF)
        self.assertEqual(r['evaluated_symbols'],['BTCUSDT'])
        self.assertEqual(r['rejected_after_cutoff'],['ETHUSDT'])
        self.assertEqual(r['failed_symbols']['ETHUSDT'],'AFTER_FROZEN_CUTOFF')
        self.assertEqual(len(r['observations']),1)

    def test_never_requested_is_not_a_request_failure_or_market_negative(self):
        names=('AUSDT','BUSDT','CUSDT')
        r=PartitionEngine(Source(),RequestBudget(1,retry_calls=0,interval_seconds=0),partition_size=1,
            transient_recovery=True).run(provisional(names),replace(pack(),supported_symbols=names),CUTOFF)
        self.assertEqual(r['not_requested_symbols'],['BUSDT','CUSDT'])
        self.assertEqual(r['failed_symbols'],{})
        self.assertEqual(r['missing_after_request'],[])
        self.assertEqual(set(r['deferred_symbols']),{'BUSDT','CUSDT'})
        self.assertFalse(r['zero_opportunities_established'])

    def test_http202_empty_is_a_named_pending_response(self):
        http=SimpleNamespace(request=lambda *a,**kw:Response(b'',{}, {'http_status':202,'response_sha256':'empty'}))
        with self.assertRaisesRegex(ProviderError,'PROVIDER_PENDING_EMPTY_202'):
            BasisMCP(http)._rpc('tools/call',{})
        # Empty202 remains valid for the protocol notification.
        self.assertEqual(BasisMCP(http)._rpc('notifications/initialized',{},notification=True),{})

    def test_conditional_research_with_fee_gap_keeps_strict_ready_closed(self):
        c,f,refs,b=case(qualification='TRIAL',current=100)
        f.pop('ROUND_TRIP_FEE_BPS');c=replace(c,evidence_ids=tuple(i for i in c.evidence_ids if i in f))
        r=review_card(c,f,refs,as_of=b[-1].end)
        picked,why=conditional_research([r],[c],f,refs,as_of=b[-1].end)
        self.assertEqual(len(picked),1,why)
        self.assertEqual(picked[0]['stage'],'CONDITIONAL_RESEARCH_ONLY')
        self.assertIn('ROUND_TRIP_FEE_BPS',picked[0]['missing_evidence'])
        self.assertFalse(picked[0]['trade_authorization'])
        self.assertNotIn(r['stage'],{'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'})

    def test_unknown_current_price_never_becomes_conditional_research(self):
        c,f,refs,b=case(qualification='TRIAL',current=100)
        f.pop('RESEARCH_PRICE');c=replace(c,evidence_ids=tuple(i for i in c.evidence_ids if i in f))
        r=review_card(c,f,refs,as_of=b[-1].end)
        picked,why=conditional_research([r],[c],f,refs,as_of=b[-1].end)
        self.assertFalse(picked);self.assertIn('SOURCE_GAP',why[0]['disposition'])

    def test_cross_timeframe_obstacle_without_lifecycle_stays_unknown(self):
        c,f,refs,b=case(qualification='TRIAL',current=100)
        refs=[refs[0],replace(refs[1],timeframe='15m')]
        r=review_card(c,f,refs,as_of=b[-1].end)
        picked,why=conditional_research([r],[c],f,refs,as_of=b[-1].end)
        self.assertTrue(picked,why)
        self.assertEqual(picked[0]['research_room']['status'],'ROOM_UNKNOWN')
        self.assertIn('LIFECYCLE_UNVERIFIED',picked[0]['research_room']['reason'])

    def test_contradictory_primary_cannot_pass_research_policy(self):
        c,f,refs,b=case(qualification='TRIAL',current=100)
        event_id=c.events[-1]['id']
        c=replace(c,hypotheses=tuple(replace(h,contradicting_ids=(event_id,))
            if h.family==c.primary_family else h for h in c.hypotheses))
        r=review_card(c,f,refs,as_of=b[-1].end)
        self.assertEqual(r['reason_code'],'CAUSAL_PREMISE_CONTRADICTED')
        self.assertEqual(r['invalidating_event_ids'],[event_id])
        self.assertFalse(conditional_research([r],[c],f,refs,as_of=b[-1].end)[0])

    def test_far_and_cross_tf_duplicate_watch_are_not_extra_active_coins(self):
        c,f,refs,b=case(qualification='TRIAL',current=100)
        r=review_card(c,f,refs,as_of=b[-1].end)
        duplicate=copy.deepcopy(r);duplicate['card_id']='other';duplicate['reference']['timeframe']='15m'
        far=copy.deepcopy(r);far['instrument']='FARUSDT';far['distance_atr_at_verification']=20
        rows=active_coin_watches([r,duplicate,far],as_of=b[-1].end)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['deduplicated_zones'],1)
        self.assertEqual(rows[0]['timeframe_relationships'],['15m','1h'])

    def test_source_gap_depth_does_not_erase_independent_scenario_answers(self):
        c,f,refs,b=case();source={'receipt':{'received_at_utc':b[-1].end},'source_response_sha256':'fixture'}
        # Remove existing scenarios, so this tests actual attachment independently.
        keep=[i for i in c.evidence_ids if f[i].measurement not in {'ROUND_TRIP_FEE_BPS','FUNDING_BOUND_BPS','HORIZON_SECONDS','HORIZON_RELEVANT'}]
        c=replace(c,evidence_ids=tuple(keep))
        ids,assessment=attach(c,f,refs,b,next(iter(f.values())).instrument,source,None,
            load_config()['session55']['economics'],as_of=b[-1].end)
        self.assertEqual(assessment['status'],'SOURCE_GAP')
        self.assertIn('HORIZON_RELEVANT',{f[i].measurement for i in ids})
        self.assertIn('ROUND_TRIP_FEE_BPS',{f[i].measurement for i in ids})

    def test_f9_code_state_and_production_state_are_separate(self):
        f=next(f for f in capability_coverage(load_config())['families'] if f['id']=='F9')
        self.assertEqual(f['state'],'IMPLEMENTED_TRIAL')
        self.assertTrue(f['analytical_implementation']['implemented_code'])
        self.assertFalse(f['production_enabled'])

    def test_multi_coin_point_refresh_filters_obstacles_to_the_current_coin(self):
        from researcher.admission_facts import refresh_selected
        from researcher.research import fact_id
        cards=[];facts={};refs=[];members=[];books=[]
        for name in ('AUSDT','BUSDT'):
            c,own,rs,b=case(name=name,current=100)
            generic={i for i in own if len(i)!=64}
            mapping={i:fact_id(name,i) for i in generic}
            own={mapping.get(i,i):replace(f,id=mapping.get(i,i)) for i,f in own.items()}
            c=replace(c,evidence_ids=tuple(mapping.get(i,i) for i in c.evidence_ids))
            rs=[replace(r,source_ids=tuple(mapping.get(i,i) for i in r.source_ids)) for r in rs]
            cards.append(c);facts.update(own);refs.extend(rs);members.append(next(iter(own.values())).instrument)
            books.append({'native_symbol':name,'values':{'bid':D(100),'ask':D('100.1'),'spread_bps':D(10)},
                'source_time_utc':b[-1].end,'received_at_utc':b[-1].end,'source_response_sha256':name})
        api=SimpleNamespace(pulse=lambda *a,**kw:[{'kind':'book','observations':books}])
        def depth(api,instrument):return {'native_symbol':instrument.native_symbol,'time':b[-1].end,
            'received':b[-1].end,'source_hash':instrument.native_symbol}
        with patch('researcher.economic_sources.depth_snapshot',depth),patch('researcher.admission_facts.book_cost',
                return_value={'status':'OBSERVED','depth_usdt_within_room':D(10000),'slippage_excluding_spread_bps':D(0)}):
            updated,depths,faults,at=refresh_selected(cards,facts,refs,api,SimpleNamespace(instruments=members),
                load_config()['session55']['economics'],clock=lambda:b[-1].end)
        self.assertEqual(len(updated),2);self.assertEqual(faults,[])
        self.assertEqual(len(depths),2)

    def test_ordinary_recovery_call_graph_investigates_more_than_two_and_is_portable(self):
        from test_session5 import FakeAPI,FakeClient,fake_pack,AT
        from researcher.discovery import scan_market_research
        names=('BTCUSDT','ETHUSDT','AAAUSDT','BBBUSDT','CCCUSDT','DDDUSDT')
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as temp, \
                patch('researcher.screening.PartitionEngine.run',fake_pack), \
                patch.dict('sys.modules',{'resource':None}):
            r=scan_market_research(api=FakeAPI(names=names),client=FakeClient(),
                clock=lambda:AT,mode='LIVE',ledger_path=Path(temp)/'test.sqlite')
        self.assertEqual(r['investigation_funnel']['actual_non_context_alt_count'],4,r['source_faults'])
        self.assertEqual(len(r['nominee_dispositions']),len(r['nominations']))
        self.assertFalse(r['trade_authorization']);self.assertEqual(r['new_orders_created'],0)
        self.assertEqual(r['shortlist'],[])
        for route in r['route_coverage'].values():
            self.assertLessEqual(route['evaluated'],route['returned'])
            self.assertLessEqual(route['returned'],route['requested'])


if __name__=='__main__':unittest.main()
