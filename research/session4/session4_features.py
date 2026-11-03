"""Causal setup questions. Bar opens and confirmation/availability clocks stay separate."""
import json
import math
import numpy as np
import pandas as pd
import talib.abstract as ta
from PlaybookRiskV1 import session_features
from advanced_features import advanced
from causal_structure import structure
from policy_features import features as v3_features, raw_signals, suitability, plan


def hour_plan(r,recipe,side):
    """Independent hour geometry, 9 hourly ATR objective bound and longer hold."""
    sign=1 if side=='long' else -1;entry=float(r.close);atr=float(r.atr14)
    extreme=min(float(r.low),float(r.pullback_low)) if sign==1 else max(float(r.high),float(r.pullback_high))
    if recipe=='reversal':extreme=float(r.low if sign==1 else r.high)
    stop=extreme-sign*.2*atr;risk=sign*(entry-stop)/entry;target=entry+sign*3*risk*entry
    if not .003<=risk<=.025:return None,'HOUR_STOP_OUTSIDE_0.3_2.5_PERCENT'
    if sign*(target-entry)>9*atr:return None,'HOUR_TARGET_EXCEEDS_9ATR'
    rr=(3*risk-.0038)/(risk+.0038)
    if rr<1.25:return None,'HOUR_NET_RR_UNDER_1.25'
    at=r.date+pd.Timedelta(minutes=15)
    return dict(policy_id='structure-execution-v4.0.0',recipe=recipe,side=side,reference=entry,signal_close=entry,
        stop=stop,structural_stop=stop,target=target,target_origin='HOUR_3R_MAX_9ATR',risk_fraction=risk,
        modeled_loss_per_notional=risk+.0038,after_cost_rr=rr,admission_cost_allowance=.0038,
        available_at=at.isoformat(),expires_at=(at+pd.Timedelta(minutes=5)).isoformat(),
        max_hold_hours=24 if recipe=='continuation' else 12,deviation_fraction=min(.0015,.25*atr/entry),
        atr_at_signal=atr,boundary=float(r.prior_low if sign==1 else r.prior_high) if recipe=='reversal' else None,
        invalidation='PRIOR6_HOURLY_EXTREME_PLUS_0.2_HOURLY_ATR',profile_fidelity='OHLCV_PROXY',
        flow={'status':'UNKNOWN'},entry_policy='CLOSED_HOUR_SIGNAL_CLOSE_LIMIT',fill_model='NATIVE_LIMIT_RANGE_QUEUE_UNKNOWN'), 'TRADE'


def hourly(d):
    d=d.copy()
    for key,n in [('ema20',20),('ema50',50)]:d[key]=ta.EMA(d,timeperiod=n)
    d['adx']=ta.ADX(d,timeperiod=14);d['atr']=ta.ATR(d,timeperiod=14)
    d['context_valid']=np.isfinite(d[['open','high','low','close','volume']]).all(axis=1)&d.volume.gt(0)&d.date.diff().eq(pd.Timedelta(hours=1))
    d=structure(d,'1h')
    day=d.date.dt.floor('D');typical=(d.high+d.low+d.close)/3
    d['hour_vwap']=(typical*d.volume).groupby(day).cumsum()/d.volume.groupby(day).cumsum().replace(0,np.nan)
    d['hour_rvol']=d.volume/d.volume.shift().rolling(20).mean()
    d['hour_pull_low']=d.low.shift().rolling(6).min();d['hour_pull_high']=d.high.shift().rolling(6).max()
    d['hour_prev_high']=d.high.shift();d['hour_prev_low']=d.low.shift()
    d['hour_boundary_low']=d.low.shift().rolling(20).min();d['hour_boundary_high']=d.high.shift().rolling(20).max()
    d['hour_touch_long']=(d.low<=d.ema20+.35*d.atr).shift().rolling(4).max().eq(1)
    d['hour_touch_short']=(d.high>=d.ema20-.35*d.atr).shift().rolling(4).max().eq(1)
    return d


def liquidity(d):
    """No partial-day liquidity or future membership. Quote volume is an OHLCV estimate."""
    day=d.date.dt.floor('D');quote=d.volume*(d.high+d.low+d.close)/3
    daily=pd.DataFrame(dict(day=day,q=quote)).groupby('day').q.sum()
    count=d.groupby(day).size()
    # Missing calendar days cannot masquerade as seven consecutive observations.
    full=pd.date_range(day.min(),day.max(),freq='D',tz='UTC')
    daily=daily.reindex(full);count=count.reindex(full)
    complete=count.eq(96)
    prior=daily.where(complete).shift()
    avg=prior.rolling(7,min_periods=7).mean()
    return pd.DataFrame(dict(prior_day_quote=day.map(prior),prior7_quote=day.map(avg),
        eligible=day.map(avg).ge(1e7)&day.map(prior).ge(1e7)&(d.date>=d.date.iloc[0]+pd.Timedelta(days=10)),
        return4h=d.close.pct_change(16),activity=quote.rolling(16).sum()/quote.shift(16).rolling(16).sum()),index=d.index)


def indicators(d):
    d=v3_features(advanced(session_features(d)))
    for key in ('poc','val','vah'):d['vp2_'+key]=d['vp_'+key]
    d['vp2_known_at']=d.date
    metrics=liquidity(d)
    for key in metrics:d[key]=metrics[key]
    # Remember a zone only AFTER its formation bar closes. Expire after 8 bars.
    for direction in ('up','down'):
        zones=[];active=None
        for i,r in d.iterrows():
            known=r.date+pd.Timedelta(minutes=15);retest=False;stamp=None
            if active and known-active['known']<=pd.Timedelta(hours=2):
                if direction=='up':retest=r.low<=active['upper'] and r.close>active['lower'] and r.close>r.open
                else:retest=r.high>=active['lower'] and r.close<active['upper'] and r.close<r.open
                stamp=active['known']
            if bool(r['fvg_'+direction]):
                active=dict(lower=float(d.high.shift(2).loc[i]) if direction=='up' else float(r.high),
                            upper=float(r.low) if direction=='up' else float(d.low.shift(2).loc[i]),known=known)
            zones.append((bool(retest),stamp))
        d['fvg_retest_'+direction]=[x[0] for x in zones]
        d['fvg_retest_'+direction+'_known_at']=pd.to_datetime([x[1] for x in zones],utc=True)
    for side,direction in [('long','UP'),('short','DOWN')]:
        shift=d.struct_event.isin(['CHOCH','INITIAL_BREAK'])&d.struct_direction.eq(direction)
        d['recent_shift_'+side]=shift.rolling(4,min_periods=1).max().eq(1)
    # Sweep clocks/levels are carried forward at most three bars, never rewritten.
    raw=raw_signals(d,validity(d))
    for side in ('long','short'):
        mask=raw[('reversal',side)]
        for label,key in [('extreme','low' if side=='long' else 'high'),('boundary','prior_low' if side=='long' else 'prior_high')]:
            d['sweep_'+label+'_'+side]=d[key].where(mask).ffill(limit=3)
        d['sweep_known_'+side]=(d.date+pd.Timedelta(minutes=15)).where(mask).ffill(limit=3)
    return d


def validity(d):
    cols=['open','high','low','close','volume','atr14','ema20','ema50','rvol','ema20_1h','ema50_1h','adx_1h']
    age=d.date+pd.Timedelta(minutes=15)-(d.date_1h+pd.Timedelta(hours=1))
    return np.isfinite(d[cols]).all(axis=1)&d.volume.gt(0)&d.contiguous&d.atr_ratio.between(.001,.025)&d.context_valid_1h.eq(True)&age.between(pd.Timedelta(0),pd.Timedelta(minutes=45))


def structure_reason(r,recipe,side):
    sign=1 if side=='long' else -1;direction='UP' if sign==1 else 'DOWN'
    if recipe=='continuation':
        # Either coherent hourly bias OR a causal local imbalance retest; not an all-condition checklist.
        return 'MATCH' if (r.get('struct_direction_1h')==direction or
            (bool(r.get('fvg_retest_up' if sign==1 else 'fvg_retest_down',False)) and r.get('struct_direction')==direction)) else 'WATCH_STRUCTURE_BIAS'
    boundary=r.get('sweep_boundary_'+side)
    if pd.isna(boundary):return 'WAIT_SWEEP'
    keys=['prior_day_low','prior_session_low','prior_swing_low'] if sign==1 else ['prior_day_high','prior_session_high','prior_swing_high']
    external=any(pd.notna(r.get(k)) and abs(float(r[k])-float(boundary))<=.5*r.atr14 for k in keys)
    shift=bool(r.get('recent_shift_'+side,False))
    displacement=bool(r.get('displace_up' if sign==1 else 'displace_down',False))
    reclaimed=sign*(r.close-float(boundary))>0
    return 'MATCH' if external and reclaimed and (shift or displacement) else 'WAIT_EXTERNAL_SWEEP_REACCEPTANCE_OR_SHIFT'


def candidates(d,mode='structure'):
    masks=raw_signals(d,validity(d));records=[]
    if mode=='structure':
        for side,sign in [('long',1),('short',-1)]:
            known=d['sweep_known_'+side]
            boundary=d['sweep_boundary_'+side]
            masks[('reversal',side)]=validity(d)&known.notna()&(sign*(d.close-boundary)>0)&(d['recent_shift_'+side]|d['displace_up' if sign==1 else 'displace_down'])
    if mode=='hour':
        hourclose=d.date.dt.minute.eq(45)&validity(d)
        masks={}
        for side,sign in [('long',1),('short',-1)]:
            masks[('continuation',side)]=hourclose&(sign*(d.ema20_1h-d.ema50_1h)>0)&d.adx_1h.ge(20)&d.hour_rvol_1h.ge(1)&d['hour_touch_'+side+'_1h']&(sign*(d.close_1h-d['hour_prev_high_1h' if sign==1 else 'hour_prev_low_1h'])>0)&(sign*(d.close_1h-d.hour_vwap_1h)>0)
            b=d.hour_boundary_low_1h if sign==1 else d.hour_boundary_high_1h
            masks[('reversal',side)]=hourclose&d.adx_1h.le(30)&d.hour_rvol_1h.ge(1.2)&(sign*(d.close_1h-b)>0)&(sign*(d['low_1h' if sign==1 else 'high_1h']-b)<0)
    for (recipe,side),mask in masks.items():
        for idx,r in d.loc[mask].iterrows():
            reason=suitability(r,recipe,side) if mode!='hour' else 'MATCH'
            p=r.copy()
            if mode=='structure':
                reason=structure_reason(r,recipe,side)
                if recipe=='reversal':
                    p['low' if side=='long' else 'high']=r['sweep_extreme_'+side]
                    p['prior_low' if side=='long' else 'prior_high']=r['sweep_boundary_'+side]
            if mode=='hour':
                for k,hk in [('atr14','atr_1h'),('pullback_low','hour_pull_low_1h'),('pullback_high','hour_pull_high_1h'),('low','low_1h'),('high','high_1h'),('prior_low','hour_boundary_low_1h'),('prior_high','hour_boundary_high_1h')]:p[k]=r[hk]
            g,why=hour_plan(p,recipe,side) if mode=='hour' else plan(p,recipe,side)
            if reason=='MATCH':reason=why
            if g:
                if mode=='hour':g['max_hold_hours']=24 if recipe=='continuation' else 12
                g['decision_id']=f'{mode}:{r.get("symbol", "") }:{recipe}:{side}:{g["available_at"]}'
                g['methodology']=mode;g['structure_confirmation_at']=str(r.struct_known_at)
                g['hour_structure']=str(r.get('struct_direction_1h'));g['dealing_location']=float(r.dealing_location) if pd.notna(r.dealing_location) else None
                g['orderflow_fidelity']='UNKNOWN_HISTORICAL';g['profile_fidelity']='OHLCV_PROXY'
            records.append(dict(index=int(idx),at=(r.date+pd.Timedelta(minutes=15)).isoformat(),recipe=recipe,side=side,reason=reason,plan=g))
    return records
