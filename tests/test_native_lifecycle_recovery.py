"""Lifecycle fault injection using observed provider layouts; no live model calls."""
import copy
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from researcher.contracts import ContractError,encode
from researcher.agent_review import exchange
from researcher.native_identity import assert_current
from researcher.native_app import wait_for_reply
from researcher import openbot_runner as runner
import test_native_runtime as native
import test_openbot_runner as jobs


class ParentLifecycleRecovery(unittest.TestCase):
    def setUp(self):
        self.f=native.CodexRuntimeFixtures();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def advance_pointer(self):
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute("UPDATE projection_threads SET active_turn_id='NEXT_TURN'")
            db.execute("UPDATE projection_turns SET status='completed',completed_at=? WHERE turn_id='PARENT_TURN'",(self.f.time(4),))
            db.execute("UPDATE projection_provider_sessions SET state='closed' WHERE id='PARENT_SESSION'")
            db.execute('INSERT INTO projection_provider_sessions VALUES(?,?,?,?,?,?)',
                ('NEXT_SESSION','MAIN','codex','NEXT',self.f.agent['model'],'active'))
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',
                ('NEXT_TURN','MAIN','NEXT_SESSION','running',self.f.time(5),None))

    def publish(self):
        folder=self.f.root/'review';folder.mkdir()
        (folder/(self.f.key+'.request.json')).write_text(encode(self.f.request))
        return folder

    def test_collect_uses_frozen_parent_after_legitimate_pointer_and_session_change(self):
        self.advance_pointer()
        raw,audit=self.f.get()
        self.assertEqual(raw,self.f.raw);self.assertEqual(audit['native_identity'],self.f.identity)
        with self.assertRaises(ContractError):assert_current(self.f.identity,self.f.config)

    def test_cached_import_and_publication_use_original_parent_not_new_active_pointer(self):
        folder=self.publish();self.advance_pointer()
        receipt=wait_for_reply(folder,self.f.key,self.f.cf,clock=lambda:self.f.time(5))
        self.assertEqual(receipt['status'],'NATIVE_RECEIPT_COLLECTED',receipt)
        result=exchange(folder,(),{},as_of=self.f.time(5),previous={'material_sha256':self.f.key},
            cached=True,audit_config=self.f.cf,require_identity=True)
        self.assertEqual(result['status'],'VALIDATED_ADVISORY_ONLY',result)

    def test_changed_frozen_parent_bindings_still_fail_closed(self):
        original=Path(self.f.config['openbot_db']).read_bytes()
        changes=["UPDATE projection_turns SET thread_id='OTHER' WHERE turn_id='PARENT_TURN'",
            "UPDATE projection_turns SET started_at='2000-01-01T00:00:00+00:00' WHERE turn_id='PARENT_TURN'",
            "UPDATE projection_provider_sessions SET thread_id='OTHER' WHERE id='PARENT_SESSION'",
            "UPDATE projection_provider_sessions SET external_session_id='CHILD' WHERE id='PARENT_SESSION'",
            "UPDATE projection_threads SET agent_id='OTHER' WHERE thread_id='MAIN'"]
        for sql in changes:
            with self.subTest(sql=sql):
                with sqlite3.connect(self.f.config['openbot_db']) as db:db.execute(sql)
                with self.assertRaises(ContractError):self.f.get()
                with open(self.f.config['openbot_db'],'wb') as f:f.write(original)

    def test_later_parent_turn_is_outside_original_handoff_scope(self):
        self.advance_pointer()
        self.f.parent.append(self.f.record(5,'turn_context',{'turn_id':'NEXT_TURN','model':'next-turn-model'}))
        self.f.write()
        self.assertEqual(self.f.get()[0],self.f.raw)

    def test_child_app_turn_and_session_must_belong_to_exact_task_thread(self):
        original=Path(self.f.config['openbot_db']).read_bytes()
        for sql in ["UPDATE projection_turns SET thread_id='MAIN' WHERE turn_id='CHILD_TURN'",
                "UPDATE projection_provider_sessions SET thread_id='MAIN' WHERE id='CHILD_SESSION'"]:
            with self.subTest(sql=sql):
                with sqlite3.connect(self.f.config['openbot_db']) as db:db.execute(sql)
                with self.assertRaises(ContractError):self.f.get()
                with open(self.f.config['openbot_db'],'wb') as f:f.write(original)

    def test_duplicate_successful_parent_submissions_are_rejected_even_with_one_app_task(self):
        self.f.parent.append(copy.deepcopy(self.f.parent[-1]));self.f.write()
        with self.assertRaisesRegex(ContractError,'HANDOFF_UNATTESTED'):self.f.get()

    def test_parent_handoff_before_request_cannot_bind_substituted_task(self):
        self.f.parent[-1]['timestamp']=self.f.time(-1);self.f.write()
        with self.assertRaisesRegex(ContractError,'HANDOFF_UNATTESTED'):self.f.get()

    def test_receipt_only_resume_reaudits_completed_task_without_redispatch(self):
        folder=self.publish()
        (folder/(self.f.key+'.dispatch.json')).write_text(encode({'reserved_at_utc':self.f.at}))
        first=wait_for_reply(folder,self.f.key,self.f.cf,clock=lambda:self.f.time(5))
        self.advance_pointer()
        second=wait_for_reply(folder,self.f.key,self.f.cf,clock=lambda:self.f.time(5))
        self.assertEqual(first['status'],second['status']);self.assertEqual(second['status'],'NATIVE_RECEIPT_COLLECTED')
        self.assertEqual(len(list(folder.glob('*.review-task.json'))),1)
        self.assertEqual(len(list(folder.glob('*.dispatch.json'))),1)
        self.f.child[-1]['payload']['last_agent_message']='tampered';self.f.write()
        rejected=wait_for_reply(folder,self.f.key,self.f.cf,clock=lambda:self.f.time(5))
        self.assertEqual(rejected['status'],'NATIVE_REPLY_PROVENANCE')

    def test_persisted_task_creation_anchor_rejects_replacement_on_receipt_resume(self):
        folder=self.publish()
        first=wait_for_reply(folder,self.f.key,self.f.cf,clock=lambda:self.f.time(5))
        self.assertEqual(first['status'],'NATIVE_RECEIPT_COLLECTED')
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute("UPDATE projection_agent_threads SET thread_id='SUBSTITUTED_TASK'")
        resumed=wait_for_reply(folder,self.f.key,self.f.cf,clock=lambda:self.f.time(5))
        self.assertEqual(resumed['status'],'NATIVE_SESSION_MISMATCH')
        self.assertEqual(resumed['observed_model_attempts'],0)

    def test_first_reader_fault_does_not_mask_a_later_terminal_integrity_failure(self):
        folder=self.publish()
        with patch('researcher.native_app.collect',side_effect=[sqlite3.OperationalError('database is locked'),
                ContractError('NATIVE_UNAUTHORIZED_TOOL')]):
            receipt=wait_for_reply(folder,self.f.key,self.f.cf,clock=lambda:self.f.time(5),wait_seconds=2)
        self.assertEqual(receipt['first_error']['code'],'NATIVE_STORAGE_LOCKED')
        self.assertEqual(receipt['terminal_error']['code'],'NATIVE_UNAUTHORIZED_TOOL')
        self.assertEqual(receipt['status'],'NATIVE_UNAUTHORIZED_TOOL')

    def test_missing_task_after_reservation_has_a_precise_terminal_cause(self):
        folder=self.publish()
        with sqlite3.connect(self.f.config['openbot_db']) as db:db.execute('DELETE FROM projection_agent_threads')
        (folder/(self.f.key+'.dispatch.json')).write_text('{}')
        receipt=wait_for_reply(folder,self.f.key,self.f.cf,clock=lambda:self.f.time(5))
        self.assertEqual(receipt['terminal_error']['code'],'NATIVE_DISPATCH_RESERVED_TASK_MISSING')
        self.assertEqual(receipt['native_task_observation']['task_state'],'MISSING')


class DispatchRecovery(unittest.TestCase):
    def setUp(self):
        self.j=jobs.OpenBotRunnerContract();self.j.setUp();self.addCleanup(self.j.doCleanups)
        self.f=self.j.f;self.job=runner.start(self.j.key)['job_id'];self.folder=runner._job(self.job)
        review=self.folder/'review';review.mkdir()
        (review/(self.f.key+'.review-task.json')).write_text(encode({'title':'OPENBOT-RESEARCH-'+self.f.key,'brief':self.f.brief}))
        runner._transition(self.folder,'REVIEW_READY',material_sha256=self.f.key)
        with sqlite3.connect(self.f.config['openbot_db']) as db:db.execute('DELETE FROM projection_agent_threads')

    def test_dead_worker_never_issues_task_arguments_or_consumes_a_ticket(self):
        with patch.object(runner.os,'kill',side_effect=ProcessLookupError):result=runner.status(self.job,include_review=True)
        self.assertEqual(result['state'],'INTERRUPTED');self.assertNotIn('start_task_arguments',result)
        self.assertFalse(list((self.folder/'review').glob('*.dispatch.json')))

    def test_reserved_but_missing_task_is_reported_and_never_resubmitted(self):
        first=runner.status(self.job,include_review=True)
        second=runner.status(self.job,include_review=True)
        self.assertEqual(second['state'],'REVIEW_DISPATCH_RESERVED');self.assertNotIn('start_task_arguments',second)
        self.assertEqual(second['native_task_state'],'MISSING')
        self.assertEqual(first['dispatch_receipt'],second['dispatch_receipt'])

    def test_status_uses_frozen_parent_during_legitimate_active_pointer_change(self):
        runner.status(self.job,include_review=True)
        with sqlite3.connect(self.f.config['openbot_db']) as db:db.execute('UPDATE projection_threads SET active_turn_id=NULL')
        result=runner.status(self.job,include_review=True)
        self.assertEqual(result['state'],'REVIEW_DISPATCH_RESERVED',result)
        self.assertNotIn('start_task_arguments',result)
