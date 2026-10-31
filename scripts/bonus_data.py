"""Reuse native acquisition and validator; never write previous session evidence."""
import subprocess
import sys
import pandas as pd
from bonus_common import *
from validate_data import inspect


def verify():
    m = read(OUT/'source-manifest.json')
    if not m['valid'] or m['protocol_sha256'] != sha(PROTOCOL):
        raise ValueError('invalid bonus source identity')
    for r in m['files']:
        if sha(ROOT/r['path']) != r['sha256']:
            raise ValueError('source changed: '+r['path'])
    return m


def acquire():
    check()
    if (OUT/'source-manifest.json').exists():
        return verify()
    from public_exchange import public_exchange
    e = public_exchange(); markets = e.load_markets()
    contracts = {}
    for symbol in spec()['pairs']:
        m = markets[symbol]; i = m['info']
        if not (m['active'] and m['swap'] and m['linear'] and m['quote']=='USDT'
                and m['settle']=='USDT' and i.get('contract_type')==''
                and i.get('in_delisting') is False and i.get('is_pre_market') is False
                and i.get('launch_time') and i.get('funding_interval')==28800):
            raise ValueError('ineligible or unsupported funding schedule: '+symbol)
        contracts[symbol] = {k:m[k] for k in ('id','symbol','contractSize','linear','swap','settle')}
        contracts[symbol].update(launch_time=i['launch_time'],funding_interval=28800,
                                limits=m['limits'],precision=m['precision'])
    p = OUT/'acquisition-output.txt'
    with p.open('x') as f:
        r = subprocess.run([sys.executable,str(ROOT/'scripts/bonus_common.py'),
                            'download-data','VWAPTrendContinuationV1'],
                           env=sanitized_env(),stdout=f,stderr=subprocess.STDOUT)
    if r.returncode: raise ValueError('native acquisition failed; retain log')
    start,end = [pd.to_datetime(x,format='%Y%m%d',utc=True) for x in spec()['download_timerange'].split('-')]
    files=[]
    for s in spec()['pairs']:
        for tf,kind,seconds in [('15m','futures',900),('1h','futures',3600),
                                ('1h','mark',3600),('1h','funding_rate',28800)]:
            p = DATA/'futures'/(s.replace('/','_').replace(':','_')+'-'+tf+'-'+kind+'.feather')
            d = pd.read_feather(p)
            d = d.loc[(d.date>=start)&(d.date<end)].reset_index(drop=True)
            d.to_feather(p)
            report = inspect(d,seconds,start,end,pd.Timestamp.now(tz='UTC'),kind=='funding_rate')
            if kind=='funding_rate' and (d.empty or d.date.iloc[0]>start or d.date.iloc[-1]+pd.Timedelta(seconds=seconds)<end):
                report['errors'].append('FUNDING_COVERAGE')
            files.append(report|{'path':str(p.relative_to(ROOT)),'symbol':s,'timeframe':tf,
                                 'candle_type':kind,'sha256':sha(p),'bytes':p.stat().st_size})
    obj={'valid':all(not r['errors'] for r in files),'files':files,'contracts':contracts,
         'protocol_sha256':sha(PROTOCOL),'received_utc':pd.Timestamp.now(tz='UTC').isoformat(),
         'source':'native Freqtrade2026.10 / CCXT4.5.90 Gate public REST',
         'fidelity':'ACTUAL_PUBLIC_OHLCV_MARK_AND_FUNDING','raw_redistribution':False,
         'membership_limitation':spec()['membership']}
    write(OUT/'source-manifest.json',obj)
    if not obj['valid']: raise ValueError('data validation failed')
    return obj


def frame(symbol,tf='15m',kind='futures'):
    return pd.read_feather(DATA/'futures'/(symbol.replace('/','_').replace(':','_')+'-'+tf+'-'+kind+'.feather'))


def restore_prior_raw():
    """Only restore absent raw files whose bytes match recorded prior manifests."""
    import shutil
    m=verify();lookup={(r['symbol'],r['timeframe'],r['candle_type']):r for r in m['files']};rows=[]
    for path in ['evidence/session-1/market-data-manifest.json','evidence/session-2/source-data-manifest.json',
                 'evidence/session-3/cohorts/s3-development-v1/source-data-manifest.json',
                 'evidence/session-3/cohorts/s3-transfer-v1/source-data-manifest.json']:
        for old in read(ROOT/path).get('files',[]):
            r=lookup.get((old.get('symbol'),old.get('timeframe'),old.get('candle_type')))
            if r and old.get('sha256')==r['sha256']:
                p=ROOT/old['path']
                if p.exists() and sha(p)!=old['sha256']:raise ValueError('refuse to overwrite prior raw file')
                if not p.exists():p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/r['path'],p)
                rows.append({'path':old['path'],'matches':True})
    write(OUT/'prior-raw-restoration.json',rows)
    return rows


def detail():
    """Public 5m candles on predeclared October window, no new simulator."""
    from public_exchange import public_exchange
    e=public_exchange(); rows=[]
    for s in spec()['pairs']:
        p=DATA/'futures'/(s.replace('/','_').replace(':','_')+'-5m-futures.feather')
        if p.exists(): raise ValueError('detail exists; preserve')
        start=pd.Timestamp('2026-10-01',tz='UTC');end=pd.Timestamp('2026-10-30',tz='UTC')
        cursor=int(start.timestamp()*1000); last=int(end.timestamp()*1000); values=[]
        for _ in range(10):
            if cursor>=last:break
            page=e.fetch_ohlcv(s,'5m',since=cursor,limit=1000)
            selected=[r for r in page if cursor<=r[0]<last]
            if not selected or selected[0][0]!=cursor:raise ValueError('detail coverage gap')
            values.extend(selected);cursor=selected[-1][0]+300000
        if cursor!=last:raise ValueError('bounded detail pagination exhausted')
        d=pd.DataFrame(values,columns=['date','open','high','low','close','volume'])
        d['date']=pd.to_datetime(d.date,unit='ms',utc=True)
        report=inspect(d,300,start,end,pd.Timestamp.now(tz='UTC'))
        if report['errors']:raise ValueError('detail invalid')
        d.to_feather(p);rows.append(report|{'symbol':s,'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
    write(OUT/'detail-manifest.json',{'files':rows,'valid':True})


def risk_examples():
    """Current public margin tiers on a historical plan; illustrative, not backdated."""
    from public_exchange import public_exchange
    sys.path.insert(0,str(ROOT/'research/bonus'))
    from futures_risk import evaluate
    plans=read(OUT/'trade-plans.json')
    p=next(p for p in plans if p['variant']=='RouterOnlyV1');symbol=p['symbol'];g=p['plan']
    e=public_exchange();m=e.load_markets()[symbol]
    native=e.fetch_market_leverage_tiers(symbol)
    tiers=[{'min_notional':t['minNotional'],'max_notional':t['maxNotional'],
            'max_leverage':t['maxLeverage'],'maintenance_rate':t['maintenanceMarginRate'],
            'maintenance_deduction':float(t.get('info',{}).get('deduction',0))} for t in native]
    base=dict(price=g['reference'],equity=1000.,day_start_equity=1000.,available_margin=100.,
              unrealized_pnl=0.,contract_size=m['contractSize'],min_contracts=1.,step_contracts=1.,tiers=tiers)
    cases=[]
    for side in ('long','short'):
        stop=g['reference']*(1-g['risk_fraction'] if side=='long' else 1+g['risk_fraction'])
        for lev in (1,10,20):cases.append(evaluate(**base,side=side,stop=stop,leverage=lev))
    for label,update in [('unrealized_daily_halt',{'unrealized_pnl':-11.}),('pending_exposure',{'pending_risk':6.}),
                         ('correlated_exposure',{'correlated_notional':500.}),('tier_unknown',{'tiers':None})]:
        r=evaluate(**(base|update),side='long',stop=g['stop'],leverage=20)
        cases.append({'case':label,**r})
    write(OUT/'risk-scenarios.json',{'symbol':symbol,'historical_plan_id':p['decision_id'],
                                   'tier_observed_at':pd.Timestamp.now(tz='UTC').isoformat(),
                                   'current_public_tiers':native,'cases':cases,'owner_approved':False,
                                   'limitation':'Current tier snapshot, not historical-tier reconstruction; no credentials, orders or leveraged activation'})
    print(json.dumps(cases,indent=2))
