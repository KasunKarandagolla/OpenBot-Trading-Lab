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

    def test_multiple_batches_survive_same_agent_task_pointer_changes(self):
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
        self.assertGreater(report['consultant']['batch_count'],1)
        self.assertEqual(report['consultant']['accepted'],len(w.app.input_cards))
        self.assertFalse(report['native_review_coverage']['unreviewed_or_stale_finalist_card_ids'])
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))

    def test_rejected_batch_preserves_independent_valid_interpretations_and_deterministic_results(self):
        first=[]
        def transform(request,reply):
            if not first:
                first.extend(c['card_id'] for c in request['cards'])
                reply['interpretations'][0]['priority']='INVALID_ENUM'
            return reply
        self.w.app.reply_transform=transform
        from researcher.native_workflow import plan_batches
        def with_oversized(*args,**kwargs):
            groups,omitted=plan_batches(*args,**kwargs)
            return groups,[*omitted,{'card_id':'oversized_fixture','native_symbol':'PARTIUSDT',
                'reason':'SINGLE_CARD_EXCEEDS_PROVIDER_INPUT_LIMIT; FULL_SKILL_RETAINED'}]
        with patch('researcher.native_workflow.plan_batches',side_effect=with_oversized):
            job,state,report=self.w.run_workflow()
        self.assertEqual(state['state'],'PARTIAL')
        self.assertEqual(report['consultant']['status'],'NATIVE_REVIEW_INCOMPLETE')
        self.assertEqual(report['consultant']['planning_error']['code'],'AGENT_INPUT_SIZE')
        self.assertEqual(report['consultant']['first_error']['code'],'AGENT_REPLY_ADVICE')
        self.assertGreater(report['consultant']['accepted'],0)
        self.assertTrue(report['native_control_comparison']['accepted_current_advice'])
        self.assertEqual(report['llm_calls'],len(self.w.app.submitted))
        self.assertTrue(any(c['reasoning_status']=='NATIVE_REVIEWED' for c in report['conditional_research_candidates']))
        self.assertTrue(any(c['card_id'] in first and c['native_review_status']=='NOT_REVIEWED' for c in report['candidate_consideration']))
        self.assertFalse(report['native_review_coverage']['complete_for_final_candidates'])
        self.assertFalse(report['trade_authorization']);self.assertEqual(report['shortlist'],[])
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))

    def test_zero_candidate_market_exports_honest_partial_without_inventing_model_calls(self):
        self.w.api.names=('BTCUSDT','ETHUSDT')
        with patch('subprocess.Popen',return_value=SimpleNamespace(pid=os.getpid())):
            job=runner.start(self.w.request_id)['job_id']
        state=runner.run_job(job)
        report=json.loads((runner._job(job)/'report.json').read_text())
        self.assertEqual(state['state'],'PARTIAL')
        self.assertEqual(report['coverage']['eligible_contracts'],2)
        self.assertEqual(report['conditional_research_candidates'],[]);self.assertEqual(report['shortlist'],[])
        self.assertEqual(report['llm_calls'],0);self.assertFalse(self.w.app.submitted)
        self.assertEqual(report['consultant']['cards'],0)
        self.assertFalse(report['trade_authorization'])
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))

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
        self.assertEqual(report['consultant']['status'],'VALIDATED_ADVISORY_ONLY')
        self.assertEqual(len(w.app.submitted),report['llm_calls']+1)
        self.assertEqual(state['transport_model_attempts'],1)
        self.assertFalse(report['native_review_coverage']['unreviewed_or_stale_finalist_card_ids'])
        archived={c['card_id'] for c in w.app.input_cards if c['mode']=='AUTHENTIC_REPLAY'}
        self.assertEqual(len(archived),1)
        self.assertFalse(archived & set(report['consultant']['reviewed_card_ids']))
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))
        self.assertFalse(report['trade_authorization'])
