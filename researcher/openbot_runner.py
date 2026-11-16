"""Fixed-purpose asynchronous runner for the existing OpenBot Researcher.

Start is gated by a real current owner delivery AND a provider-recorded command
in that agent's current main turn. This module never submits a model request.
No MCP server, Local Scripts, scheduler, arbitrary shell endpoint or API key.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sqlite3
import sys
import time
import uuid
from .contracts import ContractError, digest, encode, now_utc, utc
from .settings import ROOT
from .native_identity import active_identity, assert_current, load_private, read_db, ref, under_work

BASE=ROOT/'work/openbot-integration'
PRIVATE=BASE/'native-audit-local.json'
OWNER_COMMAND='run the complete market research now'
FINAL={'COMPLETED','PARTIAL','FAILED','INTERRUPTED','FINAL_DELIVERED'}


def _job(key):
    if not isinstance(key,str) or not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{32}',key):
        raise ContractError('RUNNER_JOB_INVALID')
    return under_work(BASE/'jobs'/key)


def _read(path):
    path=under_work(path)
    if path.stat().st_size>2*1024*1024:raise ContractError('RUNNER_STATE_INVALID')
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict):raise ContractError('RUNNER_STATE_INVALID')
    return value


def _write(path,value):
    path=under_work(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name('.'+path.name+'-'+uuid.uuid4().hex)
    try:
        with temp.open('x',encoding='utf-8') as f:
            f.write(encode(value)+'\n');f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)


def _transition(folder,state,**fields):
    data=_read(folder/'state.json');at=now_utc()
    if data['state']!=state:
        data.setdefault('lifecycle',[]).append({'state':state,'at_utc':at,
            **{k:fields[k] for k in ('material_sha256','batch_index','batch_count','first_error') if k in fields}})
    data.update(fields,state=state,updated_at_utc=at)
    _write(folder/'state.json',data)
    return data


def _owner_proof(identity,config):
    from .native_host import delegated,call
    if delegated(config):return call(config,'owner_proof',{'identity':identity})
    with read_db(config['openbot_db']) as db:
        rows=db.execute('''SELECT d.turn_id,m.text,m.sender_kind FROM projection_deliveries d
          JOIN projection_mailbox_messages m ON m.message_id=d.message_id
          WHERE d.recipient_agent_id=? AND m.sender_kind='user' ''',(identity['agent_id'],)).fetchall()
    rows=[r for r in rows if ref(r[0])==identity['turn_ref'] and r[1].strip().casefold().rstrip('.!')==OWNER_COMMAND]
    if len(rows)!=1:raise ContractError('RUNNER_OWNER_START_REQUIRED')
    return {'owner_message_sha256':digest(rows[0][1].encode()),'owner_origin':'OPENBOT_CURRENT_USER_DELIVERY'}


def start(request_id):
    if not isinstance(request_id,str) or not re.fullmatch('[0-9a-f]{32}',request_id):
        raise ContractError('RUNNER_REQUEST_INVALID')
    if Path.cwd().resolve()!=ROOT:raise ContractError('RUNNER_WRONG_WORKING_DIRECTORY')
    config=load_private(PRIVATE);identity=active_identity(config)
    if identity['provider']!='codex':raise ContractError('RUNNER_AUTONOMOUS_HANDOFF_UNSUPPORTED_FOR_PROVIDER')
    owner=_owner_proof(identity,config)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):
        raise ContractError('RUNNER_DIRTY_CHECKOUT')
    BASE.mkdir(parents=True,exist_ok=True);lock=under_work(BASE/'active.json')
    # The owner message/turn is the idempotency key, even if the model invents a
    # new request id on retry. Concurrent or interrupted work never starts twice.
    try:
        with lock.open('x',encoding='utf-8') as f:
            key=utc(now_utc()).strftime('%Y%m%dT%H%M%SZ')+'-'+request_id
            f.write(encode({'job_id':key,'turn_ref':identity['turn_ref']}))
    except FileExistsError:
        existing=_read(lock)
        if existing.get('turn_ref')==identity['turn_ref']:return status(existing['job_id'])
        if status(existing['job_id'])['state'] not in FINAL:raise ContractError('RUNNER_ALREADY_ACTIVE')
        # Serialize replacement: only the next owner turn can release a finished
        # lock. Exclusive request lock prevents two callers replacing it at once.
        guard=BASE/'replace.lock'
        try:
            with guard.open('x'):pass
        except FileExistsError:raise ContractError('RUNNER_ALREADY_ACTIVE') from None
        try:
            if _read(lock)!=existing:raise ContractError('RUNNER_ALREADY_ACTIVE')
            lock.unlink()
            return start(request_id)
        finally:guard.unlink(missing_ok=True)
    folder=_job(key);folder.mkdir(parents=True)
    _write(folder/'state.json',{'schema_version':'openbot.research-job.v1','job_id':key,
        'state':'STARTING','created_at_utc':now_utc(),'updated_at_utc':now_utc(),
        'commit':sha,'native_identity':identity,'request_id':request_id,**owner,
        'lifecycle':[{'state':'OWNER_AUTHORIZED','at_utc':now_utc()}],
        'trade_authorization':False,'live_acceptance':'PARTIAL; NO_LIVE_RUN_YET'})
    try:
        with (folder/'worker.log').open('x',encoding='utf-8') as log:
            child=subprocess.Popen([sys.executable,'-m','researcher.openbot_runner','_worker','--job-id',key],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        _write(folder/'process.json',{'pid':child.pid})
    except OSError:
        _transition(folder,'FAILED',reason='RUNNER_PROCESS_START_FAILED');raise ContractError('RUNNER_PROCESS_START_FAILED') from None
    return status(key)


def recorded_launch_matches(item,request_id,root,host_os):
    """Match the observed argv schema, not text mentioning an authorized command."""
    import shlex
    from pathlib import PureWindowsPath
    expected=['python3','-m','researcher.openbot_runner','start','--request-id',request_id]
    command=item.get('command')
    if not isinstance(command,list) or not all(isinstance(v,str) for v in command):return False
    if (len(command) in {3,4} and PureWindowsPath(command[0]).name.casefold()=='powershell.exe'
            and command[1:-1] in (['-Command'],['-NoProfile','-Command'])):
        try:argv=shlex.split(command[-1])
        except ValueError:return False
        if host_os=='nt':root='/mnt/'+root[0].lower()+'/'+root[3:].replace(chr(92),'/')
        return argv==['wsl.exe','--cd',root,'--',*expected]
    return command==expected and str(item.get('cwd',''))==root


def attest_start(state,config):
    from .native_host import delegated,call
    if delegated(config):return call(config,'attest_start',{'state':state})
    from .native_codex import records,context_matches
    from datetime import timedelta
    identity=state['native_identity'];assert_current(identity,config)
    if _owner_proof(identity,config)['owner_message_sha256']!=state['owner_message_sha256']:
        raise ContractError('RUNNER_OWNER_START_REQUIRED')
    with read_db(config['openbot_db']) as db:
        rows=db.execute('''SELECT p.external_session_id,t.turn_id,t.started_at FROM projection_turns t
          JOIN projection_provider_sessions p ON p.id=t.provider_session_id
          JOIN projection_threads h ON h.thread_id=t.thread_id WHERE h.agent_id=?''',(identity['agent_id'],)).fetchall()
    rows=[r for r in rows if ref(r[0])==identity['external_session_ref'] and ref(r[1])==identity['turn_ref']]
    if len(rows)!=1:raise ContractError('RUNNER_START_UNATTESTED')
    session,turn,start_at=rows[0]
    context=False;proof=None
    for x in records(config,session,config['agent_workspace'],start=utc(start_at)-timedelta(seconds=1),end=utc(now_utc()),backend=identity.get('provider_backend')):
        p=x['payload']
        if x['type']=='turn_context':
            context_matches(p,turn,identity['model'],config['agent_workspace'])
            context=True
        if x['type']=='event_msg' and p.get('type')=='item_completed' and p.get('turn_id')==turn:
            if p.get('thread_id')!=session:raise ContractError('NATIVE_SESSION_MISMATCH')
            item=p.get('item',{})
            if (context and item.get('type')=='CommandExecution' and item.get('status')=='completed'
                    and type(item.get('exit_code')) is int and item['exit_code']==0
                    and recorded_launch_matches(item,state['request_id'],str(ROOT),os.name)):
                proof={'status':'VERIFIED_OPENBOT_AGENT_COMMAND','source':'CODEX_PROVIDER_COMMAND_EXECUTION',
                    'parent_turn_ref':ref(turn),'command_sha256':digest(encode(item['command']).encode()),
                    'verified_at_utc':now_utc()}
    if proof is not None:return proof
    raise ContractError('RUNNER_START_UNATTESTED')


def run_job(key):
    """Called only by the detached worker. Offline tests patch the dependencies."""
    folder=_job(key);state=_read(folder/'state.json');config=load_private(PRIVATE)
    if state['state']!='STARTING':return status(key)  # no replay after any transition
    # Exclusive durable claim also prevents two workers racing before transition.
    try:
        with (folder/'worker.claim').open('x',encoding='utf-8') as stream:
            stream.write(encode({'claimed_at_utc':now_utc()}))
    except FileExistsError:return status(key)
    try:
        # The launching command must finish before its completed provider receipt
        # exists. Wait for that receipt only; no market operation before proof.
        proof=None
        for _ in range(30):
            try:proof=attest_start(state,config);break
            except ContractError as error:
                if str(error)!='RUNNER_START_UNATTESTED':raise
            time.sleep(1)
        if proof is None:raise ContractError('RUNNER_START_UNATTESTED')
        _transition(folder,'COMMAND_ATTESTED',start_proof=proof)
        _transition(folder,'SCANNING',scanner_started_at_utc=now_utc())
        from .discovery import scan_market_research
        def progress(stage,seconds):
            current=_read(folder/'state.json')['state']
            _transition(folder,current,stage=stage,stage_seconds=seconds)
        def native_progress(state,**fields):
            _transition(folder,state,**fields)
        report=scan_market_research(ledger_path=BASE/'research.sqlite',
            native_review_dir=folder/'review',native_audit_config=PRIVATE,
            native_wait_seconds=600,native_max_cards=4,progress=progress,native_progress=native_progress,job_id=key,clock=now_utc)
        report['openbot_orchestration']={'job_id':key,'commit':state['commit'],'start_proof':proof,
            'native_identity':state['native_identity'],'invocation_source':'EXISTING_OPENBOT_RESEARCHER',
            'acceptance':'PARTIAL; FINAL_APP_DELIVERY_NOT_YET_OBSERVED','trade_authorization':False}
        data=_transition(folder,'RECONCILED',scanner_completed_at_utc=now_utc())
        report['openbot_orchestration']['lifecycle']=data.get('lifecycle',[])
        report['openbot_orchestration']['final_delivery']='AWAITING_NATIVE_APP_ATTACHMENT_AND_RESPONSE_PROOF'
        from .__main__ import write_report
        from .diagnostic_export import sanitize
        report=sanitize(report)
        report['output_payload_sha256']=digest(encode({k:v for k,v in report.items()
            if k not in {'persistence','output_payload_sha256'}}).encode())
        write_report(folder/'report.json',report)
        from .diagnostic_export import export_job
        artifact=export_job(folder,report,config)
        _transition(folder,'EXPORTED',artifact=artifact)
        native=report.get('consultant',{})
        complete=(report.get('mode')=='LIVE' and native.get('status')=='VALIDATED_ADVISORY_ONLY'
            and native.get('accepted',0)>0 and native.get('native_receipt',{}).get('native_identity')==state['native_identity'])
        # Delivery is a subsequent native main-chat action. This worker never
        # asserts FULL acceptance before observing the real delivered answer.
        _transition(folder,'COMPLETED' if complete else 'PARTIAL',artifact=artifact,
            native_status=native.get('status'),native_collector=native.get('native_collector'),
            first_error=native.get('first_error'),observed_model_attempts=native.get('observed_model_attempts',0),
            live_acceptance='PARTIAL; AWAITING_OPENBOT_RESULT_AND_ZIP_DELIVERY' if complete else 'PARTIAL; NATIVE_OR_SOURCE_GATE_NOT_PASSED')
    except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
        # No private exception/path/token is included in the user-facing state.
        code=str(error) if isinstance(error,ContractError) and re.fullmatch('[A-Z0-9_; ]{1,160}',str(error)) else 'RUNNER_DEPENDENCY_OR_STORAGE_UNAVAILABLE'
        from .native_identity import safe_diagnostic
        diagnostic=safe_diagnostic(getattr(error,'diagnostic',None))
        _transition(folder,'FAILED',reason=code,live_acceptance='PARTIAL',
            **({'native_diagnostic':diagnostic} if diagnostic else {}))
    return status(key)


def status(key,include_review=False):
    folder=_job(key);data=_read(folder/'state.json')
    delivery_error=None
    if data['state'] in {'COMPLETED','PARTIAL'} and data.get('artifact'):
        try:
            from .native_runtime import delivery_proof
            receipt=delivery_proof(data,load_private(PRIVATE))
            if receipt:data=_transition(folder,'FINAL_DELIVERED',delivery_receipt=receipt)
        except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
            from .native_app import failure
            delivery_error=failure(error,'FINAL_DELIVERY_OBSERVATION')
    result={k:data[k] for k in ('schema_version','job_id','state','created_at_utc','updated_at_utc','commit',
        'stage','stage_seconds','reason','native_status','native_collector','artifact','live_acceptance','trade_authorization',
        'delivery_receipt','lifecycle','material_sha256','batch_index','batch_count','first_error','observed_model_attempts') if k in data}
    if delivery_error:result['delivery_observation_error']=delivery_error
    from .native_identity import safe_diagnostic
    diagnostic=safe_diagnostic(data.get('native_diagnostic'))
    if diagnostic:result['native_diagnostic']=diagnostic
    if data['state'] not in FINAL:
        material=data.get('material_sha256')
        if material and re.fullmatch('[0-9a-f]{64}',material):
            task=folder/'review'/(material+'.review-task.json')
            ready=[task] if task.is_file() and data['state'] in {'REVIEW_READY','REVIEW_RUNNING'} else []
        else:ready=list((folder/'review').glob('*.review-task.json'))
        if len(ready)>1:raise ContractError('RUNNER_REVIEW_COLLISION')
        if ready:
            args=_read(ready[0]);result['state']='REVIEW_READY'
            if (set(args)!={'title','brief'} or args['title']!='OPENBOT-RESEARCH-'+ready[0].name.split('.')[0]
                    or not isinstance(args['brief'],str) or len(args['brief'])>100000):
                raise ContractError('NATIVE_HANDOFF_UNATTESTED')
            try:
                private=load_private(PRIVATE)
                assert_current(data['native_identity'],private)
                from .native_app import review_count
                count=review_count({'native_identity':data['native_identity'],
                    'material_sha256':ready[0].name.split('.')[0]},private)
                if count>1:
                    result.update(state='REVIEW_FAILED',reason='NATIVE_HANDOFF_UNATTESTED')
                elif count:result['state']='REVIEW_RUNNING'
            except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
                from .native_app import failure
                result['review_observation_error']=failure(error,'DISPATCH_OBSERVATION')
                # Publication remains usable during a receipt-reader outage.
                fault=result['review_observation_error']
                if fault['code'] in {'NATIVE_STORAGE_UNAVAILABLE','NATIVE_STORAGE_TIMED_OUT',
                        'NATIVE_STORAGE_LOCKED','NATIVE_READER_PROCESS_UNAVAILABLE'}:
                    result['state']=data['state'] if data['state']=='REVIEW_RUNNING' else 'REVIEW_READY'
                else:result.update(state='REVIEW_FAILED',reason=fault['code'])
            if result['state']=='REVIEW_READY':
                # Atomic one-shot dispatch reservation. A second status caller
                # cannot receive another submission ticket while app storage is
                # catching up. Lost callers time out; never auto-resubmit.
                lease=ready[0].with_name(ready[0].name.replace('.review-task.json','.dispatch.json'))
                if lease.exists():
                    result['state']='REVIEW_DISPATCH_RESERVED'
                    result['dispatch_receipt']=_read(lease)
                elif include_review:
                    receipt={'material_sha256':ready[0].name.split('.')[0],
                        'arguments_sha256':digest(encode(args).encode()),'reserved_at_utc':now_utc(),
                        'submission_policy':'EXACTLY_ONE_TICKET; NEVER_AUTOMATICALLY_RESUBMIT'}
                    try:
                        with lease.open('x',encoding='utf-8') as stream:
                            stream.write(encode(receipt));stream.flush();os.fsync(stream.fileno())
                    except FileExistsError:result['state']='REVIEW_DISPATCH_RESERVED'
                    else:
                        result['start_task_arguments']=args;result['dispatch_receipt']=receipt

        proc=folder/'process.json'
        if proc.exists():
            try:os.kill(_read(proc)['pid'],0)
            except ProcessLookupError:
                _transition(folder,'INTERRUPTED',reason='RUNNER_PROCESS_ENDED; NO_AUTOMATIC_LIVE_REPLAY')
                result.update(state='INTERRUPTED',reason='RUNNER_PROCESS_ENDED; NO_AUTOMATIC_LIVE_REPLAY')
    if data['state'] in {'COMPLETED','PARTIAL','FINAL_DELIVERED'} and (folder/'report.json').is_file():
        from .discovery import research_summary,coverage_summary,watch_summary
        report=json.loads((folder/'report.json').read_text(encoding='utf-8'))
        native=report.get('consultant',{})
        result.update(results=research_summary(report),coverage=coverage_summary(report),watches=watch_summary(report),
            costs=report.get('costs'),native_review={'status':native.get('status'),'accepted':native.get('accepted'),
                'reply':native.get('reply'),'decision_delta':report.get('native_control_comparison')})
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','status','_worker','preflight'])
    parser.add_argument('--request-id');parser.add_argument('--job-id');parser.add_argument('--include-review',action='store_true')
    args=parser.parse_args()
    try:
        if args.action=='preflight':
            from .native_identity import configured_identity
            config=load_private(PRIVATE);identity=configured_identity(config)
            from .settings import validate_config,load_config
            validate_config(load_config())
            result={'status':'OFFLINE_PREFLIGHT_ONLY','identity':identity,'live_calls':0,'live_acceptance':'PARTIAL; OWNER_INITIATION_REQUIRED'}
        elif args.action=='start':result=start(args.request_id)
        elif args.action=='status':result=status(args.job_id,args.include_review)
        else:result=run_job(args.job_id)
        print(encode(result));return 0
    except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
        code=str(error) if isinstance(error,ContractError) else 'RUNNER_PRIVATE_DEPENDENCY_UNAVAILABLE'
        print(encode({'state':'REJECTED','reason':code,'trade_authorization':False}));return 2


if __name__=='__main__':raise SystemExit(main())
