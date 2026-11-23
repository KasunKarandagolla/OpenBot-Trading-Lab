"""Full ordinary orchestration with fake external APIs and provider event fixtures.

No scanner, family reducer, admission function, receipt validator, ledger or
exporter is mocked. Provider replies below are fixtures, never live LLM calls.
"""
import io,json,os,sqlite3,threading,time,unittest,zipfile
import shlex
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from researcher import openbot_runner as runner
from researcher.contracts import digest,encode,utc
from researcher.diagnostic_export import verify_zip
from researcher.native_handoff import COMPACT_PAGES, CONFIRMED_PAGES, PARENT_OUTPUT_BYTES
from researcher.settings import ROOT
import test_native_runtime as native
from workflow_fixtures import ScenarioAPI,ScenarioScreen,FakeClient,AT


class SimulatedApp:
    """App storage + real-shaped 0.169 ordinal envelopes, scoped by exact task."""
    def __init__(self,fixture,clock):
        self.f=fixture;self.clock=clock;self.submitted={};self.pending=[];self.input_cards=[]
        self.reply_transform=None;self.provider_attempts=0
        self.parent_session='PARENT';self.parent_turn='PARENT_TURN'
    def envelope(self,at,kind,payload):return {'timestamp':at,'type':kind,'payload':payload}
    def write(self,name,rows):
        p=self.f.root/'sessions'/(name+'.jsonl')
        p.write_text(''.join(json.dumps({**r,'ordinal':j})+'\n' for j,r in enumerate(rows)),encoding='utf-8')
    def dispatch_once(self,args,job=None,receipt=None):
        title=args['title']
        if title in self.submitted:return False
        self.submitted[title]=args
        brief=args['brief'];full=brief;pages=[];commands=[]
        if job is not None and receipt['evidence_pages']:
            fingerprint=receipt['packet_sha256']
            self.assert_exact_arguments(args,receipt)
            first_command=next(line for line in brief.splitlines() if line.startswith('wsl.exe '))
            for number in range(1,receipt['evidence_pages']+1):
                if first_command.endswith('N'):cmd=first_command.removesuffix('N')+str(number)
                else:cmd=first_command if number==1 else json.loads(pages[-1])['next_command']
                argv=shlex.split(cmd.split(' -- python3 -m researcher.openbot_runner ',1)[1])
                cli=dict(zip(argv[1::2],argv[2::2],strict=True))
                pages.append(runner.review_page(cli['--job-id'],cli['--material'],cli.get('--packet-sha256'),int(cli['--page'])))
                commands.append(cmd)
            full=''.join(json.loads(page)['text'] for page in pages)
            if digest(full.encode())!=fingerprint:raise AssertionError('packet hash')
        request=json.loads(full.split('<canonical-request>\n',1)[1].split('\n</canonical-request>',1)[0])
        if request.get('input_transport'):
            self.assert_exact_arguments(args,receipt)
            if digest(full.encode())!=receipt['packet_sha256']:raise AssertionError('AI packet hash')
            if request['stage']=='SHORTLIST':self.input_cards.extend(request['evidence'])
        else:self.input_cards.extend(request['cards'])
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
        wrapper={'name':'openbot.start_task','arguments':args};call_id='START_TASK_'+name
        self.f.parent.append(e(at,'response_item',{'type':'function_call','name':'tool_call','namespace':'openbot',
            'call_id':call_id,'arguments':json.dumps(wrapper)}))
        self.f.parent.append(e(at,'event_msg',{'type':'item_completed','turn_id':self.parent_turn,'thread_id':self.parent_session,
            'item':{'type':'DynamicToolCall','namespace':'openbot','tool':'tool_call','status':'completed','success':True,
                'id':call_id,'arguments':wrapper,'content_items':[{'type':'inputText',
                    'text':json.dumps({'taskId':thread,'title':title})}]}}))
        self.write(self.parent_session,self.f.parent)
        rows=[e(at,'session_meta',{'id':name,'originator':'openbot','model_provider':'openai',
                'cli_version':'0.169.0','cwd':str(self.f.workspace)}),
            e(at,'event_msg',{'type':'task_started','turn_id':turn}),
            e(at,'turn_context',{'turn_id':turn,'model':identity['model']}),
            e(at,'event_msg',{'type':'item_completed','turn_id':turn,'thread_id':name,
                'item':{'type':'UserMessage','content':[{'type':'text','text':'OpenBot task envelope\n'+brief}]}})]
        if pages:
            for number,(cmd,page) in enumerate(zip(commands,pages,strict=True),1):
                if request.get('input_transport') in {CONFIRMED_PAGES,COMPACT_PAGES}:
                    self.provider_attempts+=1
                    rows.append(e(at,'token_usage_record',{'turn_id':turn,'thread_id':name,
                        'response_id':f'FIXTURE_{name}_PAGE_{number}','usage':{'input_tokens':100,'output_tokens':100}}))
                call='PAGE_'+str(number)
                command_args={'cmd':cmd,'login':False,'max_output_tokens':16000}
                if 'yield_time_ms:30000' in brief:command_args['yield_time_ms']=30000
                rows.extend([e(at,'response_item',{'type':'function_call','name':'exec_command','call_id':call,
                        'arguments':json.dumps(command_args)}),
                    e(at,'event_msg',{'type':'item_completed','turn_id':turn,'thread_id':name,
                        'item':{'type':'CommandExecution','id':call,'status':'completed','exit_code':0,
                            'command':['powershell.exe','-NoProfile','-Command',cmd],'aggregated_output':page}}),
                    e(at,'response_item',{'type':'function_call_output','call_id':call,
                        'output':'Wall time: 0.01 seconds\nProcess exited with code 0\nOutput:\n'+page})])
        self.write(name,rows)
        self.pending.append((time.monotonic()+1.1,request,name,turn,thread,rows))
        return True

    @staticmethod
    def assert_exact_arguments(args,receipt):
        if digest(encode(args).encode())!=receipt['arguments_sha256']:
            raise AssertionError('argument hash')
    def complete_due(self):
        for item in list(self.pending):
            due,request,name,turn,thread,rows=item
            if time.monotonic()<due:continue
            self.pending.remove(item);at=self.clock()
            if request.get('input_transport'):
                reply={'schema_version':'openbot.ai-research.reply.v1','material_sha256':request['material_sha256'],
                    'stage':request['stage'],'trade_authorization':False,'rows':[]}
                if request['stage']=='DISCOVERY':
                    evidence=sorted(request['evidence'],key=lambda c:c['native_symbol']!='BEARUSDT')
                    control=next((c for c in evidence if c['native_symbol'] not in {'BTCUSDT','ETHUSDT'}),None)
                    if control:
                        reply['rows']=[{'row_id':control['id'],'family':'F4','method':'M05','direction':'BEARISH',
                            'stage':'EARLY','support':[next(iter(control['citations']))],'contradiction':[],
                            'rival':'F2','question':'VERIFY_METHOD_SEQUENCE','expiry':'NEXT_CLOSED_RESPONSE'}]
                else:
                    selected=set()
                    for card in sorted(request['evidence'],key=lambda c:c['native_symbol']!='BEARUSDT'):
                        symbol=card['native_symbol']
                        admit=card['eligible'] and card['formation_citations'] and len(selected)<4 and symbol not in selected
                        support=card['formation_citations'][0] if admit else next(iter(card['citations']))
                        reply['rows'].append({'id':card['id'],'interpretation':card['primary_family'] if admit else 'NULL',
                            'rival':'NULL','stage':'READY_FOR_DEEP' if admit else 'UNKNOWN',
                            'decision':'HANDOFF' if admit else 'DECLINE','support':[support],'contradiction':[],
                            'next_question':'FIRST_OBSTACLE','deciding_factor':'ORDERED_CONFIRMATION' if admit else 'NO_SUPPORTED_FORMATION'})
                        if admit:selected.add(symbol)
                    reply['assessment']={'finding':'RESEARCH_HANDOFFS' if selected else 'NO_SUPPORTED_OPPORTUNITY',
                        'citations':[next(iter(request['assessment_evidence']))]}
            else:
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
            self.provider_attempts+=1
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
            # Bound the offline harness separately from the runner's dispatch
            # and freshness limits. Fake scanning alone can take 90s on WSL.
            seen=[];deadline=time.monotonic()+180;wait_observed=False
            while time.monotonic()<deadline:
                status=runner.status(job);seen.append(status['state'])
                if status['state']=='REVIEW_READY':
                    if status.get('review_transport')==COMPACT_PAGES:
                        wire=(encode(status,compact=True)+'\n').encode()
                        self.assertLessEqual(len(wire),PARENT_OUTPUT_BYTES)
                        status=json.loads(wire[:8192])
                        self.assertTrue(status['submission_permitted'])
                        self.assertEqual(status['end_frame'],'END_OPENBOT_COMPACT_DISPATCH_V1')
                    elif status.get('review_transport')==CONFIRMED_PAGES:
                        wire=(encode(status,compact=True)+'\n').encode()
                        self.assertLessEqual(len(wire),PARENT_OUTPUT_BYTES)
                        status=json.loads(wire[:8192])
                        self.assertEqual(runner.status(job,include_review=True),status)
                        command=shlex.split(status['reserve_command_prefix'].split(' reserve-review ',1)[1])
                        reservation=runner.reserve_review(job,status['material_sha256'],
                            command[command.index('--confirm')+1],status['z_end_frame'])
                        self.assertTrue(reservation['submission_permitted'])
                    else:
                        # Historical paged material still requires its
                        # original explicit one-shot dispatch request.
                        status=runner.status(job,include_review=True)
                    args=status['start_task_arguments']
                    second=runner.status(job,include_review=True)
                    self.assertEqual(second['state'],'REVIEW_DISPATCH_RESERVED')
                    self.assertNotIn('start_task_arguments',second)
                    self.assertTrue(self.thread.is_alive());self.assertFalse((runner._job(job)/(job+'.zip')).exists())
                    self.assertTrue(self.app.dispatch_once(args,job,second['dispatch_receipt']))
                    self.assertFalse(self.app.dispatch_once(args,job,second['dispatch_receipt']))
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

    def test_owner_command_real_scanner_both_passes_and_verified_zip(self):
        job,status,r=self.run_workflow()
        self.assertEqual(runner.run_job(job)['state'],'COMPLETED',r.get('ai_research'))
        ai=r['ai_research']
        finalists=ai['stages']['SHORTLIST']['supplied_ids']
        self.assertEqual(ai['state'],'AI_RESEARCH_COMPLETE')
        self.assertEqual(len(self.app.submitted),2)
        self.assertEqual(r['llm_calls'],self.app.provider_attempts)
        self.assertGreater(r['llm_calls'],2)
        self.assertEqual(ai['stages']['DISCOVERY']['status'],'AI_DISCOVERY_VERIFIED')
        self.assertEqual(ai['stages']['SHORTLIST']['status'],'AI_SHORTLIST_VERIFIED')
        for stage in ai['stages'].values():
            self.assertIn(stage['receipt']['verified_evidence_pages'],range(1,6))
            self.assertEqual(stage['receipt']['model_requests'],stage['receipt']['verified_evidence_pages']+1)
            self.assertEqual(stage['receipt']['parent_delivery'],'EXACT_TASK_ARGUMENTS_IN_PROVIDER_RECORD')
            self.assertTrue(stage['receipt']['native_invocation_verified'])
        self.assertEqual(ai['investigations'][0]['native_symbol'],'BEARUSDT')
        self.assertEqual(ai['investigations'][0]['status'],'VERIFIED_SOURCE_OBSERVATION')
        self.assertTrue(any(a['lane']=='VERIFIED_AI_OPPORTUNITY' for a in r['targeted_allocation']))
        self.assertLessEqual(r['costs']['by_provider']['binance']['http_requests'],80)
        self.assertFalse(any(f['code']=='REQUEST_BUDGET_EXHAUSTED' for f in r['source_faults']))
        self.assertEqual(len(finalists),len(set(finalists)))
        candidates=r['conditional_research_candidates']
        self.assertTrue(candidates,ai['reconciliation'])
        self.assertIn('BEARUSDT',{c['instrument'] for c in candidates})
        self.assertEqual(r['shortlist'],[])
        self.assertTrue(all(c['reasoning_status']=='VERIFIED_AI_SHORTLIST' for c in candidates))
        self.assertTrue(r['point_reconciliation']['depth_snapshots'])
        self.assertEqual(len(r['measurement_coverage']),27)
        self.assertEqual(r['measurement_coverage']['VALUE3']['code_path'],'specialists.true_profile')
        phases=[s['state'] for s in runner._read(runner._job(job)/'state.json')['lifecycle']]
        for phase in ('OWNER_AUTHORIZED','COMMAND_ATTESTED','SCANNING',
                'REVIEW_READY','REVIEW_RUNNING','REVIEW_VERIFIED','RECONCILED','EXPORTED'):
            self.assertIn(phase,phases)
        raw=Path(status['artifact']['attachment_path']).read_bytes();self.assertTrue(verify_zip(raw))
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(json.loads(z.read('manifest.json'))['job_id'],job)
            saved=json.loads(z.read('report.json'));self.assertEqual(saved['job_id'],job)
            self.assertEqual(saved['ai_research'],ai)
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
                'finalists':len(finalists),'reviewed':ai['stages']['SHORTLIST']['accepted'],
                'fixture_provider_attempts':r['llm_calls'],
                'ai_state':ai['state'],'stages':{k:v['status'] for k,v in ai['stages'].items()},
                'costs':r['costs'],'point_reconciliation':r['point_reconciliation'],
                'zip_sha256':digest(raw),'zip_integrity':True,'trade_authorization':False}
            (ROOT/'work/final-e2e-proof.json').write_text(encode(proof)+'\n')

    def test_aged_point_quotes_depth_refresh_and_consumed_obstacle_invalidate_candidate(self):
        job,status,r=self.run_workflow(invalidate=True,age_points=True)
        self.assertEqual(r['ai_research']['state'],'AI_RESEARCH_COMPLETE',r['ai_research'])
        self.assertNotIn('AAAUSDT',{c['instrument'] for c in r['conditional_research_candidates']})
        self.assertTrue(any(c['native_symbol']=='AAAUSDT' and c['disposition'] in {
            'FIRST_OPPOSING_OBSTACLE_CONSUMED','DECISION_ZONE_DISTANT_OR_UNKNOWN','INVALID_LATE_OR_SOURCE_UNASSESSABLE'}
            for c in r['conditional_research_dispositions']))
        self.assertGreaterEqual(self.offset,61)
        self.assertTrue(r['point_reconciliation']['depth_snapshots'])
        for c in r['conditional_research_candidates']:
            self.assertLessEqual((utc(r['completed_at_utc'])-utc(c['current_price']['source_time'])).total_seconds(),30)
        self.assertFalse(r['trade_authorization']);self.assertEqual(r['shortlist'],[])
