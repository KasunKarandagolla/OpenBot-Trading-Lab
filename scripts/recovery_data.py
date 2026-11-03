"""Bounded, public-only Gate source acquisition via the pinned CCXT adapter.

New evaluation prices are acquired only after the protocol/source seal exists.
No future reserved dates are accepted. No generated prices or invented funding.
"""
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import time
import pandas as pd
import ccxt
from recovery_common import *

WINDOWS = {'development': ('2026-07-26', '2026-11-03'),
           'independent': ('2025-12-22', '2026-07-26')}

def client():
    cfg = dict(enableRateLimit=True, timeout=15000, requests_trust_env=True,
               has={'fetchCurrencies':False},
               options={'defaultType':'swap', 'fetchMarkets':{'types':['swap']}})
    if os.environ.get('HTTPS_PROXY'): cfg['httpsProxy']=os.environ['HTTPS_PROXY']
    if os.environ.get('SSL_CERT_FILE'): cfg['cafile']=os.environ['SSL_CERT_FILE']
    return ccxt.gate(cfg)

def metadata():
    target=DATA/'contract-source.json'
    if target.exists(): return read(target)
    ex=client(); ex.load_markets(); rows={}
    for pair in pairs():
        m=ex.market(pair)
        if not (m['linear'] and m['swap'] and m['id']==pair.split('/')[0]+'_USDT'):
            raise ValueError('contract identity')
        tiers=ex.fetch_market_leverage_tiers(pair)
        rows[pair]=dict(market=m,tiers=tiers,observed_at=now())
    write(target,rows)
    # Preserve the previously reviewed small-notional risk contracts separately.
    write(OUT/'contracts.json',{p:read(ROOT/'evidence/session4/run-001/contracts.json')[p] for p in pairs()})
    return rows

def fetch_one(window,pair,tf,kind,start=None,end=None):
    start,end=(start,end) if start else WINDOWS[window]
    a=int(pd.Timestamp(start,tz='UTC').timestamp()*1000)
    b=int(pd.Timestamp(end,tz='UTC').timestamp()*1000)
    if b>int(pd.Timestamp('2026-11-03',tz='UTC').timestamp()*1000): raise ValueError('future forbidden')
    target=DATA/window/'gate/futures'/(slug(pair)+'-'+tf+'-'+kind+'.feather')
    if target.exists(): return
    ex=client(); ex.set_markets([r['market'] for r in metadata().values()]); events=[]; errors=[]
    seconds=ex.parse_timeframe(tf); cursor=a
    # Funding uses bounded 14-day slices; hourly label is native storage, not funding frequency.
    width=14*86400000 if kind=='funding_rate' else 1900*seconds*1000
    while cursor<b:
        stop=min(cursor+width,b)
        for attempt in range(2):
            try:
                if kind=='funding_rate':
                    rows=ex.fetch_funding_rate_history(pair,cursor,1000,{'until':stop-1})
                    part=[[r['timestamp'],r['fundingRate'],0.,0.,0.,0.] for r in rows]
                else:
                    rows=ex.fetch_ohlcv(pair,tf,cursor,1900,dict(until=stop-1,**({'price':kind} if kind=='mark' else {})))
                    part=rows
                events.extend(r for r in part if cursor<=r[0]<stop)
                break
            except Exception as exc:
                errors.append(dict(start=cursor,end=stop,attempt=attempt,error=str(exc)[:200]))
                if attempt: raise
        cursor=stop
    f=pd.DataFrame(events,columns=['date','open','high','low','close','volume'])
    if f.empty: raise ValueError('empty actual source '+pair+' '+tf+' '+kind)
    f['date']=pd.to_datetime(f.date,unit='ms',utc=True).dt.as_unit('ns')
    f=f.sort_values('date').reset_index(drop=True)
    if f.date.duplicated().any(): raise ValueError('duplicate source')
    for k in ['open','high','low','close','volume']:f[k]=f[k].astype(float)
    if kind=='futures':f['volume']*=float(metadata()[pair]['market']['contractSize'])
    if kind=='funding_rate': f=f[['date','open']].rename(columns={'open':'funding_rate'})
    target.parent.mkdir(parents=True,exist_ok=True); f.to_feather(target)
    entry=dict(path=str(target.relative_to(ROOT)),sha256=sha(target),rows=len(f),first=str(f.date.iloc[0]),last=str(f.date.iloc[-1]),
               gaps=int(f.date.diff().dropna().ne(pd.Timedelta(seconds=seconds)).sum()) if kind!='funding_rate' else None,
               actual_funding_intervals_seconds={str(k):int(v) for k,v in f.date.diff().dt.total_seconds().value_counts().items()} if kind=='funding_rate' else None,
               source='PUBLIC_GATE_REST_PINNED_CCXT_4.5.90',received_at=now(),errors=errors,
               historical_contract_specs='UNKNOWN; current public spec and listing clock only',
               volume_unit='BASE_ASSET; Gate contract count multiplied by current public contractSize' if kind=='futures' else 'NOT_APPLICABLE',
               flow='UNKNOWN',historical_spread='UNKNOWN')
    write(OUT/'sources'/window/(target.stem+'.json'),entry)
    print(window,pair,tf,kind,len(f),flush=True)

def acquire(window):
    if window=='independent' and not (OUT/'freeze.json').exists():raise ValueError('freeze before independent acquisition')
    metadata()
    tasks=[(window,p,tf,k) for p in pairs() for tf,k in [('15m','futures'),('1h','futures'),('1h','mark'),('1h','funding_rate')]]
    def job(t):
        try:fetch_one(*t)
        except Exception as e:write(OUT/'source-errors'/window/(slug(t[1])+'-'+t[2]+'-'+t[3]+'.json'),dict(at=now(),error=str(e)))
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(job,tasks))
    manifest=[read(p) for p in sorted((OUT/'sources'/window).glob('*.json'))]
    write(OUT/('data-'+window+'.json'),dict(files=manifest,source_snapshot_sha256=sha(DATA/'contract-source.json'),
        universe=pairs(),membership='CONDITIONAL_CURRENT_SURVIVORS; historical delistings unknown; causal 7day liquidity and 10day warmup',
        private_parent_archive='NOT_PROVIDED; no restore claimed; separate source reacquisition',
        evaluation='20260101-20260726' if window=='independent' else '20260805-20261103'))

if __name__=='__main__':acquire(sys.argv[1])
