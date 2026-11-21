"""Clock, SQLite and actual process interleavings for the native recovery."""
import json
import multiprocessing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from researcher import native_app, native_host, openbot_runner as runner
from researcher.contracts import ContractError
from researcher.native_identity import read_db
from researcher.settings import ROOT
import test_native_handoff as handoff


class ObservationRecovery(unittest.TestCase):
    def setUp(self):
        self.fixture=handoff.NativeHandoff()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_unreserved_observer_failure_closes_at_ninety(self):
        original=native_app.observe_handoff
        def observe(*args,**kwargs):
            if self.fixture.monotonic==0:
                return original(*args,**kwargs)
            raise ContractError('NATIVE_STORAGE_UNAVAILABLE')
        with patch.object(native_app,'observe_handoff',side_effect=observe):
            result=self.fixture.wait()
        self.assertEqual(result['status'],'NATIVE_SUBMISSION_UNVERIFIED',result)
        self.assertEqual(result['elapsed_seconds'],90)
        self.assertEqual(result['observed_model_attempts'],0)

    def test_reserved_task_reads_late_pages_and_eventually_verifies_original_receipts(self):
        f=self.fixture
        original=native_app.observe_handoff

        def observe(*args,**kwargs):
            if f.monotonic<100:
                raise ContractError('NATIVE_STORAGE_UNAVAILABLE')
            return original(*args,**kwargs)

        def tick():
            if f.monotonic!=95:
                return
            status=runner.status(f.job,include_review=True)
            self.assertEqual(status['state'],'REVIEW_SUBMISSION_UNVERIFIED')
            self.assertNotIn('start_task_arguments',status)
            pending=f.app.pending[0][-1]
            for page in range(8,11):
                value=runner.review_page(f.job,f.material,f.receipt['packet_sha256'],page)
                self.assertEqual(json.loads(value)['page'],page)
                # The provider-shaped records retain the actual late occurrence.
                for row in pending:
                    payload=row['payload']
                    if payload.get('call_id')==f'PAGE_{page}' or payload.get('item',{}).get('id')==f'PAGE_{page}':
                        row['timestamp']=f.clock()
            f.app.complete_due()

        def ready():
            f.ticket()
            self.assertTrue(f.app.dispatch_once(f.args,f.job,f.receipt))
            f.on_sleep=tick

        with patch.object(native_app,'observe_handoff',side_effect=observe):
            result=f.wait(ready)
        self.assertEqual(result['status'],'NATIVE_RECEIPT_COLLECTED',result)
        self.assertEqual(result['submission_observation_status'],'VERIFIED_AFTER_OBSERVER_INTERRUPTION')
        self.assertEqual(result['submission_observation_closed_seconds'],90)
        self.assertEqual(result['submission_attempts'],1)
        self.assertEqual(result['observed_model_attempts'],1)
        audit=json.loads((f.directory/(f.material+'.audit.json')).read_bytes())
        self.assertEqual(audit['verified_evidence_pages'],10)
        self.assertFalse(result['trade_authorization'])

    def test_only_timely_provider_attempts_can_recover_and_true_expiry_closes_pages(self):
        f=self.fixture
        original=native_app.observe_handoff

        def observe(*args,**kwargs):
            if f.monotonic<100:
                raise ContractError('NATIVE_STORAGE_UNAVAILABLE')
            return original(*args,**kwargs)

        def tick():
            if f.monotonic==95:
                f.record_submission(response={'taskId':'LATE_TASK','title':f.args['title']})

        def ready():
            with self.assertRaisesRegex(ContractError,'HANDOFF_UNATTESTED'):
                runner.review_page(f.job,f.material,'0'*64,1)
            f.ticket()
            f.on_sleep=tick

        with patch.object(native_app,'observe_handoff',side_effect=observe):
            result=f.wait(ready)
        self.assertEqual(result['status'],'NATIVE_SUBMISSION_OUTSIDE_WINDOW',result)
        with self.assertRaisesRegex(ContractError,'DISPATCH_WINDOW_CLOSED'):
            runner.review_page(f.job,f.material,f.receipt['packet_sha256'],1)

    def test_reserved_outage_does_not_renew_expiry_or_confirm_task_absence(self):
        f=self.fixture
        def tick():
            if f.monotonic==599:
                runner.review_page(f.job,f.material,f.receipt['packet_sha256'],10)
            if f.monotonic==600:
                with self.assertRaisesRegex(ContractError,'REQUEST_STALE'):
                    runner.review_page(f.job,f.material,f.receipt['packet_sha256'],10)
        def ready():
            f.ticket()
            f.on_sleep=tick

        with patch.object(native_app,'observe_handoff',
                          side_effect=ContractError('NATIVE_STORAGE_UNAVAILABLE')):
            result=f.wait(ready)
        self.assertEqual(result['submission_observation_closed_seconds'],90)
        self.assertEqual(result['elapsed_seconds'],600)
        self.assertEqual(result['first_error']['code'],'NATIVE_STORAGE_UNAVAILABLE')
        self.assertNotIn(result['status'],{'NATIVE_TASK_NOT_SUBMITTED','NATIVE_DISPATCH_RESERVED_TASK_MISSING'})
        with self.assertRaisesRegex(ContractError,'DISPATCH_WINDOW_CLOSED'):
            runner.review_page(f.job,f.material,f.receipt['packet_sha256'],10)

    def test_scoped_windows_reader_preserves_integrity_rejection_and_phase_timeout(self):
        f=self.fixture
        exe=f.f.root/'python.exe';exe.touch()
        config={'native_python':str(exe),'_config_file':str(f.j.private)}
        denied=SimpleNamespace(returncode=2,stdout='{"reason":"NATIVE_REVIEW_REQUEST_HASH"}')
        with patch.object(native_host.subprocess,'run',return_value=denied) as reader:
            with self.assertRaisesRegex(ContractError,'NATIVE_REVIEW_REQUEST_HASH'):
                native_host.call(config,'observe_handoff',timeout_seconds=1.5)
        self.assertEqual(reader.call_args.kwargs['timeout'],1.5)


def _interleaved_worker(folder,ready,release):
    write=runner._write
    def stall(path,state):
        if path.name=='state.json' and state['state']=='REVIEW_RUNNING':
            ready.set()
            if not release.wait(10):
                raise RuntimeError('test barrier expired')
        write(path,state)
    with patch.object(runner,'_write',side_effect=stall):
        runner._transition(folder,'REVIEW_RUNNING')


def _status_writer(folder,started,finished):
    started.set()
    runner._transition(folder,'PARTIAL',reason='TERMINAL_FROM_INDEPENDENT_WRITER')
    finished.set()


def _lock_holder(path,ready):
    with runner._file_guard(path):
        ready.set()
        multiprocessing.Event().wait(30)


class StateAndDiagnostics(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        temp=tempfile.TemporaryDirectory(dir=ROOT/'work')
        self.addCleanup(temp.cleanup)
        self.folder=Path(temp.name)

    @unittest.skipUnless('fork' in multiprocessing.get_all_start_methods(),'Requires the POSIX runner')
    def test_processes_preserve_terminal_state_across_prewrite_interleaving(self):
        ctx=multiprocessing.get_context('fork')
        runner._write(self.folder/'state.json',{'state':'REVIEW_READY'})
        ready,release,started,finished=(ctx.Event() for _ in range(4))
        worker=ctx.Process(target=_interleaved_worker,args=(self.folder,ready,release))
        writer=ctx.Process(target=_status_writer,args=(self.folder,started,finished))
        worker.start()
        try:
            self.assertTrue(ready.wait(5))
            writer.start()
            self.assertTrue(started.wait(5))
            # Baseline lets the terminal writer finish while the stale worker
            # holds pre-terminal bytes. The guarded version serializes both.
            finished.wait(.25)
        finally:
            release.set()
            for child in (worker,writer):
                if child.pid is not None:
                    child.join(5)
                    if child.is_alive():child.kill();child.join(5)
        self.assertEqual((worker.exitcode,writer.exitcode),(0,0))
        result=runner._read(self.folder/'state.json')
        self.assertEqual(result['state'],'PARTIAL')
        self.assertEqual(result['reason'],'TERMINAL_FROM_INDEPENDENT_WRITER')
        self.assertEqual(runner._transition(self.folder,'PARTIAL',reason='STALE'),result)
        delivered=runner._transition(self.folder,'FINAL_DELIVERED',delivery_receipt={'proof':'fixture'})
        self.assertEqual(delivered['state'],'FINAL_DELIVERED')
        self.assertEqual(runner._transition(self.folder,'REVIEW_READY'),delivered)

    @unittest.skipUnless('fork' in multiprocessing.get_all_start_methods(),'Requires the POSIX runner')
    def test_kernel_releases_state_lock_after_process_death(self):
        ctx=multiprocessing.get_context('fork')
        path=self.folder/'state.lock';ready=ctx.Event()
        owner=ctx.Process(target=_lock_holder,args=(path,ready))
        owner.start()
        try:
            self.assertTrue(ready.wait(5))
            with self.assertRaisesRegex(ContractError,'RUNNER_ALREADY_ACTIVE'):
                with runner._file_guard(path,nonblocking=True):
                    self.fail('concurrent lock admission')
        finally:
            owner.kill();owner.join(5)
        with runner._file_guard(path,nonblocking=True):
            self.assertTrue(path.is_file())

    def test_read_only_sqlite_failures_are_classified_without_private_schema_or_paths(self):
        path=self.folder/'private-sentinel.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE real_table (id INT)')
        with self.assertRaises(ContractError) as schema:
            with read_db(path) as db:
                db.execute('SELECT secret_column FROM real_table')
        diagnostic=native_app.failure(schema.exception,'RECEIPT_COLLECTION')
        self.assertEqual(diagnostic['code'],'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
        self.assertEqual(diagnostic['diagnostic']['classification'],'FIXED_SCHEMA_MISMATCH')
        self.assertEqual(diagnostic['diagnostic']['retryability'],'TERMINAL')
        self.assertNotIn('secret_column',json.dumps(diagnostic))
        with self.assertRaises(ContractError) as unavailable:
            with read_db(path.with_name('private-missing.sqlite')):
                self.fail('unexpected read')
        diagnostic=native_app.failure(unavailable.exception,'RECEIPT_COLLECTION')
        self.assertEqual(diagnostic['code'],'NATIVE_STORAGE_UNAVAILABLE')
        self.assertEqual(diagnostic['diagnostic']['stage'],'SQLITE_OPEN')
        self.assertEqual(diagnostic['diagnostic']['classification'],'CANNOT_OPEN')
        self.assertNotIn('private-',json.dumps(diagnostic))
