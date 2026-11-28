"""Offline transport tests using OpenBot 0.71.0 and Codex 0.169 record shapes."""
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch

from researcher import openbot_runner as runner
from researcher.agent_review import _material, exchange, parse_reply
from researcher.contracts import ContractError, digest, encode, utc
from researcher.native_app import wait_for_reply
from researcher.native_codex import review_brief
from researcher.native_handoff import (LEGACY_SUBMISSION_POLICY, RESERVED_SUBMISSION_POLICY,
    BOUNDED_WAIT_PAGE_COMMANDS, TICKET_BOUND_PAGE_COMMANDS, VERBATIM_PAGE_COMMANDS,
    STAGE_BOUND_PAGE_COMMANDS, COMPACT_PAGES, command_page, confirmed_packet, packet,
    verify_submission_window)
from researcher.native_runtime import collect
from researcher.settings import ROOT
import test_openbot_runner as jobs
from test_workflow_e2e import SimulatedApp


class NativeHandoff(unittest.TestCase):
    def setUp(self):
        self.j=jobs.OpenBotRunnerContract();self.j.setUp();self.addCleanup(self.j.doCleanups)
        self.f=self.j.f;self.seconds=5;self.monotonic=0
        self.clock=lambda:self.f.time(self.seconds)
        for target,value in [('researcher.openbot_runner.now_utc',self.clock),
                ('researcher.native_app.time.monotonic',lambda:self.monotonic),
                ('researcher.native_app.time.sleep',self.sleep)]:
            mocked=patch(target,value);mocked.start();self.addCleanup(mocked.stop)
        self.job=runner.start(self.j.key)['job_id'];self.folder=runner._job(self.job)
        self.directory=self.folder/'review';self.directory.mkdir()
        self.f.parent=self.f.parent[:2];self.f.write()
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute('DELETE FROM projection_agent_threads')
        self.request=dict(self.f.request,context={'fixture_evidence':'','unicode':'漢字'},as_of_utc=self.clock(),
            dispatch_reservation_policy=RESERVED_SUBMISSION_POLICY,page_command_policy=VERBATIM_PAGE_COMMANDS)
        padding=95_759-len(review_brief(self.request))
        self.request['context']['fixture_evidence']=('Evidence with spaces and delimiters [ ] { } / ' * padding)[:padding]
        self.pin_request()
        self.app=SimulatedApp(self.f,self.clock)
        self.on_sleep=lambda:None

    def pin_request(self):
        self.material=digest(encode(_material(self.request)).encode())
        self.request['material_sha256']=self.material
        self.request_path=self.directory/(self.material+'.request.json')
        self.request_path.write_text(encode(self.request),encoding='utf-8')

    def sleep(self,seconds):
        self.seconds+=seconds;self.monotonic+=seconds;self.on_sleep()

    def wait(self,on_ready=lambda:None):
        def progress(state,**fields):
            if state=='REVIEW_READY' and 'review_transport' in fields:
                # Production selects v2 at command attestation. The file is
                # already visible here while the durable state is still earlier.
                staged=runner.status(self.job,include_review=True)
                self.assertEqual(staged['state'],'COMMAND_ATTESTED')
                self.assertNotIn('dispatch_receipt',staged)
            runner._transition(self.folder,state,**fields)
            if state=='REVIEW_READY' and 'review_transport' in fields:on_ready()
        runner._transition(self.folder,'COMMAND_ATTESTED',review_transport='PAGED_V2')
        return wait_for_reply(self.directory,self.material,self.j.private,clock=self.clock,
            wait_seconds=600,progress=progress,verified_identity=self.f.identity)

    def ticket(self):
        self.status=runner.status(self.job,include_review=True)
        self.args=self.status['start_task_arguments']
        self.receipt=self.status['dispatch_receipt']
        return self.status

    def record_submission(self,*,response=None,arguments=None):
        wrapper={'name':'openbot.start_task','arguments':arguments or self.args}
        call_id='ONE_NATIVE_ATTEMPT'
        self.f.parent.append(self.f.record(self.seconds,'response_item',{'type':'function_call',
            'name':'tool_call','namespace':'openbot','call_id':call_id,'arguments':json.dumps(wrapper)}))
        if response is not None:
            self.f.parent.append(self.f.record(self.seconds,'event_msg',{'type':'item_completed',
                'turn_id':'PARENT_TURN','thread_id':'PARENT','item':{'type':'DynamicToolCall','namespace':'openbot',
                    'tool':'tool_call','id':call_id,'status':'failed' if response is False else 'completed',
                    'success':response is not False,'arguments':wrapper,'content_items':[{'type':'inputText',
                        'text':json.dumps(response)}]}}))
        self.app.write('PARENT',self.f.parent)

    def test_real_size_packet_crosses_64_kib_output_cap_and_reconciles_one_task(self):
        def ready():
            # Large status history must not compete with the one-shot reply.
            history=runner._read(self.folder/'state.json')['lifecycle']
            runner._transition(self.folder,'REVIEW_READY',lifecycle=[{'state':'previous','detail':'x'*65_536},*history])
            self.assertGreater(len((self.folder/'state.json').read_bytes()),65536)
            visible_status=json.loads(encode(runner.status(self.job)).encode()[:65536])
            self.assertEqual(visible_status['state'],'REVIEW_READY')
            status=self.ticket();receipt=self.receipt
            full=review_brief(self.request)
            self.assertEqual(len(full),95_759)
            original=encode({'title':self.args['title'],'brief':full}).encode()
            with self.assertRaises(ValueError):json.loads(original[:65536])
            # The status cap can truncate the former object but preserves this
            # versioned object completely, including quoting and the SHA-256.
            self.assertEqual(json.loads(encode(status).encode()[:65536])['start_task_arguments'],self.args)
            self.assertEqual(self.args,runner._read(self.directory/(self.material+'.review-task.json')))
            self.assertEqual(digest(encode(self.args).encode()),receipt['arguments_sha256'])
            self.assertEqual(digest(full.encode()),receipt['packet_sha256'])
            second=runner.status(self.job,include_review=True)
            self.assertEqual(second['state'],'REVIEW_DISPATCH_RESERVED')
            self.assertEqual(second['dispatch_receipt'],receipt)
            self.assertNotIn('start_task_arguments',second)
            self.assertTrue(self.app.dispatch_once(self.args,self.job,receipt))
            self.assertEqual(len(self.app.submitted),1)
            self.on_sleep=self.app.complete_due
        result=self.wait(ready)
        self.assertEqual(result['status'],'NATIVE_RECEIPT_COLLECTED',result)
        self.assertEqual(result['submission_attempts'],1)
        self.assertEqual(result['observed_model_attempts'],1)
        states=[x['state'] for x in runner._read(self.folder/'state.json')['lifecycle']]
        expected=['REVIEW_READY','TASK_SUBMISSION_ATTEMPTED','TASK_CREATED','MODEL_EXECUTED','REVIEW_VERIFIED']
        self.assertEqual([s for s in states if s in expected],expected)
        imported=exchange(self.directory,(),{},cached=True,previous={'material_sha256':self.material},
            as_of=self.clock(),audit_config=self.j.private,require_identity=True)
        self.assertEqual(imported['status'],'VALIDATED_ADVISORY_ONLY',imported)
        self.assertEqual(imported['accepted'],1)
        self.assertFalse(imported['trade_authorization'])

    def code_mode_rollout(self, *, multiline=False):
        def ready():
            self.ticket()
            self.assertTrue(self.app.dispatch_once(self.args, self.job, self.receipt))
            self.on_sleep = self.app.complete_due

        self.assertEqual(self.wait(ready)['status'], 'NATIVE_RECEIPT_COLLECTED')
        path = self.f.root/'sessions/REVIEW_1.jsonl'
        records = [json.loads(line) for line in path.read_text().splitlines()]
        for row in records:
            payload = row['payload']
            at = utc(row['timestamp']).timestamp()
            metadata = {'turn_id': 'TURN_1', 'create_time': at}
            if payload.get('type') == 'function_call':
                arguments = json.loads(payload['arguments'])
                literal = json.dumps(arguments['cmd'])
                wait = ',yield_time_ms:30000' if arguments.get('yield_time_ms') == 30000 else ''
                script = ('const r = await tools.exec_command({cmd:'+literal
                          +',login:false,max_output_tokens:16000'+wait+'}); text(r.output);\n')
                if multiline:
                    script = ('const r = await tools.exec_command({\n'
                              f'  cmd: {literal},\n'
                              '  login: false,\n  max_output_tokens: 16000'
                              + (',\n  yield_time_ms: 30000' if wait else '')
                              + '\n});\ntext(r.output);')
                row['payload'] = {
                    'type': 'custom_tool_call', 'id': 'ctc_'+payload['call_id'],
                    'status': 'completed', 'call_id': payload['call_id'], 'name': 'exec',
                    'input': script,
                    'internal_chat_message_metadata_passthrough': metadata,
                }
            elif payload.get('item', {}).get('type') == 'CommandExecution':
                item = payload['item']
                item.update(id='inner_'+item['id'], source='unified_exec_startup')
                payload.update(started_at_ms=int(at*1000), completed_at_ms=int(at*1000))
            elif payload.get('type') == 'function_call_output':
                page = payload['output'].split('\nOutput:\n', 1)[1]
                row['payload'] = {
                    'type': 'custom_tool_call_output', 'id': 'ctco_'+payload['call_id'],
                    'call_id': payload['call_id'],
                    'output': [{'type':'input_text','text':'Script completed\nWall time 0.5 seconds\nOutput:\n'},
                               {'type':'input_text','text':page}],
                    'internal_chat_message_metadata_passthrough': metadata,
                }
        return records

    def test_code_mode_owner_host_shape_attests_all_ten_page_reads(self):
        self.app.write('REVIEW_1', self.code_mode_rollout())
        observed = collect(self.request, self.f.config, as_of=self.clock(), directory=self.directory)
        self.assertEqual(observed[1]['verified_evidence_pages'], 10)
        self.assertEqual(observed[1]['submission_attempts'], 1)
        self.assertEqual(observed[1]['reply_validation_status'], 'VALIDATED')
        self.assertTrue(observed[1]['model_execution_observed'])
        self.assertEqual(observed[1]['verified_model_requests'], observed[1]['model_requests'])

    def test_code_mode_november_22_multiline_receipt_attests_all_ten_pages(self):
        self.app.write('REVIEW_1', self.code_mode_rollout(multiline=True))
        _, attestation = collect(self.request, self.f.config, as_of=self.clock(), directory=self.directory)
        self.assertEqual(attestation['verified_evidence_pages'], 10)
        self.assertEqual(attestation['submission_attempts'], 1)
        self.assertEqual(attestation['reply_validation_status'], 'VALIDATED')

    def test_code_mode_accepts_property_order_whitespace_and_header_line_ending_variants(self):
        records=self.code_mode_rollout(multiline=True)
        call=next(row['payload'] for row in records if row['payload'].get('type')=='custom_tool_call')
        command=json.loads(call['input'].split('cmd: ',1)[1].split(',',1)[0])
        call['input']=('const r=await tools.exec_command({ max_output_tokens:16000, '
            'login:false, cmd:'+json.dumps(command)+' }); text ( r.output )')
        output=next(row['payload'] for row in records if row['payload'].get('type')=='custom_tool_call_output')
        output['output'][0]['text']=output['output'][0]['text'].replace('\n','\r\n').replace('0.5 seconds','0.50 seconds')
        self.app.write('REVIEW_1',records)
        _,proof=collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)
        self.assertEqual(proof['verified_evidence_pages'],10)
        self.assertEqual(proof['reply_validation_status'],'VALIDATED')

    def test_november_23_early_empty_output_is_incomplete_not_unauthorized(self):
        from researcher.native_codex import _code_mode_command
        fixture=json.loads((ROOT/'tests/fixtures/native-codex-0171-page-five.json').read_text())
        first=fixture['page1_call']
        self.assertEqual((first['ordinal'],first['timestamp']),(18,'2026-11-23T01:54:46.792Z'))
        self.assertFalse(first['input'].rstrip().endswith(';'))
        command=_code_mode_command({'name':'exec','status':'completed','input':first['input']})
        self.assertTrue(command.endswith('--page 1'))
        self.assertEqual(fixture['page5_output']['output'][1]['text'],'')
        self.assertEqual(fixture['page5_execution']['exit_code'],0)
        self.assertTrue(fixture['page5_execution']['page5_bytes_exact'])
        self.assertLess(fixture['page5_output']['ordinal'],fixture['page5_execution']['ordinal'])
        records=self.code_mode_rollout(multiline=True)
        calls=[i for i,row in enumerate(records) if row['payload'].get('type')=='custom_tool_call']
        for index in calls:
            records[index]['payload']['input']=records[index]['payload']['input'].rstrip(';')
        fifth=calls[4]
        records[fifth+2]['payload']['output'][1]['text']=''
        records[fifth+1],records[fifth+2]=records[fifth+2],records[fifth+1]
        self.app.write('REVIEW_1',records)
        with self.assertRaisesRegex(ContractError,'^NATIVE_READ_INCOMPLETE$'):
            collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)

    def test_bounded_wait_policy_accepts_complete_pages_and_rejects_missing_wait(self):
        self.request['page_command_policy']=BOUNDED_WAIT_PAGE_COMMANDS
        self.pin_request()
        records=self.code_mode_rollout(multiline=True)
        self.app.write('REVIEW_1',records)
        _,proof=collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)
        self.assertEqual(proof['verified_evidence_pages'],10)
        self.assertEqual(proof['reply_validation_status'],'VALIDATED')
        self.assertEqual(proof['validated_rows'],len(self.request['cards']))
        first=next(r for r in records if r['payload'].get('type')=='custom_tool_call')
        first['payload']['input']=first['payload']['input'].replace(',\n  yield_time_ms: 30000','')
        self.app.write('REVIEW_1',records)
        with self.assertRaisesRegex(ContractError,'^NATIVE_UNAUTHORIZED_TOOL$'):
            collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)

    def test_interrupted_child_without_final_is_a_terminal_failure(self):
        self.app.write('REVIEW_1',self.code_mode_rollout(multiline=True))
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute("DELETE FROM projection_thread_messages WHERE turn_id='TURN_1' AND item_type='final_answer'")
            db.execute("UPDATE projection_turns SET status='interrupted' WHERE turn_id='TURN_1'")
        with self.assertRaisesRegex(ContractError,'^NATIVE_TASK_FAILED$'):
            collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)
        self.assertEqual(len(self.app.submitted),1)

    @staticmethod
    def saved_page_seven():
        return json.loads((ROOT/'tests/fixtures/native-codex-0171-page-seven.json').read_text(encoding='utf-8'))

    def test_saved_page_seven_digest_deletion_still_fails_closed(self):
        saved=self.saved_page_seven()
        decoder=json.JSONDecoder()
        script=saved['stored_script']
        offset=script.index('cmd: ')+len('cmd: ')
        command,_=decoder.raw_decode(script,offset)
        expected=saved['delivered_next_command']
        wanted=expected.split('--packet-sha256 ',1)[1].split()[0]
        wrong=command.split('--packet-sha256 ',1)[1].split()[0]
        self.assertEqual(expected.replace(wanted,wrong),command)
        self.assertEqual(wanted[44:46],'c3')
        self.assertEqual(wrong,wanted[:44]+wanted[46:])
        self.assertEqual(saved['call_record']['ordinal'],60)
        self.assertEqual(saved['command_record']['exit_code'],1)
        self.assertEqual(json.loads(saved['command_record']['stdout'])['reason'],'NATIVE_HANDOFF_UNATTESTED')
        self.assertEqual(saved['model_output_record']['output'][1]['text'],saved['command_record']['stdout'])
        with self.assertRaisesRegex(ContractError,'AGENT_REPLY_JSON'):
            parse_reply(saved['child_final'])
        records=self.code_mode_rollout(multiline=True)
        calls=[r['payload'] for r in records if r['payload'].get('type')=='custom_tool_call']
        fingerprint=self.receipt['packet_sha256']
        calls[6]['input']=calls[6]['input'].replace(fingerprint,fingerprint[:44]+fingerprint[46:])
        self.app.write('REVIEW_1',records)
        with self.assertRaisesRegex(ContractError,'^NATIVE_UNAUTHORIZED_TOOL$'):
            collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)

    def test_ticket_bound_code_mode_reads_all_pages_and_validates_the_reply(self):
        self.request['page_command_policy']=TICKET_BOUND_PAGE_COMMANDS
        self.pin_request()
        records=self.code_mode_rollout(multiline=True)
        args,fingerprint,pages=packet(self.request,self.directory)
        self.assertIn(f'The expected packet SHA-256 is {fingerprint}.',args['brief'])
        first=next(line for line in args['brief'].splitlines() if line.startswith('wsl.exe '))
        commands=[first,*[json.loads(page)['next_command'] for page in pages[:-1]]]
        self.assertTrue(all('--packet-sha256' not in command for command in commands))
        self.assertEqual(len(commands),10)
        self.assertEqual(digest(''.join(json.loads(page)['text'] for page in pages).encode()),fingerprint)
        self.app.write('REVIEW_1',records)
        _,proof=collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)
        self.assertEqual(proof['verified_evidence_pages'],10)
        self.assertEqual(proof['validated_rows'],len(self.request['cards']))
        self.assertEqual(proof['reply_validation_status'],'VALIDATED')
        self.assertEqual(proof['submission_attempts'],1)
        self.assertEqual(proof['packet_sha256'],fingerprint)
        seventh=next(i for i,r in enumerate(records) if r['payload'].get('type')=='custom_tool_call'
                     and '--page 7"' in r['payload']['input'])
        saved=self.saved_page_seven()
        for fault,error in [('changed_material','NATIVE_UNAUTHORIZED_TOOL'),('extra_hash','NATIVE_UNAUTHORIZED_TOOL'),
                ('extra_shell','NATIVE_UNAUTHORIZED_TOOL'),('altered_page','NATIVE_READ_INCOMPLETE'),
                ('failed_read','NATIVE_READ_INCOMPLETE'),('other_turn','NATIVE_UNAUTHORIZED_TOOL'),
                ('unsupported_tool','NATIVE_UNAUTHORIZED_TOOL')]:
            with self.subTest(fault=fault):
                changed=copy.deepcopy(records)
                call,execution,output=(r['payload'] for r in changed[seventh:seventh+3])
                if fault=='changed_material':
                    call['input']=call['input'].replace(self.material,'0'*64)
                elif fault=='extra_hash':
                    call['input']=call['input'].replace('--page 7',f'--packet-sha256 {fingerprint} --page 7')
                elif fault=='extra_shell':
                    call['input']=call['input'].replace('login: false','shell: "powershell", login: false')
                elif fault=='altered_page':
                    output['output'][1]['text']=pages[6][:-1]
                elif fault=='failed_read':
                    event=saved['command_record']
                    execution['item'].update(status='failed',exit_code=event['exit_code'],aggregated_output=event['stdout'])
                    output['output']=saved['model_output_record']['output']
                elif fault=='other_turn':
                    call['internal_chat_message_metadata_passthrough']['turn_id']='UNBOUND_TURN'
                elif fault=='unsupported_tool':
                    call['type']='web_search_call'
                self.app.write('REVIEW_1',changed)
                with self.assertRaisesRegex(ContractError,f'^{error}$'):
                    collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)

    def test_ticket_bound_reader_recomputes_both_saved_hashes(self):
        self.request['page_command_policy']=TICKET_BOUND_PAGE_COMMANDS
        self.pin_request()

        def ready():
            self.ticket()
            path=self.directory/(self.material+'.dispatch.json')
            saved=path.read_bytes()
            for field in ('packet_sha256','arguments_sha256'):
                with self.subTest(field=field):
                    path.write_text(encode({**self.receipt,field:'0'*64}),encoding='utf-8')
                    with self.assertRaisesRegex(ContractError,'^NATIVE_HANDOFF_UNATTESTED$'):
                        runner.review_page(self.job,self.material,None,7)
            path.write_bytes(saved)
            with self.assertRaisesRegex(ContractError,'^NATIVE_HANDOFF_UNATTESTED$'):
                runner.review_page(self.job,self.material,self.receipt['packet_sha256'],7)
            self.assertTrue(self.app.dispatch_once(self.args,self.job,self.receipt))
            self.on_sleep=self.app.complete_due

        result=self.wait(ready)
        self.assertEqual(result['status'],'NATIVE_RECEIPT_COLLECTED')

    def test_exact_page_commands_are_supplied_without_path_or_number_substitution(self):
        args,fingerprint,pages=packet(self.request,self.directory)
        first=next(line for line in args['brief'].splitlines() if line.startswith('wsl.exe '))
        self.assertIn('Do not specify shell, cwd, or other arguments.',args['brief'])
        commands=[first,*[json.loads(page)['next_command'] for page in pages[:-1]]]
        self.assertNotIn('next_command',json.loads(pages[-1]))
        self.assertEqual([command_page({'command':['powershell.exe','-Command',cmd]},
            self.directory,self.material,fingerprint) for cmd in commands],list(range(1,11)))

    def test_stage_bound_page_command_omits_hashes_and_separates_stage_and_batch(self):
        from researcher.native_handoff import _page_argv, wsl_root
        root=wsl_root().replace("'","''")
        stem=f"wsl.exe --cd '{root}' -- "
        argv=_page_argv(self.directory,self.material,None,stage='DISCOVERY',batch_index=1)
        command=stem+' '.join(argv)+' 2'
        self.assertNotIn(self.material,command)
        self.assertNotIn('--packet-sha256',command)
        self.assertEqual(command_page({'command':['powershell.exe','-Command',command]},
            self.directory,self.material,None,stage='DISCOVERY',batch_index=1),2)
        other_stage=stem+' '.join(_page_argv(self.directory,self.material,None,stage='SHORTLIST',batch_index=1))+' 2'
        with self.assertRaisesRegex(ContractError,'^NATIVE_PAGE_BINDING_INVALID$'):
            command_page({'command':['powershell.exe','-Command',other_stage]},
                self.directory,self.material,None,stage='DISCOVERY',batch_index=1)
        other_batch=stem+' '.join(_page_argv(self.directory,self.material,None,stage='DISCOVERY',batch_index=2))+' 2'
        with self.assertRaisesRegex(ContractError,'^NATIVE_PAGE_BINDING_INVALID$'):
            command_page({'command':['powershell.exe','-Command',other_batch]},
                self.directory,self.material,None,stage='DISCOVERY',batch_index=1)
        reordered=stem+('python3 -m researcher.openbot_runner review-page --stage DISCOVERY '
            f'--page 2 --batch-index 1 --job-id {self.job}')
        self.assertEqual(command_page({'command':['powershell.exe','-Command',reordered]},
            self.directory,self.material,None,stage='DISCOVERY',batch_index=1),2)
        missing=stem+('python3 -m researcher.openbot_runner review-page --job-id '
            f'{self.job} --stage DISCOVERY --page')
        with self.assertRaisesRegex(ContractError,'^NATIVE_PAGE_BINDING_INVALID$'):
            command_page({'command':['powershell.exe','-Command',missing]},
                self.directory,self.material,None,stage='DISCOVERY',batch_index=1)
        legacy=stem+('python3 -m researcher.openbot_runner review-page --job-id '
            f'{self.job} --material {self.material} --packet-sha256 {"0"*64} --page 2')
        with self.assertRaisesRegex(ContractError,'^NATIVE_PAGE_BINDING_INVALID$'):
            command_page({'command':['powershell.exe','-Command',legacy]},
                self.directory,self.material,None,stage='DISCOVERY',batch_index=1)

    def test_historical_compact_packet_retains_its_original_hash_bound_command(self):
        request={'input_transport':COMPACT_PAGES,'stage':'DISCOVERY'}
        args, fingerprint, pages=confirmed_packet({'title':'historical'},'historical packet text',
            self.directory,'a'*64,request=request)
        first=args['brief'].split('First command:\n',1)[1].splitlines()[0]
        self.assertIn('--material '+'a'*64,first)
        self.assertNotIn('--stage',first)
        self.assertIn(f'packet SHA-256 {fingerprint}',args['brief'])
        self.assertEqual(json.loads(pages[0])['packet_sha256'],fingerprint)

    def test_codex_code_mode_attests_stage_bound_pages_without_hash_echo(self):
        self.request.update(stage='DISCOVERY',review_batch_index=1,
            page_command_policy=STAGE_BOUND_PAGE_COMMANDS)
        self.pin_request()
        records=self.code_mode_rollout(multiline=True)
        first=next(row['payload'] for row in records if row['payload'].get('type')=='custom_tool_call')
        from researcher.native_codex import _code_mode_command
        self.assertNotIn(self.material,_code_mode_command(first))
        self.assertNotIn('--packet-sha256',_code_mode_command(first))
        self.app.write('REVIEW_1',records)
        _,proof=collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)
        self.assertEqual(proof['verified_evidence_pages'],10)
        self.assertEqual(proof['reply_validation_status'],'VALIDATED')

    def test_codex_wrong_stage_command_is_binding_error(self):
        self.request.update(stage='DISCOVERY',review_batch_index=1,
            page_command_policy=STAGE_BOUND_PAGE_COMMANDS)
        self.pin_request()
        records=self.code_mode_rollout(multiline=True)
        call=next(row['payload'] for row in records if row['payload'].get('type')=='custom_tool_call')
        call['input']=call['input'].replace('--stage DISCOVERY','--stage SHORTLIST')
        execution=next(row['payload'] for row in records if row['payload'].get('item',{}).get('type')=='CommandExecution')
        execution['item']['command'][-1]=execution['item']['command'][-1].replace(
            '--stage DISCOVERY','--stage SHORTLIST')
        self.app.write('REVIEW_1',records)
        with self.assertRaisesRegex(ContractError,'^NATIVE_PAGE_BINDING_INVALID$') as caught:
            collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)
        self.assertTrue(caught.exception.model_execution_observed)

    def test_wrong_final_keeps_execution_observed_but_unverified(self):
        records=self.code_mode_rollout(multiline=True)
        records[-1]['payload']['last_agent_message']='altered final response'
        self.app.write('REVIEW_1',records)
        with self.assertRaisesRegex(ContractError,'^NATIVE_REPLY_PROVENANCE$') as caught:
            collect(self.request,self.f.config,as_of=self.clock(),directory=self.directory)
        self.assertTrue(caught.exception.model_execution_observed)
        self.assertEqual(getattr(caught.exception,'verified_model_requests',0),0)

    def test_active_review_page_rejects_old_discovery_binding_on_shortlist_packet(self):
        from researcher.agent_review import _material
        request=dict(self.request,stage='SHORTLIST',review_batch_index=1,
            page_command_policy=STAGE_BOUND_PAGE_COMMANDS)
        material=digest(encode(_material(request)).encode())
        request['material_sha256']=material
        (self.directory/(material+'.request.json')).write_text(encode(request),encoding='utf-8')
        state=runner._read(self.folder/'state.json')
        state.update(state='REVIEW_READY',material_sha256=material,review_transport='PAGED_V2',
            native_identity=request['native_identity'],request_prepared_at_utc=self.clock(),request_expires_monotonic=1000)
        runner._write(self.folder/'state.json',state)
        saved=runner._read(self.directory/(material+'.request.json'))
        self.assertEqual(encode(saved),encode(request))
        self.assertEqual(digest(encode(_material(saved)).encode()),material)
        self.assertEqual(saved['native_identity'],runner._read(self.folder/'state.json')['native_identity'])
        with self.assertRaisesRegex(ContractError,'^NATIVE_PAGE_BINDING_INVALID$'):
            runner.review_page(self.job,material,None,1)
        with self.assertRaisesRegex(ContractError,'^NATIVE_PAGE_BINDING_INVALID$'):
            runner.review_page(self.job,None,None,1,stage='DISCOVERY',batch_index=1)

    def test_followup_answer_cannot_obscure_or_replace_the_original_child_turn(self):
        self.app.write('REVIEW_1',self.code_mode_rollout(multiline=True))
        at=self.clock()
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',
                ('FOLLOWUP','THREAD_1','SESSION_1','completed',at,at))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',
                ('THREAD_1','FOLLOWUP','assistant','final_answer','completed',at,2,encode({'text':'unrelated'})))
        proof=collect(self.request,self.f.config,as_of=at,directory=self.directory)[1]
        self.assertEqual(proof['reply_validation_status'],'VALIDATED')
        self.assertEqual(proof['verified_evidence_pages'],10)
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute("DELETE FROM projection_thread_messages WHERE turn_id='TURN_1' AND item_type='final_answer'")
        self.assertIsNone(collect(self.request,self.f.config,as_of=at,directory=self.directory))

    def test_code_mode_rejects_extra_commands_and_broken_page_relationships(self):
        original = self.code_mode_rollout(multiline=True)
        first = next(i for i, row in enumerate(original) if row['payload'].get('type') == 'custom_tool_call')
        for fault, code in (
                ('extra_code', 'UNAUTHORIZED_TOOL'), ('wrong_tool', 'UNAUTHORIZED_TOOL'),
                ('explicit_shell', 'UNAUTHORIZED_TOOL'), ('wrong_checkout', 'UNAUTHORIZED_TOOL'),
                ('embedded_comment', 'UNAUTHORIZED_TOOL'), ('computed_command', 'UNAUTHORIZED_TOOL'),
                ('changed_execution', 'UNAUTHORIZED_TOOL'), ('wrong_call_id', 'UNAUTHORIZED_TOOL'),
                ('wrong_turn', 'UNAUTHORIZED_TOOL'), ('nonzero_exit', 'READ_INCOMPLETE'),
                ('reordered', 'READ_INCOMPLETE'), ('missing_execution', 'READ_INCOMPLETE'),
                ('duplicate_page', 'UNAUTHORIZED_TOOL'),
                ('missing_page', 'READ_INCOMPLETE'), ('missing_output', 'UNAUTHORIZED_TOOL'),
                ('truncated_output', 'READ_INCOMPLETE'), ('truncated_execution', 'READ_INCOMPLETE'),
                ('wrong_final', 'REPLY_PROVENANCE')):
            with self.subTest(fault=fault):
                records = copy.deepcopy(original)
                call, execution, output = (records[i]['payload'] for i in range(first, first+3))
                if fault == 'extra_code':
                    call['input'] += 'text(r);'
                elif fault == 'explicit_shell':
                    call['input'] = call['input'].replace('  login:', '  shell: "powershell",\n  login:')
                elif fault == 'wrong_checkout':
                    call['input'] = call['input'].replace("' -- python3", "-codex' -- python3", 1)
                elif fault == 'embedded_comment':
                    call['input'] = call['input'].replace('  login:', '  /* extra */ login:')
                elif fault == 'computed_command':
                    call['input'] = call['input'].replace(',\n  login:', ' + "",\n  login:', 1)
                elif fault == 'wrong_tool':
                    call['name'] = 'other'
                elif fault == 'changed_execution':
                    execution['item']['command'][-1] += '; Write-Output x'
                elif fault == 'wrong_call_id':
                    output['call_id'] = 'different'
                elif fault == 'wrong_turn':
                    output['internal_chat_message_metadata_passthrough']['turn_id'] = 'other'
                elif fault == 'nonzero_exit':
                    execution['item']['exit_code'] = 1
                elif fault == 'reordered':
                    records[first+1], records[first+2] = records[first+2], records[first+1]
                elif fault == 'missing_execution':
                    del records[first+1]
                elif fault == 'duplicate_page':
                    records[first+3]['payload']['input'] = call['input']
                elif fault == 'missing_page':
                    del records[first:first+3]
                elif fault == 'missing_output':
                    del records[first+2]
                elif fault == 'truncated_output':
                    output['output'][1]['text'] = output['output'][1]['text'][:-1]
                elif fault == 'truncated_execution':
                    execution['item']['aggregated_output'] = execution['item']['aggregated_output'][:-1]
                elif fault == 'wrong_final':
                    records[-1]['payload']['last_agent_message'] = 'altered'
                self.app.write('REVIEW_1', records)
                with self.assertRaisesRegex(ContractError, code):
                    collect(self.request, self.f.config, as_of=self.clock(), directory=self.directory)

    def test_windows_uses_wsl_and_rejects_added_shell_operations(self):
        with patch('researcher.native_handoff.ROOT',r'C:\OpenBot Labs\Researcher'):
            args,fingerprint,pages=packet(self.request,self.directory)
            stem=next(line for line in args['brief'].splitlines() if line.startswith('wsl.exe '))
            command=stem
            self.assertTrue(command.startswith("wsl.exe --cd '/mnt/c/OpenBot Labs/Researcher' -- "))
            argv=[r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','-NoProfile','-Command',command]
            self.assertEqual(command_page({'command':argv},self.directory,self.material,fingerprint),1)
            self.assertIsNone(command_page({'command':[*argv[:-1],command+'; echo forged']},
                self.directory,self.material,fingerprint))
            self.assertEqual(''.join(json.loads(page)['text'] for page in pages),review_brief(self.request))
            self.assertTrue(all(page.isascii() and len(page)<65536 for page in pages))

    def test_ticket_reservation_without_native_tool_attempt_fails_at_submission_bound(self):
        result=self.wait(self.ticket)
        self.assertEqual(result['status'],'NATIVE_DISPATCH_RESERVED_TASK_MISSING',result)
        self.assertEqual(result['submission_attempts'],0)
        self.assertLessEqual(result['elapsed_seconds'],91)
        self.assertNotIn('start_task_arguments',runner.status(self.job,include_review=True))

    def test_second_live_timing_preserves_one_ticket_and_accepts_the_exact_attempt(self):
        def tick():
            if self.monotonic==61:
                status=self.ticket()
                self.assertEqual((utc(status['submit_before_utc'])-utc(self.clock())).total_seconds(),90)
            if self.monotonic==121:
                repeated=runner.status(self.job,include_review=True)
                self.assertEqual(repeated['state'],'REVIEW_DISPATCH_RESERVED')
                self.assertNotIn('start_task_arguments',repeated)
                self.assertTrue(self.app.dispatch_once(self.args,self.job,self.receipt))
                legacy={**self.receipt,'submission_policy':LEGACY_SUBMISSION_POLICY}
                with self.assertRaisesRegex(ContractError,'NATIVE_SUBMISSION_OUTSIDE_WINDOW'):
                    verify_submission_window({'submission_attempts':1,'attempted_at_utc':self.clock()},legacy)
            self.app.complete_due()

        result=self.wait(lambda:setattr(self,'on_sleep',tick))
        self.assertEqual(result['status'],'NATIVE_RECEIPT_COLLECTED',result)
        self.assertEqual(result['submission_attempts'],1)
        self.assertEqual(result['observed_model_attempts'],1)
        self.assertEqual(len(self.app.submitted),1)

    def test_attempt_at_reservation_deadline_is_rejected_and_pages_close(self):
        def tick():
            if self.monotonic==61:self.ticket()
            if self.monotonic==151:self.record_submission()

        result=self.wait(lambda:setattr(self,'on_sleep',tick))
        self.assertEqual(result['status'],'NATIVE_SUBMISSION_OUTSIDE_WINDOW',result)
        with self.assertRaisesRegex(ContractError,'NATIVE_DISPATCH_WINDOW_CLOSED'):
            runner.review_page(self.job,self.material,self.receipt['packet_sha256'],1)

    def test_no_handoff_ticket_fails_at_submission_bound(self):
        result=self.wait()
        self.assertEqual(result['status'],'NATIVE_TASK_NOT_SUBMITTED',result)
        self.assertEqual(result['submission_attempts'],0)
        self.assertLessEqual(result['elapsed_seconds'],91)

    def test_no_native_response_after_attempt_has_own_bound(self):
        def ready():self.ticket();self.record_submission()
        result=self.wait(ready)
        self.assertEqual(result['status'],'NATIVE_TOOL_RESPONSE_NOT_OBSERVED',result)
        self.assertEqual(result['submission_attempts'],1)
        self.assertLessEqual(result['elapsed_seconds'],31)

    def test_positive_tool_response_without_app_task_has_own_bound(self):
        def ready():self.ticket();self.record_submission(response={'taskId':'MISSING_TASK','title':self.args['title']})
        result=self.wait(ready)
        self.assertEqual(result['status'],'NATIVE_ACKNOWLEDGED_TASK_MISSING',result)
        self.assertEqual(result['observed_model_attempts'],0)
        self.assertLessEqual(result['elapsed_seconds'],31)

    def test_native_tool_rejection_is_not_a_missing_task(self):
        def ready():self.ticket();self.record_submission(response=False)
        result=self.wait(ready)
        self.assertEqual(result['status'],'NATIVE_TOOL_REJECTED',result)
        self.assertEqual(result['submission_attempts'],1)
        self.assertEqual(result['observed_model_attempts'],0)

    def test_native_tool_input_size_rejection_uses_utf16_units(self):
        def ready():
            self.ticket();self.record_submission(response=False,arguments={**self.args,'brief':'𝄞'*50_001})
        result=self.wait(ready)
        self.assertEqual(result['status'],'NATIVE_TOOL_INPUT_SIZE_REJECTED',result)
        self.assertEqual(result['submission_attempts'],1)

    def test_duplicate_native_attempt_is_rejected_even_with_one_ticket(self):
        def ready():
            self.ticket();self.record_submission();self.record_submission()
        result=self.wait(ready)
        self.assertEqual(result['terminal_error']['code'],'NATIVE_HANDOFF_UNATTESTED',result)
        self.assertEqual(len(list(self.directory.glob('*.dispatch.json'))),1)
        self.assertEqual(result['observed_model_attempts'],0)

    def test_truncated_provider_page_cannot_validate_or_import(self):
        def ready():
            self.ticket();self.app.dispatch_once(self.args,self.job,self.receipt)
            for item in self.app.pending[0][-1]:
                if item['payload'].get('type')=='function_call_output':
                    item['payload']['output']=item['payload']['output'][:-64]
                    break
            self.on_sleep=self.app.complete_due
        result=self.wait(ready)
        self.assertEqual(result['terminal_error']['code'],'NATIVE_READ_INCOMPLETE',result)
        self.assertEqual(result['observed_model_attempts'],0)
        imported=exchange(self.directory,(),{},cached=True,previous={'material_sha256':self.material},
            as_of=self.clock(),audit_config=self.j.private,require_identity=True)
        self.assertEqual(imported.get('reason'),'NATIVE_READ_INCOMPLETE',imported)
        self.assertFalse((self.directory/(self.material+'.reply.json')).exists())

    def test_clock_discontinuity_cannot_revive_stale_packet(self):
        def suspended():self.seconds+=601
        def ready():self.ticket();self.on_sleep=suspended
        result=self.wait(ready)
        self.assertEqual(result['status'],'NATIVE_REQUEST_STALE',result)
        self.assertEqual(result['clock_diagnostic']['code'],'ELAPSED_TIME_DISCONTINUITY')
        self.assertEqual(result['submission_attempts'],0)

    def test_changed_saved_arguments_or_ticket_cannot_expose_packet(self):
        def ready():
            self.ticket()
            task=self.directory/(self.material+'.review-task.json')
            task.write_text(encode({**self.args,'brief':self.args['brief'][:-1]}))
            with self.assertRaisesRegex(ContractError,'HANDOFF_UNATTESTED'):
                runner.review_page(self.job,self.material,self.receipt['packet_sha256'],1)
            task.write_text(encode(self.args))
            lease=self.directory/(self.material+'.dispatch.json')
            lease.write_text(encode({**self.receipt,'arguments_sha256':'0'*64}))
        result=self.wait(ready)
        self.assertEqual(result['terminal_error']['code'],'NATIVE_HANDOFF_UNATTESTED',result)
