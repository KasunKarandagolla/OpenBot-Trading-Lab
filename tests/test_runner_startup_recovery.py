"""Startup crash/PID fault injection. No process, market or model is launched."""
import os,sqlite3,unittest
from unittest.mock import patch
from researcher import openbot_runner as runner
from researcher.contracts import ContractError,encode
import test_openbot_runner as jobs


class StartupRecovery(unittest.TestCase):
    def setUp(self):
        self.j=jobs.OpenBotRunnerContract();self.j.setUp();self.addCleanup(self.j.doCleanups)
        self.f=self.j.f

    def interrupt_publication(self):
        original=runner._write
        def fail(path,value):
            if path.name=='state.json':raise OSError('controlled interrupted startup')
            return original(path,value)
        with patch.object(runner,'_write',side_effect=fail):
            with self.assertRaises(OSError):runner.start(self.j.key)
        self.j.process.assert_not_called()
        return runner._read(self.j.base/'active.json')

    def test_published_start_reservation_survives_crash_before_job_state_without_replay(self):
        active=self.interrupt_publication()
        self.assertEqual(active['initial_state']['native_identity']['turn_ref'],active['turn_ref'])
        result=runner.start('b'*32)
        self.assertEqual(result['job_id'],active['job_id']);self.assertEqual(result['state'],'INTERRUPTED')
        self.assertIn('START_PUBLICATION',result['reason']);self.j.process.assert_not_called()

    def test_new_actual_owner_command_can_replace_an_interrupted_start_reservation(self):
        active=self.interrupt_publication();runner.status(active['job_id'])
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute("UPDATE projection_threads SET active_turn_id='NEXT_OWNER_TURN' WHERE thread_id='MAIN'")
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',
                ('NEXT_OWNER_TURN','MAIN','PARENT_SESSION','running',self.f.time(5),None))
            db.execute('INSERT INTO projection_deliveries VALUES(?,?,?)',('NEXT_OWNER_TURN','AGENT','NEXT_OWNER'))
            db.execute('INSERT INTO projection_mailbox_messages VALUES(?,?,?)',
                ('NEXT_OWNER','Run the complete market research now.','user'))
        result=runner.start('d'*32)
        self.assertNotEqual(result['job_id'],active['job_id']);self.assertEqual(result['state'],'STARTING')
        self.assertEqual(self.j.process.call_count,1)

    def test_missing_process_record_expires_to_interrupted_instead_of_sticking_forever(self):
        job=runner.start(self.j.key)['job_id'];folder=runner._job(job)
        (folder/'process.json').unlink()
        runner._transition(folder,'STARTING',created_at_utc='2000-01-01T00:00:00+00:00')
        state=runner.status(job,include_review=True)
        self.assertEqual(state['state'],'INTERRUPTED');self.assertNotIn('start_task_arguments',state)
        self.assertEqual(self.j.process.call_count,1)

    def test_reused_live_pid_is_not_mistaken_for_the_original_worker(self):
        job=runner.start(self.j.key)['job_id'];folder=runner._job(job)
        runner._write(folder/'process.json',{'pid':os.getpid(),'start_token':'REPLACED_PROCESS'})
        self.assertEqual(runner.status(job)['state'],'INTERRUPTED')
        self.assertEqual(self.j.process.call_count,1)

    def test_worker_records_its_own_process_before_any_attestation_or_scanner_operation(self):
        job=runner.start(self.j.key)['job_id'];folder=runner._job(job)
        (folder/'process.json').unlink()
        def attest(*args):
            self.assertEqual(runner._read(folder/'process.json')['pid'],os.getpid())
            raise ContractError('RUNNER_START_UNATTESTED')
        with patch.object(runner,'attest_start',side_effect=attest),patch.object(runner.time,'sleep'),\
                patch('researcher.discovery.scan_market_research') as scanner:
            state=runner.run_job(job)
        self.assertEqual(state['state'],'FAILED');scanner.assert_not_called()
        self.assertTrue((folder/'process.json').is_file())
        self.assertEqual(state['reason'],'RUNNER_START_UNATTESTED')

    def test_terminal_failure_survives_stale_liveness_and_progress_transitions(self):
        job=runner.start(self.j.key)['job_id'];folder=runner._job(job)
        original=runner._transition(folder,'FAILED',reason='NATIVE_SESSION_MISMATCH')
        for state in ('SCANNING','INTERRUPTED','REVIEW_READY','FINAL_DELIVERED'):
            result=runner._transition(folder,state,reason='STALE_OBSERVER')
            self.assertEqual(result,original)
