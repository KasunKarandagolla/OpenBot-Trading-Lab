"""Fault injection around the parent stdout boundary, with no native calls."""
from contextlib import redirect_stdout
from io import StringIO
import json
import shlex
import sqlite3
import unittest
from unittest.mock import patch

from researcher import openbot_runner as runner
from researcher.agent_review import _material
from researcher.ai_core import AIResearch, DISCOVERY, INLINE
from researcher.contracts import ContractError, digest, encode
from researcher.native_app import wait_for_reply
from researcher.native_codex import review_brief
from researcher.native_handoff import (
    CONFIRMED_PAGES, EVIDENCE_PAGE_BYTES, PARENT_OUTPUT_BYTES, load_dispatch, packet,
)
from researcher.settings import load_config
from test_workflow_e2e import SimulatedApp
import test_openbot_runner as jobs


CLIP_BYTES = 8192
INCIDENT_BRIEF_BYTES = 39263


class ConfirmedDispatch(unittest.TestCase):
    def setUp(self):
        self.j = jobs.OpenBotRunnerContract()
        self.j.setUp()
        self.addCleanup(self.j.doCleanups)
        self.f = self.j.f
        self.seconds = 5
        self.monotonic = 0
        self.clock = lambda: self.f.time(self.seconds)
        self.on_sleep = lambda: None
        for target,value in [('researcher.openbot_runner.now_utc',self.clock),
                             ('researcher.native_app.time.monotonic',lambda:self.monotonic),
                             ('researcher.native_app.time.sleep',self.sleep)]:
            mock = patch(target,value)
            mock.start()
            self.addCleanup(mock.stop)
        self.job = runner.start(self.j.key)['job_id']
        self.folder = runner._job(self.job)
        self.directory = self.folder/'review'
        self.directory.mkdir()
        self.f.parent = self.f.parent[:2]
        self.f.write()
        self.app = SimulatedApp(self.f,self.clock)
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute('DELETE FROM projection_agent_threads')

    def sleep(self, duration):
        self.monotonic += duration
        self.seconds += duration
        self.on_sleep()

    def pin_request(self, transport=CONFIRMED_PAGES):
        research = AIResearch(identity=self.f.identity,clock=self.clock)
        request = research._request(DISCOVERY, [], at=self.clock(), mode='AUTHENTIC_REPLAY',
            extra={'fixture_evidence':'','omitted_count':0},config=load_config())
        request['input_transport'] = transport
        needed = INCIDENT_BRIEF_BYTES-len(review_brief(request).encode())
        request['fixture_evidence'] = ('Retained closed-bar evidence with symbols, boundaries and contradictions. ' *
                                       needed)[:needed]
        request['material_sha256'] = digest(encode(_material(request)).encode())
        self.assertEqual(len(review_brief(request).encode()), INCIDENT_BRIEF_BYTES)
        self.request = request
        self.material = request['material_sha256']
        self.lease = self.directory/(self.material+'.dispatch.json')
        (self.directory/(self.material+'.request.json')).write_text(encode(request),encoding='utf-8')

    def publish(self, transport=CONFIRMED_PAGES):
        from researcher.native_app import prepare
        self.pin_request(transport)
        prepare(self.directory,self.material,self.j.private,verified_identity=self.f.identity,as_of=self.clock())
        runner._transition(self.folder,'REVIEW_READY',review_transport=transport,material_sha256=self.material,
            request_prepared_at_utc=self.clock(),submission_expires_monotonic=90,request_expires_monotonic=600)

    def preview(self):
        # Use the actual CLI wire representation before imposing a separate
        # fixture channel limit. Runner success alone establishes no delivery.
        output = StringIO()
        with patch('sys.argv',['openbot_runner','status','--job-id',self.job,'--include-review']), redirect_stdout(output):
            self.assertEqual(runner.main(),0)
        return output.getvalue().encode()

    def options(self, frame):
        words = shlex.split(frame['reserve_command_prefix'].split(' reserve-review ',1)[1])
        self.assertEqual(words[-1],'--end-frame')
        self.assertNotIn(frame['z_end_frame'],frame['reserve_command_prefix'])
        return words[words.index('--confirm')+1],frame['z_end_frame']

    def accept(self, frame):
        result = runner.reserve_review(self.job,self.material,*self.options(frame))
        self.assertTrue(result['submission_permitted'])
        return runner._read(self.lease)

    def wait(self, ready, *, seconds=600):
        self.pin_request()
        def progress(state,**fields):
            runner._transition(self.folder,state,**fields)
            if state=='REVIEW_READY' and 'review_transport' in fields:
                ready(json.loads(self.preview()[:CLIP_BYTES]))
        return wait_for_reply(self.directory,self.material,self.j.private,clock=self.clock,
            wait_seconds=seconds,progress=progress,verified_identity=self.f.identity)

    def test_39263_byte_historical_inline_status_clips_after_creating_ticket(self):
        self.publish(INLINE)
        old = self.preview()
        self.assertGreater(len(old),INCIDENT_BRIEF_BYTES)
        self.assertLess(len(old),65536)
        with self.assertRaises(json.JSONDecodeError):
            json.loads(old[:CLIP_BYTES])
        self.assertTrue(self.lease.is_file())
        self.assertEqual(runner.status(self.job,include_review=True)['state'],'REVIEW_DISPATCH_RESERVED')

    def test_same_size_packet_preserves_all_bytes_behind_small_repeatable_preview(self):
        self.publish()
        raw = self.preview()
        self.assertLessEqual(len(raw),PARENT_OUTPUT_BYTES)
        self.assertFalse(self.lease.exists())
        frame = json.loads(raw[:CLIP_BYTES])
        self.assertEqual(self.preview(),raw)
        args,fingerprint,pages = packet(self.request,self.directory)
        self.assertEqual(frame['start_task_arguments'],args)
        self.assertEqual(frame['packet_sha256'],fingerprint)
        self.assertEqual(len(pages),4)
        self.assertTrue(all(len(page.encode())<=EVIDENCE_PAGE_BYTES for page in pages))
        recovered = ''.join(json.loads(page)['text'] for page in pages)
        self.assertEqual(recovered,review_brief(self.request))
        self.assertEqual(digest(recovered.encode()),fingerprint)
        self.assertEqual(frame['argument_integrity']['arguments_sha256'],digest(encode(args).encode()))
        self.assertEqual(frame['argument_integrity']['brief_bytes'],len(args['brief'].encode()))
        self.assertEqual(frame['argument_integrity']['brief_characters'],len(args['brief']))
        self.assertEqual(frame['argument_integrity']['brief_utf16_units'],len(args['brief'].encode('utf-16-le'))//2)
        ticket = self.accept(frame)
        self.assertEqual(ticket['preview_sha256'],digest(raw))
        self.assertEqual(load_dispatch(self.directory,self.request,as_of=self.clock())[3],ticket)
        self.assertFalse(runner.reserve_review(self.job,self.material,*self.options(frame))['submission_permitted'])
        status = runner.status(self.job,include_review=True)
        self.assertFalse(status['submission_permitted'])
        self.assertNotIn('start_task_arguments',status)

    def test_parent_truncation_or_bad_argument_bytes_leave_preview_recoverable(self):
        self.publish()
        raw = self.preview()
        frame = json.loads(raw)
        proof,end = self.options(frame)
        with self.assertRaises(json.JSONDecodeError):
            json.loads(raw[:-len(end)//2])
        for received,tail,reason in [
            (None,None,'NATIVE_PARENT_OUTPUT_TRUNCATED'),
            (proof[:-5],end,'NATIVE_PARENT_OUTPUT_TRUNCATED'),
            (proof,None,'NATIVE_PARENT_OUTPUT_TRUNCATED'),
            (proof,'BAD_HASH','NATIVE_PARENT_ARGUMENT_MISMATCH'),
            (('B' if proof[20]=='A' else 'A').join((proof[:20],proof[21:])),end,'NATIVE_PARENT_ARGUMENT_MISMATCH'),
        ]:
            with self.subTest(reason=reason), patch.object(runner,'assert_parent') as observer:
                denied = runner.reserve_review(self.job,self.material,received,tail)
                self.assertEqual(denied['reason'],reason)
                self.assertFalse(denied['submission_permitted'])
                self.assertFalse(self.lease.exists())
                observer.assert_not_called()
        self.assertEqual(self.preview(),raw)
        self.assertTrue(self.accept(frame))

    def test_concurrent_confirmations_grant_only_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        self.publish()
        frame = json.loads(self.preview())
        proof,end = self.options(frame)
        barrier = Barrier(2)
        verified = runner.assert_parent

        def meet(*args,**kwargs):
            barrier.wait(timeout=10)
            return verified(*args,**kwargs)

        with patch.object(runner,'assert_parent',side_effect=meet), ThreadPoolExecutor(max_workers=2) as executor:
            results = [executor.submit(runner.reserve_review,self.job,self.material,proof,end) for _ in range(2)]
            issued = [r.result(timeout=15)['submission_permitted'] for r in results]
        self.assertCountEqual(issued,[True,False])

    def test_mutated_saved_arguments_or_confirmation_receipt_cannot_be_collected(self):
        self.publish()
        frame = json.loads(self.preview())
        ticket = self.accept(frame)
        task = self.directory/(self.material+'.review-task.json')
        task.write_text(encode({**frame['start_task_arguments'],'brief':'changed'}),encoding='utf-8')
        with self.assertRaisesRegex(ContractError,'NATIVE_HANDOFF_UNATTESTED'):
            load_dispatch(self.directory,self.request,as_of=self.clock())
        task.write_text(encode(frame['start_task_arguments']),encoding='utf-8')
        runner._write(self.lease,{**ticket,'preview_sha256':'0'*64})
        with self.assertRaisesRegex(ContractError,'NATIVE_HANDOFF_UNATTESTED'):
            load_dispatch(self.directory,self.request,as_of=self.clock())

    def test_unconfirmed_parent_uses_no_submission_or_windows_receipt_observations(self):
        def ready(frame):
            runner.reserve_review(self.job,self.material)
        with patch('researcher.native_app.observe_handoff') as observe, patch('researcher.native_app.collect') as collect:
            result = self.wait(ready,seconds=4)
        self.assertEqual(result['status'],'NATIVE_PARENT_OUTPUT_TRUNCATED')
        observe.assert_not_called()
        collect.assert_not_called()
        self.assertFalse(self.lease.exists())

    def test_complete_preview_without_grant_is_distinct_from_missing_reserved_task(self):
        with patch('researcher.native_app.observe_handoff') as observe:
            result = self.wait(lambda _:None,seconds=4)
        self.assertFalse(self.lease.exists())
        self.assertEqual(result['status'],'NATIVE_PARENT_DELIVERY_UNCONFIRMED')
        observe.assert_not_called()

    def test_valid_reservation_without_task_is_still_missing(self):
        result = self.wait(self.accept,seconds=4)
        self.assertTrue(self.lease.exists())
        self.assertEqual(result['status'],'NATIVE_DISPATCH_RESERVED_TASK_MISSING')
        self.assertEqual(result['observed_model_attempts'],0)

    def test_acknowledged_task_with_delayed_projection_and_windows_timeout(self):
        from researcher.native_app import observe_handoff
        from researcher.native_identity import NativeEvidenceError
        seen = 0
        def transient(*args,**kwargs):
            nonlocal seen
            seen += 1
            if seen==1:
                raise NativeEvidenceError('NATIVE_STORAGE_TIMED_OUT')
            return observe_handoff(*args,**kwargs)
        def ready(frame):
            ticket = self.accept(frame)
            self.app.dispatch_once(frame['start_task_arguments'],self.job,ticket)
            # Release provider/app final projection only after the first
            # receipt read. The verifier still checks the exact bound turn.
            self.on_sleep = lambda:self.complete_after_retry(seen)
        with patch('researcher.native_app.observe_handoff',side_effect=transient):
            result = self.wait(ready,seconds=20)
        self.assertEqual(result['status'],'NATIVE_RECEIPT_COLLECTED',result)
        self.assertEqual(result['first_error']['code'],'NATIVE_STORAGE_TIMED_OUT')
        self.assertEqual(result['observed_model_attempts'],5)

    def test_complete_process_page_with_clipped_model_output_cannot_verify(self):
        def ready(frame):
            ticket = self.accept(frame)
            self.app.dispatch_once(frame['start_task_arguments'],self.job,ticket)
            rows=self.app.pending[0][-1]
            output=next(row['payload'] for row in rows if row['payload'].get('type')=='function_call_output')
            output['output']=output['output'][:-20]
            self.on_sleep=lambda:self.complete_after_retry(2)
        result = self.wait(ready,seconds=20)
        self.assertEqual(result['status'],'NATIVE_READ_INCOMPLETE')
        self.assertEqual(result['observed_model_attempts'],0)
        self.assertFalse((self.directory/(self.material+'.audit.json')).exists())

    def complete_after_retry(self, seen):
        if seen>=2:
            with patch('test_workflow_e2e.time.monotonic',return_value=self.monotonic+10):
                self.app.complete_due()
