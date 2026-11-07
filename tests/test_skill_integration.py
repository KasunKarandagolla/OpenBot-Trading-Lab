"""Current-contract negatives, real-source chronology and scoped scratch recovery."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from binance_research_data import DataError
from trading_lab import skills
from trading_lab.charts import validate_request, confirmed_swings, render
from trading_lab.skill_install import prepare, apply, rollback, inventory
from trading_lab.workflow import Inbox, atomic_reply

ROOT = Path(__file__).resolve().parents[1]
REAL = os.environ.get('OPENBOT_REAL_PACKET')


class ContractTests(unittest.TestCase):
    def test_complete_pack_and_exact_owners(self):
        r=skills.check_pack();self.assertEqual(r['assignments'],27);self.assertEqual(r['skill_files'],55)
        self.assertEqual(sorted(r['owners'].values()),[1,5,6,6,9])

    def test_new_sessions_have_current_capabilities(self):
        for a in json.loads((skills.PACK/'contract.json').read_text())['assignments']:
            card=skills.bootstrap(a['owner']);self.assertEqual(card['execution_authority'],'NONE')
        with self.assertRaises(DataError):skills.bootstrap('replacement-risk')

    def test_readiness_scan_schema_and_expiry(self):
        base=dict(schema='openbot.shared.request.v2',request_id='test',kind='READINESS',created_at_ms=1000,expires_at_ms=2000,payload={})
        self.assertEqual(skills.validate_envelope(base,1000),base)
        for change in [{'payload':{'account':{}}},{'expires_at_ms':1000},{'created_at_ms':1001},
                       {'expires_at_ms':601001},{'kind':'SHELL'},{'kind':'SCAN','payload':{'universe':23}},
                       {'kind':'SCAN','payload':{'shortlist':7}}]:
            with self.subTest(change=change),self.assertRaises(DataError):skills.validate_envelope({**base,**change},1000)

    def test_watch_missing_risk_and_veto_cannot_be_action(self):
        for rec in ['TRADE','WATCH','NO_TRADE']:
            r=skills.reconcile(rec,{'status':'PASS'},risk_verified=False)
            self.assertEqual(r['decision'],'NO_ACTION');self.assertIn('AGENT_NOT_VERIFIED',r['reasons'])
            self.assertFalse(r['order_authorized'])
        self.assertEqual(skills.reconcile('TRADE',{'status':'VETO'},risk_verified=True)['decision'],'NO_ACTION')
        with self.assertRaises(DataError):skills.reconcile('BUY',{})

    def test_watch_not_valid_order_intent(self):
        from trading_lab.risk import validate_market_plan
        self.assertEqual(validate_market_plan({'decision':'WATCH'},{},None,1000)['status'],'VETO')
        with self.assertRaises(DataError):skills.schema_check({'decision':'WATCH'},ROOT/'research/openbot_current/order-intent.schema.json')

    def test_kline_proxy_and_cross_venue_flow_fail_closed(self):
        self.assertIsNone(skills.verify_flow([],{'venue':'gate'},1000)['signed_delta_base'])
        self.assertEqual(skills.verify_flow([],{'venue':'binance','market_type':__import__('openbot_current_market').MARKET,'fidelity':'OHLCV'},1000)['reason'],
                         'KLINE_PROXY_IS_NOT_TRADE_PRINTS')

    def test_print_delta_requires_continuity_units_side_boundaries(self):
        market=__import__('openbot_current_market')
        rows=[dict(a=1,T=100,m=True,q='3'),dict(a=2,T=200,m=False,q='1')]
        def provenance(rows):
            return dict(venue='binance',market_type=market.MARKET,fidelity='BINANCE_AGG_TRADES',units='BASE_ASSET',
                        source_sha256=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                        start_ms=0,end_ms=300,aggressor_semantics='BUYER_IS_MAKER',start_boundary_verified=True,end_boundary_verified=True)
        p=provenance(rows);self.assertEqual(skills.verify_flow(rows,p,300)['signed_delta_base'],'-2')
        for change in [{'end_boundary_verified':False},{'source_sha256':'0'*64},{'units':'CONTRACTS'},{'aggressor_semantics':'UNKNOWN'}]:
            self.assertIsNone(skills.verify_flow(rows,{**p,**change},300)['signed_delta_base'])
        bad=[rows[0],{**rows[1],'a':3}];self.assertIsNone(skills.verify_flow(bad,provenance(bad),300)['signed_delta_base'])

    def test_no_pixel_candidate_and_visible_claims_fail(self):
        assessment=dict(schema='openbot.vision.assessment.v2',candidate_id='test',packet_sha256='a'*64,cutoff_ms=1000,
                        execution_authority='NONE',order_authorized=False,research_status='RESEARCH_CANDIDATE',
                        interest='MARKET_INTERESTING',trigger='UNKNOWN',admissibility='NOT_ESTABLISHED',images=[],
                        observations=[],hypotheses=[],contradictions=[],unknowns=[],insight_gained=None,confidence='PARTIAL_EVIDENCE')
        with self.assertRaises(DataError):skills.schema_check(assessment,skills.PACK/'schemas/vision-assessment.schema.json')

    def test_outcome_gaps_cannot_produce_path_metrics(self):
        import pandas as pd
        from trading_lab.casebook import validate_outcome_window
        full=pd.DataFrame({'open_time_ms':[0,300000,600000],'available_at_ms':[300000,600000,900000]})
        validate_outcome_window(full,0,900000)
        for bad in [full.drop(index=1),full.iloc[:2],full.assign(available_at_ms=[300000,600001,900000])]:
            with self.assertRaisesRegex(DataError,'OUTCOME_WINDOW'):validate_outcome_window(bad,0,900000)


@unittest.skipUnless(REAL,'Set OPENBOT_REAL_PACKET to an authentic sealed Binance packet for real-source integration')
class RealSourceTests(unittest.TestCase):
    def setUp(self):
        self.packet=Path(REAL);self.seal,self.identity=skills.verified_packet(self.packet)
        self.scratch=tempfile.TemporaryDirectory();self.addCleanup(self.scratch.cleanup)
        self.revisions=Path(self.scratch.name)/'revisions'

    def request(self,**changes):
        r=skills.chart_envelope(self.packet,'frozen-run','real-vision',purpose='Investigate known levels',now=1000)
        r['payload']['chart'].update(changes);return r

    def test_real_request_render_replay_and_source_receipt(self):
        r=self.request();skills.validate_envelope(r,1000,self.packet,self.seal['packet_sha256'])
        receipt=render(self.packet,r['payload']['chart'],self.revisions)
        self.assertEqual(receipt,render(self.packet,r['payload']['chart'],self.revisions))
        self.assertEqual(receipt['packet_sha256'],self.seal['packet_sha256'])
        self.assertLessEqual(receipt['last_available_ms'],self.identity['as_of_ms'])
        self.assertEqual(receipt['visible_candles'],120)
        with self.assertRaises(DataError):render(self.packet,{**r['payload']['chart'],'purpose':'Mutated same revision'},self.revisions)

    def test_exact_chart_failures(self):
        for change in [{'venue':'GATE'},{'candidate_id':'wrong'},{'symbol':'BTC_SPOT'},
                       {'timeframe':'1d'},{'visible_candles':201},{'overlays':['vwap','ema20','ema50','confirmed_swings']},
                       {'end_ms':self.identity['as_of_ms']+1},{'cutoff_ms':self.identity['as_of_ms']+1},
                       {'revision':5},{'overlays':[{}]},{'request_id':False}]:
            with self.subTest(change=change),self.assertRaises(DataError):skills.validate_envelope(self.request(**change),1000,self.packet)
        with self.assertRaisesRegex(DataError,'CHART_FEED_NOT_CAPTURED'):skills.validate_envelope(self.request(timeframe='1m'),1000,self.packet)
        with self.assertRaises(DataError):skills.validate_envelope(self.request(),1000,self.packet,'0'*64)

    def test_real_source_future_mutation_detected_even_if_resealed(self):
        import openbot_current_market as market
        target=Path(self.scratch.name)/self.packet.name;shutil.copytree(self.packet,target)
        source=market.load(target/'candles/5m.json');source['bars'][-1][6]+=300000
        market.write(target/'candles/5m.json',source)
        manifest=market.load(target/'MANIFEST.json');manifest['candles/5m.json']=skills.sha(target/'candles/5m.json');market.write(target/'MANIFEST.json',manifest)
        with self.assertRaises(DataError):skills.verified_packet(target)

    def test_quality_is_not_qualification(self):
        observation=skills.quality_observations(self.packet)
        self.assertFalse(observation['qualified_for_execution']);self.assertIn('source_windows',observation)

    def test_gate_schema_rejects_account_injection_at_actual_inbox(self):
        inbox=Inbox(Path(self.scratch.name)/'TradingLab-Workflow-v2')
        run=inbox.root/'runs'/'frozen-run';(run/'packets').mkdir(parents=True)
        shutil.copytree(self.packet,run/'packets'/self.packet.name)
        market=__import__('openbot_current_market');market.write(run/'index.json',{'packets':[self.seal]})
        r=self.request();r.update(kind='GATE',payload=dict(run_id='frozen-run',candidate_id=self.packet.name,account={'authenticated':True}))
        f=inbox.root/'requests'/ 'real-vision-r1.json';atomic_reply(f,r)
        with self.assertRaises(DataError):inbox.handle(f,1000)

    def test_confirmed_swing_prefix_equivalence(self):
        import pandas as pd
        from binance_research_data import KLINE_COLUMNS
        market=__import__('openbot_current_market');source=market.load(self.packet/'candles/5m.json')
        f=pd.DataFrame(source['bars'],columns=KLINE_COLUMNS)
        f['date']=pd.to_datetime(f.open_time,unit='ms',utc=True);f['available_at_ms']=f.close_time+1
        for k in ['high','low']:f[k]=pd.to_numeric(f[k])
        cut=len(f)-10;known=int(f.iloc[cut-1].available_at_ms)
        self.assertEqual(confirmed_swings(f.iloc[:cut]),[x for x in confirmed_swings(f) if x['known_at_ms']<=known])

    def test_swing_claim_rejects_pivot_bar_as_confirmation_time(self):
        import pandas as pd
        from binance_research_data import KLINE_COLUMNS
        market=__import__('openbot_current_market');source=market.load(self.packet/'candles/5m.json')
        f=pd.DataFrame(source['bars'],columns=KLINE_COLUMNS)
        f['date']=pd.to_datetime(f.open_time,unit='ms',utc=True);f['available_at_ms']=f.close_time+1
        for k in ['high','low']:f[k]=pd.to_numeric(f[k])
        level=confirmed_swings(f)[-1]
        claim=dict(text='Structured confirmed swing',classification='NUMERIC_VERIFIED',evidence_id='source-level',
                   price=str(level['price']),source_sha256=source['source']['sha256'],available_at_ms=level['known_at_ms'],
                   feature='CONFIRMED_SWING',swing=dict(feature_version='chart-swings-2L2R-v1',timeframe='5m',**{k:level[k] for k in ['pivot_open_ms','known_at_ms','kind']}))
        assessment=dict(schema='openbot.vision.assessment.v2',candidate_id=self.packet.name,packet_sha256=self.seal['packet_sha256'],
                        cutoff_ms=self.identity['as_of_ms'],execution_authority='NONE',order_authorized=False,research_status='WATCH',
                        interest='MARKET_INTERESTING',trigger='UNKNOWN',admissibility='NOT_ESTABLISHED',images=[],observations=[claim],
                        hypotheses=[],contradictions=[],unknowns=[],insight_gained=None,confidence='PARTIAL_EVIDENCE')
        skills.validate_assessment(self.packet,assessment,self.revisions)
        wrong=level['pivot_open_ms']+300000
        claim['swing']['known_at_ms']=wrong;claim['available_at_ms']=wrong
        with self.assertRaisesRegex(DataError,'SWING_CONFIRMATION'):skills.validate_assessment(self.packet,assessment,self.revisions)

    def test_vwap_is_actually_plotted_and_matches_quote_base_utc_math(self):
        import matplotlib.axes
        market=__import__('openbot_current_market')
        request=self.request(timeframe='15m',visible_candles=20,overlays=['vwap'])['payload']['chart']
        called=[];actual_plot=matplotlib.axes.Axes.plot
        def observed(axis,*args,**kwargs):
            called.append(kwargs.get('label'));return actual_plot(axis,*args,**kwargs)
        with patch.object(matplotlib.axes.Axes,'plot',observed):receipt=render(self.packet,request,self.revisions)
        self.assertIn('VWAP',called)
        self.assertEqual(sum(label in {'VWAP','Session VWAP'} for label in called),1)
        rows=market.load(self.packet/'candles/15m.json')['bars'];day=rows[-1][0]//86400000*86400000
        rows=[r for r in rows if r[0]>=day]
        expected=sum(float(r[7]) for r in rows)/sum(float(r[5]) for r in rows)
        self.assertAlmostEqual(receipt['indicator_last_values']['vwap'],expected,places=10)

    def test_candidate_byte_cap_checks_the_new_image_too(self):
        prior=self.revisions/'synthetic-byte-budget';prior.mkdir(parents=True)
        with (prior/'chart.png').open('wb') as stream:stream.truncate(24*1024*1024-1)
        request=self.request()['payload']['chart']
        with self.assertRaisesRegex(DataError,'BYTE_BUDGET'):render(self.packet,request,self.revisions)
        self.assertFalse((self.revisions/'real-vision-r1').exists())


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory();self.addCleanup(self.scratch.cleanup)
        self.root=Path(self.scratch.name);self.roots={}
        contract=json.loads((skills.PACK/'contract.json').read_text())
        for a in contract['assignments']:
            owner=self.root/a['owner'];self.roots[a['owner']]=str(owner)
            for sid in a['skills']:
                target=owner/sid;target.mkdir(parents=True);(target/'SKILL.md').write_text('OWNER-PRIVATE-ORIGINAL:'+sid)
            (owner/'generic-untouched').mkdir();(owner/'generic-untouched/SKILL.md').write_text('generic')
        self.before={k:inventory(v) for k,v in self.roots.items()};self.tx=self.root/'transaction'

    def test_opt_in_install_and_exact_rollback_in_shadow_only(self):
        prepare(self.roots,self.tx)
        with self.assertRaises(DataError):apply(self.tx)
        self.assertEqual(apply(self.tx,True)['status'],'APPLIED')
        self.assertEqual(rollback(self.tx,True)['status'],'ROLLED_BACK')
        self.assertEqual(self.before,{k:inventory(v) for k,v in self.roots.items()})

    def test_drift_aborts_before_any_assignment_changed(self):
        prepare(self.roots,self.tx)
        p=next(Path(self.roots['astrabot-lead']).glob('*/SKILL.md'));p.write_text('changed by owner')
        before={k:inventory(v) for k,v in self.roots.items()}
        with self.assertRaises(DataError):apply(self.tx,True)
        self.assertEqual(before,{k:inventory(v) for k,v in self.roots.items()})

    def test_partial_failure_restores_every_original(self):
        prepare(self.roots,self.tx)
        real_replace=os.replace;calls=0
        def fail_once(source,target):
            nonlocal calls
            if '/staged/' in str(source):
                calls+=1
                if calls==3:raise OSError('injected scratch rename failure')
            return real_replace(source,target)
        with patch('trading_lab.skill_install.os.replace',side_effect=fail_once):
            with self.assertRaises(OSError):apply(self.tx,True)
        self.assertEqual(self.before,{k:inventory(v) for k,v in self.roots.items()})

    def test_tampered_subset_transaction_rejected_before_mutation(self):
        prepare(self.roots,self.tx);path=self.tx/'transaction.private.json'
        plan=json.loads(path.read_text());plan['entries']=plan['entries'][:1];path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(DataError,'EXACT_27'):apply(self.tx,True)
        self.assertEqual(self.before,{k:inventory(v) for k,v in self.roots.items()})

    def test_owner_root_symlink_swap_rejected_before_mutation(self):
        prepare(self.roots,self.tx)
        owner=Path(self.roots['astrabot-lead']);moved=self.root/'moved-lead';owner.rename(moved)
        other=self.root/'unrelated';shutil.copytree(moved,other);before=inventory(other);owner.symlink_to(other,target_is_directory=True)
        with self.assertRaisesRegex(DataError,'ROOT_IDENTITY_OR_SYMLINK'):apply(self.tx,True)
        self.assertEqual(before,inventory(other))
