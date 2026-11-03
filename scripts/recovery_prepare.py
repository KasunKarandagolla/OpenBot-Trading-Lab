"""Causal feature caches and pre-registered plans. Freqtrade owns portfolio simulation."""
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
import sys
import numpy as np
import pandas as pd
from recovery_common import *

def feature_job(task):
    window,pair=task
    from freqtrade.strategy import merge_informative_pair
    from session4_features import hourly,indicators
    from recovery_features import augment
    target=WORK/window/'features'/(slug(pair)+'.pkl')
    if target.exists():return pair
    base=DATA/window/'gate/futures'
    d=pd.read_feather(base/(slug(pair)+'-15m-futures.feather'))
    h=pd.read_feather(base/(slug(pair)+'-1h-futures.feather'))
    d=augment(indicators(merge_informative_pair(d,hourly(h),'15m','1h',ffill=True)))
    listing=read(DATA/'contract-source.json')[pair]['market']['info'].get('create_time')
    if listing:d['eligible'] &= d.date>=pd.Timestamp(int(listing),unit='s',tz='UTC')
    target.parent.mkdir(parents=True,exist_ok=True);d.to_pickle(target)
    print('features',window,pair,len(d),flush=True)
    return pair

def prepare(window):
    from session4_features import candidates
    from recovery_features import context_pass,momentum_plan
    target=OUT/('plans-'+window+'.json')
    if target.exists():raise ValueError('preserve completed plans')
    if window=='independent' and not (OUT/'freeze.json').exists():raise ValueError('not frozen')
    with ProcessPoolExecutor(max_workers=4) as pool:list(pool.map(feature_job,[(window,p) for p in pairs()]))
    frames={p:pd.read_pickle(WORK/window/'features'/(slug(p)+'.pkl')) for p in pairs()}
    wide=pd.concat([d[['date','eligible','prior_day_quote','return4h','return24h','activity','ema20_1h','ema50_1h','atr14','close','prior_low','prior_high']].assign(pair=p) for p,d in frames.items()],ignore_index=True)
    btc=frames['BTC/USDT:USDT'].set_index('date')
    breadth=wide.loc[wide.eligible].assign(up=lambda q:q.return24h>0).groupby('date').up.mean()
    for pair,d in frames.items():
        d['btc_return4h']=d.date.map(btc.return4h);d['relative24h']=d.return24h-d.date.map(btc.return24h)
        d['breadth']=d.date.map(breadth)
        d.to_pickle(WORK/window/'features'/(slug(pair)+'.pkl'))
    variants=['reference','structure','context','context-smc','momentum','liquid-momentum']+['rank-'+str(i) for i in range(1,32)]
    plans={v:{} for v in variants};slots={v:{} for v in ['reference','structure']+['rank-'+str(i) for i in range(1,32)]}
    rngs={v:np.random.default_rng(61000+int(v[5:])) for v in slots if v.startswith('rank-')}
    begin='2026-08-05' if window=='development' else '2026-01-01'
    end='2026-11-03' if window=='development' else '2026-07-26'
    for date,group in wide.groupby('date',sort=True):
        if not begin<=date.isoformat()<end:continue
        at=(date+pd.Timedelta(minutes=15)).isoformat()
        q=group.loc[group.eligible & np.isfinite(group.return4h)&np.isfinite(group.activity)].copy()
        if q.empty:continue
        q['relative']=q.return4h-float(btc.loc[date,'return4h'])
        q.loc[q.pair.eq('BTC/USDT:USDT'),'relative']=q.return4h
        for recipe in ('continuation','reversal'):
            for side,s in [('long',1),('short',-1)]:
                g=q.loc[s*(q.ema20_1h-q.ema50_1h)>0].copy() if recipe=='continuation' else q.copy()
                if g.empty:continue
                g['score']=s*g.relative+.01*g.activity.clip(upper=3) if recipe=='continuation' else s*(g.close-(g.prior_low if s==1 else g.prior_high))/g.atr14
                lane=recipe+':'+side
                for v in ['reference','structure']:slots[v].setdefault(at,{})[lane]=g.sort_values(['score','pair'],ascending=[False,True]).pair.head(3).tolist()
                for v,rng in rngs.items():slots[v].setdefault(at,{})[lane]=rng.choice(sorted(g.pair),min(3,len(g)),replace=False).tolist()
        # Daily cross-sectional rank uses only completed daily returns and prior liquidity.
        if (date+pd.Timedelta(minutes=15)).hour==0 and date.minute==45:
            for side,s in [('long',1),('short',-1)]:
                g=q.loc[s*q.return24h>0].copy()
                if g.empty:continue
                for v,key in [('momentum','return24h'),('liquid-momentum','prior_day_quote')]:
                    ordered=g.sort_values([key,'pair'],ascending=[side=='short' if key=='return24h' else False,True])
                    # One per side. Missing/too volatile winner means abstention, never choose next winner retrospectively.
                    pair=ordered.pair.iloc[0];r=frames[pair].loc[frames[pair].date.eq(date)].iloc[0]
                    p=momentum_plan(r,side,pair)
                    if p:plans[v].setdefault(pair,{})[at]=p
    summary={};opps=[]
    for pair,d in frames.items():
        for mode in ['reference','structure']:
            for item in candidates(d,mode):
                if not begin<=item['at']<end:continue
                p=item['plan'];lane=item['recipe']+':'+item['side'];at=item['at'];r=d.iloc[item['index']]
                eligible=pair in slots[mode].get(at,{}).get(lane,[])
                opps.append(dict(pair=pair,variant=mode,**item,ranked=eligible))
                if item['reason']!='TRADE' or p is None:continue
                p=dict(p,decision_id=pair+':'+p['decision_id'])
                if eligible:plans[mode].setdefault(pair,{})[at]=p
                if mode=='reference':
                    for v in rngs:
                        if pair in slots[v].get(at,{}).get(lane,[]):plans[v].setdefault(pair,{})[at]=p
                if eligible and item['recipe']=='continuation' and context_pass(r,item['side']):
                    plans['context' if mode=='reference' else 'context-smc'].setdefault(pair,{})[at]=dict(p,policy_id='recovery-v1.0.0',methodology='context')
    for v,by_pair in plans.items():
        write(WORK/window/'plans'/(v+'.json'),by_pair)
        summary[v]=dict(plans=sum(len(z) for z in by_pair.values()),sha256=sha(WORK/window/'plans'/(v+'.json')))
    write(target,summary);write(OUT/('opportunities-'+window+'.json'),opps)
    write(OUT/('features-'+window+'.json'),{p:sha(WORK/window/'features'/(slug(p)+'.pkl')) for p in pairs()})
    print(window,summary,flush=True)

if __name__=='__main__':prepare(sys.argv[1])
