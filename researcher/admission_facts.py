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
    add('DECISION_PRICE',(ref.lo+ref.hi)/2,'USDT_PER_BASE',end=ref.known_at,available=ref.available_at,
        provider='FROZEN_REFERENCE_LEDGER:'+ref.id,source_hash=digest(encode(ref).encode()))
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
        ('HORIZON_RELEVANT',bool(card.events) and (utc(as_of)-utc(
            card.formation['families'][card.primary_family]['timeline'][-1]['known_at'] if card.formation else
            card.events[-1]['known_at'])).total_seconds()<=54000,'BOOLEAN')):
        add(measurement,value,units,provider='DECLARED_RESEARCH_SCENARIO:'+assumptions['fee_source'],
            source_hash=digest(encode(assumptions).encode()),end=card.cutoff)
    return tuple(ids),{**cost,'assumptions':assumptions,'room':room,
        'horizon_scope':'RESEARCH_QUESTION_EXPIRES_WITHIN_15H; NO_PREDICTED_PRICE_ARRIVAL'}


def refresh_cached(export,api,pulse,members,assumptions,*,clock,sources,refresh=True):
    """Reassess frozen admissions with current point sources, without history.

    The existing export is the single typed cache contract. New point evidence
    cannot manufacture new closed events or move their original availability.
    """
    from dataclasses import replace,asdict
    from .handoff import decode_export
    from .economic_sources import depth_snapshot
    from .candidate_review import remaining_room
    from .contracts import ContractError
    from .screening import safe_error
    cards=[];facts={};references={};faults=[];depths={};consumed=[]
    for card,own,refs in decode_export(export):
        n=card.native_symbol;inst=members[n]
        if card.formation and card.primary_family not in sources.qualified(n,card.timeframe,card.cutoff,as_of=clock()):
            card=replace(card,qualification='TRIAL')
        ids=list(card.evidence_ids)
        def add(measurement,value,units,end,received,provider,source_hash,age=30):
            fid=fact_id(card.id,measurement,value,source_hash)
            own[fid]=Fact(fid,inst,measurement,value,units,'CURRENT',end,end,received,received,
                provider,source_hash,'EXACT_REPORTED',True,'QUALIFIED',card.mode,age,cluster='EXECUTION_FRICTION')
            ids.append(fid);return own[fid]
        if refresh:
            changed={'RESEARCH_PRICE','SPREAD_BPS','DEPTH_USDT_WITHIN_ROOM','SLIPPAGE_BOUND_BPS','HORIZON_RELEVANT'}
            ids=[i for i in ids if own[i].measurement not in changed]
            books=[o for p in pulse if p['kind']=='book' for o in p['observations'] if o['native_symbol']==n]
            if len(books)==1:
                b=books[0];end=b['source_time_utc'];received=b['received_at_utc'];sha=b['source_response_sha256']
                add('RESEARCH_PRICE',(b['values']['bid']+b['values']['ask'])/2,'USDT_PER_BASE',end,received,'OFFICIAL_BINANCE_TOP_OF_BOOK',sha)
                add('SPREAD_BPS',b['values']['spread_bps'],'BPS',end,received,'OFFICIAL_BINANCE_TOP_OF_BOOK',sha)
            else:faults.append({'phase':'cached_quote','symbol':n,'code':'FRESH_BOOK_UNAVAILABLE_OR_AMBIGUOUS'})
            at=clock();latest=card.formation['families'][card.primary_family]['timeline'][-1] if card.formation else card.events[-1]
            add('HORIZON_RELEVANT',(utc(at)-utc(latest['known_at'])).total_seconds()<=54000,'BOOLEAN',at,at,
                'DECLARED_RESEARCH_SCENARIO:CURRENT_RESEARCH_HORIZON',digest(encode([latest['id'],at]).encode()))
            card=replace(card,evidence_ids=tuple(ids))
            room=remaining_room(card,own,refs,as_of=clock())
            if room['status']=='ROOM_EXHAUSTED' and books:
                b=books[0]
                witness=add('OBSTACLE_LIFECYCLE',{'reference_id':room['first_obstacle_id'],
                    'after':card.window_start,'consumed':True,'witnessed_at':b['source_time_utc']},
                    'REFERENCE_STATE',b['source_time_utc'],b['received_at_utc'],'OFFICIAL_BINANCE_TOP_OF_BOOK',
                    b['source_response_sha256'],age=7*86400)
                consumed.append({'native_symbol':n,'candidate_reference_id':card.reference.id,
                    'event_window_start':card.window_start,'obstacle_id':room['first_obstacle_id'],
                    'valid_until':card.reference.valid_until,'fact':asdict(witness)})
            if room['status']=='ROOM_OBSERVED':
                if n not in depths:
                    try:depths[n]=depth_snapshot(api,inst)
                    except (ContractError,OSError,KeyError,ValueError,TypeError) as e:
                        depths[n]=None;faults.append({'phase':'cached_native_depth','symbol':n,'code':safe_error(e)})
                depth=depths[n]
                if depth:
                    side=next(h.direction for h in card.hypotheses if h.family==card.primary_family)
                    direction=1 if side=='BULLISH' else -1
                    obstacle=next(r for r in refs if r.id==room['first_obstacle_id'])
                    cost=book_cost(depth,inst,notional=assumptions['probe_notional_usdt'],
                        obstacle=obstacle.lo if direction==1 else obstacle.hi,direction=direction)
                    if cost['status']=='OBSERVED':
                        add('DEPTH_USDT_WITHIN_ROOM',cost['depth_usdt_within_room'],'USDT',depth['time'],
                            depth['received'],'OFFICIAL_BINANCE_DISPLAYED_DEPTH',depth['source_hash'])
                        add('SLIPPAGE_BOUND_BPS',cost['slippage_excluding_spread_bps']+
                            D(assumptions['additional_slippage_assumption_bps']),'BPS',depth['time'],depth['received'],
                            'DECLARED_RESEARCH_SCENARIO:'+assumptions['fee_source'],
                            digest(encode([depth['source_hash'],assumptions]).encode()))
                    else:faults.append({'phase':'cached_native_depth','symbol':n,'code':cost.get('reason','DEPTH_UNASSESSABLE')})
            card=replace(card,evidence_ids=tuple(dict.fromkeys(ids)))
        cards.append(card);facts.update(own);references.update({r.id:r for r in refs})
    return cards,facts,list(references.values()),faults,consumed
