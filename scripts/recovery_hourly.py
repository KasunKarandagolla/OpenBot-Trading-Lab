"""Availability-driven, separately sealed hourly momentum transfer experiment.

No 15m candles are fabricated from hourly data. Daily decisions are identical
in economic definition; native entry/stop/exit resolution is explicitly hourly.
"""
from concurrent.futures import ThreadPoolExecutor
import sys
import shutil
import numpy as np
import pandas as pd
import talib.abstract as ta
from recovery_common import *

def acquire():
    from recovery_data import fetch_one
    if not (OUT/'hourly-freeze.json').exists():raise ValueError('hourly amendment not sealed')
    tasks=[(p,t,k) for p in pairs() for t,k in [('1h','futures'),('1h','mark'),('1h','funding_rate')]]
    def job(task):fetch_one('hourly-independent',*task,start='2026-05-10',end='2026-07-26')
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(job,tasks))
    write(OUT/'data-hourly-independent.json',dict(files=[read(p) for p in sorted((OUT/'sources/hourly-independent').glob('*.json'))],
        resolution='REAL_SOURCE_1H',evaluation='20260520-20260726',warmup='20260510-20260520',
        universe=pairs(),historical_specs='CURRENT_SNAPSHOT_ONLY; delistings unknown',
        no_15m_or_minute_history='Gate 10000point retention. Independent result validates hourly execution model only.'))

def prepare(window):
    from recovery_features import momentum_plan
    frames={};plans={v:{} for v in ['momentum','liquid-momentum']}
    development=window=='hourly-development';source='development' if development else window
    begin='2026-08-05' if development else '2026-05-20';end='2026-11-03' if development else '2026-07-26'
    for pair in pairs():
        base=DATA/source/'gate/futures';d=pd.read_feather(base/(slug(pair)+'-1h-futures.feather')).copy()
        d['atr14']=ta.ATR(d,timeperiod=14);d['atr_1h']=d.atr14;d['hour_atr_fraction']=d.atr14/d.close
        d['return24h']=d.close.pct_change(24);day=d.date.dt.floor('D')
        quote=d.volume*(d.high+d.low+d.close)/3;daily=quote.groupby(day).sum();counts=d.groupby(day).size()
        prior=daily.where(counts.eq(24)).shift();avg=prior.rolling(7,min_periods=7).mean()
        d['prior_day_quote']=day.map(prior);d['eligible']=day.map(prior).ge(1e7)&day.map(avg).ge(1e7)&(d.date>=d.date.iloc[0]+pd.Timedelta(days=10))
        listing=read(DATA/'contract-source.json')[pair]['market']['info'].get('create_time')
        if listing:d['eligible'] &= d.date>=pd.Timestamp(int(listing),unit='s',tz='UTC')
        d['thesis_lost_long']=False;d['thesis_lost_short']=False
        frames[pair]=d
        target=WORK/window/'features'/(slug(pair)+'.pkl');target.parent.mkdir(parents=True,exist_ok=True);d.to_pickle(target)
        if development:
            dest=DATA/window/'gate/futures';dest.mkdir(parents=True,exist_ok=True)
            for suffix in ['1h-futures','1h-mark','1h-funding_rate']:
                p=base/(slug(pair)+'-'+suffix+'.feather');q=dest/p.name
                if not q.exists():shutil.copyfile(p,q)
    wide=pd.concat([d.assign(pair=p) for p,d in frames.items()],ignore_index=True)
    for date,g in wide.loc[wide.date.dt.hour.eq(23)].groupby('date'):
        at=date+pd.Timedelta(hours=1)
        if not begin<=at.isoformat()<end:continue
        q=g.loc[g.eligible & np.isfinite(g.return24h)]
        for side,s in [('long',1),('short',-1)]:
            z=q.loc[s*q.return24h>0]
            if z.empty:continue
            for v,key in [('momentum','return24h'),('liquid-momentum','prior_day_quote')]:
                r=z.sort_values([key,'pair'],ascending=[side=='short' if key=='return24h' else False,True]).iloc[0]
                p=momentum_plan(r,side,r.pair)
                if p:
                    p.update(available_at=at.isoformat(),expires_at=(at+pd.Timedelta(minutes=5)).isoformat(),
                        decision_id=f'{r.pair}:momentum:{side}:{at.isoformat()}',fill_model='NATIVE_HOURLY_NEXT_OPEN;1H_BARRIER_SEQUENCE_UNCERTAIN')
                    plans[v].setdefault(r.pair,{})[at.isoformat()]=p
    summary={}
    for v,obj in plans.items():
        p=WORK/window/'plans'/(v+'.json');write(p,obj);summary[v]=dict(plans=sum(len(x) for x in obj.values()),sha256=sha(p))
    write(OUT/('plans-'+window+'.json'),summary)
    write(OUT/('features-'+window+'.json'),{p:sha(WORK/window/'features'/(slug(p)+'.pkl')) for p in pairs()})
    if development:write(OUT/('data-'+window+'.json'),read(OUT/'data-development.json'))
    print(window,summary,flush=True)

if __name__=='__main__':
    if sys.argv[1]=='acquire':acquire()
    else:prepare(sys.argv[1])
