"""SIMULATED durability/failure tests and authentic recorded source regressions."""
import copy
from dataclasses import asdict,replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
import zlib
from unittest.mock import patch

from researcher.contracts import ContractError,Instrument,encode,digest,utc
from researcher.core import CORE,EXPORT_SCALE,make_pack,compare_tail,oracle_value
from researcher.discovery import scan_market_research
from researcher.inventory import InventorySnapshot
from researcher.numerics import Bar
from researcher.persistence import RunLedger
from researcher.screening import normalize_screen,closed_cutoff
from researcher.settings import ROOT,load_config,validate_config
from researcher.structures import ResearchLedger,selected_family_facts,equal_level_references
from researcher.transport import ProviderError
from researcher.basis import BasisMCP
from test_session4 import case


AT='2026-01-20T12:07:00+00:00'
NAMES=('BTCUSDT','ETHUSDT','AAAUSDT','ZZZUSDT')


def instrument(n,at=AT):
    return Instrument(n,'BINANCE_USDM',quote='USDT',settlement='USDT',contract_type='PERPETUAL',
        tick_size=D('.01'),quantity_rules={'minQty':'1'},metadata_hash='SIMULATED',
        identity_status='EXCHANGE_VERIFIED',trading_status='TRADING',underlying_class='CRYPTO',
        source_id='SIMULATED',captured_at_utc=at,onboard_at_utc='2025-01-01T00:00:00+00:00')


class FakeAPI:
    def __init__(self,at=AT,*,outage=False,names=NAMES):
        self.at=at;self.outage=outage;self.names=names
        self.http=SimpleNamespace(receipts=[]);self.sample_calls=0

    def inventory(self):
        if self.outage:raise ProviderError('HTTP_451')
        return InventorySnapshot('SIMULATED','SIMULATED',self.at,self.at,'SIMULATED',
            tuple(instrument(n,self.at) for n in self.names),'VERIFIED_INVENTORY',
            eligible_symbols=self.names,complete_source_snapshot=True,freshness='FRESH')

    def pulse(self,inventory,partial=False,kinds=('ticker','book','premium')):
        return [{'kind':k,'observations':[],'mode':'SIMULATED'} for k in kinds]

    def klines(self,i,*,timeframe,cutoff,bars=300):
        from researcher.observations import WIDTHS
        self.sample_calls+=1
        width=WIDTHS[timeframe]*1000;end=int(utc(cutoff).timestamp()*1000)
        series=[]
        for j in range(bars):
            p=D(100)+D((j%12)-6)/10
            series.append(Bar(i.native_symbol,timeframe,end-(bars-j)*width,p,p+1,p-1,p,
                D(10),p*10,D(5),p*5,10,'SIMULATED',self.at))
        receipt={'received_at_utc':self.at,'response_sha256':'SIMULATED'}
        return series,{'native_symbol':i.native_symbol,'timeframe':timeframe,'cutoff':cutoff,
            'source_response_sha256':'SIMULATED','receipt':receipt}


class FakeClient:
    def __init__(self):self.http=SimpleNamespace(receipts=[]);self.connections=0
    def connect(self):self.connections+=1


def fake_pack(engine,inventory,pack,cutoff):
    obs=[]
    for i in inventory.instruments:
        values={'atr_explicit':D(2),'width16':D('.01'),'quiet_percentile':D('.1'),
            'efficiency16':D('.2'),'progress16':D('1.01'),'prior_high16':D(102),
            'prior_low16':D(98),'upper_distance':D('.02'),'lower_distance':D('.02'),
            'tr_fraction':D('.01'),'displacement':D(1),'body_fraction':D('.5'),
            'pressure_upper':D(1),'pressure_lower':D(0),'close':D(100),'quote_rvol32':D(1)}
        for f in pack.columns:
            obs.append({'instrument':asdict(i),'measurement_id':f[0],'value':values[f[0]],
                'id':digest(encode([i.native_symbol,pack.timeframe,f[0],cutoff]).encode()),
                'received_at_utc':i.captured_at_utc,'source_closed_close':D(100),
                'source_response_hash':'SIMULATED'})
    return {'timeframe':pack.timeframe,'cutoff_utc':cutoff,'observations':obs,
        'requested_symbols':list(inventory.symbols),'evaluated_symbols':list(inventory.symbols),
        'returned_symbols':list(inventory.symbols),'missing_symbols':[],'failed_symbols':{},
        'truncated_attempts':0,'attempts':[{'provider_error':None}],
        'provider_added_fillers':[]}


class OperationalDurability(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'work');self.db=Path(self.temp.name)/'research.sqlite'
        self.engine=patch('researcher.screening.PartitionEngine.run',fake_pack);self.engine.start()
    def tearDown(self):self.engine.stop();self.temp.cleanup()

    def scan(self,at=AT,**kwargs):
        return scan_market_research(api=kwargs.pop('api',FakeAPI(at)),client=kwargs.pop('client',FakeClient()),
            ledger_path=self.db,clock=lambda:at,mode='SYNTHETIC',**kwargs)

    def test_first_run_has_context_causal_watches_and_no_fake_ready(self):
        r=self.scan()
        self.assertEqual(r['mode'],'SYNTHETIC');self.assertEqual(r['source_faults'],[])
        self.assertEqual(r['coverage']['eligible_contracts'],4)
        self.assertEqual(len(r['packs']),2);self.assertEqual(r['costs']['targeted_kline_calls'],10)
        self.assertTrue(r['watches']);self.assertEqual(r['shortlist'],[])
        self.assertTrue(all(w['stage'] not in {'READY_FOR_DEEP','FAST_WITH_ROOM'} for w in r['watches']))
        self.assertEqual(sum(c['status']=='SUPPORTED' for c in r['context']['claims'][:4]),4)

    def test_backward_host_clock_preserves_original_receipts_and_commits_safely(self):
        ahead=(utc(AT)+timedelta(seconds=10)).isoformat()
        r=self.scan(api=FakeAPI(ahead))
        self.assertTrue(r['clock_anomalies']);self.assertEqual(r['shortlist'],[])
        self.assertEqual(r['time_integrity_status'],'CLOCK_UNCERTAINTY; NO_READY')
        self.assertGreaterEqual(utc(r['completed_at_utc']),utc(ahead))
        self.assertEqual(r['persistence']['run_snapshots'],1)
        self.assertTrue(all(w['reference']['available_at']==ahead for w in r['watches']))

    def test_repeat_reopens_database_without_duplicate_watch_or_events(self):
        a=self.scan();client=FakeClient();b=self.scan(client=client)
        self.assertTrue(b['costs']['cached_snapshot_reused']);self.assertEqual(client.connections,0)
        self.assertEqual(b['costs']['targeted_kline_calls'],0)
        self.assertEqual(a['persistence']['event'],b['persistence']['event'])
        self.assertEqual(a['persistence']['watch_revisions'],b['persistence']['watch_revisions'])
        self.assertEqual([w['first_seen'] for w in a['watches']],[w['first_seen'] for w in b['watches']])
        l=RunLedger(self.db)
        stored=json.loads(zlib.decompress(l.db.execute('SELECT body FROM run_snapshot ORDER BY rowid DESC LIMIT 1').fetchone()[0]))
        self.assertEqual(stored['snapshot_delta_version'],1)
        self.assertEqual(stored['base_snapshot'],a['run_key'])
        self.assertEqual(l.db.execute('SELECT count(*) FROM evidence_cache').fetchone()[0],1)
        original=l.cached(a['run_key'])
        self.assertTrue(all('measurements' not in p for p in original['packs']));l.close()

    def test_many_missed_closes_are_simulated_unobserved_not_repaired(self):
        a=self.scan();later=(utc(AT)+timedelta(days=3)).isoformat();b=self.scan(later)
        self.assertEqual(b['source_faults'],[]);self.assertTrue(b['time_gaps'])
        self.assertTrue(all(g['status']=='GAP_UNOBSERVED' and not g['current_reconstruction_repairs_prospective_gap'] for g in b['time_gaps']))
        self.assertEqual(b['shortlist'],[])

    def test_outage_preserves_last_verified_cutoff_and_frozen_reference(self):
        a=self.scan();later=(utc(AT)+timedelta(days=1)).isoformat()
        b=self.scan(later,api=FakeAPI(later,outage=True))
        self.assertEqual(b['operation_status'],'BLOCKED_OR_UNQUALIFIED')
        self.assertEqual(b['last_verified_observation_cutoffs'],a['last_verified_observation_cutoffs'])
        self.assertEqual(encode([w['reference'] for w in a['watches']]),encode([w['reference'] for w in b['watches']]))
        self.assertTrue(all(w['gap_status']=='GAP_UNOBSERVED' for w in b['watches']))

    def test_crash_mid_commit_rolls_back_all_metadata_and_recovers(self):
        def crash():raise RuntimeError('SIMULATED_CRASH')
        with self.assertRaisesRegex(RuntimeError,'SIMULATED_CRASH'):self.scan(crash_hook=crash)
        l=RunLedger(self.db)
        self.assertEqual(l.counts()['reference'],0);self.assertEqual(l.cutoffs(),{});l.close()
        r=self.scan();self.assertEqual(r['persistence']['interrupted_attempts'],1)

    def test_delisting_archives_old_identity_without_symbol_guessing(self):
        a=self.scan();later=(utc(AT)+timedelta(hours=1)).isoformat()
        b=self.scan(later,api=FakeAPI(later,names=('BTCUSDT','ETHUSDT')))
        archived=[x for x in b['invalidations'] if x.get('reason')=='DELISTED_OR_CHANGED_CONTRACT_IDENTITY']
        self.assertTrue(archived)
        l=RunLedger(self.db)
        self.assertFalse(any(r['native_symbol'] in {'AAAUSDT','ZZZUSDT'} for r in l.active_references(later)));l.close()

    def test_changed_contract_identity_quarantines_old_references(self):
        self.scan();later=(utc(AT)+timedelta(hours=1)).isoformat()
        class Changed(FakeAPI):
            def inventory(self):
                inv=super().inventory()
                return replace(inv,instruments=tuple(replace(i,tick_size=D('.02')) if i.native_symbol=='AAAUSDT' else i for i in inv.instruments))
        r=self.scan(later,api=Changed(later))
        self.assertIn('AAAUSDT',r['identity_quarantine'])
        self.assertFalse(any(w['native_symbol']=='AAAUSDT' for w in r['watches']))
        self.assertTrue(any(x.get('reason')=='DELISTED_OR_CHANGED_CONTRACT_IDENTITY' for x in r['invalidations']))

    def test_new_listing_still_nominates_without_a_long_core_baseline(self):
        class Young(FakeAPI):
            def inventory(self):
                inv=super().inventory()
                return replace(inv,instruments=tuple(replace(i,onboard_at_utc=(utc(AT)-timedelta(hours=1)).isoformat()) if i.native_symbol=='AAAUSDT' else i for i in inv.instruments))
            def klines(self,i,**kw):
                if i.native_symbol=='AAAUSDT':kw['bars']=4
                return super().klines(i,**kw)
        def missing(engine,inventory,pack,cutoff):
            r=fake_pack(engine,inventory,pack,cutoff)
            r['observations']=[o for o in r['observations'] if o['instrument']['native_symbol']!='AAAUSDT']
            r['evaluated_symbols'].remove('AAAUSDT');r['failed_symbols']['AAAUSDT']='INSUFFICIENT_HISTORY'
            return r
        with patch('researcher.screening.PartitionEngine.run',missing):r=self.scan(api=Young())
        self.assertTrue(any(n['native_symbol']=='AAAUSDT' and 'C_NEW_LISTING' in n['routes'] for n in r['nominations']))
        self.assertEqual(r['shortlist'],[])

    def test_exhausted_broad_source_has_zero_evaluation_not_no_setup(self):
        with patch('researcher.screening.PartitionEngine.run',side_effect=ProviderError('REQUEST_BUDGET_EXHAUSTED')):
            r=self.scan()
        self.assertEqual(r['packs'],[]);self.assertEqual(r['shortlist'],[])
        self.assertFalse(r['cache_reusable']);self.assertTrue(r['source_faults'])

    def test_missing_db_is_created_and_legacy_schema_is_upgraded(self):
        l=ResearchLedger(self.db);l.close();r=self.scan()
        self.assertEqual(r['persistence']['schema_version'],5)

    def test_corrupt_db_is_preserved(self):
        self.db.write_bytes(b'SIMULATED_CORRUPT_DATABASE')
        with self.assertRaises(ContractError):RunLedger(self.db)
        self.assertEqual(self.db.read_bytes(),b'SIMULATED_CORRUPT_DATABASE')

    def test_other_application_db_is_not_modified(self):
        db=sqlite3.connect(self.db);db.execute('CREATE TABLE trades(id INTEGER)');db.commit();db.close()
        before=self.db.read_bytes()
        with self.assertRaisesRegex(ContractError,'NOT_A_RESEARCH_DATABASE'):RunLedger(self.db)
        self.assertEqual(self.db.read_bytes(),before)

    def test_unknown_future_schema_is_not_modified(self):
        db=sqlite3.connect(self.db);db.execute('PRAGMA user_version=99');db.commit();db.close()
        before=self.db.read_bytes()
        with self.assertRaisesRegex(ContractError,'VERSION_UNSUPPORTED'):RunLedger(self.db)
        self.assertEqual(self.db.read_bytes(),before)


class AuthenticSourceRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof=json.loads((ROOT/'evidence/external-first/session5/core-qualification.json').read_text())

    def test_all_recorded_scalar_oracles_remain_within_declared_tolerance(self):
        count=0
        for s in self.proof['screens']:
            for c in s['oracle_checks']:
                self.assertLessEqual(abs(D(c['actual'])-D(c['independent'])),D(c['tolerance']));count+=1
        self.assertEqual(count,10*len(self.proof['formula_manifest']))

    def test_seed_initial_nulls_and_recurrence_are_recomputed_independently(self):
        samples={}
        for s in self.proof['independent_selected_bars']:
            raw=[{**s['bar_common'],**dict(zip(s['bar_columns'],b))} for b in s['bars']] if 'bar_columns' in s else s['bars']
            bars=[Bar(**{k:(D(v) if k in {'open','high','low','close','base_volume','quote_volume','buy_base','buy_quote'} else v)
                for k,v in b.items()}) for b in raw]
            samples[bars[0].native_symbol,bars[0].timeframe]=bars
        for c in self.proof['checks']:
            bars=[b for b in samples[c['native_symbol'],c['timeframe']] if b.open_ms//1000>=c['source_start']]
            actual=compare_tail(c['feature'],c['remote_data'],bars)
            self.assertTrue(actual['passed']);self.assertTrue(actual['comparisons'])
            if c['kind']=='EXACT_SEED_AND_INITIAL_NULLS':
                self.assertTrue(any(x['independent'] is None for x in actual['comparisons']))
                self.assertEqual(sum(x['independent'] is not None for x in actual['comparisons']),6)

    def test_unicode_targeted_failures_and_optional_quote_failure_remain_visible(self):
        failures=self.proof['failures']
        self.assertEqual({f['timeframe'] for f in failures if f.get('native_symbol')=='我踏马来了USDT'},{'1h','15m'})
        self.assertTrue(any(f['phase']=='optional_quote_field' and f['code']=='MCP_TOOL_ERROR' for f in failures))

    def test_no_native_atr_expression_promoted(self):
        self.assertTrue(all('atr(14)' not in f.expression for f in CORE.values()))
        self.assertFalse(load_config()['session5']['full_core_enabled'])

    def test_failed_zero_offset_pressure_trial_and_positive_remedy_are_retained(self):
        failed=json.loads((ROOT/'evidence/external-first/session5/failed-trials.json').read_text())
        for trial in failed['pressure_zero_offset_regressions']:
            rows=[c for c in trial['comparisons'] if c['native_symbol']=='BTCUSDT' and c['timeframe']=='15m' and c['feature']=='pressure_lower']
            self.assertEqual(len(rows),1);self.assertEqual(D(rows[0]['actual']),0)
            self.assertEqual(D(rows[0]['independent']),1);self.assertFalse(rows[0]['passed'])
        positive=0
        for c in self.proof['checks']:
            if not c['feature'].startswith('pressure_'):continue
            self.assertTrue(c['passed'])
            positive+=sum(v['independent'] is not None and D(v['independent'])>0 for v in c['comparisons'])
        self.assertGreater(positive,0)
        self.assertTrue(all('[0]' not in CORE[k].expression for k in ('pressure_upper','pressure_lower')))

    def test_session5_formula_evaluation_requires_bounded_source_reference(self):
        c=BasisMCP(qualification=True,session5=True);c.initialized=True
        c.tools={'formula_evaluate':{'inputSchema':{}}}
        with self.assertRaisesRegex(ContractError,'TARGETED_BOUNDED_REF_REQUIRED'):
            c.call('formula_evaluate',{'symbol':'BTCUSDT','expression':'close','includeForming':False})

    def test_multi_column_formula_and_clock_mismatch_are_rejected(self):
        s=self.proof['screens'][0];names=self.proof['selected_plan']['symbols'];tf=s['timeframe']
        labels=tuple(self.proof['formula_manifest'])
        # Retain actual provider rule order, not JSON object's sorted key order.
        by_expression={c[1]:c[0] for c in make_pack(tf,names,CORE).columns}
        order=[by_expression[r['left']['expression']] for r in s['data']['rules']]
        pack=make_pack(tf,names,order);members={n:Instrument(n,'BINANCE_USDM') for n in names}
        receipt,obs=normalize_screen(names,s['data'],s['transport'],pack=pack,instruments=members,cutoff=self.proof['cutoffs'][tf])
        self.assertEqual(len(receipt.evaluated_symbols),5)
        self.assertEqual(len(obs),5*len(order))
        if 'quote_rvol32' in order:
            zero=copy.deepcopy(s['data']);j=order.index('quote_rvol32')
            row=next(r for r in zero['results'] if r['symbol']==names[0]);row['values'][j]['left']=0
            valid,exported=normalize_screen(names,zero,s['transport'],pack=pack,instruments=members,cutoff=self.proof['cutoffs'][tf])
            self.assertIn(names[0],valid.evaluated_symbols)
            q=next(o for o in exported if o['instrument']['native_symbol']==names[0] and o['measurement_id']=='quote_rvol32')
            self.assertIsNone(q['value']);self.assertEqual(q['verdict'],'UNKNOWN')
            self.assertEqual(len([o for o in exported if o['instrument']['native_symbol']==names[0] and o['value'] is not None]),len(order)-1)
        fillers=copy.deepcopy(s['data'])
        for row in fillers['results']:
            if row['symbol'] not in names:row['values']=[];row['last']=None
        valid,_=normalize_screen(names,fillers,s['transport'],pack=pack,instruments=members,cutoff=self.proof['cutoffs'][tf])
        self.assertEqual(len(valid.evaluated_symbols),5)
        bad=copy.deepcopy(s['data']);bad['rules'][0]['left']['expression']='atr(14)'
        with self.assertRaisesRegex(ContractError,'FORMULA_MISMATCH'):
            normalize_screen(names,bad,s['transport'],pack=pack,instruments=members,cutoff=self.proof['cutoffs'][tf])
        late=(utc(self.proof['cutoffs'][tf])+timedelta(hours=1)).isoformat()
        receipt,obs=normalize_screen(names,s['data'],s['transport'],pack=pack,instruments=members,cutoff=late)
        self.assertEqual(obs,[]);self.assertEqual(len(receipt.failed_symbols),5)

    def test_unqualified_column_cannot_be_enabled_by_config_edit(self):
        c=load_config();c['session5']['qualified_price_columns'].append('NONEXISTENT')
        with self.assertRaises(ContractError):validate_config(c)


class SelectedFamilyContracts(unittest.TestCase):
    def test_equal_level_is_born_only_at_second_confirmed_pivot(self):
        from test_session3 import bars_from
        bars=bars_from([100]*20+[110,104,101,100,103,D('109.9'),104,101,100])
        refs=equal_level_references(bars,D('.1'),as_of=bars[-1].end)
        highs=[r for r in refs if r.direction==1]
        self.assertTrue(highs)
        r=highs[-1]
        self.assertEqual(r.known_at,bars[27].end)
        earlier=equal_level_references(bars,D('.1'),as_of=bars[26].end)
        self.assertNotIn(r.id,[x.id for x in earlier])
        self.assertEqual(r.fidelity,'INFERRED_LIQUIDITY_PRICE_GEOMETRY')

    def test_contiguous_equal_candles_are_not_a_liquidity_pool(self):
        from test_session3 import bars_from
        bars=bars_from([100]*20+[110]*8+[100]*3)
        self.assertFalse([r for r in equal_level_references(bars,D('.1'),as_of=bars[-1].end) if r.direction==1])

    def test_zero_atr_and_zero_volume_do_not_invent_expansion_or_liquidation(self):
        bars,_=FakeAPI().klines(instrument('AAAUSDT'),timeframe='1h',cutoff=closed_cutoff(AT,'1h'))
        flat=[replace(b,open=D(100),high=D(100),low=D(100),close=D(100),base_volume=D(0),quote_volume=D(0),buy_base=D(0),buy_quote=D(0),trades=0) for b in bars]
        r=selected_family_facts(flat,D('.01'),as_of=AT)
        self.assertEqual(next(f for f in r if f['family']=='F9')['shocks'],[])
        self.assertIsNone(next(f for f in r if f['family']=='F7')['extension_atr'])

    def test_atomic_report_failure_leaves_no_partial_output(self):
        from researcher.__main__ import write_report
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as temporary:
            target=Path(temporary)/'report.json'
            with patch('os.link',side_effect=OSError('SIMULATED_FILESYSTEM_FAULT')):
                with self.assertRaises(OSError):write_report(target,{'mode':'SYNTHETIC'})
            self.assertFalse(target.exists());self.assertEqual(list(Path(temporary).iterdir()),[])
    def test_session_value_relative_and_price_shock_do_not_claim_specialists(self):
        api=FakeAPI();i=instrument('AAAUSDT');bars,_=api.klines(i,timeframe='1h',cutoff=closed_cutoff(AT,'1h'))
        btc=[replace(b,native_symbol='BTCUSDT') for b in bars]
        r=selected_family_facts(bars,D('.01'),as_of=AT,benchmark=btc)
        self.assertTrue({'F1','F3','F6','F7','F8','F9'}-{'F1'} <= {f['family'] for f in r})
        value=next(f for f in r if f['family']=='F7')
        self.assertFalse(value['true_profile']);self.assertFalse(value['true_weighted_variance'])
        rel=next(f for f in r if f['family']=='F8')['lag_trained']
        self.assertLess(utc(rel['training_end']),utc(rel['evaluation_end']))

    def test_future_bar_append_does_not_change_frozen_asof(self):
        api=FakeAPI();bars,_=api.klines(instrument('AAAUSDT'),timeframe='1h',cutoff=closed_cutoff(AT,'1h'),bars=299)
        old=selected_family_facts(bars,D('.01'),as_of=AT)
        future=replace(bars[-1],open_ms=bars[-1].end_ms,received_at=(utc(AT)+timedelta(hours=2)).isoformat())
        self.assertEqual(old,selected_family_facts(bars+[future],D('.01'),as_of=AT))

    def test_atomic_outer_transaction_rolls_back_existing_causal_record(self):
        card,_,_,_=case();l=RunLedger()
        try:
            with self.assertRaises(RuntimeError):
                with l.writer(card.cutoff):
                    l.record(card.reference,card.events,cutoff=card.cutoff)
                    raise RuntimeError('SIMULATED')
            self.assertEqual(l.counts()['reference'],0);self.assertEqual(l.counts()['event'],0)
        finally:l.close()
