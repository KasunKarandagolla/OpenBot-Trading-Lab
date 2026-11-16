"""Bounded multi-batch native review. Publishes tasks; never submits a model.

The main OpenBot agent observes each durable REVIEW_READY and dispatches its
exact arguments. Batches cover distinct cards; repeated polling is read only.
"""
import time
from .contracts import ContractError,digest,encode,utc
from .agent_review import make_request,exchange
from .native_identity import active_identity,assert_parent,load_private
from .native_codex import review_brief
from .settings import ROOT


def probe_captured_request(directory,source,*,native_identity,audit_config,clock,progress=None,wait_seconds=600):
    """One separately labeled transport check; never a current-market review."""
    import copy,json,os
    from .native_identity import under_work
    from .agent_review import _material,REQUEST,reasoning_registry
    from .native_app import wait_for_reply
    path=under_work(source)
    if path.stat().st_size>131072:raise ContractError('AGENT_INPUT_SIZE')
    original=json.loads(path.read_text(encoding='utf-8'))
    if (original.get('schema_version')!=REQUEST or not original.get('cards') or
            digest(encode(_material(original)).encode())!=original.get('material_sha256') or
            any(c.get('mode')!='LIVE' for c in original['cards'])):
        raise ContractError('NATIVE_REVIEW_REQUEST_HASH')
    if utc(original['as_of_utc'])>utc(clock()):raise ContractError('AGENT_EVIDENCE_FUTURE')
    request=copy.deepcopy(original)
    request.update(as_of_utc=clock(),model=native_identity['model'],native_identity=dict(native_identity),
        skill_sha256=digest((ROOT/'.agents/skills/market-research-review/SKILL.md').read_bytes()),
        analytical_registry=reasoning_registry(),
        transport_check={'scope':'PREVIOUSLY_CAPTURED_LIVE_EVIDENCE; AUTHENTIC_REPLAY_TRANSPORT_ONLY',
            'source_material_sha256':original['material_sha256'],'captured_at_utc':original['as_of_utc'],
            'current_market_interpretation':False})
    request['cards']=request['cards'][:1]
    request['omitted']=[{'card_id':c['card_id'],'reason':'ARCHIVED_TRANSPORT_SINGLE_CARD_SAMPLE'} for c in original['cards'][1:]]
    for card in request['cards']:
        card['mode']='AUTHENTIC_REPLAY'
        for fact in card['evidence'].values():fact['usable_as_of']=False
    request['material_sha256']=digest(encode(_material(request)).encode())
    review_brief(request)
    folder=under_work(directory);folder.mkdir(parents=True,exist_ok=True)
    target=folder/(request['material_sha256']+'.request.json')
    if target.exists():
        saved=json.loads(target.read_text(encoding='utf-8'))
        if _material(saved)!=_material(request):raise ContractError('NATIVE_REVIEW_REQUEST_COLLISION')
    else:
        with target.open('x',encoding='utf-8') as f:f.write(encode(request)+'\n');f.flush();os.fsync(f.fileno())
    receipt=wait_for_reply(folder,request['material_sha256'],audit_config,wait_seconds=wait_seconds,
        clock=clock,progress=progress,verified_identity=native_identity)
    result=exchange(folder,(),{},as_of=clock(),cached=True,previous={'material_sha256':request['material_sha256']},
        audit_config=audit_config,require_identity=True,native_identity=native_identity) if receipt['status']=='NATIVE_RECEIPT_COLLECTED' else {
            'status':'NATIVE_REVIEW_INCOMPLETE','reason':(receipt.get('terminal_error') or {}).get('code',receipt['status'])}
    return {**result,'native_collector':receipt,'observed_model_attempts':receipt['observed_model_attempts'],
        'scope':'ARCHIVED_NATIVE_TRANSPORT_PREFLIGHT','source_material_sha256':original['material_sha256'],
        'current_market_interpretation':False,'trade_authorization':False}


def plan_batches(cards,facts,*,as_of,context,reviews,max_cards,identity):
    """Greedily pack whole cards under all real input limits, no truncation."""
    skill=digest((ROOT/'.agents/skills/market-research-review/SKILL.md').read_bytes())
    groups=[];current=[];omitted=[]
    def fits(group):
        req=make_request(group,facts,as_of=as_of,context=context,reviews=reviews,
            max_cards=max_cards,skill_sha256=skill,native_identity=identity)
        if len(req['cards'])!=len(group):raise ContractError('AGENT_INPUT_SIZE')
        review_brief(req)
    for card in dict((c.id,c) for c in cards).values():
        try:fits([*current,card])
        except ContractError as error:
            if str(error)!='AGENT_INPUT_SIZE':raise
            if current:groups.append(current);current=[]
            try:fits([card])
            except ContractError as single:
                if str(single)!='AGENT_INPUT_SIZE':raise
                omitted.append({'card_id':card.id,'native_symbol':card.native_symbol,
                    'reason':'SINGLE_CARD_EXCEEDS_PROVIDER_INPUT_LIMIT; FULL_SKILL_RETAINED'})
                continue
        current.append(card)
    if current:groups.append(current)
    return groups,omitted


def review_batches(directory,cards,facts,*,clock,context,reviews,audit_config,
                   wait_seconds=600,max_cards=4,progress=None,native_identity=None):
    """One explicitly authorized sequence, one fresh immutable request per batch."""
    from .native_app import wait_for_reply,failure
    import sqlite3
    began=time.monotonic();batches=[];omitted=[];first_error=None
    private=load_private(audit_config)
    identity=dict(native_identity) if native_identity is not None else active_identity(private)
    assert_parent(identity,private)
    groups,omitted=plan_batches(cards,facts,as_of=clock(),context=context,reviews=reviews,
        max_cards=max_cards,identity=identity)
    if omitted:first_error={'stage':'BATCH_PLANNING','code':'AGENT_INPUT_SIZE'}
    for index,group in enumerate(groups,1):
        def notify(state,**fields):
            if progress:progress(state,batch_index=index,batch_count=len(groups),**fields)
        request_at=clock();preparing=time.monotonic()
        notify('REVIEW_REQUEST_PREPARED',card_ids=[c.id for c in group])
        current=exchange(directory,group,facts,as_of=request_at,context=context,reviews=reviews,
            max_cards=max_cards,audit_config=audit_config,require_identity=True,prepare_only=True,
            ordered_card_ids=[c.id for c in group],native_identity=identity)
        preparation_seconds=time.monotonic()-preparing
        if current['status']=='AWAITING_NATIVE_APP_RESPONSE':
            receipt=wait_for_reply(directory,current['material_sha256'],audit_config,
                wait_seconds=wait_seconds,clock=clock,progress=notify,verified_identity=identity)
            # Reaudit native storage on import. A dropped JSON file is not proof.
            if receipt['status']=='NATIVE_RECEIPT_COLLECTED':
                current=exchange(directory,(),{},as_of=clock(),previous=current,cached=True,
                    audit_config=audit_config,require_identity=True,native_identity=identity)
            else:
                current.update(status=receipt['status'],reason=(receipt.get('terminal_error') or {}).get('code',receipt['status']))
            current['native_collector']=receipt
        from pathlib import Path
        import json
        lease=Path(directory)/(current.get('material_sha256','')+'.dispatch.json')
        if lease.is_file():current['dispatch_receipt']=json.loads(lease.read_text(encoding='utf-8'))
        current.update(batch_index=index,card_ids=[c.id for c in group],request_generation_seconds=round(preparation_seconds,6))
        batches.append(current)
        first_error=first_error or current.get('native_collector',{}).get('first_error')
        if current['status']!='VALIDATED_ADVISORY_ONLY':
            first_error=first_error or {'stage':'REVIEW_IMPORT','code':current.get('reason',current['status'])}
        # Never manufacture a retry after an integrity/config/identity fault.
        if current.get('reason') in {'NATIVE_MODEL_SWITCHED','NATIVE_SESSION_MISMATCH','NATIVE_AGENT_MISMATCH',
                'NATIVE_AUDIT_CONFIG_INVALID','NATIVE_UNAUTHORIZED_TOOL','NATIVE_HANDOFF_UNATTESTED',
                'NATIVE_REPLY_PROVENANCE','NATIVE_READ_INCOMPLETE','NATIVE_PROVIDER_UNSUPPORTED',
                'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED','NATIVE_DISPATCH_RESERVED_TASK_MISSING',
                'NATIVE_TASK_NOT_SUBMITTED','NATIVE_REVIEW_TIMED_OUT','NATIVE_STORAGE_UNAVAILABLE',
                'NATIVE_STORAGE_TIMED_OUT','NATIVE_READER_PROCESS_UNAVAILABLE','NATIVE_REQUEST_STALE',
                'NATIVE_AUDIT_CONFIG_MISSING','AGENT_SKILL_HASH','NATIVE_REVIEW_REQUEST_HASH',
                'NATIVE_REVIEW_REQUEST_COLLISION','NATIVE_RECEIPT_FILE_UNAVAILABLE',
                'NATIVE_TASK_FILE_UNAVAILABLE','NATIVE_REQUEST_FILE_UNAVAILABLE'}:
            for remaining in groups[index:]:
                omitted.extend({'card_id':c.id,'native_symbol':c.native_symbol,
                    'reason':'REVIEW_HALTED_AFTER_TERMINAL_TRANSPORT_OR_INTEGRITY_FAILURE'} for c in remaining)
            break
    rows=[];reviewed=set();receipts=[]
    by_card={};attempts=0;created=[]
    for batch in batches:
        collector=batch.get('native_collector',{})
        attempts+=collector.get('observed_model_attempts',0)
        if batch.get('native_receipt'):receipts.append(batch['native_receipt'])
        if batch.get('request_created_at_utc'):created.append(batch['request_created_at_utc'])
        if batch['status']=='VALIDATED_ADVISORY_ONLY':
            for row in batch['reply']['interpretations']:
                rows.append(row);reviewed.add(row['card_id'])
                by_card[row['card_id']]={'material_sha256':batch['material_sha256'],
                    'request_created_at_utc':batch['request_created_at_utc'],
                    'validation_status':'VALIDATED_ADVISORY_ONLY'}
    wanted={c.id for c in cards};complete=reviewed==wanted and not omitted
    keys=[b.get('material_sha256') for b in batches]
    return {'status':'VALIDATED_ADVISORY_ONLY' if complete and wanted else
            'NATIVE_REVIEW_INCOMPLETE' if wanted else 'NO_CHANGED_NATIVE_REVIEW_CARDS',
        'accepted':len(reviewed),'cards':len(wanted),'card_ids':sorted(wanted),
        'reviewed_card_ids':sorted(reviewed),'not_reviewed':sorted(wanted-reviewed),'omitted':omitted,
        'unique_symbols':len({c.native_symbol for c in cards}),
        'unique_references':len({c.reference.id for c in cards}),
        'batch_count':len(batches),'batches':batches,'first_error':first_error,
        'observed_model_attempts':attempts,'calls':0,'audited_prior_model_requests':attempts,
        'material_sha256':digest(encode(keys).encode()),
        'request_created_at_utc':min(created,key=utc) if created else None,
        'card_review_provenance':by_card,
        'reply':{'interpretations':rows},'native_receipt':{'native_identity':identity,
            'model_requests':attempts,'batch_receipts':receipts},
        'native_collector':{'status':'NATIVE_RECEIPT_COLLECTED' if complete and wanted else 'NATIVE_REVIEW_INCOMPLETE',
            'observed_model_attempts':attempts,'first_error':first_error},
        'elapsed_seconds':round(time.monotonic()-began,6),'trade_authorization':False,
        'can_override_deterministic_admission':False}
