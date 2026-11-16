"""Source-cited causal research cards, room/economics and transparent admission.

No entries, stops, targets, position sizing, confidence probabilities or orders.
The typed engine can review qualified facts; current recorded trials stay gated.
"""
from dataclasses import dataclass, asdict, replace
from decimal import Decimal as D
from functools import lru_cache,cached_property
from .contracts import ContractError, utc, number
from .research import cited, fact_id
from .structures import Reference


@lru_cache(maxsize=1)
def _method_contracts():
    from .settings import load_config
    return {m['id']:m for m in load_config()['methods']}

SEQUENCES={
    'F2':('PRESSURE','CLOSE_OUTSIDE','OUTSIDE_HOLD'),
    'F4':('WICK_EXCURSION','RECLAIM','OPPOSING_INITIATIVE'),
    'F5':('WICK_EXCURSION','RECLAIM','OPPOSING_ATTEMPT','REBREAK_SAME_REFERENCE','OUTSIDE_HOLD'),
}
STAGE_REQUIREMENTS={
    'PREMATURE':('APPLICABLE_METHOD',), 'EARLY':('PREKNOWN_REFERENCE','INITIATING_EVIDENCE'),
    'DEVELOPING':('PREKNOWN_REFERENCE','ORDERED_PARTIAL_SEQUENCE'),
    'APPROACHING_DECISION':('PREKNOWN_REFERENCE','ORDERED_PARTIAL_SEQUENCE','REFERENCE_SIGNIFICANCE','DECISION_PROXIMITY'),
    'READY_FOR_DEEP':('QUALIFIED_CURRENT_SEQUENCE','REFERENCE_SIGNIFICANCE','ROOM','ECONOMICS','HORIZON'),
    'FAST_WITH_ROOM':('QUALIFIED_CURRENT_SEQUENCE','REFERENCE_SIGNIFICANCE','ROOM','ECONOMICS','HORIZON','RECENT_EVENT','NEAR_DECISION'),
    'CONDITIONAL_FOR_DEEP':('QUALIFIED_CURRENT_SEQUENCE','REFERENCE_SIGNIFICANCE','ROOM','DECLARED_ECONOMIC_SCENARIO','HORIZON'),
    'LATE':('KNOWN_FIRST_OBSTACLE_CONSUMED',), 'INVALIDATED':('CAUSAL_CONTRADICTING_EVENT',),
    'UNKNOWN':('MISSING_OR_STALE_NECESSARY_EVIDENCE',),
}


@dataclass(frozen=True)
class Hypothesis:
    family: str
    direction: str
    verdict: str
    supporting_ids: tuple[str,...]
    contradicting_ids: tuple[str,...]
    next_discriminator: str


@dataclass(frozen=True)
class StructureCard:
    native_symbol: str
    venue: str
    timeframe: str
    reference: Reference
    window_start: str
    cutoff: str
    primary_family: str
    family_ids: tuple[str,...]
    method_ids: tuple[str,...]
    origins: tuple[str,...]
    events: tuple[dict,...]
    hypotheses: tuple[Hypothesis,...]
    evidence_ids: tuple[str,...]
    qualification: str
    mode: str
    trigger_to_investigate: str
    invalidating_evidence: str
    exposure_cluster: str = 'UNKNOWN'
    formation: dict | None = None

    def __post_init__(self):
        r=self.reference
        if (self.native_symbol!=r.native_symbol or self.timeframe!=r.timeframe or self.venue!='BINANCE_USDM'
                or utc(r.known_at)>utc(self.window_start) or utc(self.window_start)>utc(self.cutoff)
                or self.primary_family not in self.family_ids or not self.evidence_ids
                or not self.origins or not self.trigger_to_investigate or not self.invalidating_evidence
                or self.qualification not in {'QUALIFIED','TRIAL','UNQUALIFIED'}
                or self.mode not in {'LIVE','AUTHENTIC_REPLAY','SYNTHETIC'}
                or not set(self.family_ids)<={f'F{i}' for i in range(1,10)}
                or not set(self.method_ids)<={f'M{i:02d}' for i in range(1,32)} or 'M15' in self.method_ids):
            raise ContractError('STRUCTURE_CARD_CONTRACT')
        hs={h.family:h for h in self.hypotheses}
        if ('NULL' not in hs or not any(h.direction!=hs[self.primary_family].direction
                and h.family!='NULL' for h in self.hypotheses)):
            raise ContractError('NULL_AND_OPPOSING_RIVAL_REQUIRED')
        times=[];ids=[]
        for e in self.events:
            defining=(self.formation is not None and utc(e['known_at'])==utc(r.known_at)
                and bool(set(e['source_ids']) & set(r.source_ids)))
            if (e['reference_id']!=r.id or utc(e['occurred_from'])<utc(r.known_at) and not defining
                    or not utc(e['occurred_from'])<utc(e['occurred_to'])<=utc(e['known_at'])<=utc(e['available_at'])
                    or utc(e['known_at'])>utc(self.cutoff) or not e['source_ids']):
                raise ContractError('EVENT_CAUSAL_TIME')
            times.append(utc(e['known_at']));ids.append(e['id'])
        if times!=sorted(times) or len(ids)!=len(set(ids)):
            raise ContractError('LEDGER_NONCHRONOLOGICAL_EVENT')
        for h in self.hypotheses:
            if not set(h.supporting_ids+h.contradicting_ids)<=set(ids):
                raise ContractError('HYPOTHESIS_UNKNOWN_EVIDENCE')

    @cached_property
    def id(self):
        parts=(self.native_symbol,self.reference.id,self.window_start,self.cutoff)
        return fact_id(*parts,self.primary_family) if self.formation else fact_id(*parts)

    @property
    def material_hash(self): return fact_id(self)


def boundary_card(reference, result, *, cutoff, evidence_ids, primary_family,
                  origins=('C_TARGETED_STRUCTURE_TRIAL',), qualification='TRIAL', mode='AUTHENTIC_REPLAY'):
    events=tuple(result['events'])
    side='BULLISH' if reference.direction==1 else 'BEARISH'
    opposite='BEARISH' if side=='BULLISH' else 'BULLISH'
    hypotheses=tuple(Hypothesis(h['family'],opposite if h['family'] in {'F4','F6'} else
        'UNDETERMINED' if h['family']=='NULL' else side,h['current_formation_verdict'],
        tuple(h['supporting_ids']),tuple(h['contradicting_ids']),h['next_discriminator'])
        for h in result['hypotheses'])
    return StructureCard(reference.native_symbol,'BINANCE_USDM',reference.timeframe,reference,
        events[0]['occurred_from'] if events else reference.known_at,cutoff,primary_family,
        tuple(h.family for h in hypotheses if h.family!='NULL'),('M03','M05'),origins,events,hypotheses,
        tuple(evidence_ids),qualification,mode,'Next closed response to the same frozen reference',
        'Accepted breach/reclaim that contradicts the primary same-reference sequence')


def union_cards(cards):
    """Deduplicate exact contract/reference/event window, retaining all initiators."""
    merged={}
    for c in cards:
        if c.id not in merged:merged[c.id]=c;continue
        old=merged[c.id]
        if old.reference!=c.reference or old.events!=c.events or old.mode!=c.mode:
            raise ContractError('CONFLICTING_STRUCTURE_DUPLICATE')
        hs={h.family:h for h in old.hypotheses}
        for h in c.hypotheses:
            if h.family in hs and hs[h.family]!=h:raise ContractError('CONFLICTING_STRUCTURE_DUPLICATE')
            hs[h.family]=h
        merged[c.id]=replace(old,family_ids=tuple(sorted(set(old.family_ids+c.family_ids))),
            method_ids=tuple(sorted(set(old.method_ids+c.method_ids))),
            origins=tuple(sorted(set(old.origins+c.origins))),evidence_ids=tuple(sorted(set(old.evidence_ids+c.evidence_ids))),
            hypotheses=tuple(hs.values()),qualification=min((old.qualification,c.qualification),
                key=lambda x:{'UNQUALIFIED':0,'TRIAL':1,'QUALIFIED':2}[x]))
    return tuple(merged[k] for k in sorted(merged))


FAMILY_METHODS={
    'F1':('M01','M02','M03','M06','M07','M08','M10','M11'),
    'F2':('M01','M02','M03','M04','M06','M08','M13','M21'),
    'F3':('M03','M08','M19','M21','M30'), 'F4':('M02','M04','M05','M09','M12','M13','M21'),
    'F5':('M02','M03','M05','M07','M09'), 'F6':('M03','M16','M17','M18','M19'),
    'F7':('M16','M17','M19','M20','M21'), 'F8':('M01','M26','M29','M31'),
    'F9':('M21','M23','M24','M26','M27','M28','M30','M31')}
DISCRIMINATORS={
    'F1':'Does the protected ladder survive the next counterleg, or does accepted loss invalidate continuation?',
    'F2':'Does later acceptance hold this same boundary, or does reclaim favor F4/F6?',
    'F3':'Does expansion retain progress with room, or return to quiet balance after a late impulse?',
    'F4':'Does opposite initiative persist after reclaim, or does F5 rebreak the original level?',
    'F5':'Does acceptance survive the failed reversal, or does another reclaim restore F4?',
    'F6':'Does rejection rotate within the original balance, or does accepted escape migrate value?',
    'F7':'Does failed extension return toward the frozen value anchor, or does accepted repricing defeat reversion?',
    'F8':'Does lag-trained relative persistence retain local consequence, or is this common beta/sector noise?',
    'F9':'Does stabilization survive the next extreme, or is this a second shock/fundamental repricing?'}


def formation_cards(bundle, instrument, facts, *, cutoff, as_of, mode,
                    qualified_families=(), origins=(), freeze=lambda r:r,initiator_methods=()):
    """Interpret the actual 6A graph, retaining all same-reference rivals.

    No new detector or numeric score. Qualification is supplied only by the
    caller's independently scoped source registry; raw analyzer flags stay intact.
    """
    from .research import Fact
    groups={};methods={m['method_id']:m for m in bundle['methods']}
    for h in bundle['families']:
        if h['reference'] and h['timeline']:
            groups.setdefault(h['reference_id'],[]).append(h)
    cards=[];refs=[];bundles=[]
    for rid,hs in sorted(groups.items()):
        raw=dict(hs[0]['reference']);raw['source_ids']=tuple(raw['source_ids'])
        r=freeze(Reference(**raw));refs.append(r)
        # Family states are independent. An invalidated rival cannot invalidate
        # a surviving primary. Keep every event and its original chronology.
        events={e['id']:{k:v for k,v in e.items() if k!='stage'} for h in hs for e in h['timeline']}
        ordered=tuple(sorted(events.values(),key=lambda e:(utc(e['known_at']),utc(e['occurred_from']),e['id'])))
        fams={h['family']:h for h in hs}
        start=max((r.known_at,min((e['occurred_from'] for e in ordered),key=utc)),key=utc)
        for h in hs:
            fam=h['family'];side='BULLISH' if h['direction']==1 else 'BEARISH' if h['direction']==-1 else 'UNDETERMINED'
            hys=[]
            for f in (fam,*h['rivals']):
                other=fams.get(f)
                direction=('BULLISH' if other['direction']==1 else 'BEARISH' if other['direction']==-1 else 'UNDETERMINED') if other else (
                    'UNDETERMINED' if f=='NULL' else 'BEARISH' if side=='BULLISH' else 'BULLISH')
                support=tuple(e['id'] for e in other['timeline'] if e['stage']!='INVALIDATED') if other else ()
                against=tuple(e['id'] for e in other['timeline'] if e['stage']=='INVALIDATED') if other else ()
                hys.append(Hypothesis(f,direction,other['verdict'] if other else 'UNKNOWN',support,against,
                    DISCRIMINATORS.get(f,'Can the NULL/no-economic-opportunity explanation survive current room and source checks?')))
            # A primary can coexist with multiple family interpretations. Each
            # hypothesis has its own identity inside the shared reference graph.
            fid=fact_id(rid,fam,cutoff,'FORMATION_6B')
            availability=max([r.available_at,*(e['available_at'] for e in ordered),cutoff],key=utc)
            qualified=fam in qualified_families
            facts[fid]=Fact(fid,instrument,'CAUSAL_SEQUENCE',True,'BOOLEAN',r.timeframe,cutoff,
                availability,availability,availability,'SELECTED_FORMATION_6B',
                fact_id(sorted({facts[i].response_hash for i in r.source_ids if i in facts}),h),
                'SYNCHRONIZED_REMOTE_RECONSTRUCTION',True,'QUALIFIED' if qualified else 'TRIAL',mode,7200)
            details_id=fact_id(rid,fam,cutoff,'FAMILY_OBSERVATIONS',h['details'])
            facts[details_id]=Fact(details_id,instrument,'FAMILY_OBSERVATIONS',h['details'],'STRUCTURAL_OBSERVATIONS',
                r.timeframe,cutoff,cutoff,availability,availability,'SELECTED_FORMATION_6B',
                facts[fid].response_hash,'SYNCHRONIZED_REMOTE_RECONSTRUCTION',True,
                'QUALIFIED' if qualified else 'TRIAL',mode,7200)
            mids=tuple(dict.fromkeys((*FAMILY_METHODS[fam],*initiator_methods)))
            formation={'version':'interpretation-6b.1','families':fams,
                'primary':fam,'methods':{m:{'status':methods[m]['status'],'reason':methods[m]['reason'],
                    'version':methods[m]['version'],'role':'APPLICABLE_INTERPRETER; NOT_INDEPENDENT_CONFIRMATION'} for m in mids},
                'necessary_source_ids':list(r.source_ids),
                'unknowns':h['unknowns'],'source_qualification_scope':'OFFLINE_ONLY' if mode!='LIVE' else 'REGISTERED_SOURCE_ONLY'}
            c=StructureCard(r.native_symbol,'BINANCE_USDM',r.timeframe,r,start,cutoff,fam,
                tuple(dict.fromkeys([fam,*(f for f in h['rivals'] if f.startswith('F') and f[1:].isdigit())])),
                mids,tuple(origins) or ('C_SELECTED_FORMATION',),ordered,tuple(hys),(fid,details_id),
                'QUALIFIED' if qualified else 'TRIAL',mode,DISCRIMINATORS[fam],
                'Accepted contrary sequence at the original reference, or frozen expiry',
                exposure_cluster='NATIVE_CONTRACT:'+r.native_symbol,formation=formation)
            cards.append(c)
        bundles.append((r,list(ordered),[]))
    return cards,refs,bundles


def _one(card, facts, measurement, as_of, units, *, qualified=True):
    rows=[facts[i] for i in card.evidence_ids if i in facts and facts[i].measurement==measurement
        and facts[i].usable(as_of=as_of,native_symbol=card.native_symbol,units=units,qualified=qualified)]
    if measurement in {'SPREAD_BPS','DEPTH_USDT_WITHIN_ROOM','RESEARCH_PRICE'}:
        rows=[f for f in rows if (utc(as_of)-utc(f.window_end)).total_seconds()<=30]
    if len(rows)>1:raise ContractError('AMBIGUOUS_RESEARCH_FACT')
    return rows[0] if rows else None


def remaining_room(card, facts, references, *, as_of):
    origin=_one(card,facts,'DECISION_PRICE',as_of,'USDT_PER_BASE',qualified=False)
    current=_one(card,facts,'RESEARCH_PRICE',as_of,'USDT_PER_BASE')
    side=next(h.direction for h in card.hypotheses if h.family==card.primary_family)
    direction=1 if side=='BULLISH' else -1 if side=='BEARISH' else 0
    if not origin or not current or not direction:
        return {'status':'ROOM_UNKNOWN','reason':'FRESH_PRICE_OR_FROZEN_DECISION_PRICE_UNAVAILABLE','evidence_ids':[]}
    if utc(origin.available_at)>utc(card.window_start) or utc(origin.window_end)>utc(card.window_start):
        return {'status':'ROOM_UNKNOWN','reason':'DECISION_PRICE_NOT_PREKNOWN','evidence_ids':[origin.id]}
    choices=[]
    for r in references:
        if r.id==card.reference.id:continue
        if r.native_symbol!=card.native_symbol:raise ContractError('OBSTACLE_IDENTITY_MISMATCH')
        opposing_kinds=({'SWING_HIGH','RANGE_TOP','DAILY_HIGH','WEEKLY_HIGH','EQH_POOL_INFERRED'} if direction==1
            else {'SWING_LOW','RANGE_BOTTOM','DAILY_LOW','WEEKLY_LOW','EQL_POOL_INFERRED'})
        profile_edge=r.kind=='TRUE_VA_EDGE' and r.direction==direction
        profile_node=r.kind in {'TRUE_POC','TRUE_HVN_LVN'}
        if r.kind not in opposing_kinds and not (r.kind in {'FVG_CANDIDATE','IFVG_CANDIDATE',
                'ORDER_BLOCK_CANDIDATE','SUPPLY_DEMAND_CANDIDATE'}
                and r.direction==-direction) and not profile_edge and not profile_node:continue
        if (utc(r.known_at)>utc(card.window_start) or utc(r.available_at)>utc(card.window_start)
                or utc(r.valid_until)<utc(card.window_start)):continue
        edge=r.lo if direction==1 else r.hi
        if direction*(edge-number(origin.value))>0:
            choices.append((direction*(edge-number(origin.value)),r.id,edge,r))
    if not choices:return {'status':'ROOM_UNKNOWN','reason':'NO_PREKNOWN_OPPOSING_OBSTACLE','evidence_ids':[origin.id,current.id]}
    _,rid,edge,r=min(choices,key=lambda x:(x[0],x[1]))
    if not all(i in facts for i in r.source_ids):
        return {'status':'ROOM_UNKNOWN','reason':'FIRST_FROZEN_OBSTACLE_SOURCE_OUTSIDE_SELECTED_HISTORY',
            'first_obstacle_id':rid,'obstacle_known_at':r.known_at,'obstacle_available_at':r.available_at,
            'evidence_ids':[origin.id,current.id],'missing_source_ids':[i for i in r.source_ids if i not in facts]}
    gross=max(D(0),direction*(edge-number(current.value)))
    lifecycle=[facts[i] for i in card.evidence_ids if i in facts and facts[i].measurement=='OBSTACLE_LIFECYCLE'
        and isinstance(facts[i].value,dict) and facts[i].value.get('reference_id')==rid
        and facts[i].usable(as_of=as_of,native_symbol=card.native_symbol,qualified=True)
        and utc(facts[i].value['after'])<=utc(card.window_start)]
    consumed=any(f.value.get('consumed') is True for f in lifecycle)
    expired=utc(r.valid_until)<utc(as_of)
    return {'status':'ROOM_EXHAUSTED' if gross==0 or consumed else 'ROOM_UNKNOWN' if expired else 'ROOM_OBSERVED',
        'reason':'FIRST_PREKNOWN_OBSTACLE_EXPIRED; FARTHER_OBSTACLE_NOT_SUBSTITUTED' if expired and not consumed else None,
        'first_obstacle_id':rid,
        'obstacle_known_at':r.known_at,'obstacle_available_at':r.available_at,'gross_room':gross,
        'units':'USDT_PER_BASE','room_bps':gross/number(current.value,positive=True)*10000,
        'evidence_ids':[origin.id,current.id,*r.source_ids,*(f.id for f in lifecycle)],
        'consumed_since_initiation':consumed,
        'interpretation':'RESEARCH_GEOMETRY; NO_EXECUTABLE_TARGET_OR_PROFIT_ESTIMATE'}


def economics(card, facts, room, *, as_of):
    names={'SPREAD_BPS':'BPS','DEPTH_USDT_WITHIN_ROOM':'USDT','ROUND_TRIP_FEE_BPS':'BPS',
        'SLIPPAGE_BOUND_BPS':'BPS','FUNDING_BOUND_BPS':'BPS','HORIZON_SECONDS':'SECONDS','HORIZON_RELEVANT':'BOOLEAN'}
    found={k:_one(card,facts,k,as_of,u) for k,u in names.items()}
    missing=[k for k,f in found.items() if f is None]
    if missing:return {'status':'ECONOMICS_UNKNOWN','missing':missing,'evidence_ids':[f.id for f in found.values() if f]}
    vals={k:number(f.value) for k,f in found.items() if k!='HORIZON_RELEVANT'}
    if min(vals.values())<0 or vals['DEPTH_USDT_WITHIN_ROOM']==0:
        return {'status':'ECONOMICS_UNFAVORABLE','reason':'NEGATIVE_FRICTION_OR_NO_OBSERVED_DEPTH','evidence_ids':[f.id for f in found.values()]}
    if found['HORIZON_RELEVANT'].value is not True or not 0<vals['HORIZON_SECONDS']<=15*3600:
        return {'status':'HORIZON_UNCERTAIN','evidence_ids':[f.id for f in found.values()]}
    friction=sum((vals[k] for k in ('SPREAD_BPS','ROUND_TRIP_FEE_BPS','SLIPPAGE_BOUND_BPS','FUNDING_BOUND_BPS')),D(0))
    price=_one(card,facts,'RESEARCH_PRICE',as_of,'USDT_PER_BASE')
    cushion=card.reference.buffer/number(price.value,positive=True)*10000 if price else D(0)
    status='ECONOMICS_UNKNOWN' if room['status']=='ROOM_UNKNOWN' else (
        'ECONOMICS_FAVORABLE_FOR_RESEARCH' if room['room_bps']>friction+cushion else 'ECONOMICS_UNFAVORABLE')
    assumptions=[f.id for f in found.values() if f.source_id.startswith('DECLARED_RESEARCH_')]
    if status=='ECONOMICS_FAVORABLE_FOR_RESEARCH' and assumptions:status='ECONOMICS_CONDITIONAL_RESEARCH_SCENARIO'
    return {'status':status,'observed_friction_bound_bps':friction,'assumption_evidence_ids':assumptions,
        'resolution_cushion_bps':cushion,'buffered_room_bps':max(D(0),room.get('room_bps',D(0))-cushion),
        'price_arrival_within_horizon':'UNKNOWN; HORIZON_IS_SOURCEABLE_RESEARCH_DISCRIMINATOR_NOT_FORECAST',
        'horizon_seconds':vals['HORIZON_SECONDS'],'evidence_ids':[f.id for f in found.values()],
        'scope':'SOURCE_DECLARED_BOUNDS; EXECUTION_NOT_CERTIFIED'}


def _sequence(card):
    if card.formation:
        h=card.formation['families'][card.primary_family]
        kinds=[e['kind'] for e in h['timeline']]
        paths={
            'F1':('CONTROLLED_COUNTERLEG','DEFENDED_RESPONSE'),
            'F2':('SEPARATED_PRESSURE','BUFFERED_OUTSIDE_CLOSE','LATER_OUTSIDE_ACCEPTANCE'),
            'F3':('QUIET_AT_KNOWN_DECISION','FIRST_DISPLACEMENT','RETAINED_PROGRESS'),
            'F4':('RECLAIM','OPPOSING_INITIATIVE'),
            'F5':('RECLAIM','OPPOSING_REVERSAL_ATTEMPT','REVERSAL_FAILED_REBREAK_SAME_REFERENCE','LATER_OUTSIDE_ACCEPTANCE'),
            'F6':('ROTATION',), 'F7':('CONDITIONAL_VALUE_EXTENSION','FAILED_FURTHER_PROGRESS_RETURN'),
            'F8':('PERSISTENT_RESIDUAL_AT_LOCAL_DECISION','LOCAL_STRUCTURAL_CONSEQUENCE'),
            # Stabilization alone establishes neither directional recovery nor continuation.
            'F9':('POST_SHOCK','STABILIZATION_CANDIDATE','RENEWED_EXTREME_SECOND_LEG')}
        path=paths[card.primary_family];cursor=0;ids=[]
        for e in h['timeline']:
            if cursor<len(path) and e['kind']==path[cursor]:ids.append(e['id']);cursor+=1
        return cursor==len(path) and h['stage'] not in {'INVALIDATED','LATE'} and h['direction']!=0,ids
    sequence=SEQUENCES.get(card.primary_family)
    if sequence is None:return False,[]
    cursor=0;ids=[];last=None
    for e in card.events:
        if cursor<len(sequence) and e['kind']==sequence[cursor]:
            # Same-bar excursion/reclaim is OHLC geometry. Every later drive,
            # rebreak and acceptance must be a distinct later candle.
            if last and e['kind']!='RECLAIM' and utc(e['occurred_from'])<utc(last['occurred_to']):continue
            if e['kind']=='OUTSIDE_HOLD':
                from .observations import WIDTHS
                if (utc(e['occurred_to'])-utc(last['occurred_to'])).total_seconds()<2*WIDTHS[card.timeframe]:continue
            ids.append(e['id']);last=e;cursor+=1
    return cursor==len(sequence),ids


def review_card(card, facts, references, *, as_of):
    if any(i not in facts for i in card.evidence_ids):raise ContractError('HYPOTHESIS_UNKNOWN_EVIDENCE')
    if any(facts[i].instrument.native_symbol!=card.native_symbol or facts[i].instrument.venue!=card.venue
           or facts[i].mode!=card.mode for i in card.evidence_ids):raise ContractError('NOMINATION_EVIDENCE_SCOPE')
    if any(utc(e['available_at'])>utc(as_of) for e in card.events):raise ContractError('EVENT_NOT_AVAILABLE')
    # All raw event/reference source citations must resolve in the evidence graph.
    raw_ids=set(card.reference.source_ids)|{i for e in card.events for i in e['source_ids']}
    if not all(i in facts for i in raw_ids):raise ContractError('HYPOTHESIS_UNKNOWN_EVIDENCE')
    primary=next(h for h in card.hypotheses if h.family==card.primary_family)
    complete,sequence_ids=_sequence(card)
    room=remaining_room(card,facts,references,as_of=as_of)
    eco=economics(card,facts,room,as_of=as_of)
    significance=_one(card,facts,'REFERENCE_SIGNIFICANCE',as_of,'ORDINAL')
    proximity=_one(card,facts,'DECISION_PROXIMITY',as_of,'BOOLEAN')
    necessary=[i for i in card.evidence_ids if facts[i].measurement=='CAUSAL_SEQUENCE']
    current=(cited(necessary,facts,as_of=as_of,native_symbol=card.native_symbol,qualified=True)
        and all(facts[i].timeframe==card.timeframe and utc(facts[i].window_end)==utc(card.cutoff)
                and facts[i].value is True for i in necessary)
        and cited(raw_ids,facts,as_of=as_of,native_symbol=card.native_symbol,qualified=True))
    from .screening import closed_cutoff
    current=current and utc(card.cutoff)==utc(closed_cutoff(as_of,card.timeframe))
    formation=card.formation['families'][card.primary_family] if card.formation else None
    contradictions=[e for e in card.events if e['id'] in primary.contradicting_ids and e['kind']!='EXPIRED']
    expired=utc(card.reference.valid_until)<utc(as_of) or any(
        e['id'] in primary.contradicting_ids and e['kind']=='EXPIRED' for e in card.events)
    if contradictions:
        stage='INVALIDATED';reason='CAUSAL_PREMISE_CONTRADICTED'
    elif expired:
        stage='INVALIDATED';reason='REFERENCE_EXPIRED'
    elif formation and formation['stage']=='LATE':stage='LATE';reason='FORMATION_REACHED_PRIOR_VALUE_OR_EXHAUSTED'
    elif room['status']=='ROOM_EXHAUSTED':stage='LATE';reason='FIRST_PREKNOWN_OBSTACLE_CONSUMED'
    elif not cited(card.evidence_ids,facts,as_of=as_of,native_symbol=card.native_symbol):
        stage='UNKNOWN';reason='MISSING_STALE_OR_INCOMPLETE_SOURCE'
    elif complete and current and primary.verdict=='SUPPORTED' and card.qualification=='QUALIFIED' and significance and significance.value in {'HIGH','MED'} and room['status']=='ROOM_OBSERVED' and eco['status']=='ECONOMICS_FAVORABLE_FOR_RESEARCH':
        stage='READY_FOR_DEEP';reason='NECESSARY_PRESENT_STAGE_FACTS_VERIFIED'
        latest=formation['timeline'][-1] if formation else card.events[-1]
        event_age=(utc(as_of)-utc(latest['known_at'])).total_seconds()
        if event_age<=900 and proximity and proximity.value is True:
            stage='FAST_WITH_ROOM';reason='RECENT_VERIFIED_EVENT_WITH_ROOM_AND_FRICTION'
    elif complete and current and primary.verdict=='SUPPORTED' and card.qualification=='QUALIFIED' and significance and significance.value in {'HIGH','MED'} and room['status']=='ROOM_OBSERVED' and eco['status']=='ECONOMICS_CONDITIONAL_RESEARCH_SCENARIO':
        stage='CONDITIONAL_FOR_DEEP';reason='CAUSAL_RESEARCH_QUESTION_WITH_EXPLICIT_ECONOMIC_ASSUMPTIONS; ANALYST_MAY_DECLINE'
    elif formation and formation['stage']=='EARLY':
        stage='EARLY';reason='FORMED_REFERENCE_AND_EARLY_EVENT; LATER_CONFIRMATION_NOT_REQUIRED_FOR_WATCH'
    elif formation and formation['stage']=='APPROACHING_DECISION':
        stage='APPROACHING_DECISION';reason='MEASURED_APPROACH_TO_FROZEN_DECISION'
    elif formation and formation['stage']=='DEVELOPING':
        stage='DEVELOPING';reason='SOURCE_BACKED_DEVELOPING_FORMATION; RESPONSE_AND_RIVALS_UNRESOLVED'
    elif sequence_ids and significance and proximity and proximity.value is True:
        stage='APPROACHING_DECISION';reason='CAUSAL_SEQUENCE_AND_SIGNIFICANT_DECISION_AREA'
    elif sequence_ids or primary.supporting_ids:
        stage='DEVELOPING';reason='PARTIAL_OR_TRIAL_CAUSAL_FORMATION; ADMISSION_DEPENDENCIES_UNRESOLVED'
    elif card.events:stage='EARLY';reason='PREKNOWN_REFERENCE_AND_INITIATING_EVIDENCE'
    else:stage='PREMATURE';reason='APPLICABLE_METHOD_WITHOUT_MEANINGFUL_SEQUENCE'
    current_price=_one(card,facts,'RESEARCH_PRICE',as_of,'USDT_PER_BASE')
    closed_prices=[facts[i] for i in raw_ids if facts[i].measurement=='SELECTED_CLOSED_BAR'
        and isinstance(facts[i].value,dict) and 'close' in facts[i].value]
    price_fact=current_price or (max(closed_prices,key=lambda f:utc(f.window_end)) if closed_prices else None)
    price=number(price_fact.value if current_price else price_fact.value['close']) if price_fact else None
    distance_atr=(max(card.reference.lo-price,price-card.reference.hi,D(0))/card.reference.atr
        if price is not None and card.reference.atr>0 else None)
    if stage=='APPROACHING_DECISION' and (distance_atr is None or distance_atr>1):
        stage='DEVELOPING';reason='HISTORICAL_APPROACH; CURRENT_DISTANCE_UNKNOWN_OR_OUTSIDE_DECISION_AREA'
    missing=[]
    if not complete:missing.append('COMPLETE_FAMILY_SEQUENCE')
    if not current or card.qualification!='QUALIFIED':missing.append('QUALIFIED_CURRENT_SEQUENCE')
    if not significance:missing.append('REFERENCE_SIGNIFICANCE')
    if room['status']=='ROOM_UNKNOWN':missing.append('PREKNOWN_FIRST_OBSTACLE_AND_FRESH_PRICE')
    if eco['status']!='ECONOMICS_FAVORABLE_FOR_RESEARCH':missing.append(eco['status'])
    clusters=tuple(sorted({facts[i].cluster for i in card.evidence_ids}))
    methods=_method_contracts()
    citation_ids=set(card.evidence_ids)|raw_ids|set(room.get('evidence_ids',()))
    return {'card_id':card.id,'instrument':card.native_symbol,'scope':card.venue+'_PERPETUAL',
        'stage':stage,'reason_code':reason,'side_hypothesis':primary.direction,
        'distance_atr_at_verification':distance_atr,'distance_price_source_id':price_fact.id if price_fact else None,
        'distance_price_scope':'FRESH_TOP_OF_BOOK' if current_price else 'LATEST_CITED_CLOSED_BAR' if price_fact else 'SOURCE_GAP',
        'invalidation_kind':'EXPIRY' if stage=='INVALIDATED' and reason=='REFERENCE_EXPIRED' else
            'CAUSAL_CONTRADICTION' if stage=='INVALIDATED' else None,
        'invalidating_event_ids':[e['id'] for e in contradictions],
        'reference':{**asdict(card.reference),'id':card.reference.id},'event_window':(card.window_start,card.cutoff),
        'family_ids':card.family_ids,'method_ids':card.method_ids,'origins':card.origins,
        'primary_family':card.primary_family,
        'method_roles':{i:methods[i]['roles'] for i in card.method_ids},
        'method_capabilities':{i:{k:methods[i]['implementation'][k] for k in
            ('state','remote_qualification','production_enabled','fidelity')} for i in card.method_ids},
        'hypotheses':[asdict(h) for h in card.hypotheses], 'events':card.events,
        'supporting_evidence_ids':card.evidence_ids,'necessary_sequence_event_ids':sequence_ids,
        'missing_necessary_inputs':missing,'room':room,'economics':eco,
        'historical_significance':significance.value if significance else 'UNKNOWN',
        'evidence_clusters':clusters,'independent_confirmation_count':None,
        'contradiction_load':len(primary.contradicting_ids),'mode':card.mode,
        'source_coverage':{i:{'source_id':facts[i].source_id,'response_hash':facts[i].response_hash,
            'known_at':facts[i].known_at,'available_at':facts[i].available_at,'window_end':facts[i].window_end,
            'received_at':facts[i].received_at,'units':facts[i].units,'measurement':facts[i].measurement,
            'timeframe':facts[i].timeframe,
            'age_seconds':int((utc(as_of)-utc(facts[i].window_end)).total_seconds()),
            'fidelity':facts[i].fidelity,'qualification':facts[i].qualification} for i in sorted(citation_ids)},
        'trigger_to_investigate':card.trigger_to_investigate,'invalidating_evidence':card.invalidating_evidence,
        'exposure_cluster':card.exposure_cluster,'trade_authorization':False,
        'formation_contract':{'version':card.formation['version'],'primary':card.primary_family,
            'families':{f:{k:h[k] for k in ('id','reference_id','stage','status','direction','unknowns','details')}
                for f,h in card.formation['families'].items()},'methods':card.formation['methods'],
            'source_qualification_scope':card.formation['source_qualification_scope']} if card.formation else None,
        'why_now':{'family':card.primary_family,'latest_event':card.events[-1]['kind'] if card.events else None,
            'reference_id':card.reference.id,'present_stage':stage,'qualification':card.qualification},
        'strongest_rival':next((asdict(h) for h in card.hypotheses if h.family not in {card.primary_family,'NULL'}),None),
        'null_rival':next(asdict(h) for h in card.hypotheses if h.family=='NULL'),
        'next_deep_analyst_question':primary.next_discriminator,
        'expiry':card.reference.valid_until}


def shortlist(reviews, *, coverage, max_count=5, not_reviewed=()):
    if type(max_count) is not int or not 0<=max_count<=5:raise ContractError('MAX_SHORTLIST_FIVE')
    rows=list(reviews)
    if len({r['card_id'] for r in rows})!=len(rows):raise ContractError('CONFLICTING_STRUCTURE_DUPLICATE')
    eligible=[r for r in rows if r['stage'] in {'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'}]
    def dimensions(r):
        return (2 if r['historical_significance']=='HIGH' else 1,
                1 if r['stage']=='FAST_WITH_ROOM' else 0,
                0 if r['economics'].get('assumption_evidence_ids') else 1,
                number(r['economics'].get('buffered_room_bps',r['room']['room_bps']))-
                    number(r['economics']['observed_friction_bound_bps']),-r['contradiction_load'])
    comparisons=[];fronts=[];remaining=list(eligible)
    family_fronts={f:[] for f in sorted({r['primary_family'] for r in eligible})}
    for f in family_fronts:
        peers=[r for r in eligible if r['primary_family']==f]
        family_fronts[f]=[r['card_id'] for r in peers if not any(
            all(x>=y for x,y in zip(dimensions(b),dimensions(r))) and dimensions(b)!=dimensions(r)
            for b in peers)]
    while remaining:
        front=[]
        for a in remaining:
            dominated=False
            for b in remaining:
                if a is b:continue
                da,db=dimensions(a),dimensions(b)
                better=all(x>=y for x,y in zip(db,da)) and any(x>y for x,y in zip(db,da))
                if better:dominated=True
                if a['card_id']<b['card_id']:comparisons.append({'a':a['card_id'],'b':b['card_id'],
                    'relation':'B_DOMINATES' if better else 'A_DOMINATES' if all(x>=y for x,y in zip(da,db)) and da!=db else 'INCOMPARABLE_OR_EQUAL',
                    'dimensions':['historical_significance','urgency','observed_vs_declared_economics',
                        'room_after_resolution_and_declared_friction_bps','contradiction_load'],
                    'a_values':da,'b_values':db,
                    'family_relative':bool(set(a['family_ids'])&set(b['family_ids'])),
                    'room_economics':'Comparable bps are research geometry, not expected profit; each source/window/first obstacle remains cited'})
            if not dominated:front.append(a)
        fronts.append(front);remaining=[r for r in remaining if r not in front]
    selected=[];clusters=set()
    selected_structures=set()
    for front in fronts:
        while front and len(selected)<max_count:
            a=min(front,key=lambda r:(r['exposure_cluster']!='UNKNOWN' and r['exposure_cluster'] in clusters,r['card_id']))
            front.remove(a)
            structure=(a['instrument'],a['reference']['id'])
            if structure in selected_structures:continue
            selected.append(a);clusters.add(a['exposure_cluster']);selected_structures.add(structure)
    selected_ids={r['card_id'] for r in selected}
    return {'schema_version':'openbot.research-review.v1','shortlist':selected,
        'watches':[r for r in rows if r['stage'] in {'PREMATURE','EARLY','DEVELOPING','APPROACHING_DECISION','UNKNOWN'}],
        'near_misses':[*[dict(r,admission_reason='RESEARCH_CAPACITY_OR_DIVERSITY') for r in eligible if r['card_id'] not in selected_ids],
            *[dict(r,admission_reason='LATE_OR_NECESSARY_FACT_UNASSESSABLE') for r in rows if r['stage']=='LATE' or
                r['stage'] in {'UNKNOWN','DEVELOPING','APPROACHING_DECISION'} and
                'COMPLETE_FAMILY_SEQUENCE' not in r['missing_necessary_inputs']]],
        'invalidations':[r for r in rows if r['stage']=='INVALIDATED'],
        'late':[r for r in rows if r['stage']=='LATE'],'not_reviewed':list(not_reviewed),
        'pairwise_comparison':comparisons,'family_fronts':family_fronts,
        'selection_tiebreak':'PARETO_FRONT; DISTINCT_KNOWN_EXPOSURE; STABLE_ID; NO_CONTEXT_SIDE_VETO',
        'exposure_groups':{cluster:[r['card_id'] for r in selected if r['exposure_cluster']==cluster]
            for cluster in sorted({r['exposure_cluster'] for r in selected})},
        'coverage':coverage,'llm_calls':0,'trade_authorization':False,
        'new_orders_created':0,'empty_shortlist_reason':None if selected else 'NO_QUALIFIED_HANDOFF_WITHIN_OBSERVED_COVERAGE; NOT_A_NO_OPPORTUNITIES_CLAIM'}


def active_coin_watches(reviews,*,as_of):
    """Current coin hypotheses, distinct from the immutable reference archive."""
    by={}
    for r in reviews:
        if r['stage'] not in {'EARLY','DEVELOPING','APPROACHING_DECISION','READY_FOR_DEEP','CONDITIONAL_FOR_DEEP','FAST_WITH_ROOM'}:continue
        d=r.get('distance_atr_at_verification')
        if d is None or d>D('2.5') or utc(r['expiry'])<utc(as_of):continue
        if not r.get('events'):continue
        latest=max(r['events'],key=lambda e:utc(e['known_at']))
        if not 0<=(utc(as_of)-utc(latest['known_at'])).total_seconds()<=54000:continue
        by.setdefault(r['instrument'],[]).append(r)
    result=[]
    for name,rows in by.items():
        rows.sort(key=lambda r:(r['historical_significance'] not in {'MED','HIGH'},
            r['stage']!='APPROACHING_DECISION',r['distance_atr_at_verification'],
            -utc(max(r['events'],key=lambda e:utc(e['known_at']))['known_at']).timestamp(),r['card_id']))
        distinct=[]
        for r in rows:
            ref=r['reference'];mid=(number(ref['lo'])+number(ref['hi']))/2
            if any(abs(mid-(number(x['reference']['lo'])+number(x['reference']['hi']))/2)<=
                    max(2*number(ref['tick']),2*number(x['reference']['tick']),
                        D('.15')*min(number(ref['atr']),number(x['reference']['atr']))) for x in distinct):continue
            distinct.append(r)
        primary=distinct[0]
        def case(r):
            result={k:r[k] for k in ('card_id','primary_family','side_hypothesis','stage','reference',
                'distance_atr_at_verification','supporting_evidence_ids','strongest_rival',
                'trigger_to_investigate','invalidating_evidence','event_window','missing_necessary_inputs')}
            h=(r.get('formation_contract') or {}).get('families',{}).get(r['primary_family'],{})
            phase=h.get('details',{}).get('current_response')
            if r['primary_family']=='F9':
                result.update(observed_shock_side=r['side_hypothesis'],phase=phase,
                    attention_scope='POST_SHOCK_OBSERVATION; WIDE_SHOCK_RANGE_IS_NOT_A_DIRECTIONAL_TRIGGER')
                if phase=='RECOVERY_AGAINST_SHOCK':result['side_hypothesis']='UNDETERMINED'
            return result
        result.append({'native_symbol':name,'primary':case(primary),'alternatives':[case(r) for r in distinct[1:4]],
            'attention':'NEAR_NOW' if primary['distance_atr_at_verification']<=1 else 'DEVELOPING',
            'source_scope':primary['distance_price_scope'],'as_of':as_of,
            'reference_records':len(rows),'deduplicated_zones':len(distinct),
            'timeframe_relationships':sorted({r['reference']['timeframe'] for r in rows}),
            'trade_authorization':False})
    result.sort(key=lambda w:(w['attention']!='NEAR_NOW',w['primary']['distance_atr_at_verification'],w['native_symbol']))
    for rank,w in enumerate(result,1):w['rank']=rank
    return result


def conditional_research(reviews,cards,facts,references,*,as_of,max_count=5,deduplicate=True):
    """Owner-approved research handoffs, independently labeled from READY.

    Blueprint §§1.1, 11.3/11.4 permit developing research and documented cost
    assumptions. This does not qualify full methods, backdate availability, or
    weaken review_card. Unknown present price/identity/causality never passes.
    """
    from .observations import WIDTHS
    by_card={c.id:c for c in cards};eligible=[];decisions=[]
    for r in reviews:
        c=by_card[r['card_id']];reason=None
        own=[facts[i] for i in c.evidence_ids if i in facts]
        price=_one(c,facts,'RESEARCH_PRICE',as_of,'USDT_PER_BASE')
        spread=_one(c,facts,'SPREAD_BPS',as_of,'BPS')
        primary=next(h for h in c.hypotheses if h.family==c.primary_family)
        latest=(c.formation['families'][c.primary_family]['timeline'][-1] if c.formation else
            c.events[-1] if c.events else None)
        d=r.get('distance_atr_at_verification')
        if c.native_symbol in {'BTCUSDT','ETHUSDT'}:reason='CONTEXT_ONLY'
        elif r['stage'] in {'INVALIDATED','LATE','UNKNOWN','PREMATURE'}:reason='INVALID_LATE_OR_SOURCE_UNASSESSABLE'
        elif not price or not spread:reason='FRESH_CURRENT_PRICE_OR_SPREAD_SOURCE_GAP'
        elif not latest or not 0<=(utc(as_of)-utc(latest['known_at'])).total_seconds()<=min(54000,3*WIDTHS[c.timeframe]):reason='NO_RECENT_STRUCTURAL_EVENT'
        elif primary.contradicting_ids:reason='CONTRADICTORY_PRIMARY_CAUSAL_CASE'
        elif not primary.supporting_ids:reason='NO_SUPPORTING_STRUCTURAL_EVENT'
        elif r['historical_significance'] not in {'MED','HIGH'}:reason='REFERENCE_SIGNIFICANCE_UNVERIFIED'
        elif d is None or d>D('2.5'):reason='DECISION_ZONE_DISTANT_OR_UNKNOWN'
        elif not c.invalidating_evidence or not r['strongest_rival']:reason='RIVAL_OR_INVALIDATION_MISSING'
        family_state=c.formation['families'][c.primary_family] if c.formation else None
        primary_events=family_state['timeline'] if family_state else c.events
        if not reason and c.primary_family=='F5' and not any(
                e['kind'] in {'REVERSAL_FAILED_REBREAK_SAME_REFERENCE','REBREAK_SAME_REFERENCE'} for e in primary_events):
            reason='F5_FAILURE_NOT_OBSERVED; WATCH_RECLAIM_RIVAL'
        if not reason and c.primary_family=='F9':
            response=family_state.get('details',{}).get('current_response') if family_state else None
            reclaim=[e for e in primary_events if e['kind']=='SHOCK_MIDPOINT_RECLAIM']
            resume=[e for e in primary_events if e['kind'] in {'SHOCK_DIRECTION_REACCEPTED','RENEWED_EXTREME_SECOND_LEG'}]
            if response=='RECOVERY_AGAINST_SHOCK' or (reclaim and (not resume or
                    utc(reclaim[-1]['known_at'])>=utc(resume[-1]['known_at']))):
                reason='F9_ADVERSE_RECOVERY; NEW_DIRECTIONAL_STRUCTURE_REQUIRED'
        raw_ids=set(c.reference.source_ids)|{i for e in c.events for i in e['source_ids']}
        if not reason and not cited(raw_ids,facts,as_of=as_of,native_symbol=c.native_symbol,qualified=True):
            reason='RAW_STRUCTURE_SOURCE_UNQUALIFIED_OR_STALE'
        room={'status':'ROOM_UNKNOWN','reason':'NO_INDEPENDENT_PREKNOWN_OPPOSING_OBSTACLE',
            'scope':'CURRENT_RESEARCH_RECONSTRUCTION; ORIGINAL_RECEIPT_AVAILABILITY_RETAINED'}
        if not reason:
            direction=1 if primary.direction=='BULLISH' else -1 if primary.direction=='BEARISH' else 0
            origin=(c.reference.lo+c.reference.hi)/2;choices=[]
            kinds={'SWING_HIGH','RANGE_TOP','DAILY_HIGH','WEEKLY_HIGH','EQH_POOL_INFERRED'} if direction==1 else {
                'SWING_LOW','RANGE_BOTTOM','DAILY_LOW','WEEKLY_LOW','EQL_POOL_INFERRED'}
            for ref in references:
                if ref.native_symbol!=c.native_symbol or ref.id==c.reference.id or ref.kind not in kinds:continue
                # Market confirmation must precede initiation. Retrieval remains
                # later and is explicitly not prospective prior knowledge.
                if utc(ref.known_at)>utc(c.window_start) or utc(ref.available_at)>utc(as_of):continue
                edge=ref.lo if direction==1 else ref.hi
                if direction*(edge-origin)>0:
                    choices.append((direction*(edge-origin),ref.id,edge,ref))
            if not direction:reason='DIRECTION_UNDETERMINED'
            elif choices:
                _,rid,edge,ref=min(choices,key=lambda v:(v[0],v[1]))
                source_complete=all(i in facts for i in ref.source_ids)
                lifecycles=[f for f in own if f.measurement=='OBSTACLE_LIFECYCLE' and isinstance(f.value,dict)
                    and f.value.get('reference_id')==rid and f.usable(as_of=as_of,native_symbol=c.native_symbol)]
                consumed=any(f.value.get('consumed') is True for f in lifecycles)
                gross=direction*(edge-number(price.value))
                room.update(status='ROOM_EXHAUSTED' if consumed or gross<=0 else 'ROOM_OBSERVED',
                    reason='FIRST_OPPOSING_OBSTACLE_CONSUMED' if consumed else None,
                    first_obstacle_id=rid,level=edge,room_bps=max(D(0),gross/number(price.value)*10000),
                    obstacle_known_at=ref.known_at,obstacle_available_at=ref.available_at,
                    evidence_ids=[price.id,*(i for i in ref.source_ids if i in facts)])
                if consumed or gross<=0:reason='FIRST_OPPOSING_OBSTACLE_CONSUMED'
                elif not source_complete:
                    room.update(status='ROOM_UNKNOWN',reason='FIRST_FROZEN_OBSTACLE_SOURCE_OUTSIDE_SELECTED_HISTORY',
                        missing_source_ids=[i for i in ref.source_ids if i not in facts])
                    if d>1 or len(primary.supporting_ids)<2:reason='NEAREST_OBSTACLE_SOURCE_GAP'
                elif utc(ref.valid_until)<utc(as_of) or ref.timeframe!=c.timeframe and not lifecycles:
                    room.update(status='ROOM_UNKNOWN',reason='NEAREST_OBSTACLE_EXPIRED_OR_CROSS_TIMEFRAME_LIFECYCLE_UNVERIFIED')
                    if d>1 or len(primary.supporting_ids)<2:reason='NEAREST_OBSTACLE_LIFECYCLE_UNVERIFIED'
                elif room['room_bps']<=number(spread.value)+c.reference.buffer/number(price.value)*10000:
                    reason='OBSERVED_SPREAD_AND_RESOLUTION_EXHAUST_ROOM'
            elif d>1 or len(primary.supporting_ids)<2:reason='ROOM_UNKNOWN_WITH_INSUFFICIENT_NEAR_CURRENT_STRUCTURE'
        if reason:
            decisions.append({'card_id':c.id,'native_symbol':c.native_symbol,'disposition':reason});continue
        gaps=list(dict.fromkeys([*r['missing_necessary_inputs'],*r['economics'].get('missing',()),
            'ACCOUNT_FEE_TIER_AND_FUTURE_EXECUTION_COSTS','POTENTIAL_EVENT_WITHIN_15H_NOT_PREDICTED',
            *(['DATED_SECTOR_MEMBERSHIP; PRICE_RELATIVE_BRANCH_ONLY'] if c.primary_family=='F8' else []),
            *(['FIRST_INDEPENDENT_OPPOSING_OBSTACLE',room['reason']] if room['status']=='ROOM_UNKNOWN' else [])]))
        from datetime import timedelta
        valid_until=min((utc(c.reference.valid_until),utc(price.window_end)+timedelta(seconds=30),
            utc(spread.window_end)+timedelta(seconds=30))).isoformat()
        item={**r,'stage':'CONDITIONAL_RESEARCH_ONLY','valid_until':valid_until,'strict_admission_stage':r['stage'],
            'reason_code':'CURRENT_STRUCTURAL_RESEARCH_WITH_EXPLICIT_ANALYST_QUESTIONS',
            'research_room':room,'missing_evidence':gaps,'research_as_of':as_of,
            'source_age_seconds':int((utc(as_of)-utc(c.cutoff)).total_seconds()),
            'source_qualification':'SELECTED_SOURCE_BACKED_TRIAL; FULL_METHOD_PRODUCTION_UNQUALIFIED',
            'first_knowing_time':max((facts[i].received_at for i in raw_ids),key=utc),
            'current_price':{'value':price.value,'evidence_id':price.id,'source_time':price.window_end,'received_at':price.received_at},
            'current_spread_bps':{'value':spread.value,'evidence_id':spread.id,'source_time':spread.window_end},
            'prospective_historical_discovery':False,'trade_authorization':False,
            'analyst_question':('Verify the nearest independently confirmed opposing obstacle before any urgent handoff'
                if room['status']=='ROOM_UNKNOWN' else 'Verify room survives actual fee tier, relevant-price liquidity and the next closed response'),
            'execution_authorization':'NONE; NO_DEEP_ANALYST_CONNECTION'}
        eligible.append(item)
    eligible.sort(key=lambda r:(r['research_room']['status']!='ROOM_OBSERVED',r['distance_atr_at_verification'],
        r['source_age_seconds'],r['card_id']))
    picked=[];seen=set()
    for row in eligible:
        if deduplicate and row['instrument'] in seen or len(picked)>=max_count:
            decisions.append({'card_id':row['card_id'],'native_symbol':row['instrument'],'disposition':'ALTERNATIVE_CASE_OR_RESEARCH_CAPACITY'});continue
        picked.append(row);seen.add(row['instrument'])
    return picked,decisions


def refresh_cached_watches(watches,pulse,*,as_of):
    """Reprice unchanged closed structures without shrinking to exported finalists."""
    from .numerics import distance
    books={o['native_symbol']:o for p in pulse if p['kind']=='book' for o in p['observations']}
    kept=[];gaps=[]
    for old in watches:
        n=old['native_symbol'];b=books.get(n);p=old['primary'];ref=p['reference']
        if not b or not 0<=(utc(as_of)-utc(b['source_time_utc'])).total_seconds()<=30:
            gaps.append({'native_symbol':n,'disposition':'SOURCE_GAP','reason':'CACHED_WATCH_FRESH_BOOK_UNAVAILABLE'});continue
        if utc(ref['valid_until'])<utc(as_of):continue
        price=(number(b['values']['bid'])+number(b['values']['ask']))/2
        d=distance(price,number(ref['lo']),number(ref['hi']),number(ref['atr']))
        if d>D('2.5'):continue
        kept.append({**old,'as_of':as_of,'primary':{**p,'distance_atr_at_verification':d},
            'source_scope':'FRESH_TOP_OF_BOOK; UNCHANGED_CLOSED_STRUCTURE_CACHE',
            'attention':'NEAR_NOW' if d<=1 else 'DEVELOPING'})
    kept.sort(key=lambda w:(w['attention']!='NEAR_NOW',w['primary']['distance_atr_at_verification'],w['native_symbol']))
    for rank,w in enumerate(kept,1):w['rank']=rank
    return kept,gaps


def native_review_selection(reviews,cards,facts,references,*,as_of,max_cards=None):
    """Review actual conditional finalists, with a protected exception/rival.

    This uses the same current sources and policy as final admission. Watch
    distance alone cannot silently substitute convenient model-test cards.
    """
    finalists,_=conditional_research(reviews,cards,facts,references,as_of=as_of,max_count=len(cards),deduplicate=False)
    wanted=[r['card_id'] for r in finalists[:max_cards]]
    active=active_coin_watches(reviews,as_of=as_of)
    by={c.id:c for c in cards}
    exceptions=[r['card_id'] for r in finalists if any(s in by[r['card_id']].origins
        for s in ('C_RELATIVE_EXCEPTION','C_QUIET','C_STRATIFIED_AUDIT','C_UNOBSERVED_STRATIFIED_SOURCE_RECOVERY'))]
    fallback=[w['primary']['card_id'] for w in active if w['native_symbol'] not in {'BTCUSDT','ETHUSDT'}]
    if max_cards is not None and max_cards>1 and exceptions and exceptions[0] not in wanted:
        wanted=wanted[:max_cards-1]+[exceptions[0]]
    for cid in fallback:
        if max_cards is not None and len(wanted)>=max_cards:break
        if cid not in wanted:wanted.append(cid)
    if max_cards is None:
        for r in finalists:
            if r['card_id'] not in wanted:wanted.append(r['card_id'])
    return wanted,{'policy':'CURRENT_CONDITIONAL_FINALISTS_THEN_PROTECTED_EXCEPTION_AND_CURRENT_RIVALS',
        'deterministic_control_card_ids':[r['card_id'] for r in finalists],
        'selected':[{'card_id':cid,'native_symbol':by[cid].native_symbol,
            'relationship':'PROVISIONAL_FINALIST' if cid in {r['card_id'] for r in finalists} else 'CURRENT_WATCH_RIVAL',
            'origins':by[cid].origins} for cid in wanted],
        'omitted_finalists':[r['card_id'] for r in finalists if r['card_id'] not in wanted],
        'scope':'SOURCE_IDENTICAL_CONTROL; NO_MODEL_CALL_IMPLIED'}


def apply_native_research_advice(candidates,dispositions,consultant,*,as_of):
    """Advice can reorder/defer already eligible research, never admit evidence."""
    control=[r['card_id'] for r in candidates];picked=[];decisions=list(dispositions);links=[]
    age=(utc(as_of)-utc(consultant['request_created_at_utc'])).total_seconds() if consultant.get('request_created_at_utc') else None
    provenance=consultant.get('card_review_provenance',{})
    valid=consultant.get('status')=='VALIDATED_ADVISORY_ONLY' and age is not None and (bool(provenance) or 0<=age<=600)
    advice={a['card_id']:a for a in consultant.get('reply',{}).get('interpretations',())
        if not provenance or a['card_id'] in provenance and 0<=(utc(as_of)-utc(
            provenance[a['card_id']]['request_created_at_utc'])).total_seconds()<=600} if valid else {}
    for r in candidates:
        a=advice.get(r['card_id'])
        if a:
            challenge={k:a[k] for k in ('priority','interpretation','strongest_rival','falsifying_question',
                'supporting_evidence_ids','contradicting_ids','missed_traps','null_hypothesis')}
            challenge.update(material_sha256=provenance.get(r['card_id'],{}).get('material_sha256',consultant['material_sha256']),
                confidence_limit='ADVISORY_INTERPRETATION_OF_SUPPLIED_SOURCES; NO_PROBABILITY_OR_METHOD_CERTIFICATE')
            links.append({'card_id':r['card_id'],'native_symbol':r['instrument'],'challenge':challenge,
                'disposition':'DEFER_NATIVE_RIVAL_CHALLENGE' if a['priority']=='DECLINE' or a['null_hypothesis'] else 'CONDITIONAL_RESEARCH_ONLY'})
            if a['priority']=='DECLINE' or a['null_hypothesis']:
                decisions.append({'card_id':r['card_id'],'native_symbol':r['instrument'],
                    'disposition':'DEFER_NATIVE_RIVAL_CHALLENGE','challenge':challenge,
                    'recheck':a['falsifying_question']});continue
            r={**r,'native_challenge':challenge,'analyst_question':a['falsifying_question']}
        r={**r,'reasoning_status':'NATIVE_REVIEWED' if a else 'DETERMINISTIC_ONLY',
            'native_review_coverage_complete':consultant.get('status')=='VALIDATED_ADVISORY_ONLY'}
        picked.append(r)
    picked.sort(key=lambda r:({'INVESTIGATE':0,'WATCH':1,'UNKNOWN':2}.get(
        advice.get(r['card_id'],{}).get('priority'),1),control.index(r['card_id'])))
    for rank,r in enumerate(picked,1):
        r['rank']=rank
        r['ranking_basis']={'research_room':r['research_room']['status'],
            'distance_atr':r['distance_atr_at_verification'],'source_age_seconds':r['source_age_seconds'],
            'ordering':'NATIVE_QUESTION_PRIORITY_WHEN_VALID; OBSERVED_ROOM_THEN_PROXIMITY_THEN_FRESHNESS',
            'compared_with':[x['instrument'] for x in picked[rank:]],'calibrated_predictive_score':False}
    return picked,decisions,{'as_of':as_of,'identical_source_deterministic_control':control,
        'native_assisted_card_ids':[r['card_id'] for r in picked if r['card_id'] in advice],
        'output_card_ids':[r['card_id'] for r in picked],'linked_decisions':links,
        'accepted_current_advice':valid,'ranking_or_membership_changed':control!=[r['card_id'] for r in picked],
        'performance_improvement_established':False,'hard_gates_changed':False}
