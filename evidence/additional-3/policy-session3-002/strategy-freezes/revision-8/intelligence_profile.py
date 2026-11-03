"""V2 contiguous profile; the original frozen profile remains unchanged."""
import numpy as np

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
