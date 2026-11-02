"""Causal SMC extension, crypto UTC ICT context and explicitly approximate profile.

All row timestamps are candle opens. Values become available at row close.
Profile and prior boundaries exclude the signal candle. No retroactive pivots.
"""
import numpy as np
import pandas as pd
from causal_structure import structure


def volume_profile(prices, volumes, width=.001, fraction=.7):
    p=np.asarray(prices,dtype=float);v=np.asarray(volumes,dtype=float)
    good=np.isfinite(p)&np.isfinite(v)&(p>0)&(v>0)
    if not good.any():return None
    bins=np.floor(np.log(p[good])/width).astype('int64')
    ids,inverse=np.unique(bins,return_inverse=True)
    weights=np.bincount(inverse,weights=v[good]); mid=np.exp((ids+.5)*width)
    poc=int(np.argmax(weights));lo=hi=poc;total=weights.sum();area=weights[poc]
    # Adjacent occupied bins; deterministic lower-price tie break.
    while area<total*fraction and (lo>0 or hi<len(weights)-1):
        lower=weights[lo-1] if lo>0 else -1
        upper=weights[hi+1] if hi<len(weights)-1 else -1
        if lower>=upper:lo-=1;area+=weights[lo]
        else:hi+=1;area+=weights[hi]
    hvn=mid[weights>=np.quantile(weights,.8)]
    lvn=mid[weights<=np.quantile(weights,.2)]
    return {'poc':float(mid[poc]),'val':float(np.exp(ids[lo]*width)),
            'vah':float(np.exp((ids[hi]+1)*width)),
            'hvn':hvn.tolist(),'lvn':lvn.tolist(),'total_base_volume':float(total),
            'occupied_bins':len(ids),'value_fraction_actual':float(area/total)}


def volume_profile_v2(prices, volumes, fidelity, width=.001, fraction=.7):
    """Contiguous log-price grid; empty price bins stay empty, never bridge gaps.

    Old profile remains frozen. Input units are base asset volume. This is a
    descriptive distribution, not proof of passive liquidity or future support.
    """
    if fidelity not in ('OHLCV_PROXY', 'OBSERVED_TRADES'):
        raise ValueError('explicit profile fidelity required')
    if not 0 < width <= .05 or not 0 < fraction <= 1:
        raise ValueError('invalid profile parameters')
    p=np.asarray(prices,dtype=float); v=np.asarray(volumes,dtype=float)
    if p.shape != v.shape: raise ValueError('profile shape mismatch')
    good=np.isfinite(p)&np.isfinite(v)&(p>0)&(v>0)
    if not good.any(): return None
    bins=np.floor(np.log(p[good])/width).astype('int64')
    if bins.max()-bins.min()>20000: raise ValueError('unbounded profile')
    ids=np.arange(bins.min(),bins.max()+1)
    weights=np.bincount(bins-bins.min(),weights=v[good],minlength=len(ids))
    mids=np.exp((ids+.5)*width); poc=int(np.argmax(weights)); lo=hi=poc
    total=float(weights.sum()); area=float(weights[poc])
    while area < fraction*total and (lo>0 or hi<len(ids)-1):
        left=weights[lo-1] if lo>0 else -1
        right=weights[hi+1] if hi<len(ids)-1 else -1
        if left>=right: lo-=1; area+=weights[lo]
        else: hi+=1; area+=weights[hi]
    positive=weights[weights>0]
    hvn=mids[(weights>0)&(weights>=np.quantile(positive,.8))]
    lvn=mids[(weights>0)&(weights<=np.quantile(positive,.2))]
    return dict(poc=float(mids[poc]),val=float(np.exp(ids[lo]*width)),vah=float(np.exp((ids[hi]+1)*width)),
        hvn=hvn.tolist(),lvn=lvn.tolist(),empty_bins=int((weights==0).sum()),bins=len(ids),
        total_base_volume=total,value_fraction_actual=float(area/total),fidelity=fidelity,
        value_area_method='CONTIGUOUS_PRICE_BINS_GREEDY_FROM_POC_LOWER_TIE',
        interpretation='Observed volume concentration; passive resting liquidity UNKNOWN')


def advanced(d):
    d=structure(d)
    # Prior distinct confirmed pivot permits objectively defined equal liquidity.
    for side in ('high','low'):
        s=d['swing_'+side]
        changes=s.where(s.ne(s.shift()))
        # Shift *pivot events*, not rows. Otherwise a pivot self-matches one row
        # after confirmation. Gaps reset the comparison's causal history.
        groups=(~d.struct_valid).cumsum()
        prev=changes.groupby(groups).transform(lambda e:e.dropna().shift().reindex(e.index).ffill())
        d['equal_'+side]=(s-prev).abs()<=.1*d.atr14
    at=d.date
    day=at.dt.floor('D'); session=at.dt.floor('8h')
    for label,groups in [('day',day),('session',session)]:
        ends=d.groupby(groups).agg(high=('high','max'),low=('low','min'))
        prior=ends.shift()
        d['prior_'+label+'_high']=groups.map(prior.high)
        d['prior_'+label+'_low']=groups.map(prior.low)
    span=d.prior_day_high-d.prior_day_low
    d['dealing_location']=(d.close-d.prior_day_low)/span.replace(0,np.nan)
    d['displace_up']=(d.close-d.open>=.8*d.atr14)&(d.close>d.open)&(d.rvol>=1)
    d['displace_down']=(d.open-d.close>=.8*d.atr14)&(d.close<d.open)&(d.rvol>=1)
    d['fvg_up']=(d.low>d.high.shift(2))&d.displace_up
    d['fvg_down']=(d.high<d.low.shift(2))&d.displace_down
    # Four-bar lifetime; no ffill of expired imbalances.
    d['recent_fvg_up']=d.fvg_up.rolling(4,min_periods=1).max().eq(1)
    d['recent_fvg_down']=d.fvg_down.rolling(4,min_periods=1).max().eq(1)
    d['fvg_up_lower']=d.high.shift(2).where(d.fvg_up).ffill(limit=3)
    d['fvg_down_upper']=d.low.shift(2).where(d.fvg_down).ffill(limit=3)
    profiles=[]
    typical=(d.high+d.low+d.close)/3
    for i in range(len(d)):
        p=None
        if i>=96 and d.date.iloc[i]-d.date.iloc[i-96]==pd.Timedelta(days=1):
            p=volume_profile(typical.iloc[i-96:i],d.volume.iloc[i-96:i])
        profiles.append(p)
    for k in ('poc','val','vah'):
        d['vp_'+k]=[p[k] if p else np.nan for p in profiles]
    d['vp_hvn_nearest']=[min(p['hvn'],key=lambda v:abs(v-c)) if p and p['hvn'] else np.nan for p,c in zip(profiles,d.close)]
    d['vp_lvn_nearest']=[min(p['lvn'],key=lambda v:abs(v-c)) if p and p['lvn'] else np.nan for p,c in zip(profiles,d.close)]
    d['vp_known_at']=d.date
    d['vp_anchor']=d.date-pd.Timedelta(days=1)
    return d


def qualifiers(row, recipe, side):
    sign=1 if side=='long' else -1
    bullish=side=='long'; direction='UP' if bullish else 'DOWN'; opposite='DOWN' if bullish else 'UP'
    if recipe=='vwap':
        smc=row.get('struct_direction_1h')!=opposite and row.get('struct_direction_1h') in ('UP','DOWN')
        ict=bool(row['recent_fvg_up' if bullish else 'recent_fvg_down']) and (row.dealing_location<=.5 if bullish else row.dealing_location>=.5)
        profile=bool(sign*(row.close-row.vp_poc)>0)
    else:
        boundary=row.prior_low if bullish else row.prior_high
        swing=row.get('prior_swing_low' if bullish else 'prior_swing_high',np.nan)
        smc=bool(np.isfinite(swing) and abs(swing-boundary)<=.5*row.atr14)
        levels=[row['prior_day_low' if bullish else 'prior_day_high'],row['prior_session_low' if bullish else 'prior_session_high']]
        raid=any(np.isfinite(v) and (row.low<v<row.close if bullish else row.high>v>row.close) for v in levels)
        shift=(row.get('struct_event') in ('CHOCH','INITIAL_BREAK') and row.get('struct_direction')==direction)
        ict=bool(raid and (row['displace_up' if bullish else 'displace_down'] or shift))
        profile=bool(row.vp_val<row.close<row.vp_vah and (row.low<row.vp_val if bullish else row.high>row.vp_vah))
    return {'smc':smc,'ict':ict,'profile':profile}


def plan(row, recipe, side, integrated=True, profile_only=False):
    """Structural stop first; target must precede nearest known opposing obstacle."""
    sign=1 if side=='long' else -1; ref=float(row.close)
    stop=float(row.low-.2*row.atr14 if sign==1 else row.high+.2*row.atr14)
    risk=sign*(ref-stop)/ref
    if not np.isfinite(risk) or not .003<=risk<=.025:return None
    target=ref+sign*2*risk*ref; origin='2R_FALLBACK'
    if integrated or profile_only:
        keys=['vp_poc'] if recipe=='sweep' and profile_only else ['vp_vah' if sign==1 else 'vp_val']
        if integrated:keys+=['prior_swing_high' if sign==1 else 'prior_swing_low','prior_day_high' if sign==1 else 'prior_day_low']
        candidates=[(float(row[k]),k) for k in keys if k in row and pd.notna(row[k]) and sign*(float(row[k])-ref)>0]
        if candidates:
            nearest,origin=min(candidates,key=lambda x:sign*(x[0]-ref))
            if sign*(nearest-target)<0:target=nearest
            else:origin='2R_BEFORE_'+origin
    reward=sign*(target-ref)/ref
    rr=(reward-.0035)/(risk+.0035)
    if rr<1.25:return None
    return {'reference':ref,'stop':stop,'target':target,'risk_fraction':risk,
            'modeled_loss_per_notional':risk+.0035,'target_origin':origin,
            'after_cost_rr':rr,'recipe':recipe,'side':side,'expiry_seconds':300,
            'max_hold_hours':8 if recipe=='vwap' else 4,
            'profile_fidelity':'OHLCV_TYPICAL_PRICE_PROXY_NOT_TRADED_VOLUME_AT_PRICE'}
