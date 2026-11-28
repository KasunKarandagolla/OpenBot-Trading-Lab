"""Offline source reconciliation and external-first breadth regressions."""
import unittest,tempfile
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from researcher.contracts import encode,utc
from researcher.screening import PartitionEngine,RequestBudget
from researcher.discovery import scan_market_research
from researcher.query_planner import ResearchSources
from researcher.settings import ROOT
from test_session2 import Source,provisional,pack,response,metadata,CUTOFF
from workflow_fixtures import ScenarioAPI,ScenarioScreen,FakeClient,AT


class RecoveryCoverage(unittest.TestCase):
    def test_350_of_400_rows_recover_only_the_missing_partition_at_frozen_cutoff(self):
        names=tuple(f'ALT{j}USDT' for j in range(519))
        class Missing(Source):
            def screen(self,names,spec):
                self.calls.append(tuple(names));data=response(names,spec.timeframe)
                if len(self.calls)==8:
                    data.update(results=[],screened=len(names),evaluated=0,matched=0,returned=0,couldNotEvaluate=len(names))
                return data,metadata()
        source=Missing();result=PartitionEngine(source,RequestBudget(12,retry_calls=1,interval_seconds=0),
            transient_recovery=True).run(provisional(names),replace(pack(),supported_symbols=names),CUTOFF)
        self.assertEqual(len(result['evaluated_symbols']),519)
        self.assertEqual(result['missing_after_request'],[])
        self.assertEqual(source.calls[-1],source.calls[7]);self.assertEqual(len(source.calls[-1]),50)
        self.assertEqual(result['cutoff_utc'],CUTOFF)
        # Exhausted budget preserves exact absent vs never-requested denominators.
        result=PartitionEngine(Missing(),RequestBudget(8,retry_calls=0,interval_seconds=0),
            transient_recovery=True).run(provisional(names),replace(pack(),supported_symbols=names),CUTOFF)
        self.assertEqual(len(result['requested_symbols']),400)
        self.assertEqual(len(result['returned_symbols']),350)
        self.assertEqual(len(result['missing_after_request']),50)
        self.assertEqual(len(result['not_requested_symbols']),119)
        self.assertFalse(result['zero_opportunities_established'])

    def test_519_inventory_selective_adaptive_history_exceeds_old_twenty_and_warm_reuses(self):
        names=('BTCUSDT','ETHUSDT','我踏马来了USDT',*(f'ALT{j}USDT' for j in range(516)))
        api=ScenarioAPI(names=names);client=FakeClient();screen=ScenarioScreen(api,client)
        sources=ResearchSources(mode='LIVE',screen_source=screen)
        (ROOT/'work').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
            db=Path(tmp)/'research.sqlite'
            a=scan_market_research(api=api,client=client,sources=sources,clock=lambda:AT,ledger_path=db,job_id='first-fixture-job')
            before=api.sample_calls;calls=len(screen.calls)
            warm_api=ScenarioAPI(names=names)
            client.http.receipts.clear()
            b=scan_market_research(api=warm_api,client=client,sources=sources,clock=lambda:AT,ledger_path=db,job_id='second-fixture-job')
        self.assertEqual(b['job_id'],'second-fixture-job')
        self.assertEqual(a['coverage']['eligible_contracts'],519)
        self.assertGreater(a['investigation_funnel']['actual_non_context_alt_count'],20,a['source_faults'])
        self.assertLess(a['investigation_funnel']['actual_non_context_alt_count'],100)
        self.assertEqual(before,api.sample_calls);self.assertEqual(warm_api.sample_calls,0)
        self.assertEqual(calls,len(screen.calls))
        self.assertTrue(b['costs']['cached_snapshot_reused'])
        self.assertEqual(a['persistence']['event'],b['persistence']['event'])
        self.assertEqual(a['persistence']['reference'],b['persistence']['reference'])
        self.assertEqual(a['persistence']['watch_revisions'],b['persistence']['watch_revisions'])
        self.assertEqual(len(a['measurement_coverage']),27)
        for tf,row in a['research_coverage']['by_timeframe'].items():
            self.assertEqual(len(row['families']),9);self.assertEqual(len(row['methods']),31)
            self.assertEqual(row['methods']['M14']['code_state'],'DEFINITION_PENDING')
            self.assertEqual(row['methods']['M15']['code_state'],'DEFINITION_PENDING')
            self.assertFalse(any(m['live_eligible_universe_coverage'] for m in row['methods'].values()))
        self.assertLessEqual(a['costs']['by_provider']['binance']['http_requests'],80)
        self.assertFalse(any(f['code']=='REQUEST_BUDGET_EXHAUSTED' for f in a['source_faults']))
        self.assertFalse(a['trade_authorization']);self.assertEqual(a['shortlist'],[])
