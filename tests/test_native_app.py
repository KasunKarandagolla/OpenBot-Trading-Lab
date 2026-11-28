"""Synthetic native storage fixtures only; these never count as real LLM calls."""
import json,sqlite3,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import timedelta
from unittest.mock import patch
from researcher.settings import ROOT
from researcher.contracts import encode,digest,utc,ContractError
from researcher.agent_review import make_request,AGENT,MODEL,REPLY
from researcher.native_app import prepare,collect,wait_for_reply,_merge_handoff,_windows
from test_session4 import case


class NativeReceiptCollector(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True);self.tmp=TemporaryDirectory(dir=ROOT/'work');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.folder=self.root/'exchange';self.folder.mkdir()
        self.workspace=self.root/'existing-agent';skill=self.workspace/'.agents/skills/market-research-review/SKILL.md'
        skill.parent.mkdir(parents=True);skill.write_bytes((ROOT/'.agents/skills/market-research-review/SKILL.md').read_bytes())
        card,facts,_,bars=case(family='F4');self.at=bars[-1].end
        self.request=make_request([card],facts,as_of=self.at,skill_sha256=digest(skill.read_bytes()));self.key=self.request['material_sha256']
        (self.folder/(self.key+'.request.json')).write_text(encode(self.request)+'\n')
        self.config={'openbot_db':str(self.root/'openbot.db'),'provider_db':str(self.root/'opencode.db'),'agent_workspace':str(self.workspace)}
        self.configfile=self.root/'local.json';self.configfile.write_text(json.dumps(self.config))
        _,_,self.target=prepare(self.folder,self.key,self.configfile)
        self.reply={'schema_version':REPLY,'material_sha256':self.key,'trade_authorization':False,'interpretations':[{
            'card_id':card.id,'interpretation':'F4','supporting_evidence_ids':['seq'],'contradicting_ids':[],
            'strongest_rival':'NULL','null_hypothesis':False,'missed_traps':['SHARED_PRICE_EVIDENCE'],
            'falsifying_question':'FIRST_OBSTACLE','priority':'WATCH','claims':[]}]}
        self.end=(utc(self.at)+timedelta(seconds=2)).isoformat();self.now=(utc(self.at)+timedelta(seconds=3)).isoformat()
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.executescript('''CREATE TABLE projection_agents(agent_id,model,agent_json);
                CREATE TABLE projection_threads(thread_id,agent_id);
                CREATE TABLE projection_thread_messages(thread_id,turn_id,author,item_type,status,created_at,message_json);
                CREATE TABLE projection_turns(turn_id,provider_session_id,started_at,completed_at,status);
                CREATE TABLE projection_provider_sessions(id,model,external_session_id);''')
            db.execute('INSERT INTO projection_agents VALUES(?,?,?)',('TEST_AGENT',MODEL,json.dumps({'name':AGENT})))
            db.execute('INSERT INTO projection_threads VALUES(?,?)',('TEST_THREAD','TEST_AGENT'))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?)',('TEST_THREAD',None,'user',None,'completed',self.at,json.dumps({'text':'OPENBOT-RESEARCH-'+self.key})))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?)',('TEST_THREAD','TEST_TURN','assistant','final_answer','completed',self.end,json.dumps({'text':encode(self.reply)})))
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?)',('TEST_TURN','TEST_PROVIDER',self.at,self.end,'completed'))
            db.execute('INSERT INTO projection_provider_sessions VALUES(?,?,?)',('TEST_PROVIDER',MODEL,'TEST_EXTERNAL'))
        canonical=skill.read_text();body=canonical.split('---',2)[2].strip()
        self.tools=[{'type':'tool','name':'skill','state':{'status':'completed','input':{'id':'market-research-review'},'content':[{'type':'text','text':body}]}},
            {'type':'tool','name':'read','state':{'status':'completed','input':{'path':_windows(self.target)},'content':[{'type':'text','text':'\n'.join(f'{i}: {line}' for i,line in enumerate((encode(self.request)+'\n').splitlines(),1))}]}}]
        self.tools.append({'type':'tool','name':'grep','state':{'status':'completed',
            'input':{'path':_windows(self.target),'pattern':'card_id'},'content':[]}})
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('CREATE TABLE session_message(session_id,type,time_created,seq,data)')
        self.write_attempt()

    def test_verified_handoff_binding_survives_weaker_provider_and_app_reads(self):
        previous={'material_sha256':'a'*64,'review_stage':'DISCOVERY',
            'submission_state':'ACKNOWLEDGED','submission_attempts':1,
            'attempted_at_utc':'2026-01-01T00:00:01Z','responded_at_utc':'2026-01-01T00:00:02Z',
            'acknowledged_task_ref':'task-ref','argument_binding':'OPENBOT_SCHEMA_TRIMMED',
            'reserved_at_utc':'2026-01-01T00:00:00Z','task_created':True,
            'handoff_observation':'VERIFIED',
            'task':{'count':1,'task_state':'RUNNING','task_ref':'task-ref'}}
        weaker={'material_sha256':'a'*64,'review_stage':'DISCOVERY',
            'submission_state':'NOT_OBSERVED','submission_attempts':0,'task_created':False,
            'handoff_observation':'PARENT_ACKNOWLEDGMENT_PENDING',
            'task':{'count':0,'task_state':'MISSING'}}
        merged=_merge_handoff(previous,weaker)
        self.assertEqual(merged['submission_state'],'ACKNOWLEDGED')
        self.assertEqual(merged['acknowledged_task_ref'],'task-ref')
        self.assertEqual(merged['task']['task_state'],'RUNNING')
        self.assertEqual(merged['latest_handoff_observation'],'PARENT_ACKNOWLEDGMENT_PENDING')

        conflicting={**weaker,'submission_state':'ACKNOWLEDGED','submission_attempts':1,
            'acknowledged_task_ref':'different-task'}
        with self.assertRaisesRegex(ContractError,'NATIVE_HANDOFF_UNATTESTED'):
            _merge_handoff(previous,conflicting)

    def write_attempt(self,model='deepseek-v4.1-flash-free'):
        data={'model':{'providerID':'opencode','id':model},'content':self.tools,'finish':'stop','tokens':{'input':1,'output':1},'cost':0}
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('DELETE FROM session_message');db.execute('INSERT INTO session_message VALUES(?,?,?,?,?)',('TEST_EXTERNAL','assistant',int(utc(self.at).timestamp()*1000),1,json.dumps(data)))

    def test_schema_compatible_second_opencode_backend_uses_trusted_app_model(self):
        from researcher.agent_review import _material
        other='fixture-vendor/second-model'
        self.request['model']=other
        self.request['material_sha256']=digest(encode(_material(self.request)).encode())
        self.key=self.request['material_sha256'];self.reply['material_sha256']=self.key
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute('UPDATE projection_agents SET model=?',(other,))
            db.execute('UPDATE projection_provider_sessions SET model=?',(other,))
            db.execute("UPDATE projection_thread_messages SET message_json=? WHERE author='user'",
                (encode({'text':'OPENBOT-RESEARCH-'+self.key}),))
            db.execute("UPDATE projection_thread_messages SET message_json=? WHERE author='assistant'",
                (encode({'text':encode(self.reply)}),))
        self.tools[1]['state']['content'][0]['text']='\n'.join(f'{i}: {line}' for i,line in enumerate((encode(self.request)+'\n').splitlines(),1))
        data={'model':{'providerID':'fixture-vendor','id':'second-model'},'content':self.tools}
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('DELETE FROM session_message')
            db.execute('INSERT INTO session_message VALUES(?,?,?,?,?)',('TEST_EXTERNAL','assistant',int(utc(self.at).timestamp()*1000),1,encode(data)))
        _,audit=collect(self.request,self.config,self.target,as_of=self.now)
        self.assertEqual(audit['model'],other);self.assertEqual(audit['validated_rows'],1)

    def test_exact_native_task_is_audited_and_source_databases_are_unchanged(self):
        before={k:digest(Path(self.config[k]).read_bytes()) for k in ('openbot_db','provider_db')}
        result=wait_for_reply(self.folder,self.key,self.configfile,clock=lambda:self.now)
        self.assertEqual(result['status'],'NATIVE_RECEIPT_COLLECTED')
        audit=json.loads((self.folder/(self.key+'.audit.json')).read_text())
        self.assertEqual(audit['validated_rows'],1);self.assertTrue(audit['skill_and_request_read_completely'])
        self.assertEqual(before,{k:digest(Path(self.config[k]).read_bytes()) for k in before})
        with patch('researcher.native_app.collect',side_effect=[sqlite3.OperationalError('disk I/O error'),
                collect(self.request,self.config,self.target,as_of=self.now)]):
            again=wait_for_reply(self.folder,self.key,self.configfile,wait_seconds=1,clock=lambda:self.now)
        self.assertEqual(again['storage_read_retries'],1)
        # Cross-OS collection now delegates individual trusted scoped reads in
        # native_host, after local publication, instead of an entire wait child.
        # This legacy OpenCode fixture remains a direct read-only compatibility
        # test; Codex WSL subprocess contracts live in test_openbot_runner.
        if __import__('os').name!='nt':
            executable=self.root/'python.exe';executable.touch()
            self.configfile.write_text(json.dumps({**self.config,'native_python':str(executable)}))
            with patch('subprocess.run') as process:
                scoped=wait_for_reply(self.folder,self.key,self.configfile,clock=lambda:self.now)
            self.assertEqual(scoped['status'],'NATIVE_RECEIPT_COLLECTED')
            process.assert_not_called()

    def test_unapproved_tool_or_replacement_model_cannot_produce_a_receipt(self):
        self.tools.append({'type':'tool','name':'shell','state':{'status':'completed','input':{},'content':[]}});self.write_attempt()
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.now)
        self.tools.pop();self.tools[-1]['state']['input']['path']=_windows(self.workspace);self.write_attempt()
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.now)
        self.tools[-1]['state']['input']['path']=_windows(self.target);self.write_attempt(model='REPLACEMENT')
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.now)
        self.assertFalse((self.folder/(self.key+'.audit.json')).exists())

    def test_real_invocation_proof_is_retained_when_reply_contract_is_rejected(self):
        self.reply['interpretations'][0]['interpretation']='F4 prose is not an enum label'
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute("UPDATE projection_thread_messages SET message_json=? WHERE author='assistant'",
                (json.dumps({'text':encode(self.reply)}),))
        result=wait_for_reply(self.folder,self.key,self.configfile,clock=lambda:self.now)
        self.assertEqual(result['observed_model_attempts'],1)
        self.assertEqual(result['reply_validation_status'],'REJECTED')
        self.assertEqual(result['reply_rejection_reason'],'AGENT_REPLY_ADVICE')
        audit=json.loads((self.folder/(self.key+'.audit.json')).read_text())
        self.assertTrue(audit['native_invocation_verified']);self.assertEqual(audit['validated_rows'],0)
        from researcher.agent_review import exchange
        rejected=exchange(self.folder,(),{},as_of=self.now,cached=True,
            previous={'material_sha256':self.key})
        self.assertEqual(rejected['reason'],'AGENT_REPLY_ADVICE')
        self.assertNotEqual(rejected['status'],'VALIDATED_ADVISORY_ONLY')

    def test_incomplete_read_or_future_completion_fails_closed(self):
        self.tools[1]['state']['content'][0]['text']='1: {';self.write_attempt()
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.now)
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.at)
        self.tools[-1]['state']['input']['path']=_windows(self.workspace);self.write_attempt()
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.now)

    def test_missing_owner_submission_does_not_read_unrelated_threads_or_invoke(self):
        with sqlite3.connect(self.config['openbot_db']) as db:db.execute("DELETE FROM projection_thread_messages WHERE author='user'")
        result=wait_for_reply(self.folder,self.key,self.configfile,clock=lambda:self.now)
        self.assertEqual(result['status'],'AWAITING_OWNER_NATIVE_APP_SUBMISSION')
        self.assertFalse((self.folder/(self.key+'.reply.json')).exists())
