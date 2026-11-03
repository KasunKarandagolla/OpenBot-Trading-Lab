"""Native public source acquisition and existing broad scan, immutable v3 paths."""
import subprocess
import sys
import time
import math
from pathlib import Path
import pandas as pd
from policy_common import *


def acquire(run_id):
    from validate_data import inspect
    out,data,spec=verify(run_id)
    if (out/'data-manifest.json').exists(): raise ValueError('preserve source acquisition')
    ex=public();markets=ex.load_markets();contracts={};raw={}
    for symbol in spec['pairs']:
        m=markets[symbol];info=m['info']
        if not(m.get('linear') and m.get('swap') and m.get('active') and m.get('settle')=='USDT' and info.get('in_delisting') is False and info.get('is_pre_market') is False):raise ValueError('ineligible '+symbol)
        if m.get('taker') is None or m['taker']>spec['fee_per_side']:raise ValueError('cost evidence missing')
        try: tiers=ex.fetch_market_leverage_tiers(symbol)
        except Exception as error: tiers=[];raw[symbol]=dict(tier_error=str(error)[:300])
        normalized=[]
        for t in tiers:
            # Gate public tiers have no deduction in the documented venue
            # liquidation equation; retain raw fields for independent review.
            normalized.append(dict(min_notional=float(t['minNotional']),max_notional=float(t['maxNotional']),
                maintenance_rate=float(t['maintenanceMarginRate']),max_leverage=float(t['maxLeverage']),maintenance_deduction=0,
                source='CURRENT_PUBLIC_GATE_RISK_LIMIT_TIER'))
        raw[symbol]=dict(market={k:m.get(k) for k in ['id','symbol','contractSize','precision','limits','taker','maker','info']},tiers=tiers,observed_at=now())
        contracts[symbol]=dict(verified=True,id=m['id'],contract_size=m['contractSize'],step_contracts=m['precision']['amount'],
            min_contracts=m['limits']['amount']['min'],max_contracts=m['limits']['amount'].get('max'),min_notional=m['limits']['cost'].get('min') or 0,
            taker=m['taker'],tiers=normalized,observed_at=now(),historical_tiers='UNKNOWN_CURRENT_SPEC_SCENARIO_ONLY',funding_interval_seconds=int(info['funding_interval']))
    write(out/'contracts.json',contracts);write(data.parent/'contract-source.json',raw)
    cfg=config(run_id,'TrendPullbackBaselineV1');started=now()
    args=['freqtrade','download-data','--config',str(cfg),'--datadir',str(data),'--trading-mode','futures','--timeframes','15m','1h','--timerange',spec['download_timerange']]
    with (out/'native-download.txt').open('x') as log:
        r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
    if r.returncode:raise ValueError('native download failed; retained log')
    start,end=[pd.to_datetime(s,format='%Y%m%d',utc=True) for s in spec['download_timerange'].split('-')]
    files=[];checks=[]
    for p in sorted(data.rglob('*.feather')):
        f=pd.read_feather(p);f=f.loc[(f.date>=start)&(f.date<end)].reset_index(drop=True)
        f.to_feather(p)
        symbol=next(s for s in spec['pairs'] if p.name.startswith(s.replace('/','_').replace(':','_')+'-'))
        tf,kind=p.stem.split('-',1)[1].split('-',1)
        interval=contracts[symbol]['funding_interval_seconds'] if kind=='funding_rate' else 900 if tf=='15m' else 3600
        check=inspect(f,interval,start,end,pd.Timestamp.now(tz='UTC'),kind=='funding_rate')
        if kind=='funding_rate' and (f.empty or f.date.iloc[0]>start or f.date.iloc[-1]+pd.Timedelta(seconds=interval)<end):check['errors'].append('FUNDING_BOUNDARY_MISSING')
        files.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),rows=len(f),first=f.date.iloc[0].isoformat() if len(f) else None,last=f.date.iloc[-1].isoformat() if len(f) else None))
        checks.append(dict(file=p.name,**check))
    write(out/'data-manifest.json',dict(venue='gate',source='Native Freqtrade CCXT public REST REACQUIRED_NO_BACKUP_AVAILABLE',started_at=started,completed_at=now(),timerange=spec['download_timerange'],files=files,raw_redistribution=False))
    write(out/'data-validation.json',dict(valid=len(files)==20 and not any(c['errors'] for c in checks),checks=checks))
    if len(files)!=20 or any(c['errors'] for c in checks):raise ValueError('incomplete sources; see validation, do not fabricate missing data')
    compare_sources(run_id)
    print('Acquired and validated',len(files),'files',flush=True)


def compare_sources(run_id):
    out,data,spec=verify(run_id)
    # Old sources cannot be replaced: compare reconstructed October slices in a
    # scratch directory, preserve both full new source and original manifest.
    old=read(ROOT/'evidence/additional-2/intelligence-003/data-manifest.json');comparison=[]
    for item in old['files']:
        p=data/'futures'/Path(item['path']).name;f=pd.read_feather(p)
        crop=f.loc[(f.date>=pd.Timestamp('2026-09-21',tz='UTC'))&(f.date<pd.Timestamp('2026-11-01',tz='UTC'))].reset_index(drop=True)
        target=ROOT/'work/policy-source-comparison'/run_id/p.name;target.parent.mkdir(parents=True,exist_ok=True);crop.to_feather(target)
        comparison.append(dict(file=p.name,old_sha256=item['sha256'],reacquired_slice_sha256=sha(target),identical=sha(target)==item['sha256']))
    write(out/'parent-source-comparison.json',dict(backup_available=False,original_sources_overwritten=False,comparisons=comparison,
        interpretation='Byte identity if matching; changed files are explicitly reacquired and cannot claim exact old-source replay'))


def detail(run_id):
    out,data,spec=verify(run_id)
    cfg=config(run_id,'PolicyManagedV3')
    target=data.parent/'detail-attempt-002';args=['freqtrade','download-data','--config',str(cfg),'--datadir',str(target),'--trading-mode','futures','--timeframes','1m','--timerange','20261028-20261102']
    with (out/'native-detail-download.txt').open('x') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
    start=pd.Timestamp('2026-10-28',tz='UTC');end=pd.Timestamp('2026-11-02',tz='UTC');checks=[]
    for symbol in spec['pairs']:
        name=symbol.replace('/','_').replace(':','_')+'-1m-futures.feather';p=target/'futures'/name
        if not p.exists():checks.append(dict(symbol=symbol,valid=False,reason='NO_FILE'));continue
        f=pd.read_feather(p);f=f.loc[(f.date>=start)&(f.date<end)].reset_index(drop=True);f.to_feather(p)
        valid=len(f)==7200 and f.date.iloc[0]==start and f.date.iloc[-1]==end-pd.Timedelta(minutes=1) and f.date.diff().iloc[1:].eq(pd.Timedelta(minutes=1)).all()
        checks.append(dict(symbol=symbol,valid=bool(valid),rows=len(f),path=str(p.relative_to(ROOT)),sha256=sha(p)))
        if valid:
            destination=data/'futures'/name
            if destination.exists():raise ValueError('detail destination exists')
            shutil.copyfile(p,destination)
    write(out/'detail-manifest.json',dict(native_exit=r.returncode,timerange='20261028-20261102',checks=checks,all_valid=all(c['valid'] for c in checks),queue_priority='UNKNOWN'))
    print('Detail acquisition',checks,flush=True)


def scan(run_id):
    from scan_export import shortlist
    out,data,spec=verify(run_id);cfg_path=config(run_id,'TrendPullbackBaselineV1');cfg=read(cfg_path)
    cfg['pairlists']=read(ROOT/'configs/scanner.json')['pairlists'];cfg['exchange']['pair_whitelist']=[]
    target=cfg_path.with_name('scanner.json');write(target,cfg)
    with (out/'native-pairlist.txt').open('x') as log:
        r=subprocess.run(['freqtrade','test-pairlist','--config',str(target),'--print-json'],stdout=log,stderr=subprocess.STDOUT)
    if r.returncode:raise ValueError('native scan failed')
    native=None
    for line in (out/'native-pairlist.txt').read_text().splitlines():
        try:
            v=__import__('json').loads(line)
            if isinstance(v,list) and all(isinstance(s,str) for s in v):native=set(v)
        except ValueError:pass
    if native is None:raise ValueError('native pairlist missing')
    ex=public();markets=ex.load_markets();tickers=ex.fetch_tickers(params={'type':'swap','settle':'usdt'});rules=read(ROOT/'configs/scan-rules.json')
    count,rows,rejected,capped=shortlist(markets,tickers,rules,time.time()*1000,native)
    _,_,all_rejected,_=shortlist(markets,tickers,rules,time.time()*1000)
    write(data.parent/'scan-source.json',dict(observed_at=now(),tickers=tickers,markets={s:dict(id=m['id'],info=m['info']) for s,m in markets.items() if m.get('swap')}))
    write(out/'scan.json',dict(venue='gate',observed_at=now(),eligible_universe_count=count,native_pairlist_count=len(native),
        shortlisted=rows,rejected=all_rejected,valid_below_cap=capped,membership='CURRENT_SNAPSHOT_ONLY',historical_membership='UNKNOWN',orders_created=False))
    print('Scan',count,'eligible',len(native),'native',len(rows),'shortlist',flush=True)
