"""Contract faithful offline fixtures. No genuine model calls or market access."""
import json
import sqlite3
import time
import unittest
from unittest.mock import patch
from researcher.contracts import ContractError,encode
from researcher.native_app import wait_for_reply
import test_native_runtime as fixture


class DurableNativeHandoff(unittest.TestCase):
    def setUp(self):
        self.f=fixture.CodexRuntimeFixtures();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.folder=self.f.root/'review';self.folder.mkdir()
        (self.folder/(self.f.key+'.request.json')).write_text(encode(self.f.request))

    def test_reader_fault_after_authorization_cannot_suppress_published_task_or_wait(self):
        states=[];began=time.monotonic()
        with patch('researcher.native_app.collect',side_effect=sqlite3.OperationalError('database is locked')):
            receipt=wait_for_reply(self.folder,self.f.key,self.f.cf,wait_seconds=1,
                clock=lambda:self.f.time(5),progress=lambda state,**fields:states.append(state))
        self.assertTrue((self.folder/(self.f.key+'.review-task.json')).is_file())
        self.assertIn('REVIEW_READY',states)
        self.assertGreaterEqual(time.monotonic()-began,.95)
        self.assertEqual(receipt['status'],'NATIVE_REVIEW_TIMED_OUT')
        self.assertEqual(receipt['first_error']['stage'],'RECEIPT_COLLECTION')
        self.assertEqual(receipt['first_error']['code'],'NATIVE_STORAGE_LOCKED')
        self.assertEqual(receipt['observed_model_attempts'],0)

    def test_invalid_publication_reports_stage_and_never_waits_or_invokes(self):
        with patch('researcher.native_app.prepare',side_effect=OSError('secret path should not escape')):
            receipt=wait_for_reply(self.folder,self.f.key,self.f.cf,wait_seconds=1)
        self.assertEqual(receipt['status'],'NATIVE_TASK_PUBLICATION_FAILED')
        self.assertEqual(receipt['first_error']['stage'],'TASK_PUBLICATION')
        self.assertEqual(receipt['terminal_error'],receipt['first_error'])
        self.assertNotIn('secret',encode(receipt))

    def test_delayed_real_shaped_receipt_preserves_input_and_records_ready_running_verified(self):
        from researcher.native_app import collect as actual
        states=[];calls=[];began=time.monotonic()
        def delayed(*args,**kwargs):
            calls.append(1)
            return None if len(calls)==1 else actual(*args,**kwargs)
        with patch('researcher.native_app.collect',side_effect=delayed):
            receipt=wait_for_reply(self.folder,self.f.key,self.f.cf,wait_seconds=2,
                clock=lambda:self.f.time(5),progress=lambda state,**fields:states.append(state))
        self.assertEqual(receipt['status'],'NATIVE_RECEIPT_COLLECTED')
        self.assertGreaterEqual(time.monotonic()-began,.95)
        self.assertEqual(states[0],'REVIEW_READY')
        self.assertIn('REVIEW_RUNNING',states);self.assertIn('REVIEW_VERIFIED',states)
        task=json.loads((self.folder/(self.f.key+'.review-task.json')).read_text())
        self.assertEqual(task,{'title':'OPENBOT-RESEARCH-'+self.f.key,'brief':self.f.brief})
        self.assertEqual(receipt['observed_model_attempts'],1)

    def test_incompatible_or_inaccessible_reader_is_bounded_and_precise(self):
        for error,code in [(OSError('private executable'),'NATIVE_READER_PROCESS_UNAVAILABLE'),
                (sqlite3.OperationalError('disk I/O error'),'NATIVE_STORAGE_UNAVAILABLE'),
                (ContractError('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED'),'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')]:
            with self.subTest(code=code),patch('researcher.native_app.collect',side_effect=error):
                receipt=wait_for_reply(self.folder,self.f.key,self.f.cf,wait_seconds=0,clock=lambda:self.f.time(5))
                self.assertEqual(receipt['first_error']['code'],code)
                self.assertEqual(receipt['observed_model_attempts'],0)
                self.assertTrue((self.folder/(self.f.key+'.review-task.json')).exists())
                self.assertNotIn('private',encode(receipt))

    def test_stale_request_and_wrong_material_never_publish_usable_task(self):
        receipt=wait_for_reply(self.folder,'0'*64,self.f.cf,clock=lambda:self.f.time(5))
        self.assertEqual(receipt['status'],'NATIVE_TASK_PUBLICATION_FAILED')
        receipt=wait_for_reply(self.folder,self.f.key,self.f.cf,clock=lambda:self.f.time(601))
        self.assertEqual(receipt['first_error']['code'],'NATIVE_REQUEST_STALE')

    def test_duplicate_task_threads_are_terminal_and_do_not_count_models(self):
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute('INSERT INTO projection_agent_threads SELECT * FROM projection_agent_threads')
        receipt=wait_for_reply(self.folder,self.f.key,self.f.cf,wait_seconds=1,clock=lambda:self.f.time(5))
        self.assertEqual(receipt['status'],'NATIVE_HANDOFF_UNATTESTED')
        self.assertEqual(receipt['observed_model_attempts'],0)
        self.assertLess(receipt['elapsed_seconds'],1)

    def test_midflight_config_change_is_rejected_without_a_second_request(self):
        original=self.f.cf.read_text()
        def change(*args,**kwargs):
            self.f.cf.write_text(original+'\n');return None
        with patch('researcher.native_app.collect',side_effect=change):
            receipt=wait_for_reply(self.folder,self.f.key,self.f.cf,wait_seconds=2,clock=lambda:self.f.time(5))
        self.assertEqual(receipt['status'],'NATIVE_AUDIT_CONFIG_INVALID')
        self.assertEqual(receipt['observed_model_attempts'],0)

    def test_truncated_skill_and_failed_task_publication_fail_closed(self):
        skill=self.f.workspace/'.agents/skills/market-research-review/SKILL.md'
        skill.write_text(skill.read_text()[:-1])
        receipt=wait_for_reply(self.folder,self.f.key,self.f.cf,clock=lambda:self.f.time(5))
        self.assertEqual(receipt['first_error']['code'],'AGENT_SKILL_HASH')
        self.assertFalse((self.folder/(self.f.key+'.review-task.json')).exists())

    def test_failed_native_task_has_precise_cause_instead_of_waiting_for_a_final(self):
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute("DELETE FROM projection_thread_messages WHERE author='assistant'")
            db.execute("UPDATE projection_turns SET status='failed' WHERE turn_id='CHILD_TURN'")
        receipt=wait_for_reply(self.folder,self.f.key,self.f.cf,wait_seconds=1,clock=lambda:self.f.time(5))
        self.assertEqual(receipt['status'],'NATIVE_TASK_FAILED')
        self.assertEqual(receipt['first_error']['stage'],'RECEIPT_COLLECTION')
        self.assertEqual(receipt['observed_model_attempts'],0)
