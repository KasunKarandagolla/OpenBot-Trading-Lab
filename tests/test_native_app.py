"""Synthetic native storage fixtures only; these never count as real LLM calls."""
import json,sqlite3,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import timedelta
from unittest.mock import patch
from researcher.settings import ROOT
from researcher.contracts import encode,digest,utc,ContractError
from researcher.agent_review import make_request,AGENT,MODEL,REPLY
from researcher.native_app import prepare,collect,wait_for_reply,_windows
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
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('CREATE TABLE session_message(session_id,type,time_created,seq,data)')
        self.write_attempt()

    def write_attempt(self,model='deepseek-v4.1-flash-free'):
        data={'model':{'providerID':'opencode','id':model},'content':self.tools,'finish':'stop','tokens':{'input':1,'output':1},'cost':0}
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('DELETE FROM session_message');db.execute('INSERT INTO session_message VALUES(?,?,?,?,?)',('TEST_EXTERNAL','assistant',int(utc(self.at).timestamp()*1000),1,json.dumps(data)))

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
        if __import__('os').name!='nt':
            executable=self.root/'python.exe';executable.touch()
            self.configfile.write_text(json.dumps({**self.config,'native_python':str(executable)}))
            from types import SimpleNamespace
            with patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"status":"NATIVE_RECEIPT_COLLECTED"}')) as process:
                delegated=wait_for_reply(self.folder,self.key,self.configfile)
            self.assertEqual(delegated['receipt_reader'],'EXISTING_WINDOWS_PYTHON_SQLITE_MODE_RO')
            self.assertNotIn('shell',process.call_args.kwargs)
            import subprocess
            with patch('subprocess.run',side_effect=subprocess.TimeoutExpired('SYNTHETIC_TEST',30)):
                with self.assertRaises(ContractError):wait_for_reply(self.folder,self.key,self.configfile)

    def test_unapproved_tool_or_replacement_model_cannot_produce_a_receipt(self):
        self.tools.append({'type':'tool','name':'shell','state':{'status':'completed','input':{},'content':[]}});self.write_attempt()
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.now)
        self.tools.pop();self.write_attempt(model='REPLACEMENT')
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.now)
        self.assertFalse((self.folder/(self.key+'.audit.json')).exists())

    def test_incomplete_read_or_future_completion_fails_closed(self):
        self.tools[-1]['state']['content'][0]['text']='1: {';self.write_attempt()
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.now)
        with self.assertRaises(ContractError):collect(self.request,self.config,self.target,as_of=self.at)

    def test_missing_owner_submission_does_not_read_unrelated_threads_or_invoke(self):
        with sqlite3.connect(self.config['openbot_db']) as db:db.execute("DELETE FROM projection_thread_messages WHERE author='user'")
        result=wait_for_reply(self.folder,self.key,self.configfile,clock=lambda:self.now)
        self.assertEqual(result['status'],'AWAITING_OWNER_NATIVE_APP_SUBMISSION')
        self.assertFalse((self.folder/(self.key+'.reply.json')).exists())
