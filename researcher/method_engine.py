"""31 named methodology implementations and strict source-dependent reducers.

Registry membership is distinct from algorithm execution and qualification.
Method results describe observable facts, never orders or future success.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, time, timezone
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from .contracts import ContractError, number, utc
from .numerics import (confirmed_swings, swing_ladder, wilder_atr, displacement,
    anchored_value, touch_episodes, efficiency)
from .structures import (Reference, stable_id, event, swing_breaks, gap_lifecycle,
    equal_level_references, swing_references)
from .family_engine import (closed_prefix, boundary_family, balance_references,
    reference, evaluate_families)
from .measurements import (value_extension, flow_divergence, persistent_residual,
    sector_strength, oi_decomposition, funding_basis, catalyst)
from .specialists import (true_profile, profile_nodes, first_profile_revisit,
    footprint, aggression_attempts, liquidations, profile_analysis, SpecialistEnvelope)

VERSION='method-engine-6a.1'
DEPENDENCIES={
    'M14':'PRIMARY_SOURCE_TIMING_DEFINITION_AND_CRYPTO_APPLICABILITY',
    'M15':'KEEPSY_PRIMARY_SOURCE_EXACT_OPERATIONAL_RULES',
    'M17':'COMPLETE_EXECUTED_TAPE_VENUE_WINDOW_BINS',
    'M18':'TRUE_PROFILE_AND_CONTIGUOUS_FIRST_REVISIT_HISTORY',
    'M22':'COMPLETE_AGGRESSOR_PRICE_BIN_EXECUTIONS',
    'M23':'COMPARABLE_EXECUTED_ATTEMPTS_AND_LATER_RESPONSE',
    'M24':'COMPARABLE_EXECUTED_ATTEMPTS_AND_LATER_RESPONSE',
    'M25':'CURRENT_ORDERED_NATIVE_DEPTH', 'M26':'SYNCHRONIZED_NATIVE_OI_MARK_AND_MULTIPLIER',
    'M27':'RATE_KIND_ACTUAL_INTERVAL_UNITS_AND_ALIGNED_MARK_INDEX',
    'M28':'OBSERVED_FORCED_EXECUTIONS_AND_SAMPLING',
    'M29':'MATCHED_BENCHMARK_AND_DATED_PERP_SECTOR_MEMBERSHIPS',
    'M31':'VERIFIED_ORIGINAL_PUBLISHER_AND_CONTRACT_MAPPING'}


def result(method, value=None, *, status=None, reason=None):
    if method not in {'M'+str(i).zfill(2) for i in range(1,32)}:
        raise ContractError('UNKNOWN_METHODOLOGY')
    pending=method in {'M14','M15'}
    return {'method_id':method,'status':status or ('COMPUTED' if value is not None else
        'DEFINITION_PENDING' if pending else 'SOURCE_CAPABILITY_REQUIRED'),
        'value':value,'reason':reason or (DEPENDENCIES.get(method) if value is None else None),
        'implemented_code':method!='M15','source_supported':False,
        'method_formation_verified':False,'whole_universe_coverage':False,
        'empirically_useful':False,'production_enabled':False,'version':VERSION}


def zone_lifecycle(ref,bars,*,as_of):
    """Same original zone, two distal closes, then *later* retest; no new box."""
    if any(b.native_symbol!=ref.native_symbol or b.timeframe!=ref.timeframe for b in bars):
        raise ContractError('REFERENCE_BAR_IDENTITY')
    if utc(ref.available_at)>utc(as_of):return {'status':'SOURCE_UNKNOWN','events':[],'reference_id':ref.id}
    events=[];count=0;breach=None;flipped=False;fraction=D(0);visits=0;armed=True
    for b in bars:
        if b.open_ms<int(utc(ref.known_at).timestamp()*1000):continue
        if utc(b.end)>utc(ref.valid_until):events.append(event(ref,b,'EXPIRED'));break
        touched=b.high>=ref.lo and b.low<=ref.hi
        through=b.close<ref.lo-ref.buffer if ref.direction==1 else b.close>ref.hi+ref.buffer
        if touched and armed:
            visits+=1;armed=False;events.append(event(ref,b,'FIRST_ZONE_REVISIT' if visits==1 else 'SUBSEQUENT_ZONE_REVISIT'))
        elif not touched and max(ref.lo-b.high,b.low-ref.hi,D(0))>=D('.5')*ref.atr:armed=True
        if touched:
            span=ref.hi-ref.lo
            fraction=max(fraction,max(D(0),min(b.high,ref.hi)-max(b.low,ref.lo))/span if span else D(1))
        if breach is None:
            count=count+1 if through else 0
            if count==2:breach=b;events.append(event(ref,b,'ZONE_ACCEPTED_THROUGH'))
        elif b.open_ms>breach.open_ms and touched and through and not flipped:
            flipped=True;events.append(event(ref,b,'BREAKER_OPPOSITE_SIDE_RETEST'))
        elif flipped and (b.close>ref.hi+ref.buffer if ref.direction==1 else b.close<ref.lo-ref.buffer):
            events.append(event(ref,b,'BREAKER_INVALIDATED'));break
    return {'reference_id':ref.id,'events':[dict(asdict(e),id=e.id) for e in events],
        'visits':visits,'mitigation_fraction_bar_overlap':fraction,'accepted_breach':breach is not None,
        'breaker_candidate':flipped,'intrabar_execution':None}


def order_blocks(bars,tick,*,as_of):
    """Full-candle base (1–4), displacement, later BOS; zone born at BOS."""
    breaks=swing_breaks(bars,tick,as_of=as_of);out=[];atr=wilder_atr(bars) if len(bars)>=15 else []
    for e in breaks['events']:
        if e.kind!='BOS':continue
        i=next(j for j,b in enumerate(bars) if b.end==e.known_at);side=e.direction
        for j in range(i-1,max(14,i-5),-1):
            if not atr[j-1]:continue
            dp=displacement(bars[j-1],bars[j],atr[j-1],tick)
            if not (dp['tr_atr_previous']>=D('1.2') and dp['body_fraction']>=D('.5')
                    and side*(bars[j].close-bars[j].open)>0):continue
            opposite=[k for k in range(max(0,j-4),j) if side*(bars[k].close-bars[k].open)<0]
            if not opposite:continue
            k=opposite[-1];base=bars[k:j]
            if max(b.high for b in base)-min(b.low for b in base)>D('1.5')*atr[j-1]:continue
            b=bars[k]
            from datetime import timedelta
            if utc(bars[i].available_at or bars[i].received_at)>utc(bars[i].end)+timedelta(days=7):continue
            ref=reference(bars,i,kind='ORDER_BLOCK_CANDIDATE',lo=b.low,hi=b.high,direction=side,
                tick=tick,origin=stable_id('OB_FULL_CANDLE_BASE4',b.id,e.id),defining=(b,bars[j],bars[i]))
            out.append({'reference':ref,'bos_event_id':e.id,'base_bars':len(base),
                'displacement_at':bars[j].end,'born_at':bars[i].end,
                'lifecycle':zone_lifecycle(ref,bars,as_of=as_of),'institutional_order':None})
            break
    return out


def ote(*,start,end,price,known_at,at,zones):
    """Independent confirmed impulse + actual pre-known structural confluence."""
    if (start['kind']==end['kind'] or start['index']>=end['index']
            or utc(start['known_at'])>utc(known_at) or utc(end['known_at'])>utc(known_at)
            or utc(known_at)>utc(at) or not start['id'] or not end['id']):
        raise ContractError('INDEPENDENT_CONFIRMED_IMPULSE_REQUIRED')
    a,b=number(start['price']),number(end['price']);amp=abs(b-a)
    if not amp:raise ContractError('ZERO_IMPULSE')
    side=1 if b>a else -1;rho=side*(b-number(price))/amp
    confluence=[r.id for r in zones if utc(r.known_at)<=utc(at)<=utc(r.valid_until)
        and r.lo-r.buffer<=number(price)<=r.hi+r.buffer]
    return {'retracement':rho,'in_ote_band':D('.62')<=rho<=D('.79'),
        'contextual_candidate':D('.62')<=rho<=D('.79') and bool(confluence),
        'zone_ids':confluence,'impulse_ids':(start['id'],end['id']),'independent_confirmation':False}


def crt(ref,bars,*,as_of):
    if ref.kind!='CRT_CANDLE':raise ContractError('PRESELECTED_COMPLETED_CRT_REFERENCE_REQUIRED')
    return boundary_family('F4',ref,bars,as_of=as_of)


def amd(bars,tick,*,session_start,balance_end,as_of):
    """Experimental crypto UTC session; definition declared before outcome."""
    if utc(session_start)>=utc(balance_end):raise ContractError('PREDECLARED_SESSION_REQUIRED')
    base=[b for b in bars if utc(session_start).timestamp()*1000<=b.open_ms and utc(b.end)<=utc(balance_end)]
    if not base or base[0].open_ms!=int(utc(session_start).timestamp()*1000) or base[-1].end_ms!=int(utc(balance_end).timestamp()*1000):
        raise ContractError('INCOMPLETE_SESSION_BALANCE')
    refs=balance_references(base,tick,window=len(base),baseline_end=len(base))
    return {'definition':'PREDECLARED_CRYPTO_SESSION_AMD_VARIANT','institutional_manipulation':None,
        'branches':[boundary_family('F4',r,bars,as_of=as_of) for r in refs],
        'status':'COMPUTED' if refs else 'NO_EVENT_IN_COMPLETE_WINDOW'}


@dataclass(frozen=True)
class TimingDefinition:
    source_url: str
    primary_source_quote: str
    timezone_name: str
    start_hour: int
    end_hour: int
    canonical_qualified: bool = False


def timed_subclass(at,definition):
    if not definition.source_url.startswith('https://') or not definition.primary_source_quote:
        raise ContractError('PRIMARY_TIMING_SOURCE_REQUIRED')
    if not 0<=definition.start_hour<definition.end_hour<=24:raise ContractError('TIMING_WINDOW')
    local=utc(at).astimezone(ZoneInfo(definition.timezone_name))
    return {'inside_declared_window':definition.start_hour<=local.hour<definition.end_hour,
        'utc_offset_seconds':int(local.utcoffset().total_seconds()),'local_time':local.isoformat(),
        'source_url':definition.source_url,'canonical_qualified':definition.canonical_qualified,
        'method_enabled':False,'reason':'TIMING_ALONE_CANNOT_ESTABLISH_FVG_LIQUIDITY_SEQUENCE'}


def auction(refs,bars,*,as_of,profiles=()):
    branches=[boundary_family('F6',r,bars,as_of=as_of,balance=True) for r in refs]
    migration=None
    if len(profiles)==2:
        a,b=profiles
        if (any(a[k]!=b[k] for k in ('venue','native_symbol','bin_width','bin_origin','units','va_algorithm'))
                or not a['true_profile'] or not b['true_profile'] or a['window_end']!=b['window_start']):
            raise ContractError('PROFILE_MIGRATION_SCOPE_MISMATCH')
        migration=b['poc_interval'][0]-a['poc_interval'][0]
    return {'price_only_branches':branches,'true_value_migration':migration,
        'profile_fidelity':'TRUE_EXECUTED_PROFILE' if migration is not None else 'PRICE_ONLY_AUCTION'}


def depth_walls(snapshot,*,bps=D(10),minimum_notional=D(1000)):
    if snapshot['venue']!='BINANCE_USDM' or snapshot['units']!='PRICE_USDT_PER_BASE; QUANTITY_NATIVE_BASE':
        raise ContractError('DEPTH_IDENTITY_UNITS')
    if not 0<=(utc(snapshot['received'])-utc(snapshot['time'])).total_seconds()<=30:
        raise ContractError('STALE_DEPTH')
    s=snapshot['levels'];bid=s['bids'][0][0];ask=s['asks'][0][0]
    if bid>=ask:raise ContractError('CROSSED_BOOK')
    mid=(bid+ask)/2;totals={};walls={}
    for side,rows in s.items():
        if rows!=sorted(rows,reverse=side=='bids') or len({p for p,q in rows})!=len(rows):
            raise ContractError('ORDERED_DEPTH_REQUIRED')
        for p,q in rows:number(p,positive=True);number(q,positive=True)
        inside=[(p,q) for p,q in rows if abs(p-mid)/mid*10000<=bps]
        totals[side]=sum((p*q for p,q in inside),D(0))
        walls[side]=[(p,q) for p,q in inside if p*q>=minimum_notional]
    denominator=sum(totals.values(),D(0))
    return {'displayed_usdt':totals,'walls':walls,'spread_bps':10000*(ask-bid)/mid,
        'displayed_imbalance':(totals['bids']-totals['asks'])/denominator if denominator else None,
        'snapshot_only':True,'spoofing':None,'iceberg':None}


def specialist_method(method,**inputs):
    """Typed adapters are callable now; absent external inputs remain explicit."""
    if not inputs:return result(method)
    reducers={'M17':true_profile,'M18':profile_analysis,'M22':footprint,
        'M23':aggression_attempts,'M24':aggression_attempts,'M25':depth_walls,
        'M26':oi_decomposition,'M27':funding_basis,'M28':liquidations,'M31':catalyst}
    if method not in reducers:raise ContractError('SPECIALIST_METHOD_ADAPTER_REQUIRED')
    return result(method,reducers[method](**inputs))


def analyze_specialist_envelope(method,envelope,*,as_of):
    """Provider integration boundary; qualified source status stays external."""
    expected={'M17':'EXECUTED_BASE','M18':'EXECUTED_BASE','M22':'EXECUTED_BASE',
        'M23':'EXECUTED_BASE','M24':'EXECUTED_BASE','M25':'DISPLAYED_NATIVE_BASE',
        'M26':'CONTRACTS_BASE_USDT_MARK','M27':'FUNDING_RATE_AND_BASIS',
        'M28':'OBSERVED_FORCED_BASE','M31':'DATED_ORIGINAL_SOURCE'}
    if not isinstance(envelope,SpecialistEnvelope) or method not in expected:
        raise ContractError('STRICT_SPECIALIST_ENVELOPE_SCHEMA')
    if envelope.units!=expected[method] or utc(envelope.received_at)>utc(as_of):
        raise ContractError('SPECIALIST_ENVELOPE_SCOPE_OR_TIME')
    if envelope.coverage!='COMPLETE' and method not in {'M28','M31'}:
        return result(method,reason='COMPLETE_REQUIRED_SOURCE_WINDOW_NOT_AVAILABLE')
    payload=envelope.payload
    for key in ('profile','snapshot','before','after','row'):
        row=payload.get(key)
        if isinstance(row,dict) and (row.get('native_symbol',envelope.native_symbol)!=envelope.native_symbol
                or row.get('venue',envelope.venue)!=envelope.venue):
            raise ContractError('SPECIALIST_ENVELOPE_SCOPE_OR_TIME')
    tapes=[]
    for key in ('tape','later','response'):
        if key in payload:tapes.append(payload[key])
    tapes.extend(payload.get('attempts',()))
    if any(t.native_symbol!=envelope.native_symbol or t.venue!=envelope.venue
            or utc(t.start)<utc(envelope.start) or utc(t.end)>utc(envelope.end)
            or utc(t.received_at)>utc(envelope.received_at) for t in tapes):
        raise ContractError('SPECIALIST_ENVELOPE_SCOPE_OR_TIME')
    return {**specialist_method(method,**payload),'source_envelope':{
        k:v for k,v in asdict(envelope).items() if k!='payload'}}


def evaluate_methods(bars,tick,*,cutoff,as_of,benchmark=None,references=(),families=None,inputs=None):
    bars=closed_prefix(bars,cutoff=cutoff,as_of=as_of);inputs=inputs or {}
    results={f'M{i:02d}':result(f'M{i:02d}') for i in range(1,32)}
    if not bars:return list(results.values())
    tick=number(tick,positive=True)
    refs=tuple(r for r in references if utc(r.known_at)<=utc(cutoff) and utc(r.available_at)<=utc(as_of))
    if any(r.native_symbol!=bars[0].native_symbol or r.timeframe!=bars[0].timeframe for r in refs):
        raise ContractError('REFERENCE_BAR_IDENTITY')
    swings=confirmed_swings(bars);breaks=swing_breaks(bars,tick,as_of=as_of)
    gaps=gap_lifecycle(bars,tick,as_of=as_of)
    ob=order_blocks(bars,tick,as_of=as_of) if len(bars)>=15 else []
    zones=[*refs,*(g['reference'] for g in gaps),*(o['reference'] for o in ob)]
    results['M01']=result('M01',{'swings':swings,'ladder':swing_ladder(swings)})
    # MSS requires an opposing significant break + same-side prior sweep + displacement.
    mss=[]
    for e in breaks['events']:
        if e.kind!='CHOCH_CANDIDATE':continue
        i=next(j for j,b in enumerate(bars) if b.end==e.known_at)
        if i<15:continue
        scale=wilder_atr(bars[:i])[-1]
        if not scale:continue
        dp=displacement(bars[i-1],bars[i],scale,tick)
        sweep=any(any(x['kind']=='RECLAIM' and utc(x['known_at'])<utc(e.known_at)
            for x in boundary_family('F4',r,bars[:i],as_of=as_of)['timeline'])
            for r in refs if r.direction==-e.direction)
        if sweep and dp['tr_atr_previous']>=D('1.2') and dp['body_fraction']>=D('.5'):
            mss.append(dict(asdict(e),kind='MSS_CANDIDATE',id=stable_id(e.id,'MSS')))
    results['M02']=result('M02',{'breaks':[dict(asdict(e),id=e.id) for e in breaks['events']],'mss':mss})
    results['M03']=result('M03',{'horizontal':[{'reference_id':r.id,'episodes':touch_episodes(
        [b for b in bars if b.open_ms>=int(utc(r.known_at).timestamp()*1000)],lo=r.lo,hi=r.hi,atr=r.atr,buffer=r.buffer)}
        for r in refs if any(b.open_ms>=int(utc(r.known_at).timestamp()*1000) for b in bars)],
        'supply_demand_full_candle_displacement_bos_candidates':ob})
    results['M04']=result('M04',equal_level_references(bars,tick,as_of=as_of))
    results['M05']=result('M05',[boundary_family('F4',r,bars,as_of=as_of) for r in refs])
    results['M06']=result('M06',ob)
    results['M07']=result('M07',[zone_lifecycle(r,bars,as_of=as_of) for r in zones])
    results['M08']=result('M08',gaps)
    results['M09']=result('M09',[g for g in gaps if any(e['kind']=='IFVG_OPPOSITE_SIDE_RETEST' for e in g['events'])])
    results['M10']=result('M10',[zone_lifecycle(r,bars,as_of=as_of) for r in zones])
    if 'M11' in inputs:results['M11']=result('M11',ote(**inputs['M11']))
    elif len(swings)>=2:
        end=swings[-1];starts=[s for s in swings[:-1] if s['kind']!=end['kind'] and s['index']<end['index']]
        if starts:results['M11']=result('M11',ote(start=starts[-1],end=end,price=bars[-1].close,
            known_at=end['known_at'],at=cutoff,zones=zones))
    if 'M12' in inputs:results['M12']=result('M12',crt(inputs['M12'],bars,as_of=as_of))
    else:
        # Fixed UTC first completed source candle. Selection rule is declared
        # here, before observing any subsequent excursion, and never optimized.
        selected=next((j for j in range(len(bars)-1,13,-1) if bars[j].open_ms%86400000==0),None)
        if selected is not None:
            b=bars[selected]
            scale=wilder_atr(bars[:selected+1])[-1]
            if scale:
                r=reference(bars,selected,kind='CRT_CANDLE',lo=b.low,hi=b.high,direction=1,
                    tick=tick,origin=stable_id('CRT_UTC_FIRST_CANDLE',b.id),defining=(b,))
                results['M12']=result('M12',{'selection':'PREDECLARED_UTC_FIRST_COMPLETED_CANDLE_VARIANT',
                    'upper':crt(r,bars,as_of=as_of),'lower':crt(Reference(**{**asdict(r),'direction':-1}),bars,as_of=as_of)})
    if 'M13' in inputs:results['M13']=result('M13',amd(bars,tick,as_of=as_of,**inputs['M13']))
    elif bars[0].timeframe=='15m':
        # Versioned experimental crypto session: 00:00–08:00 UTC balance.
        # No canonical ICT timing or intent is asserted by this variant.
        from .observations import iso_seconds
        day=bars[-1].open_ms//86400000*86400000
        if bars[-1].end_ms<day+8*3600000:day-=86400000
        base=[b for b in bars if day<=b.open_ms and b.end_ms<=day+8*3600000]
        if len(base)==32 and base[0].open_ms==day:
            results['M13']=result('M13',amd(bars,tick,session_start=iso_seconds(day//1000),
                balance_end=iso_seconds(day//1000+8*3600),as_of=as_of))
    if 'M14' in inputs:results['M14']=result('M14',timed_subclass(cutoff,inputs['M14']),status='DEFINITION_PENDING')
    balance=balance_references(bars,tick)
    results['M16']=result('M16',auction(balance,bars,as_of=as_of))
    # Only a complete UTC session earns the exact first-moment name.
    day=bars[-1].open_ms//86400000*86400000
    session=[b for b in bars if b.open_ms>=day]
    if session and session[0].open_ms==day:
        from .observations import iso_seconds
        anchor=iso_seconds(day//1000)
        results['M19']=result('M19',anchored_value(session,anchor_ms=day,anchor_known_at=anchor))
        if len(session)>=17:
            atr=wilder_atr(session)[-1]
            if atr:
                v=value_extension(session,anchor_ms=day,anchor_known_at=anchor,atr_ref=atr)
                results['M20']=result('M20',{'measured_balance':bool(balance),'value':v,
                    'reversion_formation':[h for h in (families or []) if h['family']=='F7']})
    anchor=bars[0].open_ms
    from .observations import iso_seconds
    results['M21']=result('M21',{'anchor_ms':anchor,'fidelity':'BAR_AGGRESSOR_NOT_FOOTPRINT',
        'divergences':flow_divergence(bars,anchor_ms=anchor,anchor_known_at=iso_seconds(anchor//1000))})
    if benchmark is not None and len(bars)>=36:
        bench=closed_prefix(benchmark,cutoff=cutoff,as_of=as_of)
        if len(bench)==len(bars):results['M29']=result('M29',{
            'relative':persistent_residual(bars,bench),'sector':specialist_sector(inputs.get('M29'),cutoff,bars[-1].native_symbol)})
    results['M30']=result('M30',{'families':[h for h in (families or []) if h['family'] in {'F3','F9'}],
        'breadth':inputs.get('breadth',{'status':'SOURCE_CAPABILITY_REQUIRED','reason':'SYNCHRONIZED_FULL_INVENTORY_RETURNS'})})
    for method in ('M17','M18','M22','M23','M24','M25','M26','M27','M28','M31'):
        if method in inputs:results[method]=specialist_method(method,**inputs[method])
    return list(results.values())


def specialist_sector(inputs,at,native_symbol):
    return sector_strength(native_symbol,at=at,**inputs) if inputs else [
        {'status':'SOURCE_CAPABILITY_REQUIRED','reason':'DATED_EXACT_CONTRACT_MEMBERSHIPS'}]
