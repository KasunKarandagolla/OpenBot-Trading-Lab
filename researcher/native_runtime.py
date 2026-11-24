"""Provider dispatch for trusted, model-flexible native receipts. Never invokes."""
import json
from .contracts import ContractError, digest, utc
from .native_identity import NativeEvidenceError, assert_parent, checked_path, local_path, read_db, ref


def integration_preflight(config,*,as_of):
    """Read the actual current adapter and installed skills before market I/O."""
    from .native_host import delegated,call
    if delegated(config):return call(config,'integration_preflight',{'as_of':as_of})
    from .native_identity import active_identity,compact_adapter_supported,parent_binding
    from .native_codex import attest_turn_model,SCHEMA
    from .native_handoff import wsl_root
    from .settings import ROOT
    identity=active_identity(config);binding=parent_binding(identity,config,require_configured_model=True)
    if not compact_adapter_supported(identity):raise ContractError('NATIVE_PROVIDER_UNSUPPORTED')
    attest_turn_model(config,binding['external'],binding['turn'],identity['model'],config['agent_workspace'],
        start=utc(binding['started_at']),end=utc(as_of),backend=identity['provider_backend'],
        missing='NATIVE_NOT_INVOKED')
    root=wsl_root()
    hashes={}
    for name,source in [('market-research-review',ROOT/'.agents/skills/market-research-review/SKILL.md'),
            ('openbot-market-research',ROOT/'integration/openbot-market-research/SKILL.md')]:
        expected=checked_path(source,error='AGENT_SKILL_HASH').read_text(
            encoding='utf-8').replace('@@RESEARCH_ROOT@@',root).encode()
        installed=[checked_path(local_path(config['agent_workspace'])/prefix/'skills'/name/'SKILL.md',
            error='AGENT_SKILL_HASH')
            for prefix in ('.agents','.claude')]
        found=[p for p in installed if p.is_file()]
        if not found or any(p.read_bytes()!=expected for p in found):
            raise ContractError('AGENT_SKILL_HASH')
        hashes[name]=digest(expected)
    return {'status':'NATIVE_READER_AND_INSTALLED_SKILLS_VERIFIED','identity':identity,
        'provider_schema':SCHEMA,'skill_sha256':hashes,'market_requests':0,'model_requests':0,
        'native_execution_verified':False,'trade_authorization':False}


def attest_smoke_discovery(identity,config,*,as_of):
    """Bind both native tool schemas to successful discovery in the parent turn.

    Every failure names the first pipeline step that did not complete. Records
    from an earlier turn, including a setup turn, never satisfy this turn.
    """
    from datetime import timedelta
    from .native_host import delegated,call
    if delegated(config):
        return call(config,'attest_smoke_discovery',{'identity':identity,'as_of':as_of})
    from .native_identity import parent_binding
    from .native_codex import turn_records,check_turn_model
    binding=parent_binding(identity,config,require_configured_model=True,as_of=as_of)
    session,turn=binding['external'],binding['turn']
    required={'openbot.start_task':{'title','brief'},'openbot.attach_files_to_response':{'paths'}}
    pending={};completed={};delivered=set();attempted=set();parsed_tools=set()
    call_rows=calls=completion_rows=matched=parsed=0;context=False
    for row in turn_records(config,session,turn,config['agent_workspace'],
            start=utc(binding['started_at'])-timedelta(seconds=1),end=utc(as_of),backend=identity['provider_backend']):
        payload=row['payload']
        context=check_turn_model(row,session,turn,identity['model'],config['agent_workspace'],context)
        if not context:continue
        if (row['type']=='response_item' and payload.get('type')=='function_call'
                and payload.get('namespace')=='openbot' and payload.get('name')=='tool_describe'):
            call_rows+=1
            try:arguments=json.loads(payload.get('arguments',''))
            except (ValueError,TypeError):continue
            if isinstance(arguments,dict) and set(arguments)=={'names'} and isinstance(arguments['names'],list):
                call_id=payload.get('call_id')
                if isinstance(call_id,str) and call_id and call_id not in pending:
                    pending[call_id]=arguments;calls+=1
        elif row['type']=='event_msg' and payload.get('type')=='item_completed':
            item=payload.get('item')
            if not isinstance(item,dict):continue
            if (item.get('type')!='DynamicToolCall' or item.get('namespace')!='openbot'
                    or item.get('tool')!='tool_describe'):continue
            completion_rows+=1
            call_id=item.get('id')
            if not isinstance(call_id,str):continue
            if (payload.get('turn_id')!=turn or payload.get('thread_id')!=session
                    or item.get('status')!='completed' or item.get('success') is not True
                    or call_id not in pending or item.get('arguments')!=pending.pop(call_id)):
                continue
            matched+=1
            try:
                parts=item['content_items']
                if len(parts)!=1 or parts[0].get('type')!='inputText':continue
                result=json.loads(parts[0]['text'])
                discovered=set()
                for tool in result['tools']:
                    name=tool.get('name');schema=tool.get('inputSchema',{})
                    if (name in required and name in item['arguments']['names']
                            and schema.get('type')=='object'
                            and schema.get('additionalProperties') is False
                            and set(schema.get('required',()))==required[name]
                            and required[name]<=set(schema.get('properties',{}))
                            and all(schema['properties'][key].get('type')==('array' if key=='paths' else 'string')
                                for key in required[name])):
                        discovered.add(name)
                completed[call_id]=(parts[0]['text'],discovered)
                parsed_tools.update(discovered);parsed+=1
            except (ValueError,KeyError,TypeError,AttributeError):
                continue
        elif row['type']=='response_item' and payload.get('type')=='function_call_output':
            call_id=payload.get('call_id')
            if isinstance(call_id,str) and call_id in completed:
                output,discovered=completed.pop(call_id)
                attempted.update(discovered)
                if payload.get('output')==output:delivered.update(discovered)
    if delivered!=set(required):
        if not call_rows:check='NO_CALL'
        elif not calls:check='INVALID_CALL'
        elif not completion_rows:check='NO_COMPLETION'
        elif not matched:check='COMPLETION_MISMATCH'
        elif not parsed:check='CONTENT_MISMATCH'
        elif not set(required)<=parsed_tools:check='SCHEMA_MISMATCH'
        elif not set(required)<=attempted:check='NO_OUTPUT'
        else:check='OUTPUT_MISMATCH'
        raise NativeEvidenceError('NATIVE_TOOL_DISCOVERY_UNVERIFIED','TOOL_DISCOVERY',check)
    return {'status':'VERIFIED_CURRENT_PARENT_TOOL_DISCOVERY','tools':sorted(delivered)}


def collect(request,config,*,as_of,directory=None,timeout_seconds=30,require_configured_model=False):
    """Read the original receipt. Active collection also pins configuration."""
    from .native_host import delegated,call
    if delegated(config):return call(config,'collect',{'request':request,'as_of':as_of,
        'directory':str(directory) if directory is not None else None,
        'require_configured_model':require_configured_model},timeout_seconds=timeout_seconds)
    from .agent_review import parse_reply,validate_reply,REJECTION_CODES
    identity=request.get('native_identity')
    if not isinstance(identity,dict):raise ContractError('NATIVE_IDENTITY_UNAVAILABLE')
    assert_parent(identity,config,require_configured_model=require_configured_model,as_of=as_of)
    if request.get('model')!=identity['model']:raise ContractError('NATIVE_REVIEW_REQUEST_HASH')
    if not 0<=(utc(as_of)-utc(request['as_of_utc'])).total_seconds()<=600:
        raise ContractError('NATIVE_REQUEST_STALE')
    if identity['provider']=='opencode':
        # The historical OpenCode collector proves only its original native
        # skill/file-read contract. It cannot attest a parent task call or a
        # compact page transport. Never reinterpret a new AI-core request as
        # that older protocol, even when the schemas happen to look alike.
        if request.get('input_transport'):
            raise ContractError('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
        from .native_app import collect as compatibility
        target=local_path(config['agent_workspace'])/'research-review-6c'/(request['material_sha256']+'.json')
        return compatibility(request,config,target,as_of=as_of)
    if identity['provider']!='codex':raise ContractError('NATIVE_PROVIDER_UNSUPPORTED')
    from .native_codex import attest,attest_handoff,observe_submission
    from .native_handoff import (runner_review,load_dispatch,packet,page_command_fingerprint,
        verify_submission_window,FRESH_SECONDS,BOUNDED_WAIT_PAGE_COMMANDS,CONFIRMED_PAGES,COMPACT_PAGES)
    from .native_identity import under_work
    directory=under_work(directory) if directory is not None else None
    reserved=runner_review(directory)
    inline=bool(request.get('input_transport'))
    if inline and not reserved:
        raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    if reserved and (utc(as_of)-utc(request['as_of_utc'])).total_seconds()>=FRESH_SECONDS:
        raise ContractError('NATIVE_REQUEST_STALE')
    args,_,_=packet(request,directory);marker=args['title'];brief=args['brief']
    with read_db(config['openbot_db']) as db:
        # An agent-originated task of the very same configured existing agent.
        rows=db.execute('''SELECT thread_id,created_at FROM projection_agent_threads
          WHERE agent_id=? AND origin='agent' AND title=? AND created_at>=?''',
          (identity['agent_id'],marker,request['as_of_utc'])).fetchall()
        if not rows:return None
        if len(rows)!=1:raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        thread,created=rows[0]
        if ref(thread)==identity['thread_ref']:raise ContractError('NATIVE_SESSION_MISMATCH')
        inputs=db.execute('''SELECT turn_id,message_json FROM projection_thread_messages
          WHERE thread_id=? AND author='agent' AND created_at>=? ORDER BY ordinal''',
          (thread,request['as_of_utc'])).fetchall()
        if not inputs and reserved:return None
        if (not inputs or not isinstance(inputs[0][0],str) or not inputs[0][0]
                or json.loads(inputs[0][1]).get('text')!=brief):
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        input_turn=inputs[0][0]
        # Only the turn that received the immutable brief can answer it.
        finals=db.execute('''SELECT m.message_json,t.turn_id,t.started_at,t.completed_at,
           p.external_session_id,p.model,p.provider,t.thread_id,p.thread_id
          FROM projection_thread_messages m JOIN projection_turns t ON t.turn_id=m.turn_id
          JOIN projection_provider_sessions p ON p.id=t.provider_session_id
          WHERE m.thread_id=? AND m.turn_id=?
          AND m.author='assistant' AND m.item_type='final_answer'
          AND m.status='completed' AND t.status='completed' AND m.created_at>=?
          ORDER BY m.ordinal''',(thread,input_turn,request['as_of_utc'])).fetchall()
        if not finals:
            states=db.execute('SELECT status FROM projection_turns WHERE thread_id=? AND turn_id=?',(thread,input_turn)).fetchall()
            if any(s[0] in {'failed','cancelled','interrupted'} for s in states):
                raise ContractError('NATIVE_TASK_FAILED')
            return None
        if len(finals)!=1:raise ContractError('NATIVE_REVIEW_INCOMPLETE')
    message,turn,start,end,session,session_model,provider,turn_thread,session_thread=finals[0]
    if (turn_thread!=thread or session_thread!=thread or ref(session)==identity['external_session_ref']
            or ref(turn)==identity['turn_ref']):raise ContractError('NATIVE_SESSION_MISMATCH')
    if provider!=identity['provider']:
        raise NativeEvidenceError('NATIVE_MODEL_SWITCHED','IDENTITY','APP_CHILD_PROVIDER')
    model=identity['model']
    if require_configured_model and session_model!=model:
        raise NativeEvidenceError('NATIVE_MODEL_SWITCHED','IDENTITY','APP_CHILD_MODEL')
    if not utc(request['as_of_utc'])<=utc(created)<=utc(start)<=utc(end):
        raise ContractError('NATIVE_CHILD_CLOCK_INVALID' if inline else 'AGENT_EVIDENCE_FUTURE')
    if utc(end)>utc(as_of):
        # An app projection can advance while the WSL/Windows bridge reads it.
        # The next observation must prove the same timestamps against a fresh
        # host anchor. Time limits and the immutable order still apply.
        raise ContractError('NATIVE_PROJECTION_AFTER_SNAPSHOT' if inline else 'AGENT_EVIDENCE_FUTURE')
    raw=json.loads(message).get('text')
    if not isinstance(raw,str) or len(raw.encode())>32768:raise ContractError('AGENT_REPLY_SIZE')
    evidence=None
    if reserved:
        args,fingerprint,pages,ticket=load_dispatch(directory,request,as_of=as_of)
        submitted=observe_submission(config,identity,request['as_of_utc'],args,as_of=as_of,
            reserved_at=ticket['reserved_at_utc'],require_configured_model=require_configured_model)
        verify_submission_window(submitted,ticket)
        # In OpenBot 0.71.0 newly created task IDs are their thread IDs.
        if (submitted['submission_state']!='ACKNOWLEDGED' or submitted['acknowledged_task_ref']!=ref(thread)
                or not utc(ticket['reserved_at_utc'])<=utc(submitted['attempted_at_utc'])<=utc(submitted['responded_at_utc'])
                or not utc(ticket['reserved_at_utc'])<=utc(created)<=utc(submitted['responded_at_utc'])):
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        if pages:
            evidence=(directory,request['material_sha256'],page_command_fingerprint(request,fingerprint),pages,
                request.get('page_command_policy')==BOUNDED_WAIT_PAGE_COMMANDS or request.get('input_transport') in {CONFIRMED_PAGES,COMPACT_PAGES})
    else:attest_handoff(config,identity,request,as_of=as_of,require_configured_model=require_configured_model)
    proof=attest(config,session,turn,model=model,workspace=config['agent_workspace'],start=start,end=end,
        expected_input=brief,expected_reply=raw,backend=identity['provider_backend'],evidence=evidence,
        require_thread_model=require_configured_model)
    assert_parent(identity,config,require_configured_model=require_configured_model,as_of=as_of)
    try:
        validated=validate_reply(parse_reply(raw),request)
        validation={'reply_validation_status':'VALIDATED','validated_rows':validated['accepted']}
    except ContractError as e:
        if str(e) not in REJECTION_CODES:raise
        validation={'reply_validation_status':'REJECTED','reply_rejection_reason':str(e),'validated_rows':0}
    audit={'schema_version':'openbot.native-review.audit.v1','audit_source':'OPENBOT_APP_SCOPED_READ_ONLY_AUDIT',
        'agent_name':identity['agent_name'],'model':model,'provider':provider,'agent_id':identity['agent_id'],
        'native_identity':identity,'skill_sha256':request['skill_sha256'],'material_sha256':request['material_sha256'],
        'reply_sha256':digest(raw.encode()),'native_invocation_verified':True,'native_app_turns':1,
        'native_started_at_utc':start,'native_completed_at_utc':end,'audited_at_utc':as_of,
        'submission_transport':'EXISTING_AGENT_START_TASK; EXACT_PROVIDER_ATTESTED_'+('PAGED_INPUT' if evidence is not None else 'INLINE_INPUT'),
        'authority':'ADVISORY_ONLY; NO_HOST_ISOLATION_CLAIM',**proof,**validation}
    if reserved:audit.update(submission_attempts=submitted['submission_attempts'],task_ref=ref(thread),
        arguments_sha256=ticket['arguments_sha256'],packet_sha256=fingerprint,verified_evidence_pages=len(pages))
    if request.get('input_transport')==CONFIRMED_PAGES:
        audit.update(parent_delivery=ticket['parent_delivery'], argument_integrity=ticket['argument_integrity'],
            preview_sha256=ticket['preview_sha256'])
    elif request.get('input_transport')==COMPACT_PAGES:
        audit.update(parent_delivery='EXACT_TASK_ARGUMENTS_IN_PROVIDER_RECORD')
    return raw,audit


def _attached_path_matches(arguments, target):
    from pathlib import PurePosixPath, PureWindowsPath
    if not isinstance(arguments,dict) or set(arguments)!={'paths'}:
        return False
    paths=arguments['paths']
    if not isinstance(paths,list) or len(paths)!=1 or not isinstance(paths[0],str):
        return False
    path=paths[0]
    if not (PurePosixPath(path).is_absolute() or PureWindowsPath(path).is_absolute()):
        return False
    try:
        return checked_path(path,root=target.parent,error='NATIVE_REPLY_PROVENANCE')==checked_path(target,error='NATIVE_REPLY_PROVENANCE')
    except ContractError:
        return False


def delivery_proof(state,config):
    """Observe this job's real parent attachment and final; no send operation.

    A completed worker or an attachment filename in prose is insufficient.
    This can be observed by a later status read after OpenBot saves the final.
    """
    from .native_host import delegated,call
    if delegated(config):return call(config,'delivery_proof',{'state':state})
    from .native_identity import parent_binding
    from .native_codex import turn_records,context_matches
    from .contracts import now_utc
    from datetime import timedelta
    identity=state['native_identity'];binding=parent_binding(identity,config,require_configured_model=False,as_of=now_utc())
    artifact=state.get('artifact',{})
    if not artifact:return None
    target=local_path(artifact['attachment_path'])
    expected=local_path(config['agent_workspace'])/'market-research-results'/(state['job_id']+'.zip')
    if target!=expected:
        raise ContractError('NATIVE_REPLY_PROVENANCE')
    raw_zip=checked_path(target,error='NATIVE_REPLY_PROVENANCE').read_bytes()
    if digest(raw_zip)!=artifact['sha256']:raise ContractError('NATIVE_REPLY_PROVENANCE')
    from .diagnostic_export import verify_zip
    verify_zip(raw_zip)
    if binding['status']!='completed' or not binding['completed_at']:return None
    turn,start,end,session,thread=(binding[k] for k in ('turn','started_at','completed_at','external','thread'))
    with read_db(config['openbot_db']) as db:
        finals=db.execute('''SELECT message_json FROM projection_thread_messages
          WHERE thread_id=? AND turn_id=? AND author='assistant' AND item_type='final_answer'
          AND status='completed' ''',(thread,turn)).fetchall()
    if len(finals)!=1:return None
    raw=json.loads(finals[0][0]).get('text','')
    if state['job_id'] not in raw or artifact['sha256'] not in raw:return None
    attached=False;context=False;final=False
    for row in turn_records(config,session,turn,config['agent_workspace'],start=utc(start)-timedelta(seconds=1),
            end=utc(end)+timedelta(seconds=1),backend=identity.get('provider_backend')):
        p=row['payload']
        if row['type']=='turn_context':
            context_matches(p,turn,identity['model'],config['agent_workspace']);context=True
        if row['type']!='event_msg' or p.get('type')!='item_completed':continue
        if p.get('turn_id')!=turn or p.get('thread_id')!=session:raise ContractError('NATIVE_SESSION_MISMATCH')
        item=p.get('item',{});args=item.get('arguments',{})
        if (context and item.get('type')=='DynamicToolCall' and item.get('tool')=='tool_call'
                and item.get('success') is True and item.get('status')=='completed'
                and args.get('name')=='openbot.attach_files_to_response'
                and _attached_path_matches(args.get('arguments'),target)):
            attached=True
        if (attached and item.get('type')=='AgentMessage' and item.get('phase')=='final_answer'
                and __import__('researcher.native_codex',fromlist=['_text'])._text(item.get('content'))==raw):final=True
    if not (attached and final):return None
    return {'status':'VERIFIED_OPENBOT_FINAL_DELIVERY','job_id':state['job_id'],
        'zip_sha256':artifact['sha256'],'parent_turn_ref':identity['turn_ref'],
        'completed_at_utc':end,'trade_authorization':False}
