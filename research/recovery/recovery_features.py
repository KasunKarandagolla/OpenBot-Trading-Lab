"""Two economic hypotheses; no outcomes or future membership enter decisions."""
import numpy as np
import pandas as pd
import talib.abstract as ta

VERSION='recovery-v1.0.0'

def augment(d):
    d=d.copy()
    d['return24h']=d.close.pct_change(96)
    d['expanding']=d.atr14>d.atr14.shift().rolling(96,min_periods=96).median()
    d['hour_atr_fraction']=d.atr_1h/d.close
    return d

def context_pass(r,side):
    s=1 if side=='long' else -1
    return bool(s*r.btc_return4h>0 and s*r.relative24h>0 and
                (r.breadth>.5 if s==1 else r.breadth<.5) and r.expanding)

def momentum_plan(r,side,pair):
    """Daily winner/loser continuation. 2 completed-hour ATR stop,4R/24h exit."""
    s=1 if side=='long' else -1;entry=float(r.close)
    risk=max(.006,2*float(r.hour_atr_fraction))
    if not np.isfinite(risk) or risk>.025:return None
    at=r.date+pd.Timedelta(minutes=15)
    return dict(policy_id=VERSION,recipe='momentum',methodology='daily-relative-momentum',side=side,
        reference=entry,signal_close=entry,stop=entry*(1-s*risk),structural_stop=entry*(1-s*risk),
        target=entry*(1+s*4*risk),target_origin='4R_WITH_24H_TIMEOUT',risk_fraction=risk,
        modeled_loss_per_notional=risk+.0038,admission_cost_allowance=.0038,
        after_cost_rr=(4*risk-.0038)/(risk+.0038),available_at=at.isoformat(),
        expires_at=(at+pd.Timedelta(minutes=5)).isoformat(),max_hold_hours=24,
        deviation_fraction=.0015,atr_at_signal=float(r.atr14),boundary=None,
        decision_id=f'{pair}:momentum:{side}:{at.isoformat()}',
        invalidation='2_COMPLETED_HOUR_ATR_STOP',entry_policy='NEXT_OPEN_MARKET',
        fill_model='NATIVE_NEXT_OPEN; ADVERSE_COSTS_SEPARATE',profile_fidelity='OHLCV_PROXY',flow={'status':'UNKNOWN'})

