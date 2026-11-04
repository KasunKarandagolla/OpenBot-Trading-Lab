"""Supplement the V4 reference lane with the owner's selected frozen structure lane."""
import pandas as pd
import numpy as np
from setup_common import *
from session4_features import candidates
def prepare():
    frames={p:pd.read_pickle(WORK/'features/v4'/(slug(p)+'.pkl')).set_index('date',drop=False) for p in pairs()}
    btc=frames['BTC/USDT:USDT'];plans={}
    records=[]
    for pair,f in frames.items():
        for x in candidates(f.reset_index(drop=True),'structure'):
            if x['reason']!='TRADE' or not x['plan'] or not protocol()['evaluation_start']<=x['at']<protocol()['end_exclusive']:continue
            at=pd.Timestamp(x['at'])-pd.Timedelta(minutes=15);s=1 if x['side']=='long' else -1;ranking=[]
            for p,d in frames.items():
                r=d.loc[at]
                if not r.eligible or not np.isfinite(r.return4h) or not np.isfinite(r.activity):continue
                if x['recipe']=='continuation':
                    if s*(r.ema20_1h-r.ema50_1h)<=0:continue
                    score=s*(r.return4h-(0 if p=='BTC/USDT:USDT' else btc.loc[at,'return4h']))+.01*min(float(r.activity),3)
                else:score=s*(r.close-(r.prior_low if s==1 else r.prior_high))/r.atr14
                ranking.append((float(score),p))
            ranking.sort(key=lambda z:(-z[0],z[1]))
            if pair in [p for _,p in ranking[:3]]:plans.setdefault(pair,{})[x['at']]=dict(x['plan'],decision_id=pair+':'+x['plan']['decision_id'])
    path=WORK/'plans/v4-structure.json';write(path,plans)
    m=read(OUT/'plans.json');m['v4-structure']=dict(plans=sum(map(len,plans.values())),sha256=sha(path),conflicts=0)
    write(OUT/'plans.json',m)
    write(OUT/'v4-control-registration.json',dict(at=now(),method='Frozen session4_features.candidates structure mode and frozen three-per-lane V4 ranking; unchanged RecoveryPolicyR1 native lifecycle',
        scope='Correct baseline labeling: reference lane remains; structure lane is the owner-retained PaperPolicyV4 default. Added without changing any challenger rule.',
        source_sha256=sha(ROOT/'scripts/setup_v4_control.py'),plans_sha256=sha(path),plans=sum(map(len,plans.values())),outcomes_read_before_this_control=True))
if __name__=='__main__':prepare()
