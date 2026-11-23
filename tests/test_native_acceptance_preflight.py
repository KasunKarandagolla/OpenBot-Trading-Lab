"""Read-only preflight and exact owner authorization; provider replies are fixtures."""
import copy,json,sqlite3,unittest
from pathlib import Path
from unittest.mock import patch
from researcher import openbot_runner as runner,native_app
from researcher.agent_review import _material
from researcher.contracts import ContractError,encode,digest
from researcher.native_runtime import integration_preflight,attest_smoke_discovery
from researcher.native_workflow import probe_captured_request
from researcher.settings import ROOT
from researcher.diagnostic_export import export_job,verify_zip
import test_openbot_runner as jobs
from test_workflow_e2e import SimulatedApp


class AcceptancePreflight(unittest.TestCase):
    def setUp(self):
        self.j=jobs.OpenBotRunnerContract();self.j.setUp();self.addCleanup(self.j.doCleanups)
        self.f=self.j.f
        target=self.f.workspace/'.agents/skills/openbot-market-research/SKILL.md';target.parent.mkdir(parents=True)
        target.write_text((ROOT/'integration/openbot-market-research/SKILL.md').read_text().replace('@@RESEARCH_ROOT@@',str(ROOT)))

    def set_owner(self,text,sender='user'):
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute('UPDATE projection_mailbox_messages SET text=?,sender_kind=?',(text,sender))

    def captured(self):
        request=copy.deepcopy(self.f.request)
        # Synthetic values in a historical live-packet shape for transport tests.
        for card in request['cards']:card['mode']='LIVE'
        request['material_sha256']=digest(encode(_material(request)).encode())
        path=self.f.root/'captured.request.json';path.write_text(encode(request))
        return path

    def test_actual_record_shape_and_both_installed_skills_are_checked_without_model_execution(self):
        result=integration_preflight(self.f.config,as_of=self.f.time(5))
        self.assertEqual(result['status'],'NATIVE_READER_AND_INSTALLED_SKILLS_VERIFIED')
        self.assertEqual(result['model_requests'],0);self.assertEqual(result['market_requests'],0)
        self.assertFalse(result['native_execution_verified']);self.assertEqual(len(result['skill_sha256']),2)
        self.assertEqual(result['identity']['model'],self.f.agent['model'])

    def test_observed_0171_ordinal_setup_scope_passes_without_new_execution(self):
        self.f.parent[0]['payload'].update(cli_version='0.171.0', history_mode='paginated')
        context = self.f.parent[1]['payload']
        context.update(root_turn_id='PARENT_TURN', cwd=str(self.f.workspace),
                       approval_policy='on-request', permission_profile={'type':'disabled'})
        self.f.parent.insert(1,self.f.record(-10,'event_msg',{'type':'task_started','turn_id':'PARENT_TURN',
            'root_turn_id':'PARENT_TURN','turn_attribution':{}}))
        self.f.parent.append(self.f.record(6,'compacted',{'replacement_history':[]}))
        SimulatedApp(self.f,self.f.time).write('PARENT',self.f.parent)
        result=integration_preflight(self.f.config,as_of=self.f.time(5))
        self.assertEqual(result['status'],'NATIVE_READER_AND_INSTALLED_SKILLS_VERIFIED')
        self.assertEqual((result['model_requests'],result['market_requests']),(0,0))
        self.assertFalse(result['trade_authorization'])
        with self.assertRaisesRegex(ContractError,'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED') as unsupported:
            integration_preflight(self.f.config,as_of=self.f.time(6))
        self.assertEqual(unsupported.exception.diagnostic['stage'],'ENVELOPE')

    def test_0171_requires_the_observed_ordinal_envelope_and_rejects_unknown_releases(self):
        self.f.parent[0]['payload']['cli_version']='0.171.0'
        self.f.write()
        with self.assertRaisesRegex(ContractError,'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED') as unknown:
            integration_preflight(self.f.config,as_of=self.f.time(5))
        self.assertEqual(unknown.exception.diagnostic['check'],'VERSION')
        for version in ('0.171.1','0.172.0','0.171.0-dev',{}):
            with self.subTest(version=version):
                self.f.parent[0]['payload']['cli_version']=version
                SimulatedApp(self.f,self.f.time).write('PARENT',self.f.parent)
                with self.assertRaisesRegex(ContractError,'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED') as unknown:
                    integration_preflight(self.f.config,as_of=self.f.time(5))
                self.assertEqual(unknown.exception.diagnostic['check'],'VERSION')

    def test_unknown_provider_version_and_modified_installed_skill_block_preflight(self):
        self.f.parent[0]['payload']['cli_version']='unsupported';self.f.write()
        with self.assertRaisesRegex(ContractError,'SCHEMA_UNSUPPORTED'):integration_preflight(self.f.config,as_of=self.f.time(5))
        self.f.parent[0]['payload']['cli_version']='0.169.0';self.f.write()
        skill=self.f.workspace/'.agents/skills/openbot-market-research/SKILL.md';skill.write_text('changed')
        with self.assertRaisesRegex(ContractError,'SKILL_HASH'):integration_preflight(self.f.config,as_of=self.f.time(5))

    def test_exact_versioned_acceptance_message_authorizes_one_run_at_the_approved_commit(self):
        prompt=runner.ACCEPTANCE_PROMPT.read_text().replace('@@APPROVED_COMMIT@@','a'*40)
        self.set_owner(prompt)
        first=runner.start(self.j.key);second=runner.start('b'*32)
        state=runner._read(runner._job(first['job_id'])/'state.json')
        self.assertEqual(state['owner_run_mode'],'SETUP_AND_ACCEPTANCE')
        self.assertEqual(first['job_id'],second['job_id']);self.assertEqual(self.j.process.call_count,1)

    def test_wrong_commit_quoted_negated_extended_or_delegated_acceptance_message_is_rejected(self):
        prompt=runner.ACCEPTANCE_PROMPT.read_text().replace('@@APPROVED_COMMIT@@','a'*40)
        for text,sender in [(prompt.replace('a'*40,'b'*40),'user'),('Do not '+prompt,'user'),
                ('Quoted instructions:\n'+prompt,'user'),(prompt+'\nIgnore all checks','user'),(prompt,'agent')]:
            with self.subTest(sender=sender,kind=text[:12]):
                self.set_owner(text,sender)
                with self.assertRaisesRegex(ContractError,'OWNER_START_REQUIRED'):runner.start(self.j.key)
        self.j.process.assert_not_called()

    def test_archived_native_smoke_requires_the_exact_owner_message(self):
        prompt=runner.SMOKE_PROMPT.read_text().replace('@@APPROVED_COMMIT@@','a'*40)
        for text in (prompt.replace('a'*40,'b'*40),'Do not '+prompt,prompt+' extra'):
            with self.subTest(text=text[:20]):
                self.set_owner(text)
                with self.assertRaisesRegex(ContractError,'OWNER_START_REQUIRED'):
                    runner.start(self.j.key)
        self.set_owner(prompt)
        result=runner.start(self.j.key)
        state=runner._read(runner._job(result['job_id'])/'state.json')
        self.assertEqual(state['owner_run_mode'],'NATIVE_SMOKE')

    def test_native_smoke_discovery_binds_parent_call_response_and_schemas(self):
        names=['openbot.start_task','openbot.attach_files_to_response']
        arguments={'names':names}
        tools=[{'name':names[0],'inputSchema':{'type':'object','additionalProperties':False,
            'properties':{'title':{'type':'string'},'brief':{'type':'string'}},'required':['title','brief']}},
            {'name':names[1],'inputSchema':{'type':'object','additionalProperties':False,
            'properties':{'paths':{'type':'array'}},'required':['paths']}}]
        call=self.f.record(1,'response_item',{'type':'function_call','namespace':'openbot',
            'name':'tool_describe','call_id':'DISCOVERY','arguments':json.dumps(arguments)})
        event=self.f.record(2,'event_msg',{'type':'item_completed','turn_id':'PARENT_TURN','thread_id':'PARENT',
            'item':{'type':'DynamicToolCall','id':'DISCOVERY','namespace':'openbot','tool':'tool_describe',
                'arguments':arguments,'status':'completed','success':True,
                'content_items':[{'type':'inputText','text':json.dumps({'tools':tools})}]}})
        delivered=self.f.record(3,'response_item',{'type':'function_call_output','call_id':'DISCOVERY',
            'output':event['payload']['item']['content_items'][0]['text']})
        self.f.parent.extend([call,event,delivered]);self.f.write()
        result=attest_smoke_discovery(self.f.identity,self.f.config,as_of=self.f.time(5))
        self.assertEqual(result['status'],'VERIFIED_CURRENT_PARENT_TOOL_DISCOVERY')
        for fault in ('wrong_call','failed','wrong_turn','bad_schema'):
            with self.subTest(fault=fault):
                altered=copy.deepcopy(event)
                item=altered['payload']['item']
                if fault=='wrong_call':item['id']='OTHER'
                elif fault=='failed':item['success']=False
                elif fault=='wrong_turn':altered['payload']['turn_id']='OTHER'
                else:
                    bad=copy.deepcopy(tools);bad[0]['inputSchema']['additionalProperties']=True
                    item['content_items'][0]['text']=json.dumps({'tools':bad})
                self.f.parent[-2]=altered;self.f.write()
                with self.assertRaises(ContractError):
                    attest_smoke_discovery(self.f.identity,self.f.config,as_of=self.f.time(5))
        self.f.parent[-2]=event;self.f.write()
        self.f.parent.pop();self.f.write()
        with self.assertRaisesRegex(ContractError,'NATIVE_TOOL_DISCOVERY_UNVERIFIED'):
            attest_smoke_discovery(self.f.identity,self.f.config,as_of=self.f.time(5))

    def test_native_smoke_missing_discovery_exports_diagnostics(self):
        prompt=runner.SMOKE_PROMPT.read_text().replace('@@APPROVED_COMMIT@@','a'*40)
        self.set_owner(prompt)
        job=runner.start(self.j.key)['job_id']
        with patch.object(runner,'attest_start',return_value={'status':'VERIFIED_FIXTURE_ONLY'}),\
                patch('researcher.native_runtime.integration_preflight',return_value={'status':'FIXTURE_READER_ONLY'}),\
                patch('researcher.discovery.scan_market_research') as scanner:
            result=runner.run_job(job)
        scanner.assert_not_called()
        self.assertEqual(result['state'],'PARTIAL')
        self.assertEqual(result['smoke_result']['tool_discovery']['status'],'NOT_VERIFIED')
        self.assertEqual(result['first_error']['code'],'NATIVE_TOOL_DISCOVERY_UNVERIFIED')
        self.assertTrue(verify_zip(Path(result['artifact']['attachment_path']).read_bytes()))

    def test_native_smoke_exports_failure_without_market_scan(self):
        prompt=runner.SMOKE_PROMPT.read_text().replace('@@APPROVED_COMMIT@@','a'*40)
        self.set_owner(prompt)
        job=runner.start(self.j.key)['job_id']
        failure={'status':'NATIVE_REVIEW_INCOMPLETE','reason':'NATIVE_READ_INCOMPLETE',
            'first_error':{'stage':'RECEIPT_COLLECTION','code':'NATIVE_READ_INCOMPLETE'},
            'observed_model_attempts':0,'current_market_interpretation':False}
        with patch.object(runner,'attest_start',return_value={'status':'VERIFIED_FIXTURE_ONLY'}),\
                patch('researcher.native_runtime.integration_preflight',return_value={'status':'FIXTURE_READER_ONLY'}),\
                patch('researcher.native_runtime.attest_smoke_discovery',return_value={'status':'VERIFIED_FIXTURE_ONLY'}),\
                patch.object(runner,'_prior_live_packet',return_value=self.captured()),\
                patch('researcher.native_workflow.probe_captured_request',return_value=failure),\
                patch('researcher.discovery.scan_market_research') as scanner:
            result=runner.run_job(job)
        scanner.assert_not_called()
        self.assertEqual(result['state'],'PARTIAL')
        self.assertEqual(result['smoke_result']['status'],'INCOMPLETE')
        self.assertEqual(result['native_transport_preflight']['reason'],'NATIVE_READ_INCOMPLETE')
        self.assertEqual(result['costs']['market_http_requests'],0)
        self.assertTrue(verify_zip(Path(result['artifact']['attachment_path']).read_bytes()))
        self.assertFalse(result['trade_authorization'])

    def test_native_smoke_with_no_archived_packet_never_starts_scan(self):
        prompt=runner.SMOKE_PROMPT.read_text().replace('@@APPROVED_COMMIT@@','a'*40)
        self.set_owner(prompt)
        job=runner.start(self.j.key)['job_id']
        with patch.object(runner,'attest_start',return_value={'status':'VERIFIED_FIXTURE_ONLY'}),\
                patch('researcher.native_runtime.integration_preflight',return_value={'status':'FIXTURE_READER_ONLY'}),\
                patch('researcher.native_runtime.attest_smoke_discovery',return_value={'status':'VERIFIED_FIXTURE_ONLY'}),\
                patch.object(runner,'_prior_live_packet',return_value=None),\
                patch('researcher.discovery.scan_market_research') as scanner:
            result=runner.run_job(job)
        scanner.assert_not_called()
        self.assertEqual(result['state'],'PARTIAL')
        self.assertEqual(result['smoke_result']['status'],'INCOMPLETE')
        self.assertTrue(verify_zip(Path(result['artifact']['attachment_path']).read_bytes()))

    def test_archived_probe_dispatches_exact_input_and_imports_a_separately_labeled_fixture_reply(self):
        source=self.captured();before=source.read_bytes();clock=lambda:self.f.time(5)
        app=SimulatedApp(self.f,clock);actual=native_app.collect;published=[]
        def progress(state,**fields):
            if state=='REVIEW_READY':
                task=self.f.root/'probe'/(fields['material_sha256']+'.review-task.json')
                args=json.loads(task.read_text());published.append(args);app.dispatch_once(args)
        def collect(*args,**kwargs):app.complete_due();return actual(*args,**kwargs)
        with patch('researcher.native_app.collect',side_effect=collect):
            result=probe_captured_request(self.f.root/'probe',source,native_identity=self.f.identity,
                audit_config=self.f.cf,clock=clock,progress=progress,wait_seconds=3)
        self.assertEqual(result['status'],'VALIDATED_ADVISORY_ONLY',result)
        self.assertEqual(result['accepted'],1);self.assertEqual(result['observed_model_attempts'],1)
        self.assertFalse(result['current_market_interpretation']);self.assertEqual(source.read_bytes(),before)
        self.assertEqual(len(published),1)
        request=json.loads(published[0]['brief'].split('<canonical-request>\n',1)[1].split('\n</canonical-request>',1)[0])
        self.assertEqual(request['cards'][0]['mode'],'AUTHENTIC_REPLAY')
        self.assertTrue(all(f['usable_as_of'] is False for f in request['cards'][0]['evidence'].values()))
        self.assertEqual(request['transport_check']['source_material_sha256'],json.loads(before)['material_sha256'])
        self.assertFalse(result['trade_authorization'])

    def test_modified_archived_packet_is_rejected_before_publication_or_collection(self):
        source=self.captured();request=json.loads(source.read_text());request['cards'][0]['native_symbol']='FORGED'
        source.write_text(encode(request))
        with patch('researcher.native_app.wait_for_reply') as wait:
            with self.assertRaisesRegex(ContractError,'REQUEST_HASH'):
                probe_captured_request(self.f.root/'probe',source,native_identity=self.f.identity,
                    audit_config=self.f.cf,clock=lambda:self.f.time(5))
        wait.assert_not_called()

    def test_failed_transport_preflight_exports_diagnostics_without_starting_the_market_scan(self):
        job=runner.start(self.j.key)['job_id'];folder=runner._job(job)
        runner._transition(folder,'STARTING',owner_run_mode='SETUP_AND_ACCEPTANCE')
        failure={'status':'NATIVE_REVIEW_INVALID_OR_UNAVAILABLE_DETERMINISTIC_FALLBACK',
            'reason':'AGENT_REPLY_ADVICE','observed_model_attempts':1,'current_market_interpretation':False}
        with patch.object(runner,'attest_start',return_value={'status':'VERIFIED_FIXTURE_ONLY'}),\
                patch('researcher.native_runtime.integration_preflight',return_value={'status':'FIXTURE_READER_ONLY'}),\
                patch.object(runner,'_prior_live_packet',return_value=self.captured()),\
                patch('researcher.native_workflow.probe_captured_request',return_value=failure),\
                patch('researcher.discovery.scan_market_research') as scanner:
            state=runner.run_job(job)
        scanner.assert_not_called();self.assertEqual(state['state'],'PARTIAL')
        self.assertEqual(state['costs']['market_http_requests'],0)
        self.assertEqual(state['coverage'],'NOT_SCANNED')
        self.assertTrue(verify_zip(Path(state['artifact']['attachment_path']).read_bytes()))
        report=json.loads((folder/'report.json').read_text());self.assertFalse(report['market_scan_started'])
        self.assertEqual(report['native_transport_preflight']['observed_model_attempts'],1)
        self.assertFalse(report['trade_authorization'])

    def test_delivery_observer_is_bounded_and_never_submits_tasks(self):
        with patch.object(runner,'status',side_effect=[{'state':'COMPLETED'},{'state':'FINAL_DELIVERED'}]),\
                patch.object(runner.time,'sleep') as sleep:
            self.assertEqual(runner.watch_delivery('fixture',wait_seconds=1)['state'],'FINAL_DELIVERED')
        self.assertEqual(sleep.call_count,1)
        with self.assertRaisesRegex(ContractError,'WAIT_INVALID'):runner.watch_delivery('fixture',wait_seconds=601)

    def test_historical_replay_reports_failure_and_verified_artifact_without_writes(self):
        job=runner.start(self.j.key)['job_id'];folder=runner._job(job)
        directory=folder/'review';directory.mkdir()
        request=self.f.request;material=request['material_sha256']
        (directory/(material+'.request.json')).write_text(encode(request))
        runner._transition(folder,'REVIEW_FAILED',material_sha256=material)
        report={'job_id':job,'mode':'LIVE','trade_authorization':False,
            'native_control_comparison':{'accepted_current_advice':False,'hard_gates_changed':False}}
        (folder/'report.json').write_text(encode(report))
        artifact=export_job(folder,report,self.f.config)
        runner._transition(folder,'PARTIAL',artifact=artifact)
        before=(folder/'state.json').read_bytes()
        with patch('researcher.native_runtime.collect',side_effect=ContractError('NATIVE_READ_INCOMPLETE')) as collect,\
                patch('researcher.native_runtime.delivery_proof',return_value=None):
            result=runner.replay_native(job)
        self.assertEqual(result['reviews'][0]['error']['code'],'NATIVE_READ_INCOMPLETE')
        self.assertEqual(result['artifact']['status'],'VERIFIED_SAVED_ARCHIVE_AND_REPORT')
        self.assertEqual(result['artifact']['delivery'],'NOT_OBSERVED')
        self.assertFalse(result['artifact']['saved_reconciliation']['accepted_current_advice'])
        self.assertEqual((folder/'state.json').read_bytes(),before)
        self.assertEqual(collect.call_count,1)
        self.assertEqual(result['model_requests'],0);self.assertEqual(result['market_requests'],0)

    def test_delivery_proof_refuses_an_attachment_whose_bytes_changed_after_export(self):
        job=runner.start(self.j.key)['job_id'];folder=runner._job(job)
        report={'mode':'SYNTHETIC','shortlist':[],'trade_authorization':False}
        artifact=export_job(folder,report,self.f.config)
        runner._transition(folder,'PARTIAL',artifact=artifact)
        Path(artifact['attachment_path']).write_bytes(b'tampered')
        status=runner.status(job)
        self.assertEqual(status['state'],'PARTIAL')
        self.assertEqual(status['delivery_observation_error']['code'],'NATIVE_REPLY_PROVENANCE')
