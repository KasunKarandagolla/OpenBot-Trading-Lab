"""Causal v3 setup definitions and immutable price plans. No outcome inputs."""
import math
import json
import numpy as np
import pandas as pd
from intelligence_features import COST, finite


def features(d):
    d=d.copy()
    for side in ('low','high'):
        d['pullback_'+side]=getattr(d,side).shift().rolling(6,min_periods=6).agg('min' if side=='low' else 'max')
    d['prior_touch_long']=((d.low<=d[['ema20','vwap']].max(axis=1)+.35*d.atr14)&(d.close>=d.ema50-1*d.atr14)).shift().rolling(4,min_periods=4).max().eq(1)
    d['prior_touch_short']=((d.high>=d[['ema20','vwap']].min(axis=1)-.35*d.atr14)&(d.close<=d.ema50+1*d.atr14)).shift().rolling(4,min_periods=4).max().eq(1)
    d['accepted_long']=(d.close>d.vwap).shift().rolling(3,min_periods=3).sum()>=2
    d['accepted_short']=(d.close<d.vwap).shift().rolling(3,min_periods=3).sum()>=2
    d['previous_high']=d.high.shift(); d['previous_low']=d.low.shift()
    d['ema20_slope']=d.ema20-d.ema20.shift(3)
    d['lost_long']=(d.close<d.vwap)&(d.close<d.ema20)
    d['lost_short']=(d.close>d.vwap)&(d.close>d.ema20)
    d['thesis_lost_long']=d.lost_long & d.lost_long.shift(fill_value=False)
    d['thesis_lost_short']=d.lost_short & d.lost_short.shift(fill_value=False)
    return d


def raw_signals(d, validity):
    span=(d.high-d.low).replace(0,np.nan)
    context=validity & d.vwap_valid & (d.session_bars>=8) & d.same_session
    trend=context & d.adx_1h.ge(20) & d.rvol.ge(1)
    cont_long=(trend & d.ema20_1h.gt(d.ema50_1h) & d.ema20.gt(d.ema50) & d.ema20_slope.gt(0)
        & d.accepted_long & d.prior_touch_long & d.close.gt(d.previous_high) & d.close.gt(d.open)
        & ((d.close-d.low)/span).ge(.65) & ((d.close-d.pullback_low)/d.atr14).le(2.5))
    cont_short=(trend & d.ema20_1h.lt(d.ema50_1h) & d.ema20.lt(d.ema50) & d.ema20_slope.lt(0)
        & d.accepted_short & d.prior_touch_short & d.close.lt(d.previous_low) & d.close.lt(d.open)
        & ((d.high-d.close)/span).ge(.65) & ((d.pullback_high-d.close)/d.atr14).le(2.5))
    body=np.maximum((d.close-d.open).abs(),.1*d.atr14)
    sweep=validity & d.rvol.ge(1.2) & d.adx_1h.le(30)
    rev_long=(sweep & ((d.prior_low-d.low)/d.atr14).between(.1,1) & d.close.gt(d.prior_low)
        & (d[['open','close']].min(axis=1)-d.low).ge(1.5*body))
    rev_short=(sweep & ((d.high-d.prior_high)/d.atr14).between(.1,1) & d.close.lt(d.prior_high)
        & (d.high-d[['open','close']].max(axis=1)).ge(1.5*body))
    return {('continuation','long'):cont_long,('continuation','short'):cont_short,
            ('reversal','long'):rev_long,('reversal','short'):rev_short}


def suitability(r,recipe,side):
    sign=1 if side=='long' else -1
    if recipe=='continuation': return 'MATCH'
    direction='UP' if sign==1 else 'DOWN'
    shift=r.get('struct_event')=='CHOCH' and r.get('struct_direction')==direction
    opposing=(r.ema20_1h<r.ema50_1h) if sign==1 else (r.ema20_1h>r.ema50_1h)
    if r.adx_1h>=25 and opposing and not shift: return 'WATCH_OPPOSING_HOURLY_TREND_REQUIRES_LOCAL_SHIFT'
    boundary=r.prior_low if sign==1 else r.prior_high
    keys=['prior_day_low','prior_session_low','prior_swing_low'] if sign==1 else ['prior_day_high','prior_session_high','prior_swing_high']
    meaningful=any(finite(r.get(k)) and abs(float(r[k])-boundary)<=.5*r.atr14 for k in keys)
    return 'MATCH' if meaningful or shift else 'WATCH_MINOR_BOUNDARY_WITHOUT_SHIFT'


def plan(r,recipe,side,retrace=False,objective=False):
    sign=1 if side=='long' else -1; close=float(r.close); atr=float(r.atr14)
    if not all(finite(x) and x>0 for x in (close,atr)): return None,'INVALID_DATA'
    extreme=min(float(r.low),float(r.pullback_low)) if sign==1 else max(float(r.high),float(r.pullback_high))
    if recipe=='reversal': extreme=float(r.low if sign==1 else r.high)
    stop=extreme-sign*.2*atr
    original_risk=sign*(close-stop)
    entry=close-sign*.15*atr if retrace else close
    risk=sign*(entry-stop)/entry
    if not .003<=risk<=.025: return None,'STOP_DISTANCE_OUTSIDE_0.3_2.5_PERCENT'
    target=close+sign*3*original_risk; origin='FIXED_3R_FROM_SIGNAL_CLOSE'
    if sign*(target-entry)>6*atr: return None,'TARGET_EXCEEDS_6ATR_HORIZON_BOUND'
    obstacles=[]
    for k in ['prior_swing_high' if sign==1 else 'prior_swing_low','prior_day_high' if sign==1 else 'prior_day_low','prior_session_high' if sign==1 else 'prior_session_low','vp2_poc','vp2_vah' if sign==1 else 'vp2_val']:
        if finite(r.get(k)) and sign*(float(r[k])-entry)>0:
            obstacles.append(dict(source=k,price=float(r[k]),fidelity='OHLCV_PROXY' if k.startswith('vp2') else 'CONFIRMED_CLOSED_BARS'))
    obstacles.sort(key=lambda o:sign*(o['price']-entry))
    if objective:
        choices=[o for o in obstacles if o['fidelity']!='OHLCV_PROXY' and 2*original_risk<=sign*(o['price']-close)<3*original_risk
            and (sign*(o['price']-entry)/entry-COST)/(risk+COST)>=1.25]
        if choices: target=choices[0]['price']; origin=choices[0]['source']
    reward=sign*(target-entry)/entry; rr=(reward-COST)/(risk+COST)
    if rr<1.25: return None,'NET_REWARD_RISK_BELOW_1.25_WITH_38BP_COST'
    available=(r.date+pd.Timedelta(minutes=15)).isoformat()
    g=dict(policy_id='controlled-pullback-failure-v3.0.0',recipe=recipe,side=side,
        reference=entry,signal_close=close,stop=stop,structural_stop=stop,target=target,target_origin=origin,
        risk_fraction=risk,modeled_loss_per_notional=risk+COST,after_cost_rr=rr,admission_cost_allowance=COST,
        available_at=available,expires_at=(r.date+pd.Timedelta(minutes=20)).isoformat(),max_hold_hours=8 if recipe=='continuation' else 4,
        entry_policy='0.15ATR_RETRACE_SAME_STOP_AND_TARGET' if retrace else 'SIGNAL_CLOSE_LIMIT',
        deviation_fraction=min(.0015,.25*atr/close),atr_at_signal=atr,
        boundary=float(r.prior_low if sign==1 else r.prior_high) if recipe=='reversal' else None,
        invalidation='PRIOR6_PULLBACK_AND_SIGNAL_EXTREME_PLUS_0.2ATR' if recipe=='continuation' else 'FAILED_BOUNDARY_SIGNAL_EXTREME_PLUS_0.2ATR',
        obstacles=obstacles,cautions=['NEAR_OBSTACLES_ARE_CONTEXT_NOT_AUTOMATIC_VETO'] if obstacles else [],
        flow=dict(status='UNKNOWN',reason='NO_GENUINE_HISTORICAL_FLOW'),profile_fidelity='OHLCV_PROXY',
        fill_model='NATIVE_LIMIT_RANGE_SCENARIO_QUEUE_UNKNOWN')
    return g,'TRADE'


def execution_plan(g,rate,now):
    sign=1 if g['side']=='long' else -1
    if not pd.Timestamp(g['available_at'])<=pd.Timestamp(now)<pd.Timestamp(g['expires_at']): return None
    if not finite(rate) or rate<=0 or abs(rate/g['reference']-1)>g['deviation_fraction']+1e-12: return None
    risk=sign*(rate-g['stop'])/rate; reward=sign*(g['target']-rate)/rate
    if not .003<=risk<=.025 or (reward-COST)/(risk+COST)<1.25: return None
    return g|dict(risk_fraction=risk,modeled_loss_per_notional=risk+COST)
