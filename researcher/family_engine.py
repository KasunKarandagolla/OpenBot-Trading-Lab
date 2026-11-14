"""Executable F1–F9 formation reducers on bounded selected source evidence.

No economics/admission decision is made here. EARLY does not require a future
response; DEVELOPING verifies current formation, never its predictive outcome.
Historical reconstruction retains actual retrieval availability.
"""
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal as D
from statistics import median
from .contracts import ContractError, utc
from .numerics import (validate_bars, wilder_atr, true_ranges, confirmed_swings,
    swing_ladder, touch_episodes, efficiency, compression, displacement, distance)
from .structures import Reference, stable_id, event
from .measurements import persistent_residual, residual_series, residual_persistence, value_extension

VERSION = 'families-6a.1'
RIVALS = {'F1':('F7','F4','NULL'),'F2':('F4','F5','F6','NULL'),
    'F3':('F4','F9','NULL'),'F4':('F2','F5','F6','NULL'),
    'F5':('F4','F2','NULL'),'F6':('F2','F4','F7','NULL'),
    'F7':('F1','F3','NULL'),'F8':('COMMON_BETA','TEMPORARY_NOISE','NULL'),
    'F9':('RECOVERY','SECOND_LEG','FUNDAMENTAL_REPRICING','NULL')}


def closed_prefix(bars, *, cutoff, as_of):
    """Filter before validation so unseen future bars cannot affect an old run."""
    utc(cutoff); utc(as_of)
    if utc(cutoff)>utc(as_of):raise ContractError('CUTOFF_AFTER_EVALUATION')
    result=[b for b in bars if utc(b.end)<=utc(cutoff)]
    if not result:return []
    validate_bars(result,cutoff=cutoff,require_current=True)
    if any(utc(b.available_at or b.received_at)>utc(as_of) or utc(b.received_at)>utc(as_of) for b in result):
        raise ContractError('SOURCE_NOT_AVAILABLE_AT_EVALUATION')
    return result


def reference(bars, index, *, kind, lo, hi, direction, tick, origin, defining=()):
    b=bars[index];scale=wilder_atr(bars[:index+1])[-1]
    if scale is None or scale<=0:raise ContractError('ZERO_OR_UNDEFINED_REFERENCE_ATR')
    return Reference(b.native_symbol,b.timeframe,kind,lo,hi,scale,tick,direction,
        bars[0].end if not defining else defining[0].end,b.end,
        max((x.available_at or x.received_at for x in (*defining,b)),key=utc),
        (utc(b.end)+timedelta(days=7)).isoformat(),tuple(x.id for x in defining) or (b.id,),origin)


def hypothesis(family, ref=None, *, state='INSUFFICIENT_HISTORY', direction=0, timeline=(), details=None):
    latest=timeline[-1] if timeline else None
    stage=latest['stage'] if latest else 'UNKNOWN'
    return {'id':stable_id(VERSION,family,ref.id if ref else None),
        'family':family,'reference_id':ref.id if ref else None,'direction':direction,
        'stage':stage,'status':state,'known_at':latest['known_at'] if latest else None,
        'available_at':latest['available_at'] if latest else None,
        'verdict':'CONTRADICTED' if stage=='INVALIDATED' else 'SUPPORTED' if latest else 'UNKNOWN',
        'timeline':list(timeline),'reference':asdict(ref) if ref else None,'rivals':RIVALS[family],
        'details':details or {},'evidence_cluster':'VALUE_LOCATION' if family=='F7' else 'PRICE_PATH',
        'unknowns':['FIRST_OPPOSING_ROOM','CURRENT_ECONOMICS','FUTURE_OUTCOME'],
        'production_enabled':False,'source_supported':False,'whole_universe_coverage':False,
        'scope':'SELECTED_RECONSTRUCTION_NOT_PROSPECTIVE_NOMINATION','formula_version':VERSION}


def transition(timeline, ref, bar, kind, stage):
    if timeline and timeline[-1]['stage']==stage and timeline[-1]['kind']==kind:return
    e=event(ref,bar,kind)
    timeline.append({**asdict(e),'id':e.id,'stage':stage})


def boundary_family(family, ref, bars, *, as_of, balance=False):
    if family not in {'F2','F4','F5','F6'}:raise ContractError('BOUNDARY_FAMILY_REQUIRED')
    if utc(ref.available_at)>utc(as_of):return hypothesis(family,ref,state='SOURCE_UNKNOWN')
    if any(b.native_symbol!=ref.native_symbol or b.timeframe!=ref.timeframe for b in bars):
        raise ContractError('REFERENCE_BAR_IDENTITY')
    direction=ref.direction if family in {'F2','F5'} else -ref.direction
    tl=[];touches=0;armed=True;excursion=None;reclaim=None;opposing=None;broken=None;holds=0;pressure_seen=False
    previous=None;first_distance=None;last_touch=None;retreats=[]
    for b in bars:
        if b.open_ms<int(utc(ref.known_at).timestamp()*1000):continue
        if utc(b.end)>utc(ref.valid_until):transition(tl,ref,b,'EXPIRED','INVALIDATED');break
        side=ref.direction;level=ref.hi if side==1 else ref.lo
        c=side*(b.close-level);ext=side*((b.high if side==1 else b.low)-level)
        outside=c>ref.buffer;inside=c<-ref.buffer
        touched=b.high>=ref.lo-ref.buffer and b.low<=ref.hi+ref.buffer
        dist=distance(b.close,ref.lo,ref.hi,ref.atr)
        if first_distance is None:first_distance=dist
        if first_distance>dist and dist<=D('2.5') and not tl and family in {'F2','F4'}:
            transition(tl,ref,b,'APPROACH','EARLY')
        if family=='F6' and balance and dist<=D('1') and not tl:
            transition(tl,ref,b,'BALANCE_EDGE_APPROACH','EARLY')
        if touched and armed:
            touches+=1;armed=False
            if last_touch is not None:retreats.append(abs(b.close-last_touch.close))
            last_touch=b
        elif not touched and max(ref.lo-b.high,b.low-ref.hi,D(0))>=D('.5')*ref.atr:
            armed=True
        if family=='F2' and touches>=2 and not excursion and not outside:
            pressure_seen=True
            transition(tl,ref,b,'SEPARATED_PRESSURE','APPROACHING_DECISION')
        if ext>ref.buffer and excursion is None:excursion=b
        if excursion is not None and inside and reclaim is None:
            reclaim=b;holds=0;broken=None
            if family=='F2':transition(tl,ref,b,'RECLAIM_DISCONFIRMS_STRAIGHT_BREAK','INVALIDATED');break
            if family in {'F4','F5'}:transition(tl,ref,b,'RECLAIM','DEVELOPING')
            if family=='F6' and balance:transition(tl,ref,b,'EDGE_REJECTION','DEVELOPING')
        elif reclaim is not None and b.open_ms>reclaim.open_ms and inside and opposing is None:
            progress=side*(reclaim.close-b.close)
            if progress>=D('.25')*ref.atr:
                opposing=b
                dp=displacement(previous,b,ref.atr,ref.tick) if previous else {}
                if family=='F4' and dp.get('tr_atr_previous',0)>=D('1.2') and dp['body_fraction']>=D('.5'):
                    transition(tl,ref,b,'OPPOSING_INITIATIVE','DEVELOPING')
                if family=='F5':transition(tl,ref,b,'OPPOSING_REVERSAL_ATTEMPT','DEVELOPING')
                if family=='F6' and balance:transition(tl,ref,b,'ROTATION','DEVELOPING')
        # F6 can reject an ordinary edge visit without requiring a sweep.
        if family=='F6' and balance and touches and inside and previous and side*(previous.close-b.close)>D('.25')*ref.atr:
            transition(tl,ref,b,'ROTATION','DEVELOPING')
        eligible=(reclaim is None and pressure_seen) if family=='F2' else (
            opposing is not None and b.open_ms>opposing.open_ms) if family=='F5' else True
        if outside and broken is None and eligible:
            broken=b;holds=0
            if family=='F2':transition(tl,ref,b,'BUFFERED_OUTSIDE_CLOSE','DEVELOPING')
            if family=='F5':transition(tl,ref,b,'REVERSAL_FAILED_REBREAK_SAME_REFERENCE','DEVELOPING')
        elif broken is not None and b.open_ms>broken.open_ms:
            if outside:
                holds+=1
                if holds==2:
                    transition(tl,ref,b,'LATER_OUTSIDE_ACCEPTANCE',
                        'DEVELOPING' if family in {'F2','F5'} else 'INVALIDATED')
                    if family in {'F4','F6'}:break
            else:
                if holds>=2 and family in {'F2','F5'}:
                    transition(tl,ref,b,'ACCEPTANCE_FAILED','INVALIDATED');break
                broken=None;holds=0
        previous=b
    return hypothesis(family,ref,state='COMPUTED' if tl else 'NO_EVENT_IN_COMPLETE_WINDOW',
        direction=direction,timeline=tl,details={'touch_episodes':touches,'retreat_changes':retreats,
        'same_original_reference':True,'balance_established':balance,'observed_stops':False,
        'acceptance_verified':any(e['kind']=='LATER_OUTSIDE_ACCEPTANCE' for e in tl),
        'opposing_initiative_verified':any(e['kind']=='OPPOSING_INITIATIVE' for e in tl)})


def continuation(bars,tick):
    if len(bars)<20:return hypothesis('F1')
    swings=confirmed_swings(bars);tl=[];expired=0
    for s in swings:
        known=[p for p in swings if p['known_index']<=s['known_index']]
        ladder=swing_ladder(known)
        side=1 if ladder=='HH_HL' else -1 if ladder=='LH_LL' else 0
        if not side or s['kind']!=('SWING_HIGH' if side==1 else 'SWING_LOW'):continue
        starts=[p for p in known if p['index']<s['index'] and p['kind']!=s['kind']]
        if not starts:continue
        start=starts[-1];amplitude=side*(s['price']-start['price'])
        if amplitude<=2*tick:continue
        k=s['known_index']
        scale=wilder_atr(bars[:k+1])[-1]
        if not scale:continue
        if utc(bars[k].available_at or bars[k].received_at)>utc(bars[k].end)+timedelta(days=7):
            expired+=1;continue
        r=reference(bars,k,kind=start['kind'],lo=start['price'],hi=start['price'],direction=-side,
            tick=tick,origin=stable_id('F1',s['id'],start['id']),defining=(bars[start['index']],bars[s['index']]))
        if amplitude<D('1.2')*r.atr:continue
        impulse=bars[start['index']:s['index']+1];tl=[];pullback=[];prior=None;approached=False
        for b in bars[k+1:]:
            if utc(b.end)>utc(r.valid_until):transition(tl,r,b,'EXPIRED','INVALIDATED');break
            if side*(b.close-start['price'])<-r.buffer:
                transition(tl,r,b,'DEFENDED_SWING_FAILURE','INVALIDATED');break
            pullback.append(b);rho=side*(s['price']-b.close)/amplitude
            controlled=D('.15')<=rho<=D('.70') and median(x.high-x.low for x in pullback)<=median(x.high-x.low for x in impulse)
            if controlled and not tl:transition(tl,r,b,'CONTROLLED_COUNTERLEG','EARLY')
            if controlled and distance(b.close,r.lo,r.hi,r.atr)<=D('2.5'):approached=True
            if controlled and approached and tl:
                if prior and side*(b.close-prior.close)>0:
                    transition(tl,r,b,'DEFENDED_RESPONSE','DEVELOPING')
            prior=b
        if tl:return hypothesis('F1',r,state='COMPUTED',direction=side,timeline=tl,
            details={'ladder':ladder,'impulse_start':start['price'],'impulse_end':s['price'],
            'impulse_known_at':s['known_at'],'retracement':rho if pullback else None,
            'pullback_impulse_duration_ratio':D(len(pullback))/len(impulse),
            'pullback_impulse_range_ratio':median(b.high-b.low for b in pullback)/median(b.high-b.low for b in impulse)
                if pullback and median(b.high-b.low for b in impulse)>0 else None,
            'pullback_impulse_quote_volume_ratio':median(b.quote_volume for b in pullback)/median(b.quote_volume for b in impulse)
                if pullback and median(b.quote_volume for b in impulse)>0 else None,
            'pullback_efficiency':efficiency(pullback,n=len(pullback)-1) if len(pullback)>1 else None})
    return hypothesis('F1',state='STALE' if expired else 'NO_EVENT_IN_COMPLETE_WINDOW',
        details={'expired_before_first_available':expired})


def compression_family(bars,tick,refs):
    if len(bars)<159:return hypothesis('F3')
    for i in range(159,len(bars)+1):
        q=compression(bars[:i],tick=tick)
        if q['past_percentile']>D('.2'):continue
        b=bars[i-1]
        candidates=[r for r in refs if utc(r.known_at)<utc(b.end) and utc(b.end)<=utc(r.valid_until)
                    and distance(b.close,r.lo,r.hi,r.atr)<=D('2.5')]
        if not candidates:continue
        r=min(candidates,key=lambda r:distance(b.close,r.lo,r.hi,r.atr));tl=[]
        transition(tl,r,b,'QUIET_AT_KNOWN_DECISION','EARLY');expanded=None;side=0
        for j in range(i,len(bars)):
            later=bars[j]
            if utc(later.end)>utc(r.valid_until):transition(tl,r,later,'EXPIRED','INVALIDATED');break
            if expanded is None:
                atr=wilder_atr(bars[:j])[-1]
                if not atr:continue
                dp=displacement(bars[j-1],later,atr,tick)
                if dp['tr_atr_previous']>=D('1.2') and dp['body_fraction']>=D('.5') and (dp['close_location']>=D('.75') or dp['close_location']<=D('.25')):
                    side=1 if later.close>later.open else -1;expanded=later
                    transition(tl,r,later,'FIRST_DISPLACEMENT','DEVELOPING')
            elif side*(later.close-expanded.open)<=0:
                transition(tl,r,later,'EXPANSION_FAILED','INVALIDATED');break
            else:transition(tl,r,later,'RETAINED_PROGRESS','DEVELOPING')
        return hypothesis('F3',r,state='COMPUTED',direction=side,timeline=tl,details={'past_only_quiet_percentile':q['past_percentile']})
    return hypothesis('F3',state='NO_EVENT_IN_COMPLETE_WINDOW')


def balance_references(bars,tick,*,window=32,baseline_end=None):
    """Fixed completed baseline; both edges need separated visits before birth."""
    if len(bars)<window or window<17:return ()
    end=baseline_end if baseline_end is not None else max(window,len(bars)-16)
    if not window<=end<=len(bars):raise ContractError('BALANCE_BASELINE_WINDOW')
    base=bars[end-window:end];er=efficiency(base,n=window-1)
    atr=wilder_atr(bars[:end])[-1]
    if er is None or er>D('.35') or not atr:return ()
    lo=min(b.low for b in base);hi=max(b.high for b in base);buffer=max(2*tick,D('.15')*atr)
    if hi-lo<2*atr:return ()
    if min(len(touch_episodes(base,lo=p,hi=p,atr=atr,buffer=buffer)) for p in (lo,hi))<2:return ()
    if utc(base[-1].available_at or base[-1].received_at)>utc(base[-1].end)+timedelta(days=7):return ()
    return tuple(reference(bars,end-1,kind=kind,lo=p,hi=p,direction=side,tick=tick,
        origin=stable_id('BALANCE',tuple(b.id for b in base),side),defining=tuple(base))
        for p,kind,side in [(lo,'RANGE_BOTTOM',-1),(hi,'RANGE_TOP',1)])


def value_reversion(bars,tick,balance):
    if not balance:return hypothesis('F7',state='SOURCE_UNKNOWN',details={'reason':'MEASURED_BALANCE_REQUIRED'})
    # The anchor is declared by UTC, never selected using the later extension.
    from .observations import iso_seconds
    start=bars[-1].open_ms//86400000*86400000
    session=[b for b in bars if start<=b.open_ms<start+86400000]
    if not session or session[0].open_ms!=start:
        return hypothesis('F7',state='INSUFFICIENT_HISTORY',details={'reason':'COMPLETE_UTC_SESSION_REQUIRED'})
    for i in range(17,len(session)):
        if int(utc(balance[0].known_at).timestamp()*1000)>session[i-1].open_ms:continue
        atr=wilder_atr(session[:i])[-1]
        if not atr:continue
        value=value_extension(session[:i],anchor_ms=start,anchor_known_at=iso_seconds(start//1000),atr_ref=atr)
        ext=value['distance_atr']
        if ext is None or abs(ext)<1:continue
        side=-1 if ext>0 else 1;mean=value['vwap_whole_bars'];b=session[i-1]
        r=reference(session,i-1,kind='SESSION_VWAP_ANCHOR',lo=mean,hi=mean,direction=side,tick=tick,
            origin=stable_id('UTC_SESSION',start,b.id),defining=tuple(session[:i]));tl=[]
        transition(tl,r,b,'CONDITIONAL_VALUE_EXTENSION','EARLY');prior=b
        for later in session[i:]:
            if side*(later.close-prior.close)>0 and side*(later.close-b.close)>0:
                transition(tl,r,later,'FAILED_FURTHER_PROGRESS_RETURN','DEVELOPING')
            if side*(later.close-b.close)<-r.atr:
                transition(tl,r,later,'ACCEPTED_EXTENSION_REPRICING','INVALIDATED');break
            if side*(later.close-mean)>=0:
                transition(tl,r,later,'PRIOR_VALUE_REACHED','LATE');break
            prior=later
        return hypothesis('F7',r,state='COMPUTED',direction=side,timeline=tl,details=value)
    return hypothesis('F7',state='NO_EVENT_IN_COMPLETE_WINDOW')


def relative_family(bars,benchmark,refs):
    if benchmark is None:return hypothesis('F8',state='SOURCE_CAPABILITY_REQUIRED')
    if len(bars)<36:return hypothesis('F8')
    rows=residual_series(bars,benchmark)
    for i in range(36,len(bars)+1):
        rel=residual_persistence(rows[i-3:i])
        side=rel['direction']
        if not side:continue
        b=bars[i-1]
        known=[r for r in refs if utc(r.known_at).timestamp()*1000<=b.open_ms and utc(r.valid_until)>=utc(b.end)
               and distance(b.close,r.lo,r.hi,r.atr)<=D('2.5')]
        if not known:continue
        r=min(known,key=lambda r:distance(b.close,r.lo,r.hi,r.atr));tl=[]
        transition(tl,r,b,'PERSISTENT_RESIDUAL_AT_LOCAL_DECISION','EARLY')
        for j in range(i,len(bars)):
            later=bars[j]
            if utc(later.end)>utc(r.valid_until):transition(tl,r,later,'EXPIRED','INVALIDATED');break
            rj=residual_persistence(rows[j-2:j+1])
            if rj['direction']==-side:
                transition(tl,r,later,'OPPOSING_PERSISTENT_RESIDUAL','INVALIDATED');break
            level=r.hi if side==1 else r.lo
            if side*(later.close-level)>r.buffer:
                transition(tl,r,later,'LOCAL_STRUCTURAL_CONSEQUENCE','DEVELOPING')
        return hypothesis('F8',r,state='COMPUTED',direction=side,timeline=tl,details=rel)
    return hypothesis('F8',state='NO_EVENT_IN_COMPLETE_WINDOW')


def shock_family(bars,tick):
    if len(bars)<35:return hypothesis('F9')
    atr=wilder_atr(bars);trs=true_ranges(bars)
    expired=0
    for i in range(33,len(bars)):
        if not atr[i-1] or trs[i]<3*atr[i-1]:continue
        # Earlier normalized own-history ranges; current event excluded.
        past=[trs[j]/atr[j-1] for j in range(max(15,i-32),i) if atr[j-1]]
        if len(past)<16 or sum(x<trs[i]/atr[i-1] for x in past)/len(past)<D('.9'):continue
        b=bars[i];side=1 if b.close>=b.open else -1
        if utc(b.available_at or b.received_at)>utc(b.end)+timedelta(days=7):
            expired+=1;continue
        r=reference(bars,i,kind='SHOCK_BOUNDARY',lo=b.low,hi=b.high,direction=side,tick=tick,
            origin=stable_id('SHOCK',b.id),defining=(b,));tl=[]
        transition(tl,r,b,'POST_SHOCK','EARLY');stable=0
        for later in bars[i+1:]:
            if utc(later.end)>utc(r.valid_until):transition(tl,r,later,'EXPIRED','INVALIDATED');break
            new_extreme=later.high>b.high if side==1 else later.low<b.low
            if new_extreme:
                transition(tl,r,later,'RENEWED_EXTREME_SECOND_LEG','DEVELOPING');stable=0
            elif later.high-later.low<b.high-b.low:
                stable+=1
                if stable>=2:transition(tl,r,later,'STABILIZATION_CANDIDATE','DEVELOPING')
            if side*(later.close-(b.open+b.close)/2)<0:
                transition(tl,r,later,'SHOCK_MIDPOINT_RECLAIM','DEVELOPING')
        return hypothesis('F9',r,state='COMPUTED',direction=side,timeline=tl,
            details={'classification':'POST_SHOCK','confirmed_liquidation':False,'tr_atr_previous':trs[i]/atr[i-1]})
    return hypothesis('F9',state='STALE' if expired else 'NO_EVENT_IN_COMPLETE_WINDOW',
        details={'expired_before_first_available':expired})


def evaluate_families(bars,tick,*,cutoff,as_of,benchmark=None,references=()):
    bars=closed_prefix(bars,cutoff=cutoff,as_of=as_of)
    if not bars:return [hypothesis('F'+str(i)) for i in range(1,10)]
    tick=D(tick)
    if benchmark is not None:
        benchmark=closed_prefix(benchmark,cutoff=cutoff,as_of=as_of)
        # Even a missing/short benchmark must not veto the independent families.
        if len(benchmark)!=len(bars):benchmark=None
    refs=tuple(r for r in references if utc(r.known_at)<=utc(cutoff) and utc(r.available_at)<=utc(as_of))
    if any(r.native_symbol!=bars[0].native_symbol or r.timeframe!=bars[0].timeframe for r in refs):
        raise ContractError('REFERENCE_BAR_IDENTITY')
    balance=balance_references(bars,tick)
    result=[continuation(bars,tick),compression_family(bars,tick,refs),
            value_reversion(bars,tick,balance),relative_family(bars,benchmark,refs),shock_family(bars,tick)]
    for f in ('F2','F4','F5','F6'):
        candidates=balance if f=='F6' else refs
        if candidates:
            result.extend(boundary_family(f,r,bars,as_of=as_of,balance=f=='F6') for r in candidates)
        else:result.append(hypothesis(f,state='SOURCE_UNKNOWN',details={'reason':'PREKNOWN_MEANINGFUL_REFERENCE_REQUIRED'}))
    return sorted(result,key=lambda h:(h['family'],h['id']))
