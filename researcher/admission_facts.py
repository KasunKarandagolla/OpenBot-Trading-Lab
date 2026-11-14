"""Selected source-backed admission facts. No invented missing market data."""
from decimal import Decimal as D
from .contracts import utc,number,digest,encode
from .research import Fact,fact_id
from .observations import WIDTHS
from .economic_sources import book_cost


def attach(card,facts,references,bars,instrument,source,depth,assumptions,*,as_of):
    ids=list(card.evidence_ids);ref=card.reference;received=source['receipt']['received_at_utc']
    def add(measurement,value,units,*,end=None,available=None,provider='OFFICIAL_BINANCE_SELECTED',source_hash=None,age=None):
        end=end or card.cutoff;available=available or received
        fid=fact_id(card.id,measurement,value,source_hash or source['source_response_sha256'])
        f=Fact(fid,instrument,measurement,value,units,card.timeframe,end,available,available,
            max((available,received),key=utc),provider,source_hash or source['source_response_sha256'],
            'EXACT_REPORTED',True,'QUALIFIED',card.mode,age or 300*WIDTHS[card.timeframe])
        facts[f.id]=f;ids.append(f.id)
    add('DECISION_PRICE',(ref.lo+ref.hi)/2,'USDT_PER_BASE',end=ref.known_at,available=ref.available_at)
    # Significance is a declared measured pivot subclass, never a rolling level.
    pivots=[j for j,b in enumerate(bars) if b.open_ms//1000==int(utc(ref.created_at).timestamp())]
    if pivots:
        k=pivots[0]
        if 2<=k<len(bars)-2:
            level=ref.hi if ref.direction==1 else ref.lo
            leg=min(level-min(b.low for b in bars[k-2:k]),level-min(b.low for b in bars[k+1:k+3])) if ref.direction==1 else min(
                max(b.high for b in bars[k-2:k])-level,max(b.high for b in bars[k+1:k+3])-level)
            if leg>=ref.atr:
                add('REFERENCE_SIGNIFICANCE','MED','ORDINAL',end=ref.known_at,available=ref.available_at)
    add('DECISION_PROXIMITY',abs(bars[-1].close-(ref.lo+ref.hi)/2)<=ref.atr,'BOOLEAN')
    side=next(h.direction for h in card.hypotheses if h.family==card.primary_family)
    direction=1 if side=='BULLISH' else -1
    relevant=[b for b in bars if b.open_ms>=int(utc(card.window_start).timestamp()*1000)]
    for r in references:
        if r.id==ref.id or r.native_symbol!=card.native_symbol:continue
        if utc(r.known_at)>utc(card.window_start):continue
        edge=r.lo if direction==1 else r.hi
        add('OBSTACLE_LIFECYCLE',{'reference_id':r.id,'after':card.window_start,
            'consumed':any(b.high>=edge if direction==1 else b.low<=edge for b in relevant)},'REFERENCE_STATE')
    if not depth:return tuple(ids),{'status':'UNKNOWN','reason':'NO_CURRENT_TARGETED_DEPTH'}
    from dataclasses import replace
    from .candidate_review import remaining_room
    room=remaining_room(replace(card,evidence_ids=tuple(ids)),facts,references,as_of=as_of)
    obstacle=next((r for r in references if r.id==room.get('first_obstacle_id')),None)
    cost=book_cost(depth,instrument,notional=assumptions['probe_notional_usdt'],
        obstacle=(obstacle.lo if direction==1 else obstacle.hi) if obstacle else None,direction=direction)
    if cost['status']!='OBSERVED':return tuple(ids),cost
    # These are fresh source observations; future book persistence is conditional.
    common={'end':depth['time'],'available':depth['received'],'source_hash':depth['source_hash'],
        'provider':'OFFICIAL_BINANCE_DISPLAYED_DEPTH','age':30}
    if cost['depth_usdt_within_room'] is not None:
        add('DEPTH_USDT_WITHIN_ROOM',cost['depth_usdt_within_room'],'USDT',**common)
    # Bounds below are explicitly declared scenarios, not account facts or a
    # guarantee of future funding/fills. They can produce only CONDITIONAL.
    for measurement,value,units in (
        ('ROUND_TRIP_FEE_BPS',D(assumptions['round_trip_fee_assumption_bps']),'BPS'),
        ('SLIPPAGE_BOUND_BPS',cost['slippage_excluding_spread_bps']+D(assumptions['additional_slippage_assumption_bps']),'BPS'),
        ('FUNDING_BOUND_BPS',D(assumptions['funding_assumption_bound_bps']),'BPS'),
        ('HORIZON_SECONDS',D(assumptions['max_horizon_seconds']),'SECONDS'),
        ('HORIZON_RELEVANT',bool(card.events) and (utc(as_of)-utc(card.events[-1]['known_at'])).total_seconds()<=54000,'BOOLEAN')):
        add(measurement,value,units,provider='DECLARED_RESEARCH_SCENARIO:'+assumptions['fee_source'],
            source_hash=digest(encode(assumptions).encode()),end=card.cutoff)
    return tuple(ids),{**cost,'assumptions':assumptions,'room':room,
        'horizon_scope':'RESEARCH_QUESTION_EXPIRES_WITHIN_15H; NO_PREDICTED_PRICE_ARRIVAL'}
