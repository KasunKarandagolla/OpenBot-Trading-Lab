"""Versioned, one-way read-only export and disabled consultant extension."""
from dataclasses import asdict
from .contracts import ContractError,digest,encode

ALLOWED_QUESTIONS=frozenset({'SAME_REFERENCE_RIVAL','FIRST_OBSTACLE','SOURCE_GAP','NEXT_CLOSED_RESPONSE'})


def validate_consultation(reply,known_ids):
    if (not isinstance(reply,dict) or set(reply)!={'evidence_ids','next_question'}
            or reply['next_question'] not in ALLOWED_QUESTIONS or not isinstance(reply['evidence_ids'],list)
            or not reply['evidence_ids'] or not set(reply['evidence_ids'])<=set(known_ids)):
        raise ContractError('HYPOTHESIS_UNKNOWN_EVIDENCE')
    return reply


def consult_changed_cards(cards,*,provider=None):
    # A paid runtime, owner-approved model or subagent does not follow from an
    # installed SKILL.md. Keep the extension disabled until separately qualified.
    if provider is not None:raise ContractError('RESEARCH_TOOL_NOT_ALLOWED')
    return {'status':'LLM_DISABLED_NO_APPROVED_PROVIDER','calls':0,'changed_cards':len(cards),
        'allowed_query_menu':sorted(ALLOWED_QUESTIONS),'deterministic_only_ablation':'IDENTICAL; ZERO_MODEL_CALLS'}


def make_export(report,cards,facts,references):
    packets=[];wanted={r['card_id'] for r in report['shortlist']}
    if len(wanted)>5:raise ContractError('MAX_SHORTLIST_FIVE')
    for c in cards:
        if c.id not in wanted:continue
        ids=set(c.evidence_ids)|set(c.reference.source_ids)|{i for e in c.events for i in e['source_ids']}
        review=next(r for r in report['shortlist'] if r['card_id']==c.id)
        ids.update(review['room'].get('evidence_ids',()))
        if not ids<=set(facts):raise ContractError('HYPOTHESIS_UNKNOWN_EVIDENCE')
        packets.append({'card':asdict(c),'reference_id':c.reference.id,'review':review,
            'evidence':{i:asdict(facts[i]) for i in sorted(ids)},
            'obstacles':[asdict(r) for r in references if r.id==review['room'].get('first_obstacle_id')],
            'analyst_may_decline':True,'decline_side_effects':[]})
    body={'schema_version':'openbot.research-handoff.v1','direction':'RESEARCHER_TO_ANALYST_EXPORT_ONLY',
        'mode':report['mode'],'created_at':report['completed_at_utc'],'research_handoffs':packets,
        'trade_authorization':False,'order_authority':False,'execution_connection':None,
        'capabilities':report.get('coverage',{}),'method_registry':report.get('method_coverage',{}),
        'decline_semantics':'Consumer may reject any hypothesis; no callback, state write or execution operation'}
    return {**body,'payload_sha256':digest(encode(body).encode())}


def replay_export(export,*,as_of):
    """Pure local review replay, with no provider/database/consumer callback."""
    from decimal import Decimal as D
    from .contracts import Instrument
    from .research import Fact
    from .structures import Reference
    from .candidate_review import StructureCard,Hypothesis,review_card
    body={k:v for k,v in export.items() if k!='payload_sha256'}
    if (export.get('schema_version')!='openbot.research-handoff.v1' or export.get('order_authority') is not False
            or export.get('trade_authorization') is not False or export.get('execution_connection') is not None
            or digest(encode(body).encode())!=export.get('payload_sha256')
            or not isinstance(export.get('research_handoffs'),list) or len(export['research_handoffs'])>5):
        raise ContractError('STRUCTURE_CARD_CONTRACT')
    def reference(raw):
        raw={**raw}
        for k in ('lo','hi','atr','tick'):raw[k]=D(str(raw[k]))
        raw['source_ids']=tuple(raw['source_ids'])
        return Reference(**raw)
    result=[]
    for packet in export['research_handoffs']:
        raw={**packet['card']};raw['reference']=reference(raw['reference'])
        raw['hypotheses']=tuple(Hypothesis(**h) for h in raw['hypotheses'])
        card=StructureCard(**raw);facts={}
        for key,f in packet['evidence'].items():
            facts[key]=Fact(**{**f,'instrument':Instrument(**f['instrument'])})
            if facts[key].id!=key:raise ContractError('HYPOTHESIS_UNKNOWN_EVIDENCE')
        result.append(review_card(card,facts,[reference(r) for r in packet['obstacles']],as_of=as_of))
    return result
