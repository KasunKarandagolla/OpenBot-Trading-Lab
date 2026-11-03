"""Genuine bounded1m sources and attainable-range diagnostics, never queue claims."""
from concurrent.futures import ThreadPoolExecutor
import sys
import numpy as np
import pandas as pd
from recovery_common import *

def acquire():
    from recovery_data import fetch_one,client,metadata
    def job(p):fetch_one('development',p,'1m','futures',start='2026-10-29',end='2026-11-03')
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(job,pairs()))
    files=[read(OUT/'sources/development'/(slug(p)+'-1m-futures.json')) for p in pairs()]
    if any(f['rows']!=7200 or f['gaps'] for f in files):raise ValueError('incomplete minute source')
    write(OUT/'detail-manifest.json',dict(files=files,window='20261029-20261103',complete=True,
        independent_detail='UNAVAILABLE:Gate10000recent-candle retention;no request beyond supported history',
        observations='Actual traded1m ranges;queue/within-minute order sequence/partial-order probability unknown'))
    ex=client();ex.set_markets([r['market'] for r in metadata().values()]);books=[]
    for p in pairs():
        q=ex.fetch_order_book(p,20);bid=q['bids'][0][0];ask=q['asks'][0][0]
        books.append(dict(pair=p,received_at=now(),source_timestamp=q.get('timestamp'),bid=bid,ask=ask,
            spread_bp=(ask-bid)/((ask+bid)/2)*1e4,
            caveat='Instantaneous public quote;not a historical spread/slippage distribution or a queue guarantee'))
    write(OUT/'current-spreads.json',books)

def diagnose():
    rows=[]
    for variant in ['reference','structure','context','context-smc','momentum','liquid-momentum']:
        plans=read(WORK/'development/plans'/(variant+'.json'))
        for pair,items in plans.items():
            d=pd.read_feather(DATA/'development/gate/futures'/(slug(pair)+'-1m-futures.feather')).set_index('date')
            for at,p in items.items():
                a=pd.Timestamp(at)
                if not pd.Timestamp('2026-10-29',tz='UTC')<=a<pd.Timestamp('2026-11-03',tz='UTC'):continue
                q=d.loc[(d.index>=a)&(d.index<a+pd.Timedelta(minutes=5))];s=1 if p['side']=='long' else -1;e=p['reference']
                complete=len(q)==5 and (q.index==pd.date_range(a,periods=5,freq='min')).all()
                touch=(q.low<=e) if s==1 else (q.high>=e)
                through=(q.low<=e*.9999) if s==1 else (q.high>=e*1.0001)
                rows.append(dict(variant=variant,pair=pair,at=at,side=p['side'],reference=e,
                    minute_rows=len(q),complete=bool(complete),touch_within5m=bool(touch.any()) if complete else None,
                    through1bp_within5m=bool(through.any()) if complete else None,
                    next_open_marketable=bool((q.open.iloc[0]<=e) if s==1 else (q.open.iloc[0]>=e)) if complete else None,
                    first_touch_minute=int(np.flatnonzero(touch)[0]) if touch.any() else None,
                    max_5min_adverse_from_limit_bp=float(((q.low.min()/e-1) if s==1 else (1-q.high.max()/e))*1e4) if complete else None,
                    queue='UNKNOWN',fill_probability='NOT_ESTIMATED_RANGE_ONLY',funding='source_actual_events_in_native_portfolios'))
    write(OUT/'minute-feasibility.json',dict(rows=rows,summary={v:dict(n=len(q),complete=sum(r['complete'] for r in q),
        touch=sum(r['touch_within5m'] is True for r in q),through=sum(r['through1bp_within5m'] is True for r in q),
        immediate=sum(r['next_open_marketable'] is True for r in q)) for v in sorted({r['variant'] for r in rows}) for q in [[r for r in rows if r['variant']==v]]},
        limitation='Five recent days only;actual1m range feasibility upper bounds,not historical queue fill probabilities. Use complete native detail portfolios for economics.'))

if __name__=='__main__':globals()[sys.argv[1]]()
