"""Whole-run fault injection over fake APIs and observed provider-shaped storage.

All replies are fixtures. Zero genuine market/model requests in these tests.
"""
import json,os,sqlite3,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from researcher import openbot_runner as runner
from researcher.diagnostic_export import verify_zip
from researcher.contracts import encode,digest
from researcher.agent_review import _material
from researcher.settings import ROOT
import test_workflow_e2e as workflow


class WorkflowLifecycleRecovery(unittest.TestCase):
    def setUp(self):
        self.w=workflow.CompleteWorkflow();self.w.setUp();self.addCleanup(self.w.doCleanups)

    def test_both_ai_stages_survive_same_agent_task_pointer_changes(self):
        w=self.w;original_dispatch=w.app.dispatch_once;original_status=runner.status
        def dispatch(args,job=None,receipt=None):
            result=original_dispatch(args,job,receipt);n=len(w.app.submitted)
            with sqlite3.connect(w.f.config['openbot_db']) as db:
                db.execute('INSERT INTO projection_threads VALUES(?,?,?)',(f'THREAD_{n}','AGENT',f'TURN_{n}'))
                db.execute('UPDATE projection_agents SET thread_id=?',(f'THREAD_{n}',))
            return result
        def status(*args,**kwargs):
            result=original_status(*args,**kwargs)
            if result['state'] in runner.FINAL:
                with sqlite3.connect(w.f.config['openbot_db']) as db:db.execute("UPDATE projection_agents SET thread_id='MAIN'")
            return result
        w.app.dispatch_once=dispatch
        with patch.object(runner,'status',side_effect=status):job,state,report=w.run_workflow()
        self.assertEqual(state['state'],'COMPLETED',state)
        ai=report['ai_research']
        self.assertEqual(ai['model_tasks'],2)
        self.assertEqual(ai['stages']['SHORTLIST']['accepted'],len(w.app.input_cards))
        self.assertEqual(ai['state'],'AI_RESEARCH_COMPLETE')
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))

    def test_owner_authorized_archived_smoke_uses_the_paged_verifier_without_scanning(self):
        w=self.w
        installed=w.f.workspace/'.agents/skills/openbot-market-research/SKILL.md';installed.parent.mkdir(parents=True)
        installed.write_text((ROOT/'integration/openbot-market-research/SKILL.md').read_text().replace('@@RESEARCH_ROOT@@',str(ROOT)))
        prompt=runner.SMOKE_PROMPT.read_text().replace('@@APPROVED_COMMIT@@','7'*40)
        with sqlite3.connect(w.f.config['openbot_db']) as db:db.execute('UPDATE projection_mailbox_messages SET text=?',(prompt,))
        names=['openbot.start_task','openbot.attach_files_to_response']
        arguments={'names':names}
        schemas=[{'name':names[0],'inputSchema':{'type':'object','additionalProperties':False,
            'properties':{'title':{'type':'string'},'brief':{'type':'string'}},'required':['title','brief']}},
            {'name':names[1],'inputSchema':{'type':'object','additionalProperties':False,
            'properties':{'paths':{'type':'array'}},'required':['paths']}}]
        w.f.parent.extend([w.app.envelope(w.clock(),'response_item',{'type':'function_call','namespace':'openbot',
            'name':'tool_describe','call_id':'DISCOVERY','arguments':json.dumps(arguments)}),
            w.app.envelope(w.clock(),'event_msg',{'type':'item_completed','turn_id':'PARENT_TURN','thread_id':'PARENT',
                'item':{'type':'DynamicToolCall','id':'DISCOVERY','namespace':'openbot','tool':'tool_describe',
                    'arguments':arguments,'status':'completed','success':True,
                    'content_items':[{'type':'inputText','text':json.dumps({'tools':schemas})}]}}),
            w.app.envelope(w.clock(),'response_item',{'type':'function_call_output','call_id':'DISCOVERY',
                'output':json.dumps({'tools':schemas})})])
        w.app.write('PARENT',w.f.parent)
        prior=w.base/'jobs'/('20000101T000000Z-'+'c'*32);(prior/'review').mkdir(parents=True)
        packet=json.loads(encode(w.f.request))
        for card in packet['cards']:card['mode']='LIVE'
        packet['material_sha256']=digest(encode(_material(packet)).encode())
        (prior/'review'/(packet['material_sha256']+'.request.json')).write_text(encode(packet))
        (prior/'state.json').write_text(encode({'start_proof':{'status':'VERIFIED_OPENBOT_AGENT_COMMAND'},
            'scanner_started_at_utc':w.f.at,'fixture_only':True}))
        with patch('researcher.discovery.scan_market_research') as scanner:
            job,state,report=w.run_workflow()
        scanner.assert_not_called()
        self.assertEqual(state['state'],'PARTIAL')
        self.assertEqual(report['smoke_result']['status'],'VERIFIED_REVIEW')
        self.assertEqual(report['smoke_result']['tool_discovery']['status'],'VERIFIED_CURRENT_PARENT_TOOL_DISCOVERY')
        self.assertFalse(report['market_scan_started'])
        self.assertEqual(report['native_transport_preflight']['accepted'],1)
        self.assertEqual(len(w.app.submitted),1)
        proof=report['native_transport_preflight']['native_receipt']
        self.assertGreater(proof['verified_evidence_pages'],0)
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))
        self.assertFalse(report['trade_authorization'])

    def test_archived_ai_core_smoke_runs_both_stages_on_shipped_source(self):
        w=self.w
        prompt=runner.AI_SMOKE_PROMPT.read_text().replace('@@APPROVED_COMMIT@@','7'*40)
        with sqlite3.connect(w.f.config['openbot_db']) as db:
            db.execute('UPDATE projection_mailbox_messages SET text=?',(prompt,))
        with patch('researcher.native_runtime.integration_preflight',return_value={'status':'FIXTURE_READER_ONLY'}), \
                patch('researcher.native_runtime.attest_smoke_discovery',return_value={'status':'VERIFIED_FIXTURE_TOOLS'}):
            job,state,report=w.run_workflow()
        self.assertEqual(state['state'],'COMPLETED',report.get('smoke_result'))
        self.assertFalse(report['market_scan_started'])
        self.assertEqual(report['costs']['market_http_requests'],0)
        self.assertEqual(report['mode'],'AUTHENTIC_REPLAY')
        self.assertEqual(report['smoke_result']['status'],'VERIFIED_AI_CORE_REPLAY')
        self.assertFalse(report['ai_research']['current_market_interpretation'])
        self.assertEqual(len(w.app.submitted),2)
        replay=runner.replay_native(job)
        self.assertEqual(len(replay['reviews']),2)
        self.assertTrue(all(r['status']=='VERIFIED_RECEIPT' for r in replay['reviews']),replay)
        self.assertEqual(replay['artifact']['saved_ai_reconciliation']['state'],'AI_RESEARCH_COMPLETE')

    def test_rejected_final_reply_preserves_verified_discovery_without_a_fallback(self):
        def transform(request,reply):
            if request.get('stage')=='SHORTLIST':
                reply['rows'][0]['support']=['invented-evidence']
            return reply
        self.w.app.reply_transform=transform
        job,state,report=self.w.run_workflow()
        self.assertEqual(state['state'],'PARTIAL')
        ai=report['ai_research']
        self.assertEqual(ai['state'],'AI_INPUT_INVALID')
        self.assertEqual(ai['stages']['DISCOVERY']['status'],'AI_DISCOVERY_VERIFIED')
        self.assertEqual(ai['stages']['SHORTLIST']['reason'],'AGENT_REPLY_CITATION')
        self.assertEqual(ai['provider_attempts'],2)
        self.assertEqual(report['shortlist'],[])
        self.assertEqual(report['conditional_research_candidates'],[])
        self.assertTrue(ai['investigations'])
        self.assertFalse(report['trade_authorization'])
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))

    def test_zero_candidate_market_can_complete_with_a_cited_null(self):
        self.w.api.names=('BTCUSDT','ETHUSDT')
        _,state,report=self.w.run_workflow()
        self.assertEqual(state['state'],'COMPLETED',report['ai_research']['state'])
        self.assertEqual(report['coverage']['eligible_contracts'],2)
        self.assertEqual(report['conditional_research_candidates'],[])
        self.assertEqual(report['shortlist'],[])
        self.assertEqual(report['llm_calls'],2)
        self.assertEqual(report['ai_research']['stages']['SHORTLIST']['reply']['assessment']['finding'],
                         'NO_SUPPORTED_OPPORTUNITY')
        self.assertFalse(report['trade_authorization'])
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))

    def test_completed_child_without_receipt_stays_incomplete(self):
        from researcher.contracts import ContractError
        from researcher.native_app import collect
        def reject_completed(*args,**kwargs):
            if collect(*args,**kwargs) is not None:
                raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        with patch('researcher.native_app.collect',side_effect=reject_completed):
            _,state,report=self.w.run_workflow()
        self.assertEqual(state['state'],'PARTIAL')
        ai=report['ai_research']
        self.assertEqual(ai['state'],'AI_RECEIPT_UNVERIFIED')
        self.assertEqual(ai['stages']['DISCOVERY']['reason'],'NATIVE_UNAUTHORIZED_TOOL')
        self.assertEqual(ai['provider_attempts'],0)
        self.assertEqual(len(self.w.app.submitted),1)
        self.assertNotIn('SHORTLIST',ai['stages'])
        self.assertEqual(report['conditional_research_candidates'],[])

    def test_exact_setup_message_archive_preflight_then_full_current_scan_are_one_workflow(self):
        w=self.w
        installed=w.f.workspace/'.agents/skills/openbot-market-research/SKILL.md';installed.parent.mkdir(parents=True)
        installed.write_text((ROOT/'integration/openbot-market-research/SKILL.md').read_text().replace('@@RESEARCH_ROOT@@',str(ROOT)))
        prompt=runner.ACCEPTANCE_PROMPT.read_text().replace('@@APPROVED_COMMIT@@','7'*40)
        with sqlite3.connect(w.f.config['openbot_db']) as db:db.execute('UPDATE projection_mailbox_messages SET text=?',(prompt,))
        # A previous live-capture shape with entirely synthetic fixture values.
        # It exercises the real saved-packet locator; no live authenticity is claimed.
        prior=w.base/'jobs'/('20000101T000000Z-'+'c'*32);(prior/'review').mkdir(parents=True)
        packet=json.loads(encode(w.f.request))
        for card in packet['cards']:card['mode']='LIVE'
        packet['material_sha256']=digest(encode(_material(packet)).encode())
        (prior/'review'/(packet['material_sha256']+'.request.json')).write_text(encode(packet))
        (prior/'state.json').write_text(encode({'start_proof':{'status':'VERIFIED_OPENBOT_AGENT_COMMAND'},
            'scanner_started_at_utc':w.f.at,'fixture_only':True}))
        job,state,report=w.run_workflow()
        self.assertEqual(state['state'],'COMPLETED',state)
        self.assertEqual(report['native_transport_preflight']['status'],'VALIDATED_ADVISORY_ONLY')
        self.assertFalse(report['native_transport_preflight']['current_market_interpretation'])
        self.assertEqual(report['native_transport_preflight']['observed_model_attempts'],1)
        self.assertEqual(report['ai_research']['state'],'AI_RESEARCH_COMPLETE')
        self.assertEqual(len(w.app.submitted),report['llm_calls']+1)
        self.assertEqual(state['transport_model_attempts'],1)
        self.assertEqual(sum('card_id' in c and c['mode']=='AUTHENTIC_REPLAY' for c in w.app.input_cards),1)
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))
        self.assertFalse(report['trade_authorization'])
