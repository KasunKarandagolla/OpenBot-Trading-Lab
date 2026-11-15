"""Selected source-backed admission facts. No invented missing market data."""
from decimal import Decimal as D
import time
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
    # Horizon and declared scenarios are independently sourceable. A depth gap
    # must not erase unrelated answers or become an undifferentiated UNKNOWN.
    for measurement,value,units in (
        ('ROUND_TRIP_FEE_BPS',D(assumptions['round_trip_fee_assumption_bps']),'BPS'),
        ('FUNDING_BOUND_BPS',D(assumptions['funding_assumption_bound_bps']),'BPS'),
        ('HORIZON_SECONDS',D(assumptions['max_horizon_seconds']),'SECONDS'),
        ('HORIZON_RELEVANT',bool(card.events) and (utc(as_of)-utc(
            card.formation['families'][card.primary_family]['timeline'][-1]['known_at'] if card.formation else
            card.events[-1]['known_at'])).total_seconds()<=54000,'BOOLEAN')):
        add(measurement,value,units,provider='DECLARED_RESEARCH_SCENARIO:'+assumptions['fee_source'],
            source_hash=digest(encode(assumptions).encode()),end=card.cutoff)
    if not depth:return tuple(ids),{'status':'SOURCE_GAP','reason':'NO_CURRENT_TARGETED_DEPTH',
        'source_gaps':['DEPTH_USDT_WITHIN_ROOM','SLIPPAGE_BOUND_BPS'],
        'answered_independently':['ROUND_TRIP_FEE_BPS_SCENARIO','FUNDING_BOUND_BPS_SCENARIO','HORIZON_RELEVANT']}
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
        ('SLIPPAGE_BOUND_BPS',cost['slippage_excluding_spread_bps']+D(assumptions['additional_slippage_assumption_bps']),'BPS'),
        ):
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


def refresh_selected(cards,facts,references,api,inventory,assumptions,*,clock,max_depth=8):
    """Refresh point evidence after computation, for selected coins only.

    A displayed book at today's quote cannot certify future liquidity at a
    distant decision price. Persist its observed probe and that exact limitation.
    """
    from dataclasses import replace
    from .economic_sources import depth_snapshot
    from .candidate_review import remaining_room
    from .contracts import ContractError
    from .screening import safe_error
    pulse=api.pulse(inventory,partial=True,kinds=('book',))
    books={o['native_symbol']:o for p in pulse for o in p['observations']}
    members={i.native_symbol:i for i in inventory.instruments};depths={};faults=[]
    ranking={}
    for c in cards:
        if c.native_symbol in {'BTCUSDT','ETHUSDT'} or c.native_symbol not in books:continue
        primary=next(h for h in c.hypotheses if h.family==c.primary_family)
        if primary.contradicting_ids or not primary.supporting_ids:continue
        b=books[c.native_symbol];mid=(b['values']['bid']+b['values']['ask'])/2
        d=max(c.reference.lo-mid,mid-c.reference.hi,D(0))/c.reference.atr
        ranking[c.native_symbol]=min(ranking.get(c.native_symbol,D('Infinity')),d)
    depth_started=time.monotonic()
    for n in sorted(ranking,key=lambda n:(ranking[n],n))[:max_depth]:
        if ranking[n]>D('2.5'):continue
        if time.monotonic()-depth_started>=30:
            faults.append({'phase':'current_candidate_depth','symbol':n,'code':'CURRENT_DEPTH_DEFERRED_SOURCE_BUDGET'})
            continue
        try:depths[n]=depth_snapshot(api,members[n])
        except (ContractError,OSError,ValueError,KeyError,TypeError) as e:
            faults.append({'phase':'current_candidate_depth','symbol':n,'code':safe_error(e)})
    # Independent depth requests can take longer than quote freshness. Reprice
    # AFTER them; never let optional book latency erase every valid structure.
    checked_at=clock()
    if books and any((utc(checked_at)-utc(b['source_time_utc'])).total_seconds()>15 for b in books.values()):
        fresh=api.pulse(inventory,partial=True,kinds=('book',))
        books.update({o['native_symbol']:o for p in fresh for o in p['observations']})
    # Books can age during depth retrieval. The consumer rechecks every point's
    # own timestamp against the actual completion time; no freshness stamping.
    at=clock();updated=[]
    for c in cards:
        ids=[i for i in c.evidence_ids if facts[i].measurement not in {
            'RESEARCH_PRICE','SPREAD_BPS','DEPTH_USDT_WITHIN_ROOM','SLIPPAGE_BOUND_BPS','DISPLAYED_BOOK_PROBE'}]
        def add(measurement,value,units,end,received,provider,sha):
            fid=fact_id(c.id,measurement,value,sha)
            facts[fid]=Fact(fid,members[c.native_symbol],measurement,value,units,'CURRENT',end,end,
                received,received,provider,sha,'EXACT_REPORTED',True,'QUALIFIED',c.mode,30,
                cluster='EXECUTION_FRICTION');ids.append(fid)
        b=books.get(c.native_symbol)
        if b:
            add('RESEARCH_PRICE',(b['values']['bid']+b['values']['ask'])/2,'USDT_PER_BASE',
                b['source_time_utc'],b['received_at_utc'],'OFFICIAL_BINANCE_TOP_OF_BOOK',b['source_response_sha256'])
            add('SPREAD_BPS',b['values']['spread_bps'],'BPS',b['source_time_utc'],b['received_at_utc'],
                'OFFICIAL_BINANCE_TOP_OF_BOOK',b['source_response_sha256'])
        d=depths.get(c.native_symbol)
        if d and not 0<=(utc(at)-utc(d['time'])).total_seconds()<=30:
            faults.append({'phase':'current_candidate_depth','symbol':c.native_symbol,
                'code':'CURRENT_DEPTH_EXPIRED_DURING_COLLECTION'})
            d=None
        if d:
            own_references=[r for r in references if r.native_symbol==c.native_symbol]
            room=remaining_room(replace(c,evidence_ids=tuple(ids)),facts,own_references,as_of=at)
            obstacle=next((r for r in own_references if r.id==room.get('first_obstacle_id')),None)
            side=next(h.direction for h in c.hypotheses if h.family==c.primary_family)
            cost=book_cost(d,members[c.native_symbol],notional=assumptions['probe_notional_usdt'],
                obstacle=(obstacle.lo if side=='BULLISH' else obstacle.hi) if obstacle else None,
                direction=1 if side=='BULLISH' else -1)
            add('DISPLAYED_BOOK_PROBE',cost,'SNAPSHOT_PROBE',d['time'],d['received'],
                'OFFICIAL_BINANCE_DISPLAYED_DEPTH',d['source_hash'])
            if cost['status']=='OBSERVED':
                if cost['depth_usdt_within_room'] is not None:
                    add('DEPTH_USDT_WITHIN_ROOM',cost['depth_usdt_within_room'],'USDT',d['time'],d['received'],
                        'OFFICIAL_BINANCE_DISPLAYED_DEPTH',d['source_hash'])
                add('SLIPPAGE_BOUND_BPS',cost['slippage_excluding_spread_bps']+
                    D(assumptions['additional_slippage_assumption_bps']),'BPS',d['time'],d['received'],
                    'DECLARED_RESEARCH_SCENARIO:'+assumptions['fee_source'],d['source_hash'])
        updated.append(replace(c,evidence_ids=tuple(ids)))
    return updated,list(depths.values()),faults,at
