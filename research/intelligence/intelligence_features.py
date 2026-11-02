"""Versioned causal opportunity questions and economic research plans."""
import math
import numpy as np
from advanced_features import volume_profile_v2

COST=.00075*2+.002+.0003


def finite(value):
    try: return math.isfinite(float(value))
    except (ValueError,TypeError): return False


def match(row, recipe, side, structural=False):
    """Parent signal supplies reclaim/rejection. This answers continuation danger."""
    opposite='DOWN' if side=='long' else 'UP'
    direction='UP' if side=='long' else 'DOWN'
    hourly=row.get('struct_direction_1h','UNKNOWN')
    if recipe=='vwap':
        if structural and hourly not in (direction,): return 'WATCH_HOURLY_STRUCTURE_NOT_ALIGNED'
        if not bool(row.get('vwap_valid',False)): return 'REJECT_VWAP_COVERAGE'
    else:
        local_shift=row.get('struct_event')=='CHOCH' and row.get('struct_direction')==direction
        if row.adx_1h>=25 and hourly==opposite and not local_shift:
            return 'WATCH_OPPOSING_TREND_CONTINUATION_DANGER'
        if structural:
            boundary=row.prior_low if side=='long' else row.prior_high
            keys=['prior_swing_low','prior_day_low'] if side=='long' else ['prior_swing_high','prior_day_high']
            if not any(finite(row.get(k)) and abs(float(row[k])-boundary)<=.5*row.atr14 for k in keys):
                return 'WATCH_MEANINGFUL_BOUNDARY_NOT_CONFIRMED'
    return 'MATCH'


def research_plan(row, recipe, side, mode='fixed', entry_retrace=False):
    sign=1 if side=='long' else -1; close=float(row.close); atr=float(row.atr14)
    if not all(finite(x) and float(x)>0 for x in (close,atr)): return None
    ref=close-sign*.1*atr if entry_retrace else close
    stop=float(row.low-.2*atr if sign==1 else row.high+.2*atr)
    risk=sign*(ref-stop)/ref
    if not .003<=risk<=.025: return None
    target=ref+sign*2*risk*ref; origin='FIXED_2R'; obstacles=[]
    keys=[]
    if mode in ('profile','target','nearest'):
        keys=['vp2_poc','vp2_vah' if sign==1 else 'vp2_val']
    if mode in ('target','nearest'):
        keys+=['prior_swing_high' if sign==1 else 'prior_swing_low','prior_day_high' if sign==1 else 'prior_day_low']
    for k in keys:
        val=row.get(k)
        if finite(val) and sign*(float(val)-ref)>0:
            obstacles.append(dict(reference=k,price=float(val),known_at=str(row.get('vp2_known_at') if k.startswith('vp2') else row.get(k+'_known_at',row.date))))
    obstacles.sort(key=lambda x:sign*(x['price']-ref))
    caution=[]
    if obstacles and sign*(obstacles[0]['price']-target)<0:
        obj=obstacles[0]; rr=(sign*(obj['price']-ref)/ref-COST)/(risk+COST)
        if rr>=1.25 or mode=='nearest': target=obj['price']; origin=obj['reference']
        else: caution.append('NEAR_OBJECTIVE_HAS_INSUFFICIENT_NET_ROOM_FIXED_2R_RETAINS_BREAKTHROUGH_RISK')
    reward=sign*(target-ref)/ref; rr=(reward-COST)/(risk+COST)
    if rr<1.25: return None
    return dict(version=2,reference=ref,signal_close=close,stop=stop,target=target,risk_fraction=risk,
        modeled_loss_per_notional=risk+COST,admission_cost_allowance=COST,
        cost_components=dict(fees_round_trip=.0015,friction_round_trip=.002,adverse_funding=.0003),
        after_cost_rr=rr,target_origin=origin,recipe=recipe,side=side,expiry_seconds=300,
        max_hold_hours=8 if recipe=='vwap' else 4,profile_fidelity='OHLCV_PROXY',
        invalidation='BREACH_OF_SIGNAL_EXTREME_PLUS_0.2_ATR_BUFFER',
        entry_trigger='CLOSED_VWAP_RECLAIM' if recipe=='vwap' else 'CLOSED_FAILED_PRIOR_20_BAR_BOUNDARY_REJECTION',
        entry_policy='0.1_ATR_RETRACEMENT_LIMIT' if entry_retrace else 'SIGNAL_CLOSE_LIMIT',
        fill_likelihood='UNKNOWN_QUEUE; NATIVE_OHLCV_RANGE_FILL_SCENARIO_ONLY',
        obstacles=obstacles,cautions=caution)


def profiles(frame):
    d=frame.copy(); typical=(d.high+d.low+d.close)/3; result=[]
    for i in range(len(d)):
        valid=i>=96 and d.date.iloc[i]-d.date.iloc[i-96]==__import__('pandas').Timedelta(days=1)
        valid=valid and d.date.iloc[i-96:i].diff().dropna().eq(__import__('pandas').Timedelta(minutes=15)).all()
        result.append(volume_profile_v2(typical.iloc[i-96:i],d.volume.iloc[i-96:i],'OHLCV_PROXY') if valid else None)
    for k in ('poc','val','vah'):
        d['vp2_'+k]=[p[k] if p else np.nan for p in result]
    d['vp2_known_at']=d.date; d['vp2_anchor']=d.date-__import__('pandas').Timedelta(days=1)
    return d
