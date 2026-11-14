"""Source-cited causal research cards, room/economics and transparent admission.

No entries, stops, targets, position sizing, confidence probabilities or orders.
The typed engine can review qualified facts; current recorded trials stay gated.
"""
from dataclasses import dataclass, asdict, replace
from decimal import Decimal as D
from .contracts import ContractError, utc, number
from .research import cited, fact_id
from .structures import Reference

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
            if (e['reference_id']!=r.id or utc(e['occurred_from'])<utc(r.known_at)
                    or not utc(e['occurred_from'])<utc(e['occurred_to'])<=utc(e['known_at'])<=utc(e['available_at'])
                    or utc(e['known_at'])>utc(self.cutoff) or not e['source_ids']):
                raise ContractError('EVENT_CAUSAL_TIME')
            times.append(utc(e['known_at']));ids.append(e['id'])
        if times!=sorted(times) or len(ids)!=len(set(ids)):
            raise ContractError('LEDGER_NONCHRONOLOGICAL_EVENT')
        for h in self.hypotheses:
            if not set(h.supporting_ids+h.contradicting_ids)<=set(ids):
                raise ContractError('HYPOTHESIS_UNKNOWN_EVIDENCE')

    @property
    def id(self): return fact_id(self.native_symbol,self.reference.id,self.window_start,self.cutoff)

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
        opposing_kinds=({'SWING_HIGH','RANGE_TOP','DAILY_HIGH','WEEKLY_HIGH'} if direction==1
            else {'SWING_LOW','RANGE_BOTTOM','DAILY_LOW','WEEKLY_LOW'})
        if r.kind not in opposing_kinds and not (r.kind in {'FVG_CANDIDATE','IFVG_CANDIDATE'}
                and r.direction==-direction):continue
        if (utc(r.known_at)>utc(card.window_start) or utc(r.available_at)>utc(card.window_start)
                or utc(r.valid_until)<utc(as_of)):continue
        edge=r.lo if direction==1 else r.hi
        if direction*(edge-number(origin.value))>0:
            choices.append((direction*(edge-number(origin.value)),r.id,edge,r))
    if not choices:return {'status':'ROOM_UNKNOWN','reason':'NO_PREKNOWN_OPPOSING_OBSTACLE','evidence_ids':[origin.id,current.id]}
    _,rid,edge,r=min(choices,key=lambda x:(x[0],x[1]))
    if not set(r.source_ids)<=set(facts):raise ContractError('HYPOTHESIS_UNKNOWN_EVIDENCE')
    gross=max(D(0),direction*(edge-number(current.value)))
    lifecycle=[facts[i] for i in card.evidence_ids if i in facts and facts[i].measurement=='OBSTACLE_LIFECYCLE'
        and isinstance(facts[i].value,dict) and facts[i].value.get('reference_id')==rid
        and facts[i].usable(as_of=as_of,native_symbol=card.native_symbol,qualified=True)
        and utc(facts[i].value['after'])<=utc(card.window_start)]
    consumed=any(f.value.get('consumed') is True for f in lifecycle)
    return {'status':'ROOM_EXHAUSTED' if gross==0 or consumed else 'ROOM_OBSERVED','first_obstacle_id':rid,
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
    status='ECONOMICS_UNKNOWN' if room['status']=='ROOM_UNKNOWN' else (
        'ECONOMICS_FAVORABLE_FOR_RESEARCH' if room['room_bps']>friction else 'ECONOMICS_UNFAVORABLE')
    assumptions=[f.id for f in found.values() if f.source_id.startswith('DECLARED_RESEARCH_')]
    if status=='ECONOMICS_FAVORABLE_FOR_RESEARCH' and assumptions:status='ECONOMICS_CONDITIONAL_RESEARCH_SCENARIO'
    return {'status':status,'observed_friction_bound_bps':friction,'assumption_evidence_ids':assumptions,
        'horizon_seconds':vals['HORIZON_SECONDS'],'evidence_ids':[f.id for f in found.values()],
        'scope':'SOURCE_DECLARED_BOUNDS; EXECUTION_NOT_CERTIFIED'}


def _sequence(card):
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
    if not raw_ids<=set(facts):raise ContractError('HYPOTHESIS_UNKNOWN_EVIDENCE')
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
    if utc(card.reference.valid_until)<utc(as_of) or primary.contradicting_ids:
        stage='INVALIDATED';reason='REFERENCE_EXPIRED_OR_CAUSAL_PREMISE_CONTRADICTED'
    elif room['status']=='ROOM_EXHAUSTED':stage='LATE';reason='FIRST_PREKNOWN_OBSTACLE_CONSUMED'
    elif not cited(card.evidence_ids,facts,as_of=as_of,native_symbol=card.native_symbol):
        stage='UNKNOWN';reason='MISSING_STALE_OR_INCOMPLETE_SOURCE'
    elif complete and current and primary.verdict=='SUPPORTED' and card.qualification=='QUALIFIED' and significance and significance.value in {'HIGH','MED'} and room['status']=='ROOM_OBSERVED' and eco['status']=='ECONOMICS_FAVORABLE_FOR_RESEARCH':
        stage='READY_FOR_DEEP';reason='NECESSARY_PRESENT_STAGE_FACTS_VERIFIED'
        event_age=(utc(as_of)-utc(card.events[-1]['known_at'])).total_seconds()
        if event_age<=900 and proximity and proximity.value is True:
            stage='FAST_WITH_ROOM';reason='RECENT_VERIFIED_EVENT_WITH_ROOM_AND_FRICTION'
    elif complete and current and primary.verdict=='SUPPORTED' and card.qualification=='QUALIFIED' and significance and significance.value in {'HIGH','MED'} and room['status']=='ROOM_OBSERVED' and eco['status']=='ECONOMICS_CONDITIONAL_RESEARCH_SCENARIO':
        stage='CONDITIONAL_FOR_DEEP';reason='CAUSAL_RESEARCH_QUESTION_WITH_EXPLICIT_ECONOMIC_ASSUMPTIONS; ANALYST_MAY_DECLINE'
    elif sequence_ids and significance and proximity and proximity.value is True:
        stage='APPROACHING_DECISION';reason='CAUSAL_SEQUENCE_AND_SIGNIFICANT_DECISION_AREA'
    elif sequence_ids or primary.supporting_ids:
        stage='DEVELOPING';reason='PARTIAL_OR_TRIAL_CAUSAL_FORMATION; ADMISSION_DEPENDENCIES_UNRESOLVED'
    elif card.events:stage='EARLY';reason='PREKNOWN_REFERENCE_AND_INITIATING_EVIDENCE'
    else:stage='PREMATURE';reason='APPLICABLE_METHOD_WITHOUT_MEANINGFUL_SEQUENCE'
    missing=[]
    if not complete:missing.append('COMPLETE_FAMILY_SEQUENCE')
    if not current or card.qualification!='QUALIFIED':missing.append('QUALIFIED_CURRENT_SEQUENCE')
    if not significance:missing.append('REFERENCE_SIGNIFICANCE')
    if room['status']=='ROOM_UNKNOWN':missing.append('PREKNOWN_FIRST_OBSTACLE_AND_FRESH_PRICE')
    if eco['status']!='ECONOMICS_FAVORABLE_FOR_RESEARCH':missing.append(eco['status'])
    clusters=tuple(sorted({facts[i].cluster for i in card.evidence_ids}))
    from .settings import load_config
    methods={m['id']:m for m in load_config()['methods']}
    citation_ids=set(card.evidence_ids)|raw_ids|set(room.get('evidence_ids',()))
    return {'card_id':card.id,'instrument':card.native_symbol,'scope':card.venue+'_PERPETUAL',
        'stage':stage,'reason_code':reason,'side_hypothesis':primary.direction,
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
        'exposure_cluster':card.exposure_cluster,'trade_authorization':False}


def shortlist(reviews, *, coverage, max_count=5, not_reviewed=()):
    if type(max_count) is not int or not 0<=max_count<=5:raise ContractError('MAX_SHORTLIST_FIVE')
    rows=list(reviews)
    if len({r['card_id'] for r in rows})!=len(rows):raise ContractError('CONFLICTING_STRUCTURE_DUPLICATE')
    eligible=[r for r in rows if r['stage'] in {'READY_FOR_DEEP','FAST_WITH_ROOM','CONDITIONAL_FOR_DEEP'}]
    def dimensions(r):
        return (2 if r['historical_significance']=='HIGH' else 1,
                1 if r['stage']=='FAST_WITH_ROOM' else 0,-r['contradiction_load'])
    comparisons=[];fronts=[];remaining=list(eligible)
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
                    'dimensions':['historical_significance','urgency','contradiction_load'],
                    'family_relative':bool(set(a['family_ids'])&set(b['family_ids'])),
                    'room_economics':'Both passed necessary safeguards; unlike distances not forced into a score'})
            if not dominated:front.append(a)
        fronts.append(front);remaining=[r for r in remaining if r not in front]
    selected=[];clusters=set()
    for front in fronts:
        while front and len(selected)<max_count:
            a=min(front,key=lambda r:(r['exposure_cluster']!='UNKNOWN' and r['exposure_cluster'] in clusters,r['card_id']))
            front.remove(a);selected.append(a);clusters.add(a['exposure_cluster'])
    selected_ids={r['card_id'] for r in selected}
    return {'schema_version':'openbot.research-review.v1','shortlist':selected,
        'watches':[r for r in rows if r['stage'] in {'PREMATURE','EARLY','DEVELOPING','APPROACHING_DECISION','UNKNOWN'}],
        'near_misses':[dict(r,admission_reason='RESEARCH_CAPACITY_OR_DIVERSITY') for r in eligible if r['card_id'] not in selected_ids],
        'invalidations':[r for r in rows if r['stage']=='INVALIDATED'],
        'late':[r for r in rows if r['stage']=='LATE'],'not_reviewed':list(not_reviewed),
        'pairwise_comparison':comparisons,'coverage':coverage,'llm_calls':0,'trade_authorization':False,
        'new_orders_created':0,'empty_shortlist_reason':None if selected else 'NO_QUALIFIED_HANDOFF_WITHIN_OBSERVED_COVERAGE; NOT_A_NO_OPPORTUNITIES_CLAIM'}
