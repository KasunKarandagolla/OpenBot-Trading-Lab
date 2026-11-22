"""One Researcher with a different configured model on the next owner run."""
import json
import sqlite3
import unittest
from unittest.mock import patch

from researcher import native_host, openbot_runner as runner
from researcher.agent_review import exchange, make_request
from researcher.contracts import ContractError, encode
from researcher.native_app import observe_handoff
from researcher.native_runtime import collect, integration_preflight
from researcher.settings import ROOT
import test_native_handoff as handoff_fixture


class DynamicModelIdentity(unittest.TestCase):
    def setUp(self):
        self.job = handoff_fixture.NativeHandoff()
        self.job.setUp()
        self.addCleanup(self.job.doCleanups)

    def configure(self, model):
        fixture = self.job.f
        fixture.agent['model'] = model
        with sqlite3.connect(fixture.config['openbot_db']) as db:
            db.execute('UPDATE projection_agents SET model=?,agent_json=?', (model, encode(fixture.agent)))

    def complete_first(self):
        f = self.job
        self.complete_review()
        self.assertEqual(f.receipt['evidence_pages'], 10)
        runner._transition(f.folder, 'PARTIAL')

    def complete_review(self):
        f = self.job

        def ready():
            f.ticket()
            self.assertTrue(f.app.dispatch_once(f.args, f.job, f.receipt))
            f.on_sleep = f.app.complete_due

        result = f.wait(ready)
        self.assertEqual(result['status'], 'NATIVE_RECEIPT_COLLECTED', result)

    def test_historical_ticket_parent_child_and_ten_pages_survive_new_configured_model(self):
        f = self.job
        self.complete_first()
        self.configure('fixture-supported-model-B')
        observed = observe_handoff(f.f.config, identity=f.f.identity, directory=f.directory,
                                   material=f.material, as_of=f.clock())
        self.assertTrue(observed['task_created'])
        raw, audit = collect(f.request, f.f.config, as_of=f.clock(), directory=f.directory)
        self.assertEqual(audit['model'], f.f.identity['model'])
        self.assertEqual(audit['native_identity'], f.f.identity)
        self.assertEqual(audit['verified_evidence_pages'], 10)
        self.assertEqual(audit['reply_validation_status'], 'VALIDATED')
        self.assertEqual(len(f.app.submitted), 1)
        self.assertTrue(raw)

    def test_next_owner_job_captures_and_executes_its_own_supported_model(self):
        f = self.job
        self.complete_first()
        first_identity = dict(f.f.identity)
        first_dir, first_request = f.directory, f.request
        model = 'fixture-next-codex-model'
        self.configure(model)
        at = f.clock()
        cfg = f.f.config
        with sqlite3.connect(cfg['openbot_db']) as db:
            db.execute("UPDATE projection_turns SET status='completed',completed_at=? WHERE turn_id='PARENT_TURN'", (at,))
            db.execute("UPDATE projection_provider_sessions SET state='closed' WHERE id='PARENT_SESSION'")
            db.execute("UPDATE projection_threads SET active_turn_id='NEXT_TURN' WHERE thread_id='MAIN'")
            db.execute('INSERT INTO projection_provider_sessions VALUES(?,?,?,?,?,?)',
                       ('NEXT_SESSION','MAIN','codex','NEXT',model,'active'))
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',
                       ('NEXT_TURN','MAIN','NEXT_SESSION','running',at,None))
            db.execute('INSERT INTO projection_deliveries VALUES(?,?,?)', ('NEXT_TURN','AGENT','OWNER_NEXT'))
            db.execute('INSERT INTO projection_mailbox_messages VALUES(?,?,?)',
                       ('OWNER_NEXT','Run the complete market research now.','user'))
        with sqlite3.connect(cfg['provider_db']) as db:
            db.execute('INSERT INTO threads VALUES(?,?,?,?,?)', ('NEXT',
                       str(f.f.root/'sessions/NEXT.jsonl'), str(f.f.workspace), 'openai', model))
        key = 'b'*32
        record = f.app.envelope
        f.f.parent = [
            record(at,'session_meta',{'id':'NEXT','originator':'openbot','model_provider':'openai',
                   'cli_version':'0.169.0','cwd':str(f.f.workspace)}),
            record(at,'turn_context',{'turn_id':'NEXT_TURN','model':model}),
            record(at,'event_msg',{'type':'item_completed','turn_id':'NEXT_TURN','thread_id':'NEXT',
                   'item':{'type':'CommandExecution','status':'completed','exit_code':0,'cwd':str(ROOT),
                           'command':['python3','-m','researcher.openbot_runner','start','--request-id',key]}})]
        f.app.parent_session='NEXT'
        f.app.parent_turn='NEXT_TURN'
        f.app.write('NEXT', f.f.parent)
        f.job=runner.start(key)['job_id']
        f.folder=runner._job(f.job)
        state=runner._read(f.folder/'state.json')
        self.assertEqual(state['native_identity']['model'], model)
        self.assertNotEqual(state['native_identity']['session_ref'], first_identity['session_ref'])
        self.assertEqual(runner.attest_start(state,cfg)['status'], 'VERIFIED_OPENBOT_AGENT_COMMAND')

        f.f.identity=state['native_identity']
        f.request=make_request([f.f.card],f.f.facts,as_of=at,skill_sha256=first_request['skill_sha256'],
                               native_identity=f.f.identity)
        f.material=f.request['material_sha256']
        f.directory=f.folder/'review'
        f.directory.mkdir()
        (f.directory/(f.material+'.request.json')).write_text(encode(f.request), encoding='utf-8')
        self.complete_review()
        _, second=collect(f.request,cfg,as_of=f.clock(),directory=f.directory,require_configured_model=True)
        _, first=collect(first_request,cfg,as_of=f.clock(),directory=first_dir)
        self.assertEqual((first['model'],second['model']), (first_identity['model'],model))
        self.assertEqual(second['reply_validation_status'],'VALIDATED')
        self.assertEqual(len(f.app.submitted),2)

    def test_midflight_change_rejects_active_observation_and_advice_import(self):
        f = self.job
        def ready():
            f.ticket()
            self.assertTrue(f.app.dispatch_once(f.args, f.job, f.receipt))
            f.on_sleep=lambda:self.configure('fixture-unexpected-active-model')
        result=f.wait(ready)
        self.assertEqual(result['status'],'NATIVE_MODEL_SWITCHED',result)
        self.assertEqual(result['terminal_error']['diagnostic']['check'],'CONFIGURED_MODEL')
        self.assertFalse((f.directory/(f.material+'.reply.json')).exists())
        self.assertEqual(len(f.app.submitted),1)
        imported=exchange(f.directory,(),{},as_of=f.clock(),cached=True,
            previous={'material_sha256':f.material},audit_config=f.j.private,require_identity=True)
        self.assertEqual(imported['reason'],'NATIVE_MODEL_SWITCHED')

    def test_preflight_rejects_configuration_change_after_active_session_read(self):
        f = self.job
        self.configure('fixture-unexpected-active-model')
        with patch('researcher.native_identity.active_identity', return_value=f.f.identity):
            with self.assertRaisesRegex(ContractError, 'NATIVE_MODEL_SWITCHED') as failure:
                integration_preflight(f.f.config, as_of=f.clock())
        self.assertEqual(failure.exception.diagnostic['check'], 'CONFIGURED_MODEL')

    def test_historical_bridge_rejects_tampering_and_expiry_and_keeps_active_mode(self):
        f=self.job
        self.complete_first()
        model='fixture-supported-model-B'
        self.configure(model)
        values={'request':f.request,'as_of':f.clock(),'directory':str(f.directory)}
        path=f.f.root/'reader-input.json'
        def read(**changes):
            path.write_text(encode({'config_file':str(f.j.private),'values':{**values,**changes}}),encoding='utf-8')
            return native_host.execute('collect',path)
        self.assertEqual(read()[1]['model'],f.f.identity['model'])
        with self.assertRaisesRegex(ContractError,'NATIVE_MODEL_SWITCHED'):
            read(require_configured_model=True)
        with self.assertRaisesRegex(ContractError,'NATIVE_REQUEST_STALE'):
            read(as_of=f.f.time(606))
        with self.assertRaisesRegex(ContractError,'NATIVE_REVIEW_REQUEST_HASH'):
            read(request={**f.request,'model':model})
        for model_value,reason in ((None,'NATIVE_IDENTITY_UNAVAILABLE'),(model,'NATIVE_MODEL_SWITCHED')):
            with self.subTest(model_value=model_value), self.assertRaisesRegex(ContractError,reason):
                read(request={**f.request,'model':model_value,'native_identity':{**f.f.identity,'model':model_value}})
