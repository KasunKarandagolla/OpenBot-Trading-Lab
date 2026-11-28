"""Bounded selected-history method trials; never an admission or source certificate.

M32 freezes the first 32-bar balance before examining later bars. M33 accepts
only an explicitly selected completed 4H parent and separately supplied 5M
children. Neither function fetches, stores, schedules or executes anything.
"""
from decimal import Decimal as D

from .contracts import ContractError, number, utc
from .family_engine import balance_references, closed_prefix
from .numerics import Bar, touch_episodes, validate_bars
from .observations import iso_seconds
from .structures import stable_id


SHADOW_METHODS = (
    {'id':'M32','variant_id':'WYCKOFF-TR-LIFECYCLE-v0','name':'Wyckoff range lifecycle',
     'families':['F1','F2','F4','F5','F6','F9'], 'mode':'SHADOW',
     'production_enabled':False,'source_qualified':False},
    {'id':'M33','variant_id':'CRT-TBS-BODY-FAIL-v0','name':'CRT body-break failure',
     'families':['F2','F4','F5','F6'], 'mode':'SHADOW',
     'production_enabled':False,'source_qualified':False},
)


def _result(method, state, **fields):
    spec=next(m for m in SHADOW_METHODS if m['id']==method)
    return {**spec,'state':state,'rank_eligible':False,'trade_authorization':False,
        'scope':'SELECTED_HISTORY_ONLY','economic_edge':'UNPROVEN',**fields}


def _event(kind, bar, reference_ids):
    # The bar ID is the common price-observation root also cited by other
    # candle-based methods. Multiple labels cannot add independent votes.
    return {'kind':kind,'event_root_id':bar.id,'source_ids':[bar.id,bar.source_hash],
        'reference_ids':list(reference_ids),'occurred_at':bar.end,'known_at':bar.end,
        'available_at':bar.available_at or bar.received_at,'received_at':bar.received_at}


def _effort(baseline, refs):
    """Compare two non-overlapping two-bar episodes, or state UNKNOWN."""
    episodes=[]
    for ref in refs:
        touches=touch_episodes(baseline,lo=ref.lo,hi=ref.hi,atr=ref.atr,buffer=ref.buffer)
        lookup={b.id:i for i,b in enumerate(baseline)}
        for t in touches:
            i=lookup[t['bar_id']]
            if i>0:episodes.append((i,ref.direction))
    episodes.sort()
    if len(episodes)<2:return {'state':'EFFORT_RESULT_UNKNOWN','reason':'TWO_COMPARABLE_EPISODES_REQUIRED'}
    j,side=episodes[-1]
    previous=next(((i,s) for i,s in reversed(episodes[:-1]) if s==side and j-i>=2),None)
    if previous is None:
        return {'state':'EFFORT_RESULT_UNKNOWN','reason':'MATCHED_SEPARATED_EDGE_EPISODES_REQUIRED'}
    i,_=previous
    a,b=baseline[i-1:i+1],baseline[j-1:j+1]
    if (len({x.source_hash for x in (*a,*b)})!=1 or
            any(x.volume_units!='BASE_ASSET_AND_USDT_QUOTE' or x.quote_volume<=0 for x in (*a,*b))):
        return {'state':'EFFORT_RESULT_UNKNOWN','reason':'VOLUME_SOURCE_OR_BASELINE_MISSING'}
    effort_a=sum(x.quote_volume for x in a)/2; effort_b=sum(x.quote_volume for x in b)/2
    progress_a=abs(a[-1].close-a[0].open); progress_b=abs(b[-1].close-b[0].open)
    if progress_a<=0:return {'state':'EFFORT_RESULT_UNKNOWN','reason':'ZERO_PROGRESS_BASELINE'}
    return {'state':'TENSION_CANDIDATE' if effort_b>=D('1.5')*effort_a and progress_b<=D('.75')*progress_a else 'NO_TRIAL_TENSION',
        'episode_roots':[a[-1].id,b[-1].id],'effort_ratio':effort_b/effort_a,
        'progress_ratio':progress_b/progress_a,'units':'USDT_QUOTE_PER_CLOSED_BAR',
        'interpretation':'PRICE_VOLUME_COMPARISON_NOT_ABSORPTION'}


def wyckoff_shadow(bars,tick,*,cutoff,as_of):
    """First predeclared 32-bar balance; later observations cannot select it."""
    try:
        bars=closed_prefix(bars,cutoff=cutoff,as_of=as_of)
    except ContractError as error:
        if str(error) in {'MISSING_OR_MISALIGNED_BARS','BOUNDED_HISTORY_REQUIRED',
                'STALE_OR_INCOMPLETE_BAR_TAIL','SOURCE_NOT_AVAILABLE_AT_EVALUATION'}:
            return _result('M32','SOURCE_GAP',reason=str(error),events=[])
        raise
    if len(bars)<32:
        return _result('M32','UNKNOWN',reason='INSUFFICIENT_CLOSED_RANGE_HISTORY',events=[])
    tick=number(tick,positive=True)
    baseline=bars[:32]
    refs=balance_references(baseline,tick,window=32,baseline_end=32)
    if len(refs)!=2:
        return _result('M32','RANGE_CANDIDATE',reason='NO_ESTABLISHED_SEPARATED_TWO_SIDED_BALANCE',events=[])
    low,high=refs
    known=max((low.available_at,high.available_at),key=utc)
    lower,upper=low.lo,high.hi
    buffer=max(2*tick,D('.20')*low.atr)
    mid=(lower+upper)/2
    reference_ids=(low.id,high.id)
    events=[];state='ESTABLISHED_BALANCE';attempt=None;attempt_bar=None;response=None;retest=None
    holds_up=holds_down=0
    for bar in bars[32:]:
        if utc(known).timestamp()*1000>bar.open_ms:continue
        if utc(bar.end)>min(utc(low.valid_until),utc(high.valid_until)):
            state='EXPIRED';break
        outside_up=bar.close>upper+buffer;outside_down=bar.close<lower-buffer
        holds_up=holds_up+1 if outside_up else 0
        holds_down=holds_down+1 if outside_down else 0
        if (holds_up>=2 or holds_down>=2):
            events.append(_event('OUTSIDE_ACCEPTANCE_CANDIDATE',bar,reference_ids))
            state='INVALIDATED_REVERSAL' if attempt and ((attempt=='SPRING' and holds_down>=2) or (attempt=='UTAD' and holds_up>=2)) else 'OUTSIDE_HOLD'
            break
        if attempt is None:
            if bar.low<lower-buffer and bar.close>lower+buffer:
                attempt='SPRING';attempt_bar=bar;state='SPRING_CANDIDATE';events.append(_event('SPRING_GEOMETRY',bar,reference_ids));continue
            if bar.high>upper+buffer and bar.close<upper-buffer:
                attempt='UTAD';attempt_bar=bar;state='UTAD_CANDIDATE';events.append(_event('UTAD_GEOMETRY',bar,reference_ids));continue
        elif response is None:
            if utc(attempt_bar.available_at or attempt_bar.received_at).timestamp()*1000>bar.open_ms:continue
            span=bar.high-bar.low
            strong=span>=D('1.2')*low.atr and span>0 and abs(bar.close-bar.open)/span>=D('.5')
            if strong and ((attempt=='SPRING' and bar.close>mid+buffer) or (attempt=='UTAD' and bar.close<mid-buffer)):
                response=bar;state='SOS_CANDIDATE' if attempt=='SPRING' else 'SOW_CANDIDATE'
                events.append(_event(state,bar,reference_ids));continue
        elif retest is None:
            if utc(response.available_at or response.received_at).timestamp()*1000>bar.open_ms:continue
            if ((attempt=='SPRING' and bar.low<=mid+buffer and bar.close>=mid-buffer) or
                    (attempt=='UTAD' and bar.high>=mid-buffer and bar.close<=mid+buffer)):
                retest=bar;state='RETEST_CANDIDATE';events.append(_event(state,bar,reference_ids));continue
        elif (utc(retest.available_at or retest.received_at).timestamp()*1000<=bar.open_ms and
                ((attempt=='SPRING' and bar.close>retest.close) or (attempt=='UTAD' and bar.close<retest.close))):
            state='LPS_CANDIDATE' if attempt=='SPRING' else 'LPSY_CANDIDATE'
            events.append(_event(state,bar,reference_ids));break
    return _result('M32',state,reference_ids=list(reference_ids),range_low=lower,range_high=upper,
        range_known_at=low.known_at,range_available_at=known,
        baseline_source_ids=[b.id for b in baseline],events=events,effort_result=_effort(baseline,refs),
        rivals=['F2_BREAKOUT','F4_FAILED_BREAK','F6_ROTATION','NULL'],
        next_question='VERIFY_LATER_ACCEPTANCE_OR_RESPONSE',
        limitations=['FIXED_FIRST_32_BAR_BALANCE_TRIAL','NO_INSTITUTIONAL_INTENT','NO_ROOM_OR_FRICTION_GATE'])


def crt_tbs_shadow(parent,children,*,selection_known_at,cutoff,as_of,tick,atr_ref,source_complete=False,max_reclaim_bars=3):
    """Frozen 4H parent, later 5M outside close and separate later reclaim."""
    if not source_complete or parent is None or not children:
        return _result('M33','SOURCE_GAP',reason='COMPLETE_ALIGNED_4H_AND_5M_HISTORY_REQUIRED',events=[])
    if type(max_reclaim_bars) is not int or max_reclaim_bars not in {1,2,3,6,12}:
        raise ContractError('SHADOW_TRIAL_POLICY')
    tick=number(tick,positive=True);atr_ref=number(atr_ref,positive=True)
    validate_bars([parent])
    if parent.timeframe!='4h':raise ContractError('SHADOW_PARENT_TIMEFRAME')
    if utc(cutoff)>utc(as_of):raise ContractError('CUTOFF_AFTER_EVALUATION')
    if not utc(parent.end)<=utc(parent.available_at or parent.received_at)<=utc(selection_known_at)<=utc(as_of):
        return _result('M33','UNKNOWN',reason='PARENT_NOT_COMPLETED_OR_PRESELECTED',events=[])
    admitted=[b for b in children if utc(b.end)<=utc(cutoff)]
    if not admitted:return _result('M33','SOURCE_GAP',reason='NO_COMPLETED_5M_BARS',events=[])
    try:validate_bars(admitted,cutoff=cutoff,require_current=True)
    except ContractError as error:
        if str(error) in {'MISSING_OR_MISALIGNED_BARS','BOUNDED_HISTORY_REQUIRED','STALE_OR_INCOMPLETE_BAR_TAIL'}:
            return _result('M33','SOURCE_GAP',reason=str(error),events=[])
        raise
    if any(b.timeframe!='5m' or b.native_symbol!=parent.native_symbol for b in admitted):
        raise ContractError('REFERENCE_BAR_IDENTITY')
    if any(utc(b.received_at)>utc(as_of) or utc(b.available_at or b.received_at)>utc(as_of) for b in admitted):
        return _result('M33','SOURCE_GAP',reason='BAR_NOT_AVAILABLE_AT_CUTOFF',events=[])
    ref_id=stable_id('CRT-TBS-PARENT-v0',parent.id,selection_known_at)
    out=max(2*tick,D('.10')*atr_ref);inside=max(tick,D('.05')*atr_ref)
    if parent.high-parent.low<=2*inside:
        return _result('M33','UNKNOWN',reason='PARENT_TOO_NARROW_FOR_INSIDE_BUFFER',events=[])
    first_open=((int(utc(selection_known_at).timestamp())+299)//300)*300*1000
    eligible=[b for b in admitted if b.open_ms>=first_open]
    if not eligible or eligible[0].open_ms!=first_open:
        return _result('M33','SOURCE_GAP',reason='MISSING_5M_HISTORY_SINCE_PARENT_SELECTION',events=[])
    events=[];state='PARENT_FROZEN';broken=None;reclaimed=None;side=0;holds=0;age=0
    for bar in admitted:
        if utc(selection_known_at).timestamp()*1000>bar.open_ms:continue
        if bar.open_ms >= parent.end_ms+24*3600*1000:
            if broken and not reclaimed:state='EXPIRED'
            break
        if broken is None:
            side=1 if bar.close>parent.high+out else -1 if bar.close<parent.low-out else 0
            if side:
                broken=bar;state='BODY_OUTSIDE';events.append(_event(state,bar,[ref_id]));continue
        elif reclaimed is None:
            age+=1
            if age>max_reclaim_bars:state='EXPIRED';break
            if utc(broken.available_at or broken.received_at).timestamp()*1000>bar.open_ms:
                return _result('M33','UNKNOWN',reason='OUTSIDE_BAR_NOT_AVAILABLE_BEFORE_FOLLOWUP',events=events)
            outside=bar.close>parent.high+out if side==1 else bar.close<parent.low-out
            holds=holds+1 if outside else 0
            if holds>=2:
                state='ACCEPTED_OUTSIDE';events.append(_event(state,bar,[ref_id]));break
            inside_close=parent.low+inside<bar.close<parent.high-inside
            if inside_close:
                reclaimed=bar;state='RECLAIMED';events.append(_event(state,bar,[ref_id]));continue
        else:
            if utc(reclaimed.available_at or reclaimed.received_at).timestamp()*1000>bar.open_ms:continue
            span=bar.high-bar.low
            if span>=D('1.2')*atr_ref and span>0 and abs(bar.close-bar.open)/span>=D('.5') and side*(bar.close-bar.open)<0:
                state='RESPONSE_CANDIDATE';events.append(_event(state,bar,[ref_id]));break
    return _result('M33',state,parent_reference_id=ref_id,parent_bar_id=parent.id,
        parent_known_at=selection_known_at,parent_available_at=parent.available_at or parent.received_at,
        parent_source_id=parent.source_hash,events=events,rivals=['F2_ACCEPTED_BREAKOUT','F4_FAILED_BREAK','F6_ROTATION','NULL'],
        next_question='VERIFY_LATER_STRUCTURAL_RESPONSE_AND_ROOM',
        limitations=['PRESELECTED_PARENT_REQUIRED','NO_INTRABAR_ORDER','NO_ROOM_OR_FRICTION_GATE'])


def supplied_crt_tbs_shadow(data, *, cutoff, as_of, tick):
    """Keep an invalid optional offline input from breaking baseline research."""
    required={'parent','children','selection_known_at','atr_ref'}
    optional={'source_complete','max_reclaim_bars'}
    if (not isinstance(data,dict) or not required <= data.keys() or
            data.keys()-required-optional or not isinstance(data['parent'],Bar) or
            not isinstance(data['children'],(list,tuple)) or
            not all(isinstance(bar,Bar) for bar in data['children']) or
            type(data.get('source_complete',False)) is not bool):
        return _result('M33','SOURCE_GAP',reason='INVALID_OPTIONAL_SHADOW_INPUT',events=[])
    try:
        return crt_tbs_shadow(**data,cutoff=cutoff,as_of=as_of,tick=tick)
    except ContractError as error:
        return _result('M33','SOURCE_GAP',reason=str(error),events=[])
