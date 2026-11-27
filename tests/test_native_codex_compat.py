"""Observed 0.169 ordinal envelopes/PowerShell receipts; offline security cases.

Values are replaced; no private runtime record, prompt, reasoning or path is
copied into fixtures. No scanner or model is invoked by these tests.
"""
import copy
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from researcher import native_codex as codex, openbot_runner as runner, native_host
from researcher.contracts import ContractError,encode,utc
from researcher.native_identity import NativeEvidenceError,safe_diagnostic
from researcher.native_runtime import collect
from researcher.settings import ROOT
import test_openbot_runner as runner_fixture


class ObservedCodexCompatibility(unittest.TestCase):
    def setUp(self):
        self.r=runner_fixture.OpenBotRunnerContract();self.r.setUp();self.addCleanup(self.r.doCleanups)
        self.f=self.r.f
        self.layout=json.loads((ROOT/'tests/fixtures/native-codex-0169-ordinal.json').read_text())
        for session,rows in [('PARENT',self.f.parent),('CHILD',self.f.child)]:
            meta=copy.deepcopy(self.layout['session_meta'])
            meta.update(id=session,session_id=session,cwd=str(self.f.workspace),timestamp=rows[0]['timestamp'],
                runtime_workspace_roots=[str(self.f.workspace)])
            rows[0]['payload']=meta
            next(x['payload'] for x in rows if x['type']=='turn_context')['cwd']=str(self.f.workspace)
        content=copy.deepcopy(self.layout['user_content_parts']);content[1]['text']=self.f.brief
        self.f.child[3]['payload']['item']['content']=content
        self.f.child[4]['payload']['usage']=copy.deepcopy(self.layout['usage'])
        self.command=copy.deepcopy(self.layout['launch_item'])
        self.command['command'][-1]=self.command['command'][-1].replace('@ROOT@',str(ROOT)).replace('@REQUEST_ID@',self.r.key)
        self.launch=self.f.record(1,'event_msg',{'type':'item_completed','turn_id':'PARENT_TURN','thread_id':'PARENT',
            'started_at_ms':0,'completed_at_ms':1,'item':self.command})
        self.f.parent.append(self.launch)
        self.f.child.insert(-2,self.f.record(4,'response_item',{'type':'message','role':'assistant',
            'phase':'final_answer','status':'completed','content':[{'type':'output_text','text':self.f.raw}]}))
        self.write()
        job=runner.start(self.r.key)['job_id'];self.job=job;self.folder=runner._job(job)
        self.state=runner._read(self.folder/'state.json')

    def write(self):
        for session,rows in [('PARENT',self.f.parent),('CHILD',self.f.child)]:
            prepared=[]
            for ordinal,row in enumerate(rows):
                value={'timestamp':row['timestamp'],'ordinal':ordinal,'type':row['type'],'payload':row['payload']}
                if row['type']=='response_item':value['metadata']={}
                prepared.append(value)
            (self.f.root/'sessions'/(session+'.jsonl')).write_text(''.join(json.dumps(x)+'\n' for x in prepared))

    def proof(self):
        with patch.object(runner,'now_utc',return_value=self.f.time(5)):
            return runner.attest_start(self.state,self.f.config)

    def test_observed_current_owner_launch_and_isolated_review_are_attested(self):
        self.assertEqual(self.proof()['status'],'VERIFIED_OPENBOT_AGENT_COMMAND')
        raw,audit=self.f.get()
        self.assertEqual(raw,self.f.raw);self.assertEqual(audit['schema_variant'],'CODEX_0169_ORDINAL')
        self.assertEqual(audit['model_requests'],1);self.assertEqual(audit['unauthorized_tool_operations'],0)
        self.assertEqual(audit['provider_usage'],[self.layout['usage']])
        for value in (audit,self.proof()):
            self.assertNotIn('PRIVATE_',encode(value));self.assertNotIn(str(self.f.workspace),encode(value))

    def test_0171_ordinal_uses_the_same_parent_and_child_attestation_checks(self):
        for rollout in (self.f.parent,self.f.child):
            rollout[0]['payload'].update(cli_version='0.171.0',history_mode='paginated')
        self.write()
        self.assertEqual(self.proof()['status'],'VERIFIED_OPENBOT_AGENT_COMMAND')
        raw,audit=self.f.get()
        self.assertEqual(raw,self.f.raw)
        self.assertTrue(audit['native_invocation_verified'])
        self.assertEqual(audit['schema_variant'],'CODEX_0169_ORDINAL')
        self.f.child[2]['payload']['model']='fixture-wrong-model'
        self.write()
        with self.assertRaisesRegex(ContractError,'NATIVE_MODEL_SWITCHED'):self.f.get()

    def test_json_key_order_and_whitespace_are_irrelevant(self):
        for session in ('PARENT','CHILD'):
            p=self.f.root/'sessions'/(session+'.jsonl')
            rows=[json.loads(line) for line in p.read_text().splitlines()]
            p.write_text(''.join('  '+json.dumps(dict(reversed(list(r.items()))))+' \n' for r in rows))
        self.assertEqual(self.proof()['status'],'VERIFIED_OPENBOT_AGENT_COMMAND')
        self.assertIsNotNone(self.f.get())

    def test_missing_empty_truncated_duplicate_and_malformed_envelopes(self):
        p=self.f.root/'sessions/CHILD.jsonl';original=p.read_text();lines=original.splitlines(True)
        cases=['',''.join(lines[1:]),original[:-15],'{bad}\n',
            lines[0].replace('"ordinal": 0','"ordinal": 0, "ordinal": 0')+''.join(lines[1:]),
            lines[0].replace('"payload": {','"payload": null, "payload": {')+''.join(lines[1:])]
        for raw in cases:
            with self.subTest(case=cases.index(raw)):
                p.write_text(raw)
                with self.assertRaises(ContractError):self.f.get()
        p.write_text(original)

    def test_record_order_ordinal_gaps_and_bad_timestamps_fail(self):
        p=self.f.root/'sessions/CHILD.jsonl';original=p.read_text();rows=[json.loads(x) for x in original.splitlines()]
        for change in ('reverse','gap','bool','timezone','timestamp_type','time_reversal'):
            values=copy.deepcopy(rows)
            if change=='reverse':values[2],values[3]=values[3],values[2]
            if change=='gap':values[3]['ordinal']+=1
            if change=='bool':values[3]['ordinal']=True
            if change=='timezone':values[2]['timestamp']='2026-11-15T00:00:00'
            if change=='timestamp_type':values[2]['timestamp']=None
            if change=='time_reversal':values[3]['timestamp']=self.f.time(0)
            with self.subTest(change=change):
                p.write_text(''.join(json.dumps(x)+'\n' for x in values))
                with self.assertRaises(ContractError):self.f.get()
        p.write_text(original)
        # Renumbering does not restore the semantic context-before-input proof.
        self.f.child[2],self.f.child[3]=self.f.child[3],self.f.child[2];self.write()
        with self.assertRaisesRegex(ContractError,'INCOMPLETE'):self.f.get()

    def test_unsupported_version_backend_and_inconsistent_session_meta(self):
        original=copy.deepcopy(self.f.child[0]['payload'])
        for key,value,code in [('cli_version','0.170.0','SCHEMA_UNSUPPORTED'),('cli_version','0.169.1','SCHEMA_UNSUPPORTED'),
                ('originator','other','SESSION_MISMATCH'),('id','forged','SESSION_MISMATCH'),
                ('cwd','elsewhere','SESSION_MISMATCH'),('model_provider','unverified','SESSION_MISMATCH')]:
            self.f.child[0]['payload']={**original,key:value};self.write()
            with self.subTest(key=key,value=value):
                with self.assertRaisesRegex(ContractError,code):self.f.get()
        self.f.child[0]['payload']=original;self.write()
        with sqlite3.connect(self.f.config['provider_db']) as db:db.execute("UPDATE threads SET model_provider='unverified'")
        with self.assertRaisesRegex(ContractError,'SESSION_MISMATCH'):self.proof()
        with self.assertRaisesRegex(ContractError,'PROVIDER_UNSUPPORTED'):
            codex.records(self.f.config,'PARENT',self.f.workspace,start=utc(self.f.time(-10)),end=utc(self.f.time(5)),backend='unverified')

    def test_wrong_agent_owner_turn_session_workspace_and_switched_model(self):
        original=copy.deepcopy(self.state)
        for field,value in [('agent_id','wrong'),('turn_ref','wrong'),('external_session_ref','wrong')]:
            self.state=copy.deepcopy(original);self.state['native_identity'][field]=value
            with self.subTest(field=field):
                with self.assertRaises(ContractError):self.proof()
        self.state=original
        context=self.f.parent[1]['payload'];saved=copy.deepcopy(context)
        for field,value in [('turn_id','OTHER_TURN'),('cwd','wrong'),('model','different-model')]:
            context.update({field:value});self.write()
            with self.subTest(field=field):
                with self.assertRaises(ContractError):self.proof()
            context.clear();context.update(saved)
        self.write()
        with sqlite3.connect(self.f.config['openbot_db']) as db:db.execute("UPDATE projection_mailbox_messages SET sender_kind='agent'")
        with self.assertRaisesRegex(ContractError,'OWNER_START_REQUIRED'):self.proof()

    def test_command_mentions_failed_commands_other_turn_results_and_wrong_argv(self):
        original=copy.deepcopy(self.launch)
        mutations=[('status','in_progress'),('exit_code',1),('exit_code',False),('type','AgentMessage')]
        for key,value in mutations:
            self.launch['payload']['item']={**original['payload']['item'],key:value};self.write()
            with self.subTest(key=key):
                with self.assertRaisesRegex(ContractError,'START_UNATTESTED'):self.proof()
        self.launch.clear();self.launch.update(copy.deepcopy(original))
        for field in ('turn_id','thread_id'):
            self.launch['payload'][field]='OTHER';self.write()
            with self.subTest(field=field):
                with self.assertRaises(ContractError):self.proof()
            self.launch['payload'][field]=original['payload'][field]
        base=original['payload']['item']['command']
        for script in ('echo '+base[-1],base[-1]+'; echo ok',base[-1].replace(self.r.key,'b'*32),
                base[-1]+' --extra',base[-1].replace(' start ',' status ')):
            self.launch['payload']['item']['command']=[*base[:-1],script];self.write()
            with self.subTest(script_kind=script[:4]):
                with self.assertRaisesRegex(ContractError,'START_UNATTESTED'):self.proof()
        for flags in (['-ExecutionPolicy','Bypass','-Command'],['-Command','-NoProfile'],['-NoProfile','-NoProfile','-Command']):
            self.assertFalse(runner.recorded_launch_matches({'command':[base[0],*flags,base[-1]]},self.r.key,str(ROOT),'posix'))

    def test_prior_or_replayed_launch_is_not_proof(self):
        self.f.parent[0]['timestamp']=self.f.time(-30)
        self.launch['timestamp']=self.f.time(-20)
        self.f.parent.insert(1,self.f.parent.pop());self.write()
        with self.assertRaises(ContractError):self.proof()
        self.f.parent[0]['timestamp']=self.f.time(-10)
        self.launch['timestamp']=self.f.time(1);self.f.parent.append(self.f.parent.pop(1));self.write()
        self.state['request_id']='b'*32
        with self.assertRaisesRegex(ContractError,'START_UNATTESTED'):self.proof()

    def test_full_input_final_reply_and_review_tools_remain_strict(self):
        original=copy.deepcopy(self.f.child)
        for change in ('input','final','raw_final','completion','output_tool','command_tool','handoff_turn'):
            self.f.child=copy.deepcopy(original)
            if change=='input':self.f.child[3]['payload']['item']['content'][1]['text']=self.f.brief[:-1]
            if change=='final':self.f.child[-2]['payload']['item']['content'][0]['text']='forged'
            if change=='raw_final':self.f.child[-3]['payload']['content'][0]['text']='forged'
            if change=='completion':self.f.child.pop()
            if change=='output_tool':self.f.child.insert(5,self.f.record(3,'response_item',{'type':'custom_tool_call_output','output':'no call receipt'}))
            if change=='command_tool':self.f.child.insert(5,self.f.item(3,{'type':'CommandExecution','status':'completed','exit_code':0}))
            if change=='handoff_turn':self.f.parent[2]['payload']['thread_id']='OTHER'
            self.write()
            with self.subTest(change=change):
                with self.assertRaises(ContractError):self.f.get()
            self.f.parent[2]['payload']['thread_id']='PARENT'

    def test_provider_db_model_and_review_context_workspace_are_verified(self):
        with sqlite3.connect(self.f.config['provider_db']) as db:db.execute("UPDATE threads SET model='switched' WHERE id='CHILD'")
        with self.assertRaisesRegex(ContractError,'MODEL_SWITCHED'):
            collect(self.f.request,self.f.config,as_of=self.f.time(5),require_configured_model=True)
        self.assertEqual(self.f.get()[1]['model'],self.f.identity['model'])
        with sqlite3.connect(self.f.config['provider_db']) as db:db.execute("UPDATE threads SET model=? WHERE id='CHILD'",(self.f.agent['model'],))
        self.f.child[2]['payload']['cwd']='different-workspace';self.write()
        with self.assertRaisesRegex(ContractError,'SESSION_MISMATCH'):self.f.get()

    def test_historical_parent_and_child_require_one_consistent_model_context(self):
        for name, turn, session in (('parent','PARENT_TURN','PARENT'), ('child','CHILD_TURN','CHILD')):
            original=copy.deepcopy(getattr(self.f,name))
            index=next(i for i,row in enumerate(original) if row['type']=='turn_context')
            for mutation, error in (
                    ('missing','REVIEW_INCOMPLETE'), ('duplicate','REVIEW_INCOMPLETE'),
                    ('contradictory','MODEL_SWITCHED'), ('missing_model','MODEL_SWITCHED'),
                    ('changed_settings','MODEL_SWITCHED'), ('malformed_settings','SCHEMA_UNSUPPORTED')):
                with self.subTest(turn=name,mutation=mutation):
                    revised=copy.deepcopy(original)
                    context=revised[index]
                    if mutation=='missing':
                        if name=='child':
                            del revised[index]
                        else:
                            revised[index]=self.f.record(-10,'event_msg',{'type':'task_started','turn_id':turn})
                    elif mutation=='duplicate':
                        revised.insert(index+1,copy.deepcopy(context))
                    elif mutation=='contradictory':
                        revised.insert(index+1,copy.deepcopy(context))
                        revised[index+1]['payload']['model']='fixture-different-model'
                    elif mutation=='missing_model':
                        del context['payload']['model']
                    else:
                        settings={'model':'fixture-different-model'} if mutation=='changed_settings' else []
                        revised.insert(index+1,{'timestamp':context['timestamp'],'type':'event_msg',
                            'payload':{'type':'thread_settings_applied','thread_id':session,'thread_settings':settings}})
                    setattr(self.f,name,revised)
                    self.write()
                    with self.assertRaisesRegex(ContractError,error):self.f.get()
            setattr(self.f,name,original)
            self.write()

    def test_late_context_switch_and_unknown_record_kind_cannot_follow_a_valid_receipt(self):
        original=copy.deepcopy(self.f.parent)
        self.f.parent.append(self.f.record(2,'turn_context',{'turn_id':'PARENT_TURN','model':'switched'}));self.write()
        with self.assertRaisesRegex(ContractError,'MODEL_SWITCHED'):self.proof()
        with self.assertRaisesRegex(ContractError,'MODEL_SWITCHED'):self.f.get()
        self.f.parent=original
        self.f.parent.append(self.f.record(2,'unverified_provider_record',{}));self.write()
        with self.assertRaisesRegex(ContractError,'SCHEMA_UNSUPPORTED'):self.proof()

    def test_private_payloads_and_usage_are_never_exported_as_diagnostics(self):
        self.f.child[4]['payload']['usage']['secret']='PRIVATE_SECRET_SENTINEL';self.write()
        _,audit=self.f.get();self.assertNotIn('PRIVATE_',encode(audit))
        malformed={'stage':'ENVELOPE','check':'JSON','schema_variant':'PRIVATE_SECRET_SENTINEL','path':'PRIVATE_PATH'}
        self.assertEqual(safe_diagnostic(malformed),{})
        self.f.child[0]['payload']['cli_version']='PRIVATE_SECRET_SENTINEL';self.write()
        with self.assertRaises(NativeEvidenceError) as found:self.f.get()
        self.assertEqual(str(found.exception),'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
        self.assertNotIn('PRIVATE_',encode(found.exception.diagnostic))

    def test_schema_failure_diagnostic_survives_host_bridge_without_private_values(self):
        from types import SimpleNamespace
        from researcher.native_identity import load_private
        exe=self.f.root/'python.exe';exe.touch();config=load_private(self.r.private);config['native_python']=str(exe)
        good={'stage':'SESSION','check':'VERSION','schema_variant':'CODEX_0169_ORDINAL'}
        opencode={'stage':'EVIDENCE','check':'ASSISTANT_KEYS',
                  'schema_variant':'OPENCODE_SESSION_PART'}
        for diagnostic,expected in [(good,good),(opencode,opencode),
                ({**good,'secret':'PRIVATE_SECRET'},{}),({**good,'check':'PRIVATE_SECRET'}, {})]:
            response=encode({'reason':'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED','diagnostic':diagnostic})
            with patch('subprocess.run',return_value=SimpleNamespace(returncode=2,stdout=response)):
                with self.assertRaises(ContractError) as found:native_host.call(config,'configured_identity')
            self.assertEqual(getattr(found.exception,'diagnostic',{}),expected)
            self.assertNotIn('PRIVATE_',str(found.exception))

    def test_schema_failure_is_terminal_before_scanning_and_has_safe_status(self):
        self.f.parent[0]['payload']['cli_version']='PRIVATE_SECRET_SENTINEL';self.write()
        with patch.object(runner,'now_utc',return_value=self.f.time(5)),patch('researcher.discovery.scan_market_research') as scanner:
            result=runner.run_job(self.job);again=runner.run_job(self.job)
        self.assertEqual(result['state'],'FAILED');self.assertEqual(again['state'],'FAILED');scanner.assert_not_called()
        self.assertEqual(result['native_diagnostic'],{'stage':'SESSION','check':'VERSION','schema_variant':'CODEX_0169_ORDINAL'})
        self.assertNotIn('PRIVATE_',encode(result));self.assertFalse((self.folder/'research.sqlite').exists())
        state=runner._read(self.folder/'state.json')
        for key in ('start_proof','stage','scanner_started_at_utc'):self.assertNotIn(key,state)
        state['native_diagnostic']['check']='PRIVATE_SECRET_SENTINEL';runner._write(self.folder/'state.json',state)
        self.assertNotIn('native_diagnostic',runner.status(self.job))

    def test_historic_payload_and_reasoning_are_not_decoded(self):
        # Deliberately invalid nested JSON remains outside the evidence slice;
        # the outer structural envelope is sufficient to skip private content.
        p=self.f.root/'sessions/CHILD.jsonl';lines=p.read_text().splitlines(True)
        historic={'timestamp':self.f.time(0),'ordinal':1,'type':'response_item','payload':{'type':'message','content':'PRIVATE_HISTORY'}}
        rows=[json.loads(x) for x in lines];rows.insert(1,historic)
        for i,row in enumerate(rows):row['ordinal']=i
        raw=''.join(json.dumps(x)+'\n' for x in rows).replace('"PRIVATE_HISTORY"','PRIVATE_HISTORY_NOT_JSON')
        p.write_text(raw)
        self.assertIsNotNone(self.f.get())
