"""Three preregistered correction hypotheses; no outcome or fitted parameter input."""
import copy
import numpy as np
import pandas as pd
from policy_features import execution_plan,plan,raw_signals
from session4_features import validity,structure_reason

def expansion(row,side):
    sign=1 if side=='long' else -1
    return sign*(float(row.close)-float(row.open))>=.8*float(row.atr14) and float(row.rvol)>=1.2

def conditional_entry(g,row):
    result=copy.deepcopy(g)
    if g['recipe']=='reversal' or expansion(row,g['side']):
        result['entry_policy']='ORIGINAL_IMMEDIATE_ON_EXPANSION_OR_REVERSAL'
    else:
        sign=1 if g['side']=='long' else -1
        result['reference']=float(g['reference']-sign*.15*g['atr_at_signal'])
        result['entry_policy']='BOUNDED_PASSIVE_0.15ATR_WITHOUT_EXPANSION'
    return execution_plan(result,result['reference'],pd.Timestamp(result['available_at']))

def relaxed_candidates(frame):
    """Only remove the three EMA predicates; frozen structural authority remains."""
    common=validity(frame)&frame.vwap_valid&frame.session_bars.ge(8)&frame.same_session&frame.adx_1h.ge(20)&frame.rvol.ge(1)
    span=(frame.high-frame.low).replace(0,np.nan);out=[]
    for side,sign in [('long',1),('short',-1)]:
        mask=(common&frame['accepted_'+side]&frame['prior_touch_'+side]
            &(sign*(frame.close-frame['previous_high' if sign==1 else 'previous_low'])>0)&(sign*(frame.close-frame.open)>0)
            &(((frame.close-frame.low) if sign==1 else (frame.high-frame.close))/span>=.65)
            &(((frame.close-frame.pullback_low) if sign==1 else (frame.pullback_high-frame.close))/frame.atr14<=2.5))
        for i,r in frame.loc[mask].iterrows():
            if structure_reason(r,'continuation',side)!='MATCH':continue
            g,why=plan(r,'continuation',side)
            out.append(dict(index=int(i),at=(r.date+pd.Timedelta(minutes=15)).isoformat(),recipe='continuation',side=side,reason=why,plan=g))
    return out

def compatible_thesis(g,tick):
    if g['recipe']!='continuation':return False
    boundary=g.get('boundary')
    if boundary is None or not np.isfinite(boundary):return False
    sign=1 if g['side']=='long' else -1
    failure_line=boundary-sign*.15*g['atr_at_signal']
    return sign*(failure_line-g['stop'])>float(tick)
