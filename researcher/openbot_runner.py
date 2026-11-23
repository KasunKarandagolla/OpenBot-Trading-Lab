"""Fixed-purpose asynchronous runner for the existing OpenBot Researcher.

Start is gated by a real current owner delivery AND a provider-recorded command
in that agent's current main turn. This module never submits a model request.
No MCP server, Local Scripts, scheduler, arbitrary shell endpoint or API key.
"""
import argparse
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sqlite3
import sys
import time
import uuid
import zipfile
from contextlib import contextmanager
from datetime import timedelta
from .contracts import ContractError, digest, encode, now_utc, utc
from .settings import ROOT
from .native_identity import active_identity, assert_current, assert_parent, load_private, read_db, ref, under_work
from .native_handoff import CONFIRMED_PAGES, FRESH_SECONDS, JOB_ID, SHA256, SUBMISSION_SECONDS

BASE=ROOT/'work/openbot-integration'
PRIVATE=BASE/'native-audit-local.json'
OWNER_COMMAND='run the complete market research now'
SMOKE_PROMPT=ROOT/'docs/implementation/OPENBOT_NATIVE_SMOKE_PROMPT.txt'
AI_SMOKE_PROMPT=ROOT/'docs/implementation/OPENBOT_AI_CORE_SMOKE_PROMPT.txt'
ACCEPTANCE_PROMPT=ROOT/'docs/implementation/OPENBOT_RECOVERY_ACCEPTANCE_PROMPT.txt'
FINAL={'COMPLETED','PARTIAL','FAILED','INTERRUPTED','FINAL_DELIVERED'}


def _job(key):
    if not isinstance(key,str) or not re.fullmatch(JOB_ID,key):
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
    with _file_guard(folder/'state.lock'):
        return _transition_locked(folder,state,**fields)


def _transition_locked(folder,state,**fields):
    data=_read(folder/'state.json');at=now_utc()
    state=state or data['state']
    # A stale status/progress reader cannot overwrite a terminal worker result.
    delivery=(state=='FINAL_DELIVERED' and data['state'] in {'COMPLETED','PARTIAL'})
    delivery_timeout=(state==data['state'] and state in {'COMPLETED','PARTIAL'}
        and fields=={'delivery_observation_status':'FINAL_DELIVERY_NOT_OBSERVED_WITHIN_BOUND'})
    if data['state'] in FINAL and not (delivery or delivery_timeout):return data
    if delivery:fields['delivery_observation_status']='FINAL_DELIVERY_VERIFIED'
    if data['state']!=state or 'native_task_state' in fields and fields['native_task_state']!=data.get('native_task_state'):
        data.setdefault('lifecycle',[]).append({'state':state,'at_utc':at,
            **{k:fields[k] for k in ('material_sha256','batch_index','batch_count','first_error','native_task_state',
                'submission_attempts','submission_state','submission_observation_status','observed_model_attempts') if k in fields}})
    data.update(fields,state=state,updated_at_utc=at)
    _write(folder/'state.json',data)
    return data


@contextmanager
def _file_guard(path, *, nonblocking=False):
    # The approved runner executes in WSL/POSIX. OS ownership releases this
    # guard on a crash; an abandoned exclusive-create file must not block forever.
    try:import fcntl
    except ImportError:raise ContractError('RUNNER_PROCESS_LOCK_UNSUPPORTED') from None
    path=under_work(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('ab') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0))
        except BlockingIOError:raise ContractError('RUNNER_ALREADY_ACTIVE') from None
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


def _process_token(pid):
    try:return (Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()[19]
    except (OSError,IndexError):return None


def _process_record(pid):
    return {'pid':pid,'start_token':_process_token(pid)}


def _process_alive(record):
    try:os.kill(record['pid'],0)
    except ProcessLookupError:return False
    token=_process_token(record['pid'])
    return not (record.get('start_token') and token and record['start_token']!=token)


def _owner_proof(identity,config,*,expected_commit=None):
    from .native_host import delegated,call
    if delegated(config):return call(config,'owner_proof',{'identity':identity,'expected_commit':expected_commit})
    with read_db(config['openbot_db']) as db:
        rows=db.execute('''SELECT d.turn_id,m.text,m.sender_kind FROM projection_deliveries d
          JOIN projection_mailbox_messages m ON m.message_id=d.message_id
          WHERE d.recipient_agent_id=? AND m.sender_kind='user' ''',(identity['agent_id'],)).fetchall()
    def mode(text):
        if not isinstance(text,str):return None
        if text.strip().casefold().rstrip('.!')==OWNER_COMMAND:return 'ORDINARY_RESEARCH'
        if (isinstance(expected_commit,str) and re.fullmatch('[0-9a-f]{40}',expected_commit) and
                text.strip()==SMOKE_PROMPT.read_text(encoding='utf-8').replace('@@APPROVED_COMMIT@@',expected_commit).strip()):
            return 'NATIVE_SMOKE'
        if (isinstance(expected_commit,str) and re.fullmatch('[0-9a-f]{40}',expected_commit) and
                text.strip()==AI_SMOKE_PROMPT.read_text(encoding='utf-8').replace('@@APPROVED_COMMIT@@',expected_commit).strip()):
            return 'AI_CORE_SMOKE'
        # Exact versioned owner message, pinned to the checkout being launched.
        # Substrings, negated/quoted instructions and delegated senders fail.
        if (isinstance(expected_commit,str) and re.fullmatch('[0-9a-f]{40}',expected_commit) and
                text.strip()==ACCEPTANCE_PROMPT.read_text(encoding='utf-8').replace('@@APPROVED_COMMIT@@',expected_commit).strip()):
            return 'SETUP_AND_ACCEPTANCE'
        return None
    rows=[(*r,mode(r[1])) for r in rows if ref(r[0])==identity['turn_ref']]
    rows=[r for r in rows if r[3] is not None]
    if len(rows)!=1:raise ContractError('RUNNER_OWNER_START_REQUIRED')
    return {'owner_message_sha256':digest(rows[0][1].encode()),'owner_origin':'OPENBOT_CURRENT_USER_DELIVERY',
        'owner_run_mode':rows[0][3]}


def start(request_id):
    if not isinstance(request_id,str) or not re.fullmatch('[0-9a-f]{32}',request_id):
        raise ContractError('RUNNER_REQUEST_INVALID')
    if Path.cwd().resolve()!=ROOT:raise ContractError('RUNNER_WRONG_WORKING_DIRECTORY')
    config=load_private(PRIVATE);identity=active_identity(config)
    if identity['provider']!='codex':raise ContractError('RUNNER_AUTONOMOUS_HANDOFF_UNSUPPORTED_FOR_PROVIDER')
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):
        raise ContractError('RUNNER_DIRTY_CHECKOUT')
    owner=_owner_proof(identity,config,expected_commit=sha)
    BASE.mkdir(parents=True,exist_ok=True);lock=under_work(BASE/'active.json')
    # The owner message/turn is the idempotency key, even if the model invents a
    # new request id on retry. Concurrent or interrupted work never starts twice.
    with _file_guard(BASE/'start.lock',nonblocking=True):
        if lock.exists():
            existing=_read(lock)
            if existing.get('turn_ref')==identity['turn_ref']:return status(existing['job_id'])
            if status(existing['job_id'])['state'] not in FINAL:raise ContractError('RUNNER_ALREADY_ACTIVE')
        key=utc(now_utc()).strftime('%Y%m%dT%H%M%SZ')+'-'+request_id
        initial={'schema_version':'openbot.research-job.v1','job_id':key,
            'state':'STARTING','created_at_utc':now_utc(),'updated_at_utc':now_utc(),
            'commit':sha,'native_identity':identity,'request_id':request_id,**owner,
            'lifecycle':[{'state':'OWNER_AUTHORIZED','at_utc':now_utc()}],
            'trade_authorization':False,'live_acceptance':'PARTIAL; NO_LIVE_RUN_YET'}
        # Atomically publish enough state to recover a crash before state.json.
        folder=_job(key)
        with _file_guard(folder/'state.lock'):
            _write(lock,{'job_id':key,'turn_ref':identity['turn_ref'],'initial_state':initial})
            _write(folder/'state.json',initial)
    try:
        with (folder/'worker.log').open('x',encoding='utf-8') as log:
            child=subprocess.Popen([sys.executable,'-m','researcher.openbot_runner','_worker','--job-id',key],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        with _file_guard(folder/'state.lock'):
            _write(folder/'process.json',_process_record(child.pid))
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
    from .native_codex import turn_records,check_turn_model
    from datetime import timedelta
    identity=state['native_identity'];assert_current(identity,config)
    if _owner_proof(identity,config,expected_commit=state['commit'])['owner_message_sha256']!=state['owner_message_sha256']:
        raise ContractError('RUNNER_OWNER_START_REQUIRED')
    with read_db(config['openbot_db']) as db:
        rows=db.execute('''SELECT p.external_session_id,t.turn_id,t.started_at FROM projection_turns t
          JOIN projection_provider_sessions p ON p.id=t.provider_session_id
          JOIN projection_threads h ON h.thread_id=t.thread_id WHERE h.agent_id=?''',(identity['agent_id'],)).fetchall()
    rows=[r for r in rows if ref(r[0])==identity['external_session_ref'] and ref(r[1])==identity['turn_ref']]
    if len(rows)!=1:raise ContractError('RUNNER_START_UNATTESTED')
    session,turn,start_at=rows[0]
    context=False;proof=None
    for x in turn_records(config,session,turn,config['agent_workspace'],start=utc(start_at)-timedelta(seconds=1),end=utc(now_utc()),backend=identity.get('provider_backend')):
        p=x['payload']
        context=check_turn_model(x,session,turn,identity['model'],config['agent_workspace'],context)
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


def _prior_live_packet(current):
    """Only the approved runner's prior command-attested live capture area."""
    for folder in sorted((BASE/'jobs').iterdir(),reverse=True)[:32]:
        if folder==current or not folder.is_dir():continue
        state_path=under_work(folder/'state.json')
        if not state_path.is_file():continue
        state=_read(state_path)
        if (state.get('start_proof',{}).get('status')!='VERIFIED_OPENBOT_AGENT_COMMAND' or
                not state.get('scanner_started_at_utc')):continue
        for path in sorted((folder/'review').glob('*.request.json')):
            path=under_work(path)
            if path.stat().st_size>131072:continue
            request=json.loads(path.read_text(encoding='utf-8'))
            if request.get('cards') and all(c.get('mode')=='LIVE' for c in request['cards']):return path
    return None


def run_job(key):
    """Called only by the detached worker. Offline tests patch the dependencies."""
    folder=_job(key);config=load_private(PRIVATE)
    claimed=False
    with _file_guard(folder/'state.lock'):
        state=_read(folder/'state.json')
        if state['state']=='STARTING':
            try:
                with (folder/'worker.claim').open('x',encoding='utf-8') as stream:
                    stream.write(encode({'claimed_at_utc':now_utc()}))
                claimed=True
            except FileExistsError:pass
            if claimed and not (folder/'process.json').exists():
                _write(folder/'process.json',_process_record(os.getpid()))
    if not claimed:return status(key)
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
        # Select the current transport before publishing any review files. A
        # status poll in the publication window must never issue a legacy ticket.
        _transition(folder,'COMMAND_ATTESTED',start_proof=proof,review_transport='PAGED_V2')
        from .discovery import scan_market_research
        def progress(stage,seconds):
            _transition(folder,None,stage=stage,stage_seconds=seconds)
        def native_progress(state,**fields):
            _transition(folder,state,**fields)
        transport=None
        smoke=state.get('owner_run_mode')=='NATIVE_SMOKE'
        discovery=None
        if state.get('owner_run_mode') in {'SETUP_AND_ACCEPTANCE','NATIVE_SMOKE'}:
            from .native_runtime import integration_preflight
            source=None
            try:
                setup=integration_preflight(config,as_of=now_utc())
                if smoke:
                    from .native_runtime import attest_smoke_discovery
                    discovery=attest_smoke_discovery(state['native_identity'],config,as_of=now_utc())
                    setup['native_tool_discovery']=discovery
                _transition(folder,'NATIVE_INTEGRATION_PREFLIGHT',integration_preflight=setup)
                source=_prior_live_packet(folder)
            except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
                if not smoke:raise
                from .native_app import failure
                transport={'status':'NATIVE_REVIEW_INCOMPLETE','first_error':failure(error,'NATIVE_SMOKE_PREFLIGHT'),
                    'observed_model_attempts':0,'current_market_interpretation':False}
            if source and transport is None:
                from .native_workflow import probe_captured_request
                try:
                    transport=probe_captured_request(folder/'review',source,native_identity=state['native_identity'],
                        audit_config=PRIVATE,clock=now_utc,progress=lambda s,**v:native_progress(s,
                            review_scope='ARCHIVED_TRANSPORT_PREFLIGHT',**v))
                except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
                    from .native_app import failure
                    transport={'status':'NATIVE_REVIEW_INCOMPLETE','first_error':failure(error,'NATIVE_TRANSPORT_PREFLIGHT'),
                        'observed_model_attempts':0,'current_market_interpretation':False}
            elif transport is None:
                transport={'status':'NO_PREVIOUS_LIVE_PACKET; CURRENT_SCAN_REVIEW_REQUIRED','observed_model_attempts':0}
        transport_failed=(transport and not transport['status'].startswith('NO_PREVIOUS_LIVE_PACKET') and
            (transport['status']!='VALIDATED_ADVISORY_ONLY' or transport.get('accepted',0)<1 or
                transport.get('native_receipt',{}).get('native_identity')!=state['native_identity']))
        ai_smoke=state.get('owner_run_mode')=='AI_CORE_SMOKE'
        if ai_smoke:
            report=_run_ai_smoke(key,folder,state,config,progress,native_progress)
        elif smoke or transport_failed:
            report={'schema_version':'openbot.native-preflight-report.v1','mode':'AUTHENTIC_REPLAY',
                'release_status':('ARCHIVED_NATIVE_SMOKE' if smoke else 'PARTIAL_NATIVE_PREFLIGHT_FAILED'),
                'job_id':key,'market_scan_started':False,
                'completed_at_utc':now_utc(),'trade_authorization':False,'shortlist':[],
                'coverage':{'eligible_contracts':None,'all_market_structurally_covered':False},
                'consultant':{'status':('NOT_INVOKED_CURRENT_MARKET; ARCHIVED_SMOKE_ONLY' if smoke
                    else 'NOT_INVOKED_CURRENT_MARKET; PREFLIGHT_FAILED')},
                'costs':{'market_http_requests':0,'archived_native_model_attempts':transport.get('observed_model_attempts',0)}}
            if smoke:
                reconciliation={'status':'REVIEW_NOT_VALIDATED','current_market_interpretation':False}
                if not transport_failed and source and transport.get('accepted',0)>0:
                    try:
                        from .native_workflow import reconcile_archived_smoke
                        reconciliation=reconcile_archived_smoke(source,transport,as_of=now_utc())
                    except (ContractError,OSError,ValueError,TypeError,KeyError,zipfile.BadZipFile) as error:
                        from .native_app import failure
                        reconciliation={'status':'RECONCILIATION_FAILED',
                            'error':failure(error,'ARCHIVED_RECONCILIATION'),'current_market_interpretation':False}
                report['smoke_result']={'status':'VERIFIED_REVIEW' if not transport_failed and source
                    and transport.get('accepted',0)>0 else 'INCOMPLETE',
                    'tool_discovery':discovery or {'status':'NOT_VERIFIED'},
                    'reconciliation':reconciliation,
                    'final_delivery':'PENDING_PROVIDER_RECEIPT'}
        else:
            _transition(folder,'SCANNING',scanner_started_at_utc=now_utc())
            from .ai_core import research_with_native
            research=research_with_native(folder/'review',audit_config=PRIVATE,
                identity=state['native_identity'],clock=now_utc,progress=lambda s,**v:native_progress(s,
                    review_scope='CURRENT_MARKET_AI_RESEARCH',**v))
            report=scan_market_research(ledger_path=BASE/'research.sqlite',
                progress=progress,job_id=key,clock=now_utc,ai_research=research)
            report['market_scan_started']=True
        if transport:report['native_transport_preflight']=transport
        report['openbot_orchestration']={'job_id':key,'commit':state['commit'],'start_proof':proof,
            'native_identity':state['native_identity'],'invocation_source':'EXISTING_OPENBOT_RESEARCHER',
            'acceptance':'PARTIAL; FINAL_APP_DELIVERY_NOT_YET_OBSERVED','trade_authorization':False}
        data=_transition(folder,'RECONCILED' if report['market_scan_started'] or report.get('ai_research') else 'PREFLIGHT_REJECTED',
            scanner_completed_at_utc=now_utc() if report['market_scan_started'] else None)
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
        complete=(report.get('mode')=='LIVE' and report.get('ai_research',{}).get('state')=='AI_RESEARCH_COMPLETE')
        archived_complete=(ai_smoke and report.get('ai_research',{}).get('state')=='AI_RESEARCH_COMPLETE')
        # Delivery is a subsequent native main-chat action. This worker never
        # asserts FULL acceptance before observing the real delivered answer.
        _transition(folder,'COMPLETED' if complete or archived_complete else 'PARTIAL',artifact=artifact,
            native_status=native.get('status'),native_collector=native.get('native_collector'),
            first_error=native.get('first_error') or (transport or {}).get('first_error') or
                (transport or {}).get('native_collector',{}).get('first_error'),
            observed_model_attempts=native.get('observed_model_attempts',0),
            transport_model_attempts=(transport or {}).get('observed_model_attempts',0),
            live_acceptance=('ARCHIVED_NATIVE_SMOKE_ONLY' if ai_smoke else
                'PARTIAL; AWAITING_OPENBOT_RESULT_AND_ZIP_DELIVERY' if complete else 'PARTIAL; NATIVE_OR_SOURCE_GATE_NOT_PASSED'))
    except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
        # No private exception/path/token is included in the user-facing state.
        code=str(error) if isinstance(error,ContractError) and re.fullmatch('[A-Z0-9_; ]{1,160}',str(error)) else 'RUNNER_DEPENDENCY_OR_STORAGE_UNAVAILABLE'
        from .native_identity import safe_diagnostic
        diagnostic=safe_diagnostic(getattr(error,'diagnostic',None))
        _transition(folder,'FAILED',reason=code,live_acceptance='PARTIAL',
            **({'native_diagnostic':diagnostic} if diagnostic else {}))
    return status(key)


def _run_ai_smoke(key,folder,state,config,progress,native_progress):
    from .ai_core import research_with_native
    from .discovery import scan_market_research
    from .native_app import failure
    from .native_runtime import attest_smoke_discovery, integration_preflight
    from .replay import retained_session5

    discovery={'status':'NOT_VERIFIED'}
    try:
        setup=integration_preflight(config,as_of=now_utc())
        discovery=attest_smoke_discovery(state['native_identity'],config,as_of=now_utc())
        _transition(folder,'NATIVE_INTEGRATION_PREFLIGHT',integration_preflight=setup)
        api,client,sources,evidence_at,_=retained_session5()
        research=research_with_native(folder/'review',audit_config=PRIVATE,identity=state['native_identity'],
            clock=now_utc,progress=lambda stage,**fields:native_progress(stage,
                review_scope='ARCHIVED_AI_CORE_SMOKE',**fields))
        report=scan_market_research(api=api,client=client,sources=sources,mode=sources.mode,
            clock=lambda:evidence_at,ledger_path=folder/'archived-replay.sqlite',progress=progress,
            job_id=key,ai_research=research)
    except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
        report={'schema_version':'openbot.ai-core-smoke.v1','mode':'AUTHENTIC_REPLAY',
            'job_id':key,'completed_at_utc':now_utc(),'shortlist':[],
            'consultant':{'status':'AI_DISCOVERY_NOT_STARTED', 'first_error':failure(error,'NATIVE_SMOKE_PREFLIGHT')},
            'coverage':{'all_market_structurally_covered':False},'costs':{},'trade_authorization':False}
    report['market_scan_started']=False
    report['costs']['market_http_requests']=0
    report['costs']['archived_native_model_attempts']=report.get('ai_research',{}).get('provider_attempts',0)
    ai=report.get('ai_research',{})
    report['smoke_result']={'status':'VERIFIED_AI_CORE_REPLAY' if ai.get('state')=='AI_RESEARCH_COMPLETE' else 'INCOMPLETE',
        'tool_discovery':discovery,'current_market_interpretation':False,'final_delivery':'PENDING_PROVIDER_RECEIPT',
        'ai_state':ai.get('state','AI_DISCOVERY_NOT_STARTED'),
        'reasoning_stages':{name:stage['status'] for name,stage in ai.get('stages',{}).items()},
        'reconciliation':{'decisions':len(ai.get('reconciliation',[])),
            'investigations':len(ai.get('investigations',[])),
            'handoffs':len(report.get('shortlist',[]))+len(report.get('conditional_research_candidates',[]))}}
    return report


def _confirmed_review(folder, state, material, stamp, *, check_reservation_window=True):
    from .agent_review import _material
    from .native_handoff import dispatch_frame, packet

    if (state['state'] != 'REVIEW_READY' or state.get('material_sha256') != material
            or state.get('review_transport') != CONFIRMED_PAGES
            or not isinstance(material, str) or not re.fullmatch(SHA256, material)):
        raise ContractError('NATIVE_DISPATCH_WINDOW_CLOSED')
    directory = folder/'review'
    request = _read(directory/(material+'.request.json'))
    if (request.get('material_sha256') != material or request.get('input_transport') != CONFIRMED_PAGES
            or request.get('native_identity') != state['native_identity']
            or digest(encode(_material(request)).encode()) != material):
        raise ContractError('NATIVE_REVIEW_REQUEST_HASH')
    published = state['request_prepared_at_utc']
    if (not 0 <= (utc(stamp)-utc(request['as_of_utc'])).total_seconds() < FRESH_SECONDS
            or check_reservation_window and (
                not 0 <= (utc(stamp)-utc(published)).total_seconds() < SUBMISSION_SECONDS
                or time.monotonic() >= state['submission_expires_monotonic'])):
        raise ContractError('NATIVE_DISPATCH_WINDOW_CLOSED')
    args, fingerprint, pages = packet(request, directory)
    task = under_work(directory/(material+'.review-task.json'))
    if task.read_bytes() != encode(args).encode():
        raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    frame = dispatch_frame(folder.name, material, request['stage'], args, fingerprint, pages)
    return request, frame


def _preview_metadata(frame, stamp):
    return {'preview_sha256': digest((encode(frame, compact=True)+'\n').encode()), 'previewed_at_utc': stamp}


def _confirmed_status(folder, state, result, include_review):
    """Render a recoverable preview from the caller's locked state snapshot."""
    from .native_handoff import load_dispatch

    material = state.get('material_sha256')
    if state['state'] != 'REVIEW_READY' or state.get('review_transport') != CONFIRMED_PAGES:
        return
    directory = folder/'review'
    lease = directory/(material+'.dispatch.json')
    preview = directory/(material+'.preview.json')
    if not include_review and not lease.is_file():
        preview_error = directory/(material+'.preview-error.json')
        if preview_error.is_file():
            result['dispatch_state'] = _read(preview_error)['reason']
        elif preview.is_file():
            result['dispatch_state'] = 'PACKET_DELIVERABLE'
        else:
            result['dispatch_state'] = 'PACKET_PREPARED'
        return
    stamp = now_utc()
    request, frame = _confirmed_review(folder, state, material, stamp, check_reservation_window=not lease.is_file())
    if lease.is_file():
        _, _, _, receipt = load_dispatch(directory, request, as_of=stamp)
        result.update(state='REVIEW_DISPATCH_RESERVED', dispatch_state='DISPATCH_RESERVED',
                      submission_permitted=False, dispatch_receipt=receipt)
        return
    if not preview.is_file():
        _write(preview, _preview_metadata(frame, stamp))
    result.clear()
    result.update(frame)


def reserve_review(key, material, proof=None, end=None):
    """Grant once, only after a round trip of the complete canonical arguments."""
    from .native_handoff import confirm_dispatch, load_dispatch, request_dispatch_policy, submission_deadline

    folder = _job(key)
    directory = folder/'review'
    with _file_guard(folder/'state.lock'):
        state = _read(folder/'state.json')
        stamp = now_utc()
        request, frame = _confirmed_review(folder, state, material, stamp)
        lease = directory/(material+'.dispatch.json')
        if lease.is_file():
            _, _, _, receipt = load_dispatch(directory, request, as_of=stamp)
            return {'state': 'REVIEW_DISPATCH_RESERVED', 'submission_permitted': False,
                    'material_sha256': material, 'arguments_sha256': receipt['arguments_sha256'],
                    'trade_authorization': False}
        try:
            confirm_dispatch(frame, proof, end)
        except ContractError as error:
            _write(directory/(material+'.preview-error.json'), {'reason': str(error)})
            return {'state': 'REVIEW_READY', 'dispatch_state': str(error), 'reason': str(error),
                    'material_sha256': material, 'submission_permitted': False, 'trade_authorization': False}
        preview = _read(directory/(material+'.preview.json'))
        if (preview != _preview_metadata(frame, preview.get('previewed_at_utc'))
                or not utc(state['request_prepared_at_utc']) <= utc(preview['previewed_at_utc']) <= utc(stamp)):
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        identity = state['native_identity']

    # Keep the lock free during the one scoped identity check. Recheck the
    # publication window and the ticket under the lock before granting.
    assert_parent(identity, load_private(PRIVATE), require_configured_model=True)
    with _file_guard(folder/'state.lock'):
        state = _read(folder/'state.json')
        stamp = now_utc()
        request, frame = _confirmed_review(folder, state, material, stamp)
        if request['native_identity'] != identity:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        if lease.is_file():
            _, _, _, receipt = load_dispatch(directory, request, as_of=stamp)
            return {'state': 'REVIEW_DISPATCH_RESERVED', 'submission_permitted': False,
                    'material_sha256': material, 'arguments_sha256': receipt['arguments_sha256'],
                    'trade_authorization': False}
        confirm_dispatch(frame, proof, end)
        reserved_monotonic = time.monotonic()
        if reserved_monotonic >= state['submission_expires_monotonic']:
            raise ContractError('NATIVE_DISPATCH_WINDOW_CLOSED')
        integrity = frame['argument_integrity']
        ticket = {'material_sha256': material, 'arguments_sha256': integrity['arguments_sha256'],
                  'packet_sha256': frame['packet_sha256'], 'evidence_pages': frame['evidence_pages'],
                  'reserved_at_utc': stamp, 'published_at_utc': state['request_prepared_at_utc'],
                  'reserved_monotonic': reserved_monotonic, 'submission_policy': request_dispatch_policy(request),
                  'parent_delivery': 'EXACT_ARGUMENT_BYTES_CONFIRMED', 'argument_integrity': integrity, **preview}
        _write(lease, ticket)
        submit_before = min(submission_deadline(ticket), utc(request['as_of_utc'])+timedelta(seconds=FRESH_SECONDS))
        return {'state': 'REVIEW_DISPATCH_RESERVED', 'submission_permitted': True,
                'material_sha256': material, 'arguments_sha256': integrity['arguments_sha256'],
                'submit_before_utc': submit_before.isoformat(), 'trade_authorization': False}


def _paged_status(folder,data,result,include_review):
    from .agent_review import _material
    from .native_handoff import (RESERVED_SUBMISSION_POLICY, load_dispatch, packet, request_dispatch_policy,
        submission_deadline)
    import tempfile

    if data['state']!='REVIEW_READY':return
    material=data['material_sha256'];directory=folder/'review'
    if not re.fullmatch(SHA256,material):raise ContractError('NATIVE_REVIEW_REQUEST_HASH')
    lease=directory/(material+'.dispatch.json')
    request=_read(directory/(material+'.request.json'))
    if (request.get('material_sha256')!=material or request.get('native_identity')!=data['native_identity']
            or digest(encode(_material(request)).encode())!=material):
        raise ContractError('NATIVE_REVIEW_REQUEST_HASH')
    as_of=now_utc()
    if lease.exists():
        _,_,_,receipt=load_dispatch(directory,request,as_of=as_of)
        result.update(state='REVIEW_DISPATCH_RESERVED',dispatch_receipt=receipt)
        return
    if not include_review:return
    assert_parent(data['native_identity'],load_private(PRIVATE),require_configured_model=True)
    args,fingerprint,pages=packet(request,directory)
    task=under_work(directory/(material+'.review-task.json'))
    if task.read_bytes()!=encode(args).encode('utf-8'):raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    with _file_guard(folder/'state.lock'):
        current=_read(folder/'state.json')
        as_of=now_utc();reserved_monotonic=time.monotonic();published=current.get('request_prepared_at_utc')
        if (current['state']!='REVIEW_READY' or current.get('material_sha256')!=material
                or not 0<=(utc(as_of)-utc(request['as_of_utc'])).total_seconds()<FRESH_SECONDS
                or not 0<=(utc(as_of)-utc(published)).total_seconds()<SUBMISSION_SECONDS
                or reserved_monotonic>=current.get('submission_expires_monotonic',float('inf'))):
            return
        if lease.exists():
            _,_,_,receipt=load_dispatch(directory,request,as_of=as_of)
            result.update(state='REVIEW_DISPATCH_RESERVED',dispatch_receipt=receipt)
            return
        policy=request_dispatch_policy(request)
        receipt={'material_sha256':material,'arguments_sha256':digest(encode(args).encode('utf-8')),
            'packet_sha256':fingerprint,'evidence_pages':len(pages),'reserved_at_utc':as_of,
            'published_at_utc':published,'submission_policy':policy}
        if policy==RESERVED_SUBMISSION_POLICY:receipt['reserved_monotonic']=reserved_monotonic
        handoff={k:result[k] for k in ('job_id','state','review_transport','material_sha256',
            'batch_index','batch_count','ai_stage','trade_authorization') if k in result}
        submit_before=min(submission_deadline(receipt),utc(request['as_of_utc'])+timedelta(seconds=FRESH_SECONDS))
        handoff.update(start_task_arguments=args,dispatch_receipt=receipt,submit_before_utc=submit_before.isoformat())
        # Earlier batches' lifecycle does not compete with the one-shot reply.
        if len(encode(handoff).encode('utf-8'))+1>64*1024:raise ContractError('NATIVE_REVIEW_FILE_SIZE')
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=directory,delete=False) as stream:
                temporary=Path(stream.name)
                stream.write(encode(receipt));stream.flush();os.fsync(stream.fileno())
            os.link(temporary,under_work(lease))
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)
        result.clear();result.update(handoff)


def review_page(key,material,fingerprint,page):
    """Read one complete page of the pinned, unexpired packet from WSL."""
    from .agent_review import _material
    from .native_handoff import load_dispatch, page_command_fingerprint

    if not isinstance(material,str) or not re.fullmatch(SHA256,material):
        raise ContractError('NATIVE_REVIEW_REQUEST_HASH')
    folder=_job(key);directory=folder/'review'
    with _file_guard(folder/'state.lock'):
        state=_read(folder/'state.json')
        if (state['state'] not in {'REVIEW_READY','TASK_SUBMISSION_ATTEMPTED','TASK_CREATED','REVIEW_RUNNING',
                'REVIEW_SUBMISSION_UNVERIFIED'} or state.get('material_sha256')!=material
                or state.get('review_transport') not in {'PAGED_V2',CONFIRMED_PAGES}):
            raise ContractError('NATIVE_DISPATCH_WINDOW_CLOSED')
        request=_read(directory/(material+'.request.json'))
        if (request.get('material_sha256')!=material or request.get('native_identity')!=state['native_identity']
                or digest(encode(_material(request)).encode())!=material):
            raise ContractError('NATIVE_REVIEW_REQUEST_HASH')
        _,expected,pages,ticket=load_dispatch(directory,request,as_of=now_utc())
        if (ticket['published_at_utc']!=state.get('request_prepared_at_utc')
                or fingerprint!=page_command_fingerprint(request,expected)
                or type(page) is not int or not 1<=page<=len(pages)):
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        if (not 0<=(utc(now_utc())-utc(request['as_of_utc'])).total_seconds()<FRESH_SECONDS
                or time.monotonic()>=state.get('request_expires_monotonic',float('inf'))):
            raise ContractError('NATIVE_REQUEST_STALE')
        return pages[page-1]


def status(key,include_review=False):
    folder=_job(key)
    confirmed_result={}
    with _file_guard(folder/'state.lock'):
        try:data=_read(folder/'state.json')
        except FileNotFoundError:
            reservation=_read(BASE/'active.json');initial=reservation.get('initial_state',{})
            if (reservation.get('job_id')!=key or initial.get('job_id')!=key or
                    initial.get('native_identity',{}).get('turn_ref')!=reservation.get('turn_ref')):
                raise ContractError('RUNNER_STATE_INVALID') from None
            _write(folder/'state.json',initial)
            data=_transition_locked(folder,'INTERRUPTED',reason='RUNNER_START_PUBLICATION_INTERRUPTED; NO_AUTOMATIC_LIVE_REPLAY')
        if data['state'] not in FINAL:
            process=folder/'process.json'
            if process.exists() and not _process_alive(_read(process)):
                data=_transition_locked(folder,'INTERRUPTED',reason='RUNNER_PROCESS_ENDED; NO_AUTOMATIC_LIVE_REPLAY')
            elif not process.exists() and (utc(now_utc())-utc(data['created_at_utc'])).total_seconds()>30:
                data=_transition_locked(folder,'INTERRUPTED',reason='RUNNER_PROCESS_NOT_PUBLISHED; NO_AUTOMATIC_LIVE_REPLAY')
        if data.get('review_transport')==CONFIRMED_PAGES:
            # A second snapshot could pair a stale REVIEW_READY status with no
            # preview after the worker has advanced to a different phase.
            _confirmed_status(folder,data,confirmed_result,include_review)
    if 'begin_frame' in confirmed_result:return confirmed_result
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
        'delivery_receipt','lifecycle','material_sha256','batch_index','batch_count','first_error','observed_model_attempts',
        'native_task_state','native_task_observation','transport_model_attempts','review_transport','ai_stage',
        'submission_state','submission_attempts','attempted_at_utc','responded_at_utc','submission_error',
        'clock_diagnostic','submission_observation_status','delivery_observation_status') if k in data}
    if data['state']=='REVIEW_FAILED':
        result['artifact_status']='PENDING_RECONCILIATION_AND_EXPORT'
        result['next_action']=('Continue polling until the worker reaches a terminal state. '
            'Attach the returned artifact if present and report the native review failure.')
    if delivery_error:result['delivery_observation_error']=delivery_error
    from .native_identity import safe_diagnostic
    diagnostic=safe_diagnostic(data.get('native_diagnostic'))
    if diagnostic:result['native_diagnostic']=diagnostic
    if data.get('review_transport') == CONFIRMED_PAGES:
        if data['state'] not in FINAL:
            result.pop('lifecycle',None)
        result.update(confirmed_result)
    elif data.get('review_transport') in {'PAGED_V2','INLINE_AI_CORE_V1'}:
        # The main chat must see the current state even when earlier batches
        # have accumulated more history than the status console can return.
        if data['state'] not in FINAL:result.pop('lifecycle',None)
        _paged_status(folder,data,result,include_review)
    elif data['state'] not in FINAL:
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
                assert_parent(data['native_identity'],private,require_configured_model=True)
                from .native_app import review_count
                observed=review_count({'native_identity':data['native_identity'],
                    'material_sha256':ready[0].name.split('.')[0]},private,details=True)
                count=observed['count'];result['native_task_state']=observed['task_state']
                result['native_task_observation']=observed
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

    if data['state'] in {'COMPLETED','PARTIAL','FINAL_DELIVERED'} and (folder/'report.json').is_file():
        from .discovery import research_summary,coverage_summary,watch_summary
        report=json.loads((folder/'report.json').read_text(encoding='utf-8'))
        native=report.get('consultant',{})
        scanned=report.get('market_scan_started',True)
        result.update(results=research_summary(report) if scanned else (
                'Archived native smoke only. No current-market candidate conclusion.' if report.get('smoke_result')
                else 'Market scan not started: native transport preflight failed. No current-market candidate conclusion.'),
            coverage=coverage_summary(report) if scanned else 'NOT_SCANNED',
            watches=watch_summary(report) if scanned else 'NOT_REFRESHED; PREVIOUS_LEDGER_UNCHANGED',
            costs=report.get('costs'),native_review={'status':native.get('status'),'accepted':native.get('accepted'),
                'verified_model_requests':native.get('verified_model_requests',native.get('observed_model_attempts')),
                'model_requests_total':native.get('model_requests_total'),
                'unverified_dispatch_tickets':native.get('unverified_dispatch_tickets'),
                'invalid_reply_batches':native.get('invalid_reply_batches'),
                'unreviewed_cards':len(native['not_reviewed']) if 'not_reviewed' in native else None,
                'reply':native.get('reply'),'decision_delta':report.get('native_control_comparison')},
            ai_research={name:value for name,value in report.get('ai_research',{}).items()
                if name in {'state','current_market_interpretation','model_tasks','provider_attempts'}},

            native_transport_preflight=report.get('native_transport_preflight'),
            **({'smoke_result':report['smoke_result']} if 'smoke_result' in report else {}))
        if 'smoke_result' in result and data['state']=='FINAL_DELIVERED' and data.get('delivery_receipt'):
            result['smoke_result']={**result['smoke_result'],'final_delivery':'VERIFIED_PROVIDER_RECEIPT'}
    return result


def watch_delivery(key,*,wait_seconds=600):
    """Bounded receipt observation after export; no task/model/scan submission."""
    if type(wait_seconds) is not int or not 0<=wait_seconds<=600:raise ContractError('RUNNER_WAIT_INVALID')
    deadline=time.monotonic()+wait_seconds
    while True:
        result=status(key)
        if result['state']=='FINAL_DELIVERED' or result['state'] not in {'COMPLETED','PARTIAL'}:return result
        if time.monotonic()>=deadline:
            _transition(_job(key),result['state'],delivery_observation_status='FINAL_DELIVERY_NOT_OBSERVED_WITHIN_BOUND')
            return status(key)
        time.sleep(min(5,max(0,deadline-time.monotonic())))


def replay_native(key):
    """Reaudit a finished saved job without creating a task or changing its files."""
    from .agent_review import _material
    from .native_app import failure
    from .native_runtime import collect,delivery_proof
    from .diagnostic_export import verify_zip
    folder=_job(key)
    state=_read(folder/'state.json')
    if state.get('state') not in FINAL:
        raise ContractError('NATIVE_REVIEW_INCOMPLETE')
    review=folder/'review'
    paths=sorted(review.glob('*.request.json'))
    config=load_private(PRIVATE)
    entries=[]
    for path in paths:
        request=_read(path)
        material=request.get('material_sha256')
        if path.name!=str(material)+'.request.json' or digest(encode(_material(request)).encode())!=material:
            raise ContractError('NATIVE_REVIEW_REQUEST_HASH')
        moments=[e['at_utc'] for e in state.get('lifecycle',())
            if e.get('material_sha256')==material and e.get('state') in {'REVIEW_FAILED','REVIEW_VERIFIED','REVIEW_REJECTED','REVIEW_TIMED_OUT'}]
        if not moments:
            entries.append({'material_sha256':material,'status':'NO_TERMINAL_REVIEW_TIME'})
            continue
        try:
            result=collect(request,config,as_of=moments[-1],directory=review,require_configured_model=False)
            if result is None:entry={'status':'NO_COMPLETED_CHILD_RECEIPT'}
            else:
                _,audit=result
                entry={'status':'VERIFIED_RECEIPT','verified_evidence_pages':audit.get('verified_evidence_pages'),
                    'reply_validation_status':audit['reply_validation_status'],'validated_rows':audit['validated_rows']}
                if audit.get('parent_delivery'):
                    entry.update(parent_delivery=audit['parent_delivery'],
                        arguments_sha256=audit['arguments_sha256'],packet_sha256=audit['packet_sha256'])
        except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
            entry={'status':'REJECTED','error':failure(error,'HISTORICAL_RECEIPT')}
        entries.append({'material_sha256':material,'ai_stage':request.get('stage'),**entry})
    artifact=state.get('artifact',{})
    artifact_result={'status':'ABSENT'}
    if artifact.get('sha256'):
        archive=under_work(folder/(key+'.zip'))
        raw=archive.read_bytes()
        if digest(raw)!=artifact['sha256']:raise ContractError('NATIVE_REPLY_PROVENANCE')
        verify_zip(raw)
        report_path=under_work(folder/'report.json')
        if not report_path.is_file() or report_path.stat().st_size>100*1024*1024:
            raise ContractError('NATIVE_REPLY_PROVENANCE')
        report=json.loads(report_path.read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as saved:
            if json.loads(saved.read('report.json'))!=report or report.get('job_id')!=key:
                raise ContractError('NATIVE_REPLY_PROVENANCE')
        comparison=report.get('native_control_comparison') or {}
        artifact_result={'status':'VERIFIED_SAVED_ARCHIVE_AND_REPORT','sha256':artifact['sha256'],
            'saved_reconciliation':{'accepted_current_advice':comparison.get('accepted_current_advice'),
                'hard_gates_changed':comparison.get('hard_gates_changed'),
                'scope':'HISTORICAL_REPORT_ONLY'}}
        if report.get('ai_research'):
            artifact_result['saved_ai_reconciliation']={'state':report['ai_research']['state'],
                'decisions':report['ai_research'].get('reconciliation',[])}
        try:
            proof=delivery_proof(state,config)
            artifact_result['delivery']='VERIFIED' if proof else 'NOT_OBSERVED'
        except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
            artifact_result['delivery_error']=failure(error,'HISTORICAL_DELIVERY')
    return {'mode':'HISTORICAL_READ_ONLY','job_id':key,'reviews':entries,'artifact':artifact_result,
        'market_requests':0,'model_requests':0,'trade_authorization':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','status','_worker','preflight','review-page','replay-native','reserve-review'])
    parser.add_argument('--request-id');parser.add_argument('--job-id');parser.add_argument('--include-review',action='store_true')
    parser.add_argument('--material');parser.add_argument('--packet-sha256');parser.add_argument('--page',type=int)
    parser.add_argument('--confirm');parser.add_argument('--end-frame')
    args=parser.parse_args()
    try:
        if args.action=='review-page':
            sys.stdout.buffer.write(review_page(args.job_id,args.material,args.packet_sha256,args.page).encode('utf-8'))
            return 0
        if args.action=='preflight':
            from .native_runtime import integration_preflight
            config=load_private(PRIVATE)
            from .settings import validate_config,load_config
            validate_config(load_config())
            result={**integration_preflight(config,as_of=now_utc()),'live_calls':0,
                'live_acceptance':'PARTIAL; AUTHENTIC_MODEL_EXECUTION_NOT_YET_VERIFIED'}
        elif args.action=='replay-native':result=replay_native(args.job_id)
        elif args.action=='start':result=start(args.request_id)
        elif args.action=='status':result=status(args.job_id,args.include_review)
        elif args.action=='reserve-review':result=reserve_review(args.job_id,args.material,args.confirm,args.end_frame)
        else:
            result=run_job(args.job_id)
            if result['state'] in {'COMPLETED','PARTIAL'}:result=watch_delivery(args.job_id)
        print(encode(result,compact='begin_frame' in result));return 0
    except (ContractError,OSError,ValueError,TypeError,KeyError,sqlite3.Error) as error:
        code=str(error) if isinstance(error,ContractError) else 'RUNNER_PRIVATE_DEPENDENCY_UNAVAILABLE'
        print(encode({'state':'REJECTED','reason':code,'trade_authorization':False}));return 2


if __name__=='__main__':raise SystemExit(main())
