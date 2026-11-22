"""Controlled storage fixtures, zero live scans/model invocations."""
import copy
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from datetime import timedelta
import unittest
from unittest.mock import patch
from researcher.settings import ROOT
from researcher.contracts import ContractError,digest,encode,utc
from researcher.agent_review import make_request,exchange,REPLY,AGENT
from researcher.native_identity import active_identity,load_private,configured_identity
from researcher.native_codex import review_brief
from researcher.native_runtime import collect
from test_session4 import case


class CodexRuntimeFixtures(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        self.tmp=TemporaryDirectory(dir=ROOT/'work');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.workspace=self.root/'agent';self.workspace.mkdir()
        skill=self.workspace/'.agents/skills/market-research-review/SKILL.md';skill.parent.mkdir(parents=True)
        skill.write_bytes((ROOT/'.agents/skills/market-research-review/SKILL.md').read_bytes())
        self.config={'openbot_db':str(self.root/'app.sqlite'),'provider_db':str(self.root/'state.sqlite'),'agent_workspace':str(self.workspace)}
        self.cf=self.root/'private.json';self.cf.write_text(encode(self.config))
        self.card,self.facts,_,bars=case(family='F4');self.at=bars[-1].end
        self.time=lambda n:(utc(self.at)+timedelta(seconds=n)).isoformat()
        self.agent={'name':AGENT,'model':'gpt-6-luna','provider':'codex','workspacePath':str(self.workspace)}
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.executescript('''CREATE TABLE projection_agents(agent_id,thread_id,model,agent_json);
              CREATE TABLE projection_threads(thread_id,agent_id,active_turn_id);
              CREATE TABLE projection_turns(turn_id,thread_id,provider_session_id,status,started_at,completed_at);
              CREATE TABLE projection_provider_sessions(id,thread_id,provider,external_session_id,model,state);
              CREATE TABLE projection_agent_threads(thread_id,agent_id,origin,title,created_at);
              CREATE TABLE projection_thread_messages(thread_id,turn_id,author,item_type,status,created_at,ordinal,message_json);
              CREATE TABLE projection_deliveries(turn_id,recipient_agent_id,message_id);
              CREATE TABLE projection_mailbox_messages(message_id,text,sender_kind);''')
            db.execute('INSERT INTO projection_agents VALUES(?,?,?,?)',('AGENT','MAIN','gpt-6-luna',encode(self.agent)))
            db.execute('INSERT INTO projection_threads VALUES(?,?,?)',('MAIN','AGENT','PARENT_TURN'))
            db.execute('INSERT INTO projection_provider_sessions VALUES(?,?,?,?,?,?)',('PARENT_SESSION','MAIN','codex','PARENT','gpt-6-luna','active'))
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',('PARENT_TURN','MAIN','PARENT_SESSION','running',self.time(-10),None))
            db.execute('INSERT INTO projection_deliveries VALUES(?,?,?)',('PARENT_TURN','AGENT','OWNER'))
            db.execute('INSERT INTO projection_mailbox_messages VALUES(?,?,?)',('OWNER','Run the complete market research now.','user'))
        sessions=self.root/'sessions';sessions.mkdir()
        with sqlite3.connect(self.config['provider_db']) as db:
            db.execute('CREATE TABLE threads(id,rollout_path,cwd,model_provider,model)')
            for name in ('PARENT','CHILD'):db.execute('INSERT INTO threads VALUES(?,?,?,?,?)',
                (name,str(sessions/(name+'.jsonl')),str(self.workspace),'openai','gpt-6-luna'))
        self.identity=active_identity(self.config)
        self.request=make_request([self.card],self.facts,as_of=self.at,skill_sha256=digest(skill.read_bytes()),native_identity=self.identity)
        self.key=self.request['material_sha256'];self.brief=review_brief(self.request)
        self.reply={'schema_version':REPLY,'material_sha256':self.key,'trade_authorization':False,'interpretations':[{
            'card_id':self.card.id,'interpretation':'F4','supporting_evidence_ids':['seq'],'contradicting_ids':[],
            'strongest_rival':'NULL','null_hypothesis':False,'missed_traps':['SHARED_PRICE_EVIDENCE'],
            'falsifying_question':'FIRST_OBSTACLE','priority':'WATCH','claims':[]}]}
        self.raw=encode(self.reply)
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute('INSERT INTO projection_agent_threads VALUES(?,?,?,?,?)',('CHILD_THREAD','AGENT','agent','OPENBOT-RESEARCH-'+self.key,self.time(1)))
            db.execute('INSERT INTO projection_provider_sessions VALUES(?,?,?,?,?,?)',('CHILD_SESSION','CHILD_THREAD','codex','CHILD','gpt-6-luna','active'))
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',('CHILD_TURN','CHILD_THREAD','CHILD_SESSION','completed',self.time(2),self.time(4)))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',('CHILD_THREAD','CHILD_TURN','agent',None,'completed',self.time(1),0,encode({'text':self.brief})))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',('CHILD_THREAD','CHILD_TURN','assistant','final_answer','completed',self.time(4),1,encode({'text':self.raw})))
        self.parent=[self.record(-10,'session_meta',{'id':'PARENT','originator':'openbot','model_provider':'openai','cli_version':'0.169.0','cwd':str(self.workspace)}),
            self.record(-10,'turn_context',{'turn_id':'PARENT_TURN','model':'gpt-6-luna'}),
            self.record(1,'event_msg',{'type':'item_completed','turn_id':'PARENT_TURN','thread_id':'PARENT','item':{
                'type':'DynamicToolCall','tool':'tool_call','status':'completed','success':True,'arguments':{
                    'name':'openbot.start_task','arguments':{'title':'OPENBOT-RESEARCH-'+self.key,'brief':self.brief}}}})]
        self.child=[self.record(0,'session_meta',{'id':'CHILD','originator':'openbot','model_provider':'openai','cli_version':'0.169.0','cwd':str(self.workspace)}),
            self.record(2,'event_msg',{'type':'task_started','turn_id':'CHILD_TURN'}),
            self.record(2,'turn_context',{'turn_id':'CHILD_TURN','model':'gpt-6-luna'}),
            self.item(2,{'type':'UserMessage','content':[{'type':'text','text':'OpenBot task envelope\n'+self.brief}]}),
            self.record(3,'token_usage_record',{'turn_id':'CHILD_TURN','thread_id':'CHILD','response_id':'RESPONSE','usage':{'input_tokens':100,'output_tokens':100}}),
            self.item(4,{'type':'AgentMessage','phase':'final_answer','content':[{'type':'Text','text':self.raw}]}),
            self.record(4,'event_msg',{'type':'task_complete','turn_id':'CHILD_TURN','last_agent_message':self.raw})]
        self.write()

    def record(self,n,kind,payload):return {'timestamp':self.time(n),'type':kind,'payload':payload}
    def item(self,n,item):return self.record(n,'event_msg',{'type':'item_completed','turn_id':'CHILD_TURN','thread_id':'CHILD','item':item})
    def write(self):
        for name,rows in [('PARENT',self.parent),('CHILD',self.child)]:
            (self.root/'sessions'/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    def get(self):return collect(self.request,self.config,as_of=self.time(5))

    def test_current_codex_model_exact_input_and_reply_are_independently_attested(self):
        before={k:digest(Path(self.config[k]).read_bytes()) for k in ('openbot_db','provider_db')}
        raw,audit=self.get()
        self.assertEqual(raw,self.raw);self.assertEqual(audit['model'],'gpt-6-luna');self.assertEqual(audit['validated_rows'],1)
        self.assertEqual(audit['tool_operations'],[]);self.assertEqual(audit['model_requests'],1)
        self.assertNotIn('PARENT_TURN',encode(audit));self.assertNotIn('CHILD_TURN',encode(audit))
        self.assertEqual(before,{k:digest(Path(self.config[k]).read_bytes()) for k in before})

    def test_second_schema_compatible_codex_model_is_not_name_gated(self):
        other='fixture-second-schema-model'
        with sqlite3.connect(self.config['openbot_db']) as db:
            self.agent['model']=other
            db.execute('UPDATE projection_agents SET model=?,agent_json=?',(other,encode(self.agent)))
            db.execute('UPDATE projection_provider_sessions SET model=?',(other,))
        # Construct a new request after a trusted model change. Existing cards and
        # market snapshot stay identical; only the review fingerprint changes.
        with sqlite3.connect(self.config['provider_db']) as db:db.execute('UPDATE threads SET model=?',(other,))
        old=self.request;identity=active_identity(self.config)
        new=make_request([self.card],self.facts,as_of=self.at,skill_sha256=old['skill_sha256'],native_identity=identity)
        self.assertNotEqual(new['material_sha256'],old['material_sha256'])
        self.assertEqual(new['cards'],old['cards'])
        self.assertEqual(new['model'],other)
        from researcher.native_codex import attest
        self.child[2]['payload']['model']=other;self.write()
        proof=attest(self.config,'CHILD','CHILD_TURN',model=other,workspace=self.workspace,
            start=self.time(2),end=self.time(4),expected_input=self.brief,expected_reply=self.raw,backend='openai')
        self.assertEqual(proof['model_requests'],1)

    def test_model_switch_midflight_fails_without_changing_market_request(self):
        before=encode(self.request)
        with sqlite3.connect(self.config['openbot_db']) as db:
            self.agent['model']='different'
            db.execute('UPDATE projection_agents SET model=?,agent_json=?',('different',encode(self.agent)))
        with self.assertRaisesRegex(ContractError,'NATIVE_MODEL_SWITCHED'):
            collect(self.request,self.config,as_of=self.time(5),require_configured_model=True)
        self.assertEqual(before,encode(self.request))

    def test_child_wrong_model_agent_session_are_rejected(self):
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute("UPDATE projection_provider_sessions SET model='wrong' WHERE id='CHILD_SESSION'")
        with self.assertRaisesRegex(ContractError,'MODEL_SWITCHED'):
            collect(self.request,self.config,as_of=self.time(5),require_configured_model=True)
        self.assertEqual(self.get()[1]['model'],self.identity['model'])
        mutations=[
            ("UPDATE projection_agent_threads SET agent_id='wrong'",None),
            ("UPDATE projection_provider_sessions SET external_session_id='unrelated' WHERE id='CHILD_SESSION'",'SESSION_MISMATCH')]
        backup=Path(self.config['openbot_db']).read_bytes()
        for sql,reason in mutations:
            with self.subTest(sql=sql):
                with sqlite3.connect(self.config['openbot_db']) as db:db.execute(sql)
                try:
                    if reason:
                        with self.assertRaisesRegex(ContractError,reason):self.get()
                    else:self.assertIsNone(self.get())
                finally:Path(self.config['openbot_db']).write_bytes(backup)
        self.child[2]['payload']['turn_id']='another-turn';self.write()
        with self.assertRaisesRegex(ContractError,'SESSION_MISMATCH'):self.get()

    def test_incomplete_input_and_wrong_final_provenance_fail_closed(self):
        original=copy.deepcopy(self.child)
        self.child[3]['payload']['item']['content'][0]['text']=self.brief[:-100];self.write()
        with self.assertRaisesRegex(ContractError,'READ_INCOMPLETE'):self.get()
        self.child=copy.deepcopy(original);self.child[5]['payload']['item']['content'][0]['text']='forged';self.write()
        with self.assertRaisesRegex(ContractError,'REPLY_PROVENANCE'):self.get()
        self.child=original;self.child.pop();self.write()
        with self.assertRaisesRegex(ContractError,'REVIEW_INCOMPLETE'):self.get()

    def test_any_review_tool_including_shell_or_discovery_is_rejected(self):
        original=copy.deepcopy(self.child)
        for item in ({'type':'CommandExecution','command':'cat evidence'},
                     {'type':'DynamicToolCall','tool':'tool_search'}, {'type':'FileChange'}):
            self.child=copy.deepcopy(original);self.child.insert(5,self.item(3,item));self.write()
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED_TOOL'):self.get()
        self.child=copy.deepcopy(original);self.child.insert(5,self.record(3,'response_item',{'type':'custom_tool_call','name':'exec','input':'read'}));self.write()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED_TOOL'):self.get()

    def test_missing_or_forged_parent_handoff_is_not_a_native_run(self):
        self.parent.pop();self.write()
        with self.assertRaisesRegex(ContractError,'HANDOFF_UNATTESTED'):self.get()

    def test_stale_future_and_unsupported_provider_schema_are_precise(self):
        with self.assertRaisesRegex(ContractError,'REQUEST_STALE'):collect(self.request,self.config,as_of=self.time(601))
        with self.assertRaisesRegex(ContractError,'EVIDENCE_FUTURE'):collect(self.request,self.config,as_of=self.time(3))
        self.child[0]['payload']['cli_version']='unknown-future';self.write()
        with self.assertRaisesRegex(ContractError,'SCHEMA_UNSUPPORTED'):self.get()

    def test_invalid_citation_retains_real_invocation_but_never_imports_advice(self):
        bad=copy.deepcopy(self.reply);bad['interpretations'][0]['supporting_evidence_ids']=['invented'];raw=encode(bad)
        with sqlite3.connect(self.config['openbot_db']) as db:
            db.execute("UPDATE projection_thread_messages SET message_json=? WHERE author='assistant'",(encode({'text':raw}),))
        self.child[5]['payload']['item']['content'][0]['text']=raw
        self.child[6]['payload']['last_agent_message']=raw;self.write()
        _,audit=self.get();self.assertEqual(audit['reply_rejection_reason'],'AGENT_REPLY_CITATION')
        self.assertTrue(audit['native_invocation_verified']);self.assertEqual(audit['validated_rows'],0)

    def test_file_only_audit_cannot_forge_dynamic_import(self):
        folder=self.root/'exchange';folder.mkdir()
        (folder/(self.key+'.request.json')).write_text(encode(self.request))
        (folder/(self.key+'.reply.json')).write_text(self.raw)
        (folder/(self.key+'.audit.json')).write_text(encode({'native_invocation_verified':True}))
        self.parent.pop();self.write()
        result=exchange(folder,(),{},as_of=self.time(5),previous={'material_sha256':self.key},cached=True,audit_config=self.cf,require_identity=True)
        self.assertEqual(result['reason'],'NATIVE_HANDOFF_UNATTESTED')
        self.assertNotEqual(result['status'],'VALIDATED_ADVISORY_ONLY')

    def test_missing_config_malformed_config_and_unsupported_provider_are_precise(self):
        with self.assertRaisesRegex(ContractError,'CONFIG_MISSING'):load_private(self.root/'missing.json')
        self.cf.write_text('{broken')
        with self.assertRaisesRegex(ContractError,'CONFIG_INVALID'):load_private(self.cf)
        self.agent['provider']='not-an-attested-adapter'
        with sqlite3.connect(self.config['openbot_db']) as db:db.execute('UPDATE projection_agents SET agent_json=?',(encode(self.agent),))
        with self.assertRaisesRegex(ContractError,'PROVIDER_UNSUPPORTED'):configured_identity(self.config)

    def test_absent_app_reply_is_not_invoked_not_a_zero_opportunity_claim(self):
        with sqlite3.connect(self.config['openbot_db']) as db:db.execute("DELETE FROM projection_thread_messages WHERE author='assistant'")
        self.assertIsNone(self.get())

    def test_complete_dynamic_exchange_reaudits_storage_and_checks_skill(self):
        result=exchange(self.root/'exchange',[self.card],self.facts,as_of=self.at,audit_config=self.cf,require_identity=True,max_cards=1)
        self.assertEqual(result['reason'],'AGENT_EVIDENCE_FUTURE') # completed fixture is ahead of this clock
        # Actual request creation time remains unchanged in cached exchange.
        result=exchange(self.root/'exchange',(),{},as_of=self.time(5),previous={'material_sha256':self.key},cached=True,audit_config=self.cf,require_identity=True)
        self.assertEqual(result['status'],'VALIDATED_ADVISORY_ONLY')
        self.assertEqual(result['accepted'],1)
