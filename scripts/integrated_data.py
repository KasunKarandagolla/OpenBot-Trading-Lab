"""Bounded real Gate candles; no synthetic resampling into finer timeframes."""
from concurrent.futures import ThreadPoolExecutor
import os
import pandas as pd
import ccxt
from integrated_common import *

def client():
    cfg = dict(enableRateLimit=True, timeout=15000, requests_trust_env=True,
        has={'fetchCurrencies': False}, options={'defaultType': 'swap', 'fetchMarkets': {'types': ['swap']}})
    if os.environ.get('HTTPS_PROXY'): cfg['httpsProxy'] = os.environ['HTTPS_PROXY']
    if os.environ.get('SSL_CERT_FILE'): cfg['cafile'] = os.environ['SSL_CERT_FILE']
    return ccxt.gate(cfg)

def metadata():
    path = DATA/'contract-source.json'
    if path.exists(): return read(path)
    ex=client(); ex.load_markets(); rows={}
    for pair in pairs():
        m=ex.market(pair)
        if not (m['linear'] and m['swap'] and m['id']==pair.split('/')[0]+'_USDT'):
            raise ValueError('wrong market identity')
        rows[pair]=dict(market=m, tiers=ex.fetch_market_leverage_tiers(pair), observed_at=now())
    write(path, rows)
    write(OUT/'contracts.json', read(ROOT/'evidence/setup/run-003/contracts.json'))
    return rows

def fetch(pair, tf, kind, start):
    end=protocol()['end_exclusive']
    a=int(pd.Timestamp(start,tz='UTC').timestamp()*1000)
    b=int(pd.Timestamp(end,tz='UTC').timestamp()*1000)
    if b>int(pd.Timestamp('2026-11-03',tz='UTC').timestamp()*1000): raise ValueError('reserved/future dates forbidden')
    target=DATA/'gate/futures'/(slug(pair)+'-'+tf+'-'+kind+'.feather')
    receipt=OUT/'sources'/(target.stem+'.json')
    if target.exists():
        if not receipt.exists() or sha(target)!=read(receipt)['sha256']: raise ValueError('unsealed existing source')
        return read(receipt)
    ex=client(); ex.set_markets([r['market'] for r in metadata().values()])
    seconds=ex.parse_timeframe(tf)
    width=14*86400000 if kind=='funding_rate' else 1900*seconds*1000
    events=[]; requests=0
    for cursor in range(a,b,width):
        stop=min(cursor+width,b)
        if kind=='funding_rate':
            part=[[r['timestamp'],r['fundingRate'],0.,0.,0.,0.] for r in ex.fetch_funding_rate_history(pair,cursor,1000,{'until':stop-1})]
        else:
            part=ex.fetch_ohlcv(pair,tf,cursor,1900,dict(until=stop-1,**({'price':kind} if kind=='mark' else {})))
        requests+=1
        events.extend(r for r in part if cursor<=r[0]<stop)
    f=pd.DataFrame(events,columns=['date','open','high','low','close','volume'])
    if f.empty: raise ValueError('empty real source')
    f['date']=pd.to_datetime(f.date,unit='ms',utc=True).dt.as_unit('ns')
    f=f.sort_values('date').reset_index(drop=True)
    if f.date.duplicated().any(): raise ValueError('duplicate candles/events')
    for k in ['open','high','low','close','volume']: f[k]=f[k].astype(float)
    if kind=='futures': f['volume']*=float(metadata()[pair]['market']['contractSize'])
    if kind=='funding_rate': f=f[['date','open']].rename(columns={'open':'funding_rate'})
    gaps=int(f.date.diff().dropna().ne(pd.Timedelta(seconds=seconds)).sum()) if kind!='funding_rate' else None
    if kind!='funding_rate':
        expected=int((b-a)/(seconds*1000))
        if len(f)!=expected or gaps or f.date.iloc[0].value//1000000!=a or not f.date.dt.floor(tf.replace('m','min') if tf.endswith('m') else tf).equals(f.date):
            raise ValueError(f'incomplete or misaligned source: {len(f)} of {expected}, gaps {gaps}')
        if (f[['open','high','low','close']]<=0).any().any() or (f.volume<0).any(): raise ValueError('invalid price/volume')
        if ((f.low>f[['open','close']].min(axis=1))|(f.high<f[['open','close']].max(axis=1))|(f.low>f.high)).any(): raise ValueError('invalid OHLC')
    target.parent.mkdir(parents=True,exist_ok=True); f.to_feather(target)
    row=dict(path=str(target.relative_to(ROOT)),sha256=sha(target),pair=pair,timeframe=tf,kind=kind,rows=len(f),first=str(f.date.iloc[0]),last=str(f.date.iloc[-1]),gaps=gaps,
        source='GATE_PUBLIC_REST_CCXT_'+ccxt.__version__,venue='gate',market_id=pair.split('/')[0]+'_USDT',requested_start=start,end_exclusive=end,received_at=now(),requests=requests,
        volume_unit='BASE_ASSET_USING_CURRENT_CONTRACT_SIZE' if kind=='futures' else 'NOT_APPLICABLE',historical_contract_specs='UNKNOWN',spread='UNKNOWN',queue='UNKNOWN',flow='UNKNOWN')
    write(receipt,row); print(pair,tf,kind,len(f),flush=True)
    return row

def acquire():
    metadata()
    # One early 5m request probes rolling venue retention. Never replace failed data with generated bars.
    if not (OUT/'five-minute-probe.json').exists():
        ex=client(); ex.set_markets([r['market'] for r in metadata().values()])
        try:
            a=int(pd.Timestamp(protocol()['source_start'],tz='UTC').timestamp()*1000)
            sample=ex.fetch_ohlcv(pairs()[0],'5m',a,3,{'until':a+899999})
            write(OUT/'five-minute-probe.json',dict(at=now(),requested_start=protocol()['source_start'],returned=sample,status='AVAILABLE' if sample and sample[0][0]==a else 'INCOMPLETE'))
        except Exception as e:
            write(OUT/'five-minute-probe.json',dict(at=now(),requested_start=protocol()['source_start'],status='UNAVAILABLE',error=str(e)[:1000]))
    # Fixed fallback window chosen before new outcomes, leaving room within a 10,000-bar venue limit.
    five_start=protocol()['source_start'] if read(OUT/'five-minute-probe.json')['status']=='AVAILABLE' else '2026-10-05'
    jobs=[(p,tf,k,protocol()['source_start']) for p in pairs() for tf,k in [('15m','futures'),('1h','futures'),('1h','mark'),('1h','funding_rate')]]
    jobs += [(p,'5m','futures',five_start) for p in pairs()]
    def job(args):
        try: return fetch(*args)
        except Exception as e:
            name=slug(args[0])+'-'+args[1]+'-'+args[2]
            write(OUT/'source-errors'/(name+'.json'),dict(at=now(),args=args,error=str(e)[:1500]))
            print('UNAVAILABLE',name,str(e)[:250],flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(job,jobs))
    rows=[read(p) for p in sorted((OUT/'sources').glob('*.json'))]
    old={Path(x['path']).name:x['sha256'] for x in read(ROOT/'evidence/setup/run-003/data-development.json')['files']}
    for r in rows:
        r['prior_sealed_sha256']=old.get(Path(r['path']).name)
        r['byte_equal_to_sealed']=r['sha256']==r['prior_sealed_sha256']
    write(OUT/'data.json',dict(files=rows,metadata_sha256=sha(DATA/'contract-source.json'),
        private_archive='NOT_PROVIDED;NO_RESTORE_CLAIM',five_minute_start=five_start,
        prior_source_match=sum(r['byte_equal_to_sealed'] for r in rows),prior_source_files=len(old),
        cohort='CURRENT_SURVIVORS;HISTORICAL_MEMBERSHIP_UNKNOWN;NEWLY_ACQUIRED_SOURCES'))

if __name__=='__main__': acquire()
