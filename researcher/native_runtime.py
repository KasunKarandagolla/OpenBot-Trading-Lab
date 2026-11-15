"""Provider dispatch for trusted, model-flexible native receipts. Never invokes."""
import json
from .contracts import ContractError, digest, utc
from .native_identity import assert_current, read_db, ref


def collect(request,config,*,as_of):
    from .native_host import delegated,call
    if delegated(config):return call(config,'collect',{'request':request,'as_of':as_of})
    from .agent_review import parse_reply,validate_reply,REJECTION_CODES
    identity=request.get('native_identity')
    if not isinstance(identity,dict):raise ContractError('NATIVE_IDENTITY_UNAVAILABLE')
    assert_current(identity,config)
    if not 0<=(utc(as_of)-utc(request['as_of_utc'])).total_seconds()<=600:
        raise ContractError('NATIVE_REQUEST_STALE')
    if identity['provider']=='opencode':
        from .native_app import collect as compatibility
        from pathlib import Path
        target=Path(config['agent_workspace'])/'research-review-6c'/(request['material_sha256']+'.json')
        return compatibility(request,config,target,as_of=as_of)
    if identity['provider']!='codex':raise ContractError('NATIVE_PROVIDER_UNSUPPORTED')
    from .native_codex import review_brief,attest,attest_handoff
    marker='OPENBOT-RESEARCH-'+request['material_sha256'];brief=review_brief(request)
    with read_db(config['openbot_db']) as db:
        # An agent-originated task of the very same configured existing agent.
        rows=db.execute('''SELECT thread_id FROM projection_agent_threads
          WHERE agent_id=? AND origin='agent' AND title=? AND created_at>=?''',
          (identity['agent_id'],marker,request['as_of_utc'])).fetchall()
        if not rows:return None
        if len(rows)!=1:raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        thread=rows[0][0]
        inputs=db.execute('''SELECT message_json FROM projection_thread_messages
          WHERE thread_id=? AND author='agent' AND created_at>=? ORDER BY ordinal''',
          (thread,request['as_of_utc'])).fetchall()
        if not inputs or json.loads(inputs[0][0]).get('text')!=brief:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        finals=db.execute('''SELECT m.message_json,t.turn_id,t.started_at,t.completed_at,
           p.external_session_id,p.model,p.provider
          FROM projection_thread_messages m JOIN projection_turns t ON t.turn_id=m.turn_id
          JOIN projection_provider_sessions p ON p.id=t.provider_session_id
          WHERE m.thread_id=? AND m.author='assistant' AND m.item_type='final_answer'
          AND m.status='completed' AND t.status='completed' AND m.created_at>=?
          ORDER BY m.ordinal''',(thread,request['as_of_utc'])).fetchall()
        if not finals:return None
        if len(finals)!=1:raise ContractError('NATIVE_REVIEW_INCOMPLETE')
    message,turn,start,end,session,model,provider=finals[0]
    if provider!=identity['provider'] or model!=identity['model']:raise ContractError('NATIVE_MODEL_SWITCHED')
    if not utc(request['as_of_utc'])<=utc(start)<=utc(end)<=utc(as_of):raise ContractError('AGENT_EVIDENCE_FUTURE')
    raw=json.loads(message).get('text')
    if not isinstance(raw,str) or len(raw.encode())>32768:raise ContractError('AGENT_REPLY_SIZE')
    attest_handoff(config,identity,request,as_of=as_of)
    proof=attest(config,session,turn,model=model,workspace=config['agent_workspace'],start=start,end=end,
        expected_input=brief,expected_reply=raw,backend=identity['provider_backend'])
    assert_current(identity,config)
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
        'submission_transport':'EXISTING_AGENT_START_TASK; EXACT_PROVIDER_ATTESTED_INLINE_INPUT',
        'authority':'ADVISORY_ONLY; NO_HOST_ISOLATION_CLAIM',**proof,**validation}
    return raw,audit
