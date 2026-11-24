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

    def test_historical_codex_receipt_survives_provider_change(self):
        f = self.job
        self.complete_first()
        for provider, model in (('opencode', 'fixture-backend/fixture-model'),
                                ('unregistered-provider', 'fixture-other-model')):
            with self.subTest(provider=provider):
                f.f.agent.update(provider=provider, model=model)
                with sqlite3.connect(f.f.config['openbot_db']) as db:
                    db.execute('UPDATE projection_agents SET model=?,agent_json=?',
                               (model, encode(f.f.agent)))
                observed = observe_handoff(f.f.config, identity=f.f.identity, directory=f.directory,
                                           material=f.material, as_of=f.clock())
                self.assertTrue(observed['task_created'])
                _, audit = collect(f.request, f.f.config, as_of=f.clock(), directory=f.directory)
                self.assertEqual(audit['native_identity'], f.f.identity)
                self.assertEqual(audit['verified_evidence_pages'], 10)
                with self.assertRaises(ContractError):
                    collect(f.request, f.f.config, as_of=f.clock(), directory=f.directory,
                            require_configured_model=True)

    def test_historical_provider_change_does_not_accept_a_forged_adapter(self):
        f = self.job
        self.complete_first()
        f.f.agent.update(provider='opencode', model='fixture-backend/fixture-model')
        with sqlite3.connect(f.f.config['openbot_db']) as db:
            db.execute('UPDATE projection_agents SET model=?,agent_json=?',
                       (f.f.agent['model'], encode(f.f.agent)))
        from researcher.native_identity import assert_parent
        with self.assertRaises(ContractError):
            assert_parent({**f.f.identity, 'adapter': 'forged'}, f.f.config, as_of=f.clock())

    def test_selection_status_distinguishes_reader_from_live_receipt(self):
        from researcher.native_identity import configured_capability
        f = self.job.f
        status = configured_capability(f.config)
        self.assertEqual(status['model'], f.identity['model'])
        self.assertEqual(status['model_selection'], 'MODEL_SELECTED')
        self.assertEqual(status['native_adapter'], 'NATIVE_ADAPTER_SUPPORTED')
        self.assertEqual(status['provider_available'], 'UNKNOWN_NOT_PROBED')
        self.assertEqual(status['native_receipt'], 'NOT_CHECKED')
        for provider, model, missing in (
                ('opencode', 'fixture-backend/fixture-model', 'COMPACT_TASK_PAGE_AND_TURN_ATTESTATION'),
                ('unregistered-provider', 'fixture-model', 'NATIVE_PROVIDER_ADAPTER')):
            with self.subTest(provider=provider):
                f.agent.update(provider=provider, model=model)
                with sqlite3.connect(f.config['openbot_db']) as db:
                    db.execute('UPDATE projection_agents SET model=?,agent_json=?', (model, encode(f.agent)))
                status = configured_capability(f.config)
                self.assertEqual((status['provider'], status['model']), (provider, model))
                self.assertEqual(status['native_adapter'], 'PROVIDER_ATTESTATION_UNSUPPORTED')
                self.assertEqual(status['missing_capability'], missing)
                self.assertEqual(status['native_receipt'], 'NOT_CHECKED')
                self.assertFalse(status['trade_authorization'])

    def test_midflight_provider_change_rejects_active_parent(self):
        from researcher.native_identity import assert_parent
        f = self.job.f
        f.agent.update(provider='opencode', model='fixture-backend/fixture-model')
        with sqlite3.connect(f.config['openbot_db']) as db:
            db.execute('UPDATE projection_agents SET model=?,agent_json=?',
                       (f.agent['model'], encode(f.agent)))
        with self.assertRaisesRegex(ContractError, 'NATIVE_MODEL_SWITCHED'):
            assert_parent(f.identity, f.config, require_configured_model=True, as_of=self.job.clock())

    def test_reused_session_captures_new_model_and_preserves_original_turn_receipt(self):
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
            db.execute("UPDATE projection_provider_sessions SET model=? WHERE id='PARENT_SESSION'", (model,))
            db.execute("UPDATE projection_threads SET active_turn_id='NEXT_TURN' WHERE thread_id='MAIN'")
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',
                       ('NEXT_TURN','MAIN','PARENT_SESSION','running',f.f.time(f.seconds + 1),None))
            db.execute('INSERT INTO projection_deliveries VALUES(?,?,?)', ('NEXT_TURN','AGENT','OWNER_NEXT'))
            db.execute('INSERT INTO projection_mailbox_messages VALUES(?,?,?)',
                       ('OWNER_NEXT','Run the complete market research now.','user'))
        with sqlite3.connect(cfg['provider_db']) as db:
            db.execute("UPDATE threads SET model=? WHERE id='PARENT'", (model,))
        f.seconds += 1
        at = f.clock()
        key = 'b'*32
        record = f.app.envelope
        f.f.parent.extend([
            record(at,'event_msg',{'type':'thread_settings_applied','thread_id':'PARENT',
                   'thread_settings':{'model':model}}),
            record(at,'event_msg',{'type':'task_started','turn_id':'NEXT_TURN'}),
            record(at,'turn_context',{'turn_id':'NEXT_TURN','model':model}),
            record(at,'event_msg',{'type':'item_completed','turn_id':'NEXT_TURN','thread_id':'PARENT',
                   'item':{'type':'CommandExecution','status':'completed','exit_code':0,'cwd':str(ROOT),
                           'command':['python3','-m','researcher.openbot_runner','start','--request-id',key]}})])
        f.app.parent_turn='NEXT_TURN'
        f.app.write('PARENT', f.f.parent)
        f.job=runner.start(key)['job_id']
        f.folder=runner._job(f.job)
        state=runner._read(f.folder/'state.json')
        self.assertEqual(state['native_identity']['model'], model)
        for ref_key in ('thread_ref', 'session_ref', 'external_session_ref'):
            self.assertEqual(state['native_identity'][ref_key], first_identity[ref_key])
        self.assertNotEqual(state['native_identity']['turn_ref'], first_identity['turn_ref'])
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
        observed = observe_handoff(cfg, identity=first_identity, directory=first_dir,
                                   material=first_request['material_sha256'], as_of=f.clock())
        self.assertTrue(observed['task_created'])
        self.assertEqual(observed['submission_attempts'], 1)
        self.assertEqual((first['model'],second['model']), (first_identity['model'],model))
        self.assertEqual(second['reply_validation_status'],'VALIDATED')
        self.assertEqual(len(f.app.submitted),2)

    def test_historical_child_model_remains_bound_to_the_original_turn(self):
        f = self.job
        self.complete_first()
        model = 'fixture-later-child-model'
        with sqlite3.connect(f.f.config['openbot_db']) as db:
            db.execute("UPDATE projection_provider_sessions SET model=? WHERE id='SESSION_1'", (model,))
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',
                       ('LATER_CHILD', 'THREAD_1', 'SESSION_1', 'running', f.f.time(f.seconds + 2), None))
        with sqlite3.connect(f.f.config['provider_db']) as db:
            db.execute("UPDATE threads SET model=? WHERE id='REVIEW_1'", (model,))
        path = f.f.root/'sessions/REVIEW_1.jsonl'
        records = [json.loads(line) for line in path.read_text().splitlines()]
        records.extend([
            f.app.envelope(f.f.time(f.seconds + 2), 'event_msg', {'type':'task_started','turn_id':'LATER_CHILD'}),
            f.app.envelope(f.f.time(f.seconds + 2), 'turn_context', {'turn_id':'LATER_CHILD','model':model}),
        ])
        f.app.write('REVIEW_1', records)
        _, audit = collect(f.request, f.f.config, as_of=f.clock(), directory=f.directory)
        self.assertEqual(audit['model'], f.f.identity['model'])
        self.assertEqual(audit['verified_evidence_pages'], 10)
        with self.assertRaisesRegex(ContractError, 'NATIVE_MODEL_SWITCHED'):
            collect(f.request, f.f.config, as_of=f.clock(), directory=f.directory, require_configured_model=True)

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
