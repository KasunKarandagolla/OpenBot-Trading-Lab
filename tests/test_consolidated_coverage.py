"""Offline scanner and provider failure scenarios with exact coverage denominators."""
from dataclasses import replace
from datetime import timedelta
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from researcher.contracts import ContractError, encode, digest, utc
from researcher.discovery import scan_market_research
from researcher.query_planner import ResearchSources
from researcher.remote_structure import scan_registered
from researcher.screening import PartitionEngine, RequestBudget, closed_cutoff
from researcher.settings import ROOT
from researcher.transport import ProviderError
from workflow_fixtures import AT, FakeClient, ScenarioAPI, ScenarioScreen


NAMES=('BTCUSDT','ETHUSDT','AUDITUSDT','BEARUSDT','QUIETUSDT')


class CoverageScreen(ScenarioScreen):
    def __init__(self,api,client,fault=None):
        super().__init__(api,client)
        self.fault=fault

    def screen(self,names,spec):
        causal=spec.id.startswith('METHOD_STRUCTURE')
        if (causal and self.fault=='cooldown') or (spec.timeframe=='15m' and self.fault=='15m_failure'):
            self.calls.append((names,spec))
            receipt={'received_at_utc':self.api.at,'http_status':200,'request_dispatched':True,
                'response_sha256':'SYNTHETIC_PROVIDER_FAULT','response_bytes':25,'elapsed_ms':1}
            self.client.http.receipts.append(receipt)
            raise ProviderError('PROVIDER_BUSY_COOLDOWN' if causal else 'MCP_TOOL_ERROR',receipt)
        if causal:
            # Shape the rows with the existing trusted fixture builder and then
            # replace the price columns by the exact registered mask columns.
            columns=tuple(('pressure_lower',*c[1:]) if c[2]=='INTEGER_EVENT_MASK' else c for c in spec.columns)
            data,receipt=super().screen(names,replace(spec,columns=columns))
            if self.fault=='partial':
                data['results']=[r for r in data['results'] if r['symbol']!='QUIETUSDT']
                for r in data['results']:
                    if r['symbol']=='BEARUSDT':r['values'].pop()
                size=len(data['results'])
                data.update(evaluated=size,matched=size,returned=size,couldNotEvaluate=len(names)-size)
            receipt['response_sha256']=digest(encode(data).encode())
            self.calls[-1]=(names,spec)
            return data,receipt
        data,receipt=super().screen(names,spec)
        if self.fault=='non_nominated_tail' and 'AUDITUSDT' in names:
            data['results']=[r for r in data['results'] if r['symbol']!='AUDITUSDT']
            size=len(data['results'])
            data.update(evaluated=size,matched=size,returned=size,couldNotEvaluate=len(names)-size)
            receipt['response_sha256']=digest(encode(data).encode())
        return data,receipt


def speed_budget(*args,**kwargs):
    kwargs['interval_seconds']=0
    return RequestBudget(*args,**kwargs)


class OfflineCoverage(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        tmp=tempfile.TemporaryDirectory(dir=ROOT/'work')
        self.addCleanup(tmp.cleanup)
        self.directory=Path(tmp.name)
        catalog=json.loads((ROOT/'evidence/external-first/session55/provider-schema.json').read_bytes())
        self.schema=catalog['tools']['screener_run']
        p=patch('researcher.screening.RequestBudget',side_effect=speed_budget)
        p.start();self.addCleanup(p.stop)

    def scan(self,fault=None,*,api=None,client=None,ledger='coverage',schema=True):
        api=api or ScenarioAPI(names=NAMES)
        client=client or FakeClient()
        if schema:client.tools={'screener_run':self.schema}
        screen=CoverageScreen(api,client,fault)
        report=scan_market_research(api=api,client=client,
            sources=ResearchSources(mode='LIVE',screen_source=screen),
            clock=lambda:api.at,ledger_path=self.directory/(ledger+'.sqlite'))
        return report,screen

    def test_causal_pack_precedes_optional_and_complete_success_has_its_own_denominator(self):
        api=ScenarioAPI(names=NAMES);api.max_sample_calls=6
        report,screen=self.scan(api=api)
        self.assertEqual([spec.timeframe for _,spec in screen.calls[:3]],['15m','1h','1h'])
        self.assertTrue(screen.calls[1][1].id.startswith('METHOD_STRUCTURE'))
        self.assertEqual(screen.calls[3][1].columns[0][0],'quote_rvol32')
        causal=report['causal_packs'][0]
        self.assertEqual([causal[k] for k in ('requested','dispatched','returned','evaluated','deferred','not_evaluated')],
                         [5,5,5,5,0,0])
        coverage=report['coverage']['families_by_timeframe']['1h']['F4']
        self.assertEqual(coverage['remote_predicate_qualified'],5)
        self.assertEqual(coverage['complete_family_evaluated'],0)
        self.assertFalse(report['coverage']['all_market_structurally_covered'])

    def test_partial_missing_and_malformed_rows_do_not_erase_healthy_structural_rows(self):
        api=ScenarioAPI(names=NAMES);api.max_sample_calls=6
        report,_=self.scan('partial',api=api)
        causal=report['causal_packs'][0]
        self.assertEqual([causal[k] for k in ('requested','returned','evaluated','failed','missing','unsupported')],
                         [5,4,3,2,1,0])
        self.assertEqual(causal['missing_symbols'],['QUIETUSDT'])
        self.assertIn('BEARUSDT',causal['returned_symbols'])
        self.assertNotIn('BEARUSDT',causal['validated_symbols'])
        self.assertNotIn('BEARUSDT',causal['source_cutoffs'])
        self.assertEqual(causal['per_column']['boundary_12']['not_evaluated'],2)
        self.assertEqual(report['coverage']['methods_by_timeframe']['1h']['M05']['remote_evaluated'],3)

    def test_cooldown_retains_healthy_15m_and_prior_watch_nominations(self):
        first,_=self.scan()
        self.assertTrue(first['watches'])
        later=(utc(AT)+timedelta(hours=1)).isoformat()
        report,screen=self.scan('cooldown',api=ScenarioAPI(at=later,names=NAMES))
        self.assertEqual(report['packs'][0]['evaluated'],5)
        self.assertEqual(len(screen.calls),2)
        self.assertEqual(report['causal_packs'][0]['evaluated'],0)
        self.assertTrue(any('C_SAVED_WATCH' in n['routes'] for n in report['nominations']))

    def test_failed_15m_still_runs_1h_and_source_limit_defers_remaining_packs(self):
        api=ScenarioAPI(names=NAMES);api.max_sample_calls=6
        report,_=self.scan('15m_failure',api=api)
        self.assertEqual(report['packs'][0]['evaluated'],0)
        self.assertEqual(report['packs'][1]['evaluated'],5)
        self.assertEqual(report['causal_packs'][0]['evaluated'],5)
        client=FakeClient()
        client.http.receipts=[{'received_at_utc':AT,'elapsed_ms':1,'response_bytes':1} for _ in range(39)]
        report,screen=self.scan(client=client,ledger='exhausted',api=api)
        self.assertEqual(len(screen.calls),1)
        self.assertEqual(len(client.http.receipts),40)
        causal=report['causal_packs'][0]
        self.assertEqual([causal[k] for k in ('requested','returned','failed','deferred','not_evaluated')],
                         [0,0,0,5,5])

    def test_causal_time_budget_and_stale_reference_rows(self):
        api=ScenarioAPI(names=NAMES);client=FakeClient()
        source=CoverageScreen(api,client)
        seconds=[0]
        screen=source.screen
        def expired(names,spec):
            data,receipt=screen(names,spec)
            seconds[0]+=31
            data['results'][0]['observationTime']-=3600
            receipt['response_sha256']=digest(encode(data).encode())
            return data,receipt
        with patch.object(source,'screen',side_effect=expired):
            cutoff=closed_cutoff(AT,'1h')
            result=scan_registered(PartitionEngine(source,RequestBudget(3,interval_seconds=0,
                max_elapsed_seconds=30,clock=lambda:seconds[0]),partition_size=2,transient_recovery=True),
                api.inventory(),'1h',cutoff,(2,4,8,16,32))
        self.assertEqual(result['dispatched'],2)
        self.assertEqual(result['returned'],2)
        self.assertEqual(result['evaluated'],1)
        self.assertEqual(result['deferred'],3)
        self.assertEqual(set(result['deferred_symbols'].values()),{'SCREEN_WALL_BUDGET_EXHAUSTED'})
        self.assertEqual(result['requested_failed_symbols']['BTCUSDT'],'STALE_SOURCE_CUTOFF')

    def test_sampled_history_dispatch_validation_completion_and_warm_readback(self):
        report,_=self.scan('non_nominated_tail',schema=False)
        sample=report['prospective_audit']['sample'][0]
        self.assertEqual(sample['symbol'],'AUDITUSDT')
        self.assertTrue(sample['from_non_nominated_tail'])
        self.assertEqual(report['prospective_audit']['non_nominated_tail_denominator'],1)
        self.assertEqual(report['prospective_audit']['history_review_counts'],{
            'drawn':1,'selected':1,'completed':1,'incomplete_or_unreviewed':0})
        self.assertTrue(sample['price_history_reviewed'])
        warm,screen=self.scan('non_nominated_tail',schema=False)
        sample_warm=warm['prospective_audit']['sample'][0]
        self.assertEqual(sample_warm['history_review']['timeframes'],sample['history_review']['timeframes'])
        self.assertTrue(sample_warm['history_review']['snapshot_reused'])
        self.assertEqual(screen.calls,[])

    def test_sample_allocated_with_no_physical_attempt_is_deferred(self):
        api=ScenarioAPI(names=NAMES);api.max_sample_calls=6
        report,_=self.scan(api=api,schema=False)
        row=report['prospective_audit']['sample'][0]
        self.assertFalse(row['price_history_reviewed'])
        for value in row['history_review']['timeframes'].values():
            self.assertTrue(value['selected'])
            self.assertFalse(value['attempted'])
            self.assertEqual(value['status'],'DEFERRED')

    def test_sample_with_valid_history_and_failed_evaluation_stays_unreviewed(self):
        from researcher.engine_capabilities import analyze_selected
        def assess(bars,*args,**kwargs):
            if bars[0].native_symbol not in {'BTCUSDT','ETHUSDT'}:
                raise ContractError('INSUFFICIENT_HISTORY')
            return analyze_selected(bars,*args,**kwargs)
        with patch('researcher.engine_capabilities.analyze_selected',side_effect=assess):
            report,_=self.scan(schema=False)
        sample=report['prospective_audit']['sample'][0]
        self.assertTrue(sample['history_review']['required_coverage_obtained'])
        self.assertFalse(sample['price_history_reviewed'])
        for value in sample['history_review']['timeframes'].values():
            self.assertEqual(value['status'],'EVALUATION_FAILED')
            self.assertFalse(value['evaluation_completed'])

    def test_sample_faults_distinguish_timeout_cooldown_empty_invalid_and_short(self):
        for fault in ('timeout','cooldown','empty','invalid_timestamp','missing_bars','short'):
            with self.subTest(fault=fault):
                api=ScenarioAPI(names=NAMES)
                original=api.klines
                def failed(instrument,*,timeframe,cutoff):
                    bars,source=original(instrument,timeframe=timeframe,cutoff=cutoff)
                    if instrument.native_symbol in {'BTCUSDT','ETHUSDT'} or timeframe!='15m':
                        return bars,source
                    if fault in {'timeout','cooldown'}:
                        if fault=='cooldown':api.http.receipts[-1]['http_status']=429
                        raise ProviderError('NETWORK_OR_TLS_FAILURE' if fault=='timeout' else 'HTTP_429')
                    if fault=='empty':bars=[]
                    if fault=='invalid_timestamp':bars[-1]=replace(bars[-1],open_ms=bars[-1].open_ms+1)
                    if fault=='missing_bars':bars.pop(-2)
                    if fault=='short':bars=bars[-12:]
                    return bars,source
                api.klines=failed
                report,_=self.scan(api=api,ledger=fault,schema=False)
                sample=report['prospective_audit']['sample'][0]
                history=sample['history_review'];row=history['timeframes']['15m']
                self.assertFalse(sample['price_history_reviewed'])
                self.assertTrue(history['timeframes']['1h']['accepted'])
                self.assertTrue(row['attempted'])
                self.assertEqual(row['responded'],fault!='timeout')
                self.assertEqual(row['accepted'],fault=='short')
                self.assertFalse(history['required_coverage_obtained'])
                self.assertFalse(row['evaluation_completed'])
