"""Full ordinary orchestration with fake external APIs and provider event fixtures.

No scanner, family reducer, admission function, receipt validator, ledger or
exporter is mocked. Provider replies below are fixtures, never live LLM calls.
"""
import io,json,os,sqlite3,threading,time,unittest,zipfile
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from researcher import openbot_runner as runner
from researcher.contracts import digest,encode,utc
from researcher.diagnostic_export import verify_zip
from researcher.settings import ROOT
import test_native_runtime as native
from workflow_fixtures import ScenarioAPI,ScenarioScreen,FakeClient,AT


class SimulatedApp:
    """App storage + real-shaped 0.169 ordinal envelopes, scoped by exact task."""
    def __init__(self,fixture,clock):
        self.f=fixture;self.clock=clock;self.submitted={};self.pending=[];self.input_cards=[]
        self.reply_transform=None
    def envelope(self,at,kind,payload):return {'timestamp':at,'type':kind,'payload':payload}
    def write(self,name,rows):
        p=self.f.root/'sessions'/(name+'.jsonl')
        p.write_text(''.join(json.dumps({**r,'ordinal':j})+'\n' for j,r in enumerate(rows)),encoding='utf-8')
    def dispatch_once(self,args):
        title=args['title']
        if title in self.submitted:return False
        self.submitted[title]=args
        brief=args['brief'];request=json.loads(brief.split('<canonical-request>\n',1)[1].split('\n</canonical-request>',1)[0])
        self.input_cards.extend(request['cards'])
        n=len(self.submitted);name=f'REVIEW_{n}';turn=f'TURN_{n}';thread=f'THREAD_{n}';sid=f'SESSION_{n}';at=self.clock()
        identity=self.f.agent
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute('INSERT INTO projection_agent_threads VALUES(?,?,?,?,?)',(thread,'AGENT','agent',title,at))
            db.execute('INSERT INTO projection_provider_sessions VALUES(?,?,?,?,?,?)',(sid,thread,'codex',name,identity['model'],'active'))
            db.execute('INSERT INTO projection_turns VALUES(?,?,?,?,?,?)',(turn,thread,sid,'running',at,None))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',(thread,turn,'agent',None,'completed',at,0,encode({'text':brief})))
        with sqlite3.connect(self.f.config['provider_db']) as db:
            db.execute('INSERT INTO threads VALUES(?,?,?,?,?)',(name,str(self.f.root/'sessions'/(name+'.jsonl')),str(self.f.workspace),'openai',identity['model']))
        e=self.envelope
        self.f.parent.append(e(at,'event_msg',{'type':'item_completed','turn_id':'PARENT_TURN','thread_id':'PARENT',
            'item':{'type':'DynamicToolCall','tool':'tool_call','status':'completed','success':True,
                'arguments':{'name':'openbot.start_task','arguments':args}}}))
        self.write('PARENT',self.f.parent)
        rows=[e(at,'session_meta',{'id':name,'originator':'openbot','model_provider':'openai',
                'cli_version':'0.169.0','cwd':str(self.f.workspace)}),
            e(at,'event_msg',{'type':'task_started','turn_id':turn}),
            e(at,'turn_context',{'turn_id':turn,'model':identity['model']}),
            e(at,'event_msg',{'type':'item_completed','turn_id':turn,'thread_id':name,
                'item':{'type':'UserMessage','content':[{'type':'text','text':'OpenBot task envelope\n'+brief}]}})]
        self.write(name,rows)
        self.pending.append((time.monotonic()+1.1,request,name,turn,thread,rows))
        return True
    def complete_due(self):
        for item in list(self.pending):
            due,request,name,turn,thread,rows=item
            if time.monotonic()<due:continue
            self.pending.remove(item);at=self.clock()
            reply={'schema_version':'openbot.research-review.reply.v1','material_sha256':request['material_sha256'],
                'trade_authorization':False,'interpretations':[]}
            for c in request['cards']:
                evidence=next(iter(c['evidence']),c['events'][0]['id'] if c['events'] else '')
                reply['interpretations'].append({'card_id':c['card_id'],'interpretation':c['families'][0],
                    'supporting_evidence_ids':[evidence],'contradicting_ids':[],
                    'strongest_rival':'NULL','null_hypothesis':False,'missed_traps':['SHARED_PRICE_EVIDENCE'],
                    'falsifying_question':'FIRST_OBSTACLE','priority':'INVESTIGATE' if c['native_symbol']=='BEARUSDT' else 'WATCH','claims':[]})
            if self.reply_transform:reply=self.reply_transform(request,reply)
            raw=encode(reply);e=self.envelope
            rows.extend([e(at,'token_usage_record',{'turn_id':turn,'thread_id':name,'response_id':'FIXTURE_'+name,
                    'usage':{'input_tokens':100,'output_tokens':100}}),
                e(at,'event_msg',{'type':'item_completed','turn_id':turn,'thread_id':name,
                    'item':{'type':'AgentMessage','phase':'final_answer','content':[{'type':'Text','text':raw}]}}),
                e(at,'event_msg',{'type':'task_complete','turn_id':turn,'last_agent_message':raw})])
            self.write(name,rows)
            with sqlite3.connect(self.f.config['openbot_db']) as db:
                db.execute('UPDATE projection_turns SET status=?,completed_at=? WHERE turn_id=?',('completed',at,turn))
                db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',(thread,turn,'assistant',
                    'final_answer','completed',at,1,encode({'text':raw})))


class CompleteWorkflow(unittest.TestCase):
    def setUp(self):
        self.f=native.CodexRuntimeFixtures();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.began=time.monotonic();self.offset=0
        self.clock=lambda:(utc(AT)+timedelta(seconds=time.monotonic()-self.began+self.offset)).isoformat()
        self.base=self.f.root/'integration';self.base.mkdir();self.private=self.base/'native-audit-local.json'
        self.private.write_text(encode(self.f.config));self.request_id='a'*32
        e=lambda kind,payload:{'timestamp':AT,'type':kind,'payload':payload}
        self.f.parent=[e('session_meta',{'id':'PARENT','originator':'openbot','model_provider':'openai',
                'cli_version':'0.169.0','cwd':str(self.f.workspace)}),
            e('turn_context',{'turn_id':'PARENT_TURN','model':self.f.agent['model']}),
            e('event_msg',{'type':'item_completed','turn_id':'PARENT_TURN','thread_id':'PARENT',
                'item':{'type':'CommandExecution','status':'completed','exit_code':0,
                    'cwd':str(ROOT),'command':['python3','-m','researcher.openbot_runner','start','--request-id',self.request_id]}})]
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute('DELETE FROM projection_agent_threads');db.execute('DELETE FROM projection_thread_messages')
            db.execute("DELETE FROM projection_turns WHERE turn_id!='PARENT_TURN'")
            db.execute('UPDATE projection_turns SET started_at=?',(AT,))
        self.app=SimulatedApp(self.f,self.clock);self.app.write('PARENT',self.f.parent)
        self.api=ScenarioAPI(names=('BTCUSDT','ETHUSDT','AAAUSDT','BBBUSDT','CCCUSDT','DDDUSDT','BEARUSDT'))
        self.client=FakeClient();self.screen=ScenarioScreen(self.api,self.client)
        original_pulse=self.api.pulse
        def pulse(*args,**kwargs):self.api.at=self.clock();return original_pulse(*args,**kwargs)
        self.api.pulse=pulse
        for target,value in [('BASE',self.base),('PRIVATE',self.private),('now_utc',self.clock)]:
            p=patch.object(runner,target,value);p.start();self.addCleanup(p.stop)
        for name,value in [('researcher.binance.OfficialResearchAPI',self.api),
                ('researcher.discovery.BasisMCP',self.client),('researcher.screening.BasisScreenSource',self.screen)]:
            p=patch(name,return_value=value);p.start();self.addCleanup(p.stop)
        p=patch('subprocess.check_output',side_effect=lambda cmd,**kw:'7'*40+'\n' if 'rev-parse' in cmd else '')
        p.start();self.addCleanup(p.stop)

    def run_workflow(self,*,invalidate=False,age_points=False):
        go=threading.Event();worker=[];errors=[]
        def launch(argv,**kwargs):
            def work():
                go.wait()
                try:worker.append(runner.run_job(argv[-1]))
                except BaseException as error:errors.append(error)
            t=threading.Thread(target=work);t.start();self.addCleanup(lambda:t.join(30))
            self.thread=t;return SimpleNamespace(pid=os.getpid())
        with patch('subprocess.Popen',side_effect=launch) as spawned:
            job=runner.start(self.request_id)['job_id'];go.set()
            seen=[];deadline=time.monotonic()+90;wait_observed=False
            while time.monotonic()<deadline:
                status=runner.status(job,include_review=True);seen.append(status['state'])
                if status['state']=='REVIEW_READY':
                    args=status['start_task_arguments']
                    second=runner.status(job,include_review=True)
                    self.assertEqual(second['state'],'REVIEW_DISPATCH_RESERVED')
                    self.assertNotIn('start_task_arguments',second)
                    self.assertTrue(self.thread.is_alive());self.assertFalse((runner._job(job)/(job+'.zip')).exists())
                    self.assertTrue(self.app.dispatch_once(args));self.assertFalse(self.app.dispatch_once(args))
                if status['state']=='REVIEW_RUNNING':
                    self.assertTrue(self.thread.is_alive());wait_observed=True
                pending_before=len(self.app.pending)
                self.app.complete_due()
                if age_points and len(self.app.pending)<pending_before:self.offset+=61
                if invalidate and self.app.submitted:self.api.point_shift=__import__('decimal').Decimal(25)
                if status['state'] in runner.FINAL:break
                time.sleep(.05)
            else:self.fail('whole ordinary workflow exceeded offline deadline')
            self.thread.join(10);self.assertFalse(self.thread.is_alive());self.assertEqual(errors,[])
            self.assertEqual(spawned.call_count,1)
            self.assertEqual(runner.start('b'*32)['job_id'],job)
        self.assertTrue(wait_observed,status);self.assertIn('REVIEW_READY',seen);self.assertIn('REVIEW_RUNNING',seen)
        report=json.loads((runner._job(job)/'report.json').read_text())
        return job,status,report

    def test_owner_command_real_scanner_all_finalists_batched_receipts_reconciled_and_zipped(self):
        job,status,r=self.run_workflow()
        self.assertEqual(runner.run_job(job)['state'],'COMPLETED')
        self.assertEqual(len(self.app.submitted),r['llm_calls'])
        self.assertEqual(r['consultant']['status'],'VALIDATED_ADVISORY_ONLY',r['consultant'])
        self.assertGreaterEqual(len(r['conditional_research_candidates']),5,r['conditional_research_dispositions'])
        finalists=r['native_selection']['deterministic_control_card_ids']
        self.assertGreaterEqual(len({c['native_symbol'] for c in self.app.input_cards}),5)
        self.assertFalse(set(finalists)-set(r['consultant']['reviewed_card_ids']))
        self.assertFalse(r['consultant']['not_reviewed']);self.assertFalse(r['consultant']['omitted'])
        self.assertGreater(r['consultant']['batch_count'],1)
        self.assertEqual(r['llm_calls'],len(self.app.submitted))
        self.assertLessEqual(r['costs']['by_provider']['binance']['http_requests'],80)
        self.assertFalse(any(f['code']=='REQUEST_BUDGET_EXHAUSTED' for f in r['source_faults']))
        self.assertEqual(len(self.app.input_cards),len({c['card_id'] for c in self.app.input_cards}))
        candidates=r['conditional_research_candidates']
        self.assertGreaterEqual(len({c['primary_family'] for c in candidates}),2)
        self.assertGreaterEqual(len({c['reference']['timeframe'] for c in candidates}),2)
        self.assertIn('BEARUSDT',{c['instrument'] for c in candidates})
        self.assertTrue(r['native_control_comparison']['ranking_or_membership_changed'])
        self.assertFalse(r['native_control_comparison']['hard_gates_changed'])
        self.assertEqual(r['shortlist'],[])
        self.assertTrue(all(c['reasoning_status']=='NATIVE_REVIEWED' for c in candidates))
        self.assertTrue(r['point_reconciliation']['depth_snapshots'])
        self.assertEqual(len(r['measurement_coverage']),27)
        self.assertEqual(r['measurement_coverage']['VALUE3']['code_path'],'specialists.true_profile')
        phases=[s['state'] for s in runner._read(runner._job(job)/'state.json')['lifecycle']]
        for phase in ('OWNER_AUTHORIZED','COMMAND_ATTESTED','SCANNING','REVIEW_REQUEST_PREPARED',
                'REVIEW_READY','REVIEW_RUNNING','REVIEW_VERIFIED','RECONCILED','EXPORTED'):
            self.assertIn(phase,phases)
        raw=Path(status['artifact']['attachment_path']).read_bytes();self.assertTrue(verify_zip(raw))
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(json.loads(z.read('manifest.json'))['job_id'],job)
            saved=json.loads(z.read('report.json'));self.assertEqual(saved['job_id'],job)
            self.assertEqual(saved['consultant']['reviewed_card_ids'],r['consultant']['reviewed_card_ids'])
            self.assertFalse(saved['trade_authorization'])
        self.assertEqual(saved['output_payload_sha256'],digest(encode({k:v for k,v in saved.items()
            if k not in {'persistence','output_payload_sha256'}}).encode()))
        # Delivery is a separate real-shaped attachment/final receipt. A worker
        # completion cannot assert it; the persisted parent evidence must agree.
        e=self.app.envelope;at=self.clock();text='Fixture delivery '+job+' '+status['artifact']['sha256']
        self.f.parent.extend([e(at,'event_msg',{'type':'item_completed','turn_id':'PARENT_TURN','thread_id':'PARENT',
            'item':{'type':'DynamicToolCall','tool':'tool_call','status':'completed','success':True,
                'arguments':{'name':'openbot.attach_files_to_response','arguments':{'paths':[status['artifact']['attachment_path']]}}}}),
            e(at,'event_msg',{'type':'item_completed','turn_id':'PARENT_TURN','thread_id':'PARENT',
                'item':{'type':'AgentMessage','phase':'final_answer','content':[{'type':'Text','text':text}]}})])
        self.app.write('PARENT',self.f.parent)
        with sqlite3.connect(self.f.config['openbot_db']) as db:
            db.execute("UPDATE projection_turns SET status='completed',completed_at=? WHERE turn_id='PARENT_TURN'",(at,))
            db.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?,?,?,?)',
                ('MAIN','PARENT_TURN','assistant','final_answer','completed',at,999,encode({'text':text})))
        delivered=runner.status(job)
        self.assertEqual(delivered['state'],'FINAL_DELIVERED')
        self.assertEqual(delivered['delivery_receipt']['zip_sha256'],status['artifact']['sha256'])
        # The original ZIP remains immutable; subsequent delivery proof is separate.
        self.assertEqual(Path(status['artifact']['attachment_path']).read_bytes(),raw)
        # Tests export a concise proof only when specifically requested by a developer run.
        if os.environ.get('OPENBOT_WRITE_E2E_PROOF')=='1':
            proof={'fixture_only':True,'live_model_calls':0,'job_id':job,'phases':[x['state'] for x in delivered['lifecycle']],
                'lifecycle':runner._read(runner._job(job)/'state.json')['lifecycle'],
                'finalists':len(finalists),'reviewed':r['consultant']['accepted'],
                'batches':r['consultant']['batch_count'],'fixture_provider_attempts':r['llm_calls'],
                'ranking_changed':r['native_control_comparison']['ranking_or_membership_changed'],
                'costs':r['costs'],'point_reconciliation':r['point_reconciliation'],
                'zip_sha256':digest(raw),'zip_integrity':True,'trade_authorization':False}
            (ROOT/'work/final-e2e-proof.json').write_text(encode(proof)+'\n')

    def test_aged_point_quotes_depth_refresh_and_consumed_obstacle_invalidate_candidate(self):
        job,status,r=self.run_workflow(invalidate=True,age_points=True)
        self.assertEqual(r['consultant']['status'],'VALIDATED_ADVISORY_ONLY',r['consultant'])
        self.assertNotIn('AAAUSDT',{c['instrument'] for c in r['conditional_research_candidates']})
        self.assertTrue(any(c['native_symbol']=='AAAUSDT' and c['disposition'] in {
            'FIRST_OPPOSING_OBSTACLE_CONSUMED','DECISION_ZONE_DISTANT_OR_UNKNOWN','INVALID_LATE_OR_SOURCE_UNASSESSABLE'}
            for c in r['conditional_research_dispositions']))
        self.assertGreaterEqual(self.offset,61)
        self.assertTrue(r['point_reconciliation']['depth_snapshots'])
        for c in r['conditional_research_candidates']:
            self.assertLessEqual((utc(r['completed_at_utc'])-utc(c['current_price']['source_time'])).total_seconds(),30)
        self.assertFalse(r['trade_authorization']);self.assertEqual(r['shortlist'],[])
