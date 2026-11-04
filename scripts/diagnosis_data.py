"""Bounded distinct-window Gate source acquisition with immutable receipts."""
from concurrent.futures import ThreadPoolExecutor
import shutil
import pandas as pd
from diagnosis_common import *
from integrated_data import client

VDATA=ROOT/'user_data/data/diagnosis'

def acquire_one(cohort,pair,tf,kind):
    spec=read(ROOT/'research/diagnosis/protocol.json')['source_windows'][cohort]
    start,end=spec[0],spec[2]
    a=int(pd.Timestamp(start,tz='UTC').timestamp()*1000);b=int(pd.Timestamp(end,tz='UTC').timestamp()*1000)
    if not a<b<=int(pd.Timestamp('2026-11-04',tz='UTC').timestamp()*1000):raise ValueError('unregistered or future data window')
    target=VDATA/cohort/'gate/futures'/(slug(pair)+'-'+tf+'-'+kind+'.feather');receipt=OUT/'sources'/cohort/(target.stem+'.json')
    if target.exists():
        if not receipt.exists() or sha(target)!=read(receipt)['sha256']:raise ValueError('unsealed existing source')
        return
    metadata=read(DATA/'contract-source.json');ex=client();ex.set_markets([x['market'] for x in metadata.values()])
    interval=ex.parse_timeframe(tf);width=14*86400000 if kind=='funding_rate' else 1900*interval*1000;rows=[];calls=0
    for cursor in range(a,b,width):
        stop=min(cursor+width,b)
        if kind=='funding_rate':part=[[x['timestamp'],x['fundingRate'],0.,0.,0.,0.] for x in ex.fetch_funding_rate_history(pair,cursor,1000,{'until':stop-1})]
        else:part=ex.fetch_ohlcv(pair,tf,cursor,1900,dict(until=stop-1,**({'price':kind} if kind=='mark' else {})))
        rows.extend(x for x in part if cursor<=x[0]<stop);calls+=1
    f=pd.DataFrame(rows,columns=['date','open','high','low','close','volume'])
    if f.empty:raise ValueError('empty real source')
    f['date']=pd.to_datetime(f.date,unit='ms',utc=True).dt.as_unit('ns');f=f.sort_values('date').reset_index(drop=True)
    if f.date.duplicated().any():raise ValueError('duplicate source event')
    for k in ('open','high','low','close','volume'):f[k]=f[k].astype(float)
    gaps=None
    if kind=='funding_rate':f=f[['date','open']].rename(columns={'open':'funding_rate'})
    else:
        expected=int((b-a)/(interval*1000));gaps=int(f.date.diff().dropna().ne(pd.Timedelta(seconds=interval)).sum())
        if len(f)!=expected or gaps or f.date.iloc[0]!=pd.Timestamp(start,tz='UTC') or f.date.iloc[-1]+pd.Timedelta(seconds=interval)!=pd.Timestamp(end,tz='UTC'):raise ValueError(f'incomplete source {len(f)} expected{expected}, gaps{gaps}')
        if not f.date.dt.floor('15min' if tf=='15m' else 'h').equals(f.date):raise ValueError('clock alignment')
        if not ((f.low>0)&(f.high>=f[['open','close']].max(axis=1))&(f.low<=f[['open','close']].min(axis=1))&(f.volume>=0)).all():raise ValueError('invalid OHLCV')
        if kind=='futures':f['volume']*=metadata[pair]['market']['contractSize']
    target.parent.mkdir(parents=True,exist_ok=True);f.to_feather(target)
    write(receipt,dict(path=str(target.relative_to(ROOT)),sha256=sha(target),cohort=cohort,pair=pair,timeframe=tf,kind=kind,rows=len(f),gaps=gaps,
        source='PUBLIC_GATE_REST_CCXT_'+__import__('ccxt').__version__,source_start=start,end_exclusive=end,received_at=now(),requests=calls,
        first=f.date.iloc[0].isoformat(),last=f.date.iloc[-1].isoformat(),market_id=metadata[pair]['market']['id'],
        volume='BASE_ASSET_CONVERTED_WITH_CURRENT_CONTRACT_SIZE',historical_metadata='UNKNOWN_CURRENT_SNAPSHOT_ONLY',signed_flow='UNKNOWN',spread='UNKNOWN'))
    print(cohort,pair,tf,kind,len(f),flush=True)

def run():
    registration=read(OUT/'preregistration.json')
    if sha(ROOT/'research/diagnosis/protocol.json')!=registration['sha256']:raise ValueError('freeze protocol before validation prices')
    probe=OUT/'older-data-probe.json'
    if not probe.exists():
        ex=client();ex.set_markets([x['market'] for x in read(DATA/'contract-source.json').values()])
        at=int(pd.Timestamp('2026-06-01',tz='UTC').timestamp()*1000)
        try:
            rows=ex.fetch_ohlcv(pairs()[0],'15m',at,3,{'until':at+2699999})
            write(probe,dict(at=now(),start='2026-06-01',timeframe='15m',status='AVAILABLE' if rows and rows[0][0]==at else 'INCOMPLETE',rows=rows))
        except Exception as e:write(probe,dict(at=now(),start='2026-06-01',timeframe='15m',status='UNAVAILABLE',error=str(e)[:1000]))
    jobs=[(c,p,tf,k) for c in ('earlier','later') for p in pairs() for tf,k in [('15m','futures'),('1h','futures'),('1h','mark'),('1h','funding_rate')]]
    def job(args):
        try:acquire_one(*args)
        except Exception as e:
            write(OUT/'source-errors'/args[0]/(slug(args[1])+'-'+args[2]+'-'+args[3]+'.json'),dict(args=args,at=now(),error=str(e)[:1000]))
            print('UNAVAILABLE',args,str(e)[:200],flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(job,jobs))
    manifest={}
    for cohort in ('earlier','later'):
        rows=[read(p) for p in sorted((OUT/'sources'/cohort).glob('*.json'))]
        meta=VDATA/cohort/'contract-source.json';meta.parent.mkdir(parents=True,exist_ok=True)
        if not meta.exists():shutil.copyfile(DATA/'contract-source.json',meta)
        manifest[cohort]=dict(files=rows,complete=len(rows)==56,metadata_sha256=sha(meta),source_window=read(ROOT/'research/diagnosis/protocol.json')['source_windows'][cohort],
            classification='DISTINCT_EARLIER_PERIOD_PREVIOUSLY_INSPECTED_BY_BROADER_PROJECT_NOT_INDEPENDENT' if cohort=='earlier' else 'NEW_FROZEN_ONE_DAY_EXTENSION_TOO_SMALL_FOR_RELIABILITY')
    write(OUT/'data-validation.json',manifest)

if __name__=='__main__':run()
