"""Bounded public Gate acquisition; current-survivor frame is never PIT membership."""
import subprocess
import sys
import time
import pandas as pd
from session4_common import *


def acquire(reuse_registration=False):
    if not reuse_registration:register()
    ex=public(); markets=ex.load_markets(); tickers=ex.fetch_tickers(params={'type':'swap','settle':'usdt'})
    excluded={'USDC','USDE','USD1','DAI','TUSD','FDUSD','USDD','EUR','PAXG','XAUT'}
    rows=[]
    for symbol,m in markets.items():
        info=m.get('info',{});t=tickers.get(symbol,{})
        if not (m.get('linear') and m.get('swap') and m.get('active') and m.get('settle')=='USDT'
                and info.get('in_delisting') is False and info.get('is_pre_market') is False):continue
        if m.get('base') in excluded or info.get('contract_type')!='':continue
        volume=t.get('quoteVolume')
        if volume is None or float(volume)<=0:continue
        rows.append(dict(symbol=symbol,quote_volume=float(volume),timestamp=t.get('timestamp')))
    rows.sort(key=lambda r:(-r['quote_volume'],r['symbol']))
    parents=['BTC/USDT:USDT','ETH/USDT:USDT','SOL/USDT:USDT','XRP/USDT:USDT','DOGE/USDT:USDT']
    pairs=list(dict.fromkeys(parents+[r['symbol'] for r in rows]))[:20]
    write(OUT/'cohort.json',dict(pairs=pairs,observed_at=now(),ranking=rows,
        membership='CURRENT_SURVIVOR_FRAME_WITH_CAUSAL_HISTORICAL_LIQUIDITY_ELIGIBILITY',
        historical_delisted_contracts='UNAVAILABLE; complete historical universe NOT reconstructed'))
    contracts={};raw={}
    for symbol in pairs:
        m=markets[symbol];info=m['info']
        if m.get('taker') is None or m['taker']>.00075:raise ValueError('fee evidence missing '+symbol)
        tiers=[];error=None
        try:tiers=ex.fetch_market_leverage_tiers(symbol)
        except Exception as e:error=type(e).__name__+': '+str(e)[:160]
        raw[symbol]=dict(market=m,tiers=tiers,error=error,observed_at=now())
        contracts[symbol]=dict(verified=True,id=m['id'],contract_size=m['contractSize'],step_contracts=m['precision']['amount'],
            min_contracts=m['limits']['amount']['min'],max_contracts=m['limits']['amount'].get('max'),
            min_notional=m['limits']['cost'].get('min') or 0,taker=m['taker'],maker=m['maker'],
            price_precision=m['precision']['price'],funding_interval_seconds=int(info['funding_interval']),observed_at=now(),
            listing_time_source=info.get('create_time'),historical_tiers='UNKNOWN_CURRENT_SPEC_ONLY',
            tiers=[dict(min_notional=t['minNotional'],max_notional=t['maxNotional'],maintenance_rate=t['maintenanceMarginRate'],
                   max_leverage=t['maxLeverage'],maintenance_deduction=0) for t in tiers])
    write(OUT/'contracts.json',contracts);write(DATA.parent/'contract-source.json',raw)
    download()


def download():
    stage();cfg=config('PaperPolicyV4','download');path=STATE/'download.json';write(path,cfg)
    args=['freqtrade','download-data','--config',str(path),'--datadir',str(DATA),'--trading-mode','futures',
          '--timeframes','15m','1h','--timerange','20260726-20261103']
    logpath=OUT/'download.txt'
    if logpath.exists():logpath=OUT/f'download-retry-{len(list(OUT.glob("download*.txt"))):03}.txt'
    with logpath.open('x') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
    if r.returncode:raise ValueError('native download failed; inspect download.txt')
    validate()


def recohort():
    # Preserve the complete failed sampling frame and raw sources, before outcomes.
    old=OUT/'attempt-001-noncrypto-frame';old.mkdir()
    for name in ['cohort.json','contracts.json','download.txt','data-manifest.json']:
        p=OUT/name
        if p.exists():p.rename(old/name)
    if DATA.exists():DATA.rename(DATA.with_name('gate-attempt-001'))
    source=DATA.parent/'contract-source.json'
    if source.exists():source.rename(DATA.parent/'contract-source-attempt-001.json')
    amendment('Before outcome inspection: exclude Gate contract_type stocks/commodities/metals from crypto cohort. Initial broad sample and sources retained. Duplicate __init__ staging fix; no signal or numerical parameter tuning.')
    acquire(True)


def validate():
    files=[]
    contracts=read(OUT/'contracts.json')
    for p in sorted(DATA.rglob('*.feather')):
        f=pd.read_feather(p)
        f=f.loc[(f.date>=pd.Timestamp('2026-07-26',tz='UTC'))&(f.date<pd.Timestamp('2026-11-03',tz='UTC'))].reset_index(drop=True)
        f.to_feather(p)
        funding='-funding_rate' in p.name
        symbol=next(s for s in contracts if p.name.startswith(s.replace('/','_').replace(':','_')+'-'))
        step=contracts[symbol]['funding_interval_seconds'] if funding else 900 if '-15m-' in p.name else 3600 if '-1h-' in p.name else None
        intervals=f.date.diff().dropna().dt.total_seconds().value_counts().sort_index()
        files.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),rows=len(f),first=f.date.min().isoformat() if len(f) else None,
            last=f.date.max().isoformat() if len(f) else None,duplicates=int(f.date.duplicated().sum()),
            gaps=int((f.date.diff().iloc[1:]!=pd.Timedelta(seconds=step)).sum()) if step and not funding else None,
            observed_intervals_seconds={str(int(k)):int(v) for k,v in intervals.items()},
            funding_schedule_completeness='UNKNOWN_HISTORICAL_INTERVAL_CHANGES_POSSIBLE; actual returned events reconciled' if funding else None,
            nonfinite=int((~__import__('numpy').isfinite(f.select_dtypes('number'))).any(axis=1).sum()),
            missing_boundary=bool(len(f)==0 or f.date.min()>pd.Timestamp('2026-07-26',tz='UTC')),
            listing_availability='ACTUAL_SOURCE_FIRST_CANDLE_NOT_PROOF_OF_LISTING_DATE'))
    old=OUT/'data-manifest.json'
    if old.exists():old.rename(OUT/f'data-manifest-attempt-{len(list(OUT.glob("data-manifest*.json"))):03}.json')
    write(old,dict(at=now(),source='FREQTRADE_2026.10_CCXT_GATE_PUBLIC_REST',files=files,
         membership_uncertainty='Delisted historical contracts absent; listing availability bounded by returned coverage. Eligibility only after observed warmup.',
         complete_files=len(files),expected_files=80,original_sources_available=False))
    print('Downloaded',len(files),'files',sum(f['rows'] for f in files),'rows',flush=True)


def detail():
    cfg=config(label='detail-download');path=STATE/'detail-download.json';write(path,cfg)
    args=['freqtrade','download-data','--config',str(path),'--datadir',str(DATA),'--trading-mode','futures',
          '--timeframes','1m','--timerange','20261029-20261103']
    with (OUT/'detail-download.txt').open('x') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
    checks=[]
    for pair in cfg['exchange']['pair_whitelist']:
        p=DATA/'futures'/(pair.replace('/','_').replace(':','_')+'-1m-futures.feather')
        if not p.exists():checks.append(dict(pair=pair,complete=False));continue
        f=pd.read_feather(p);f=f.loc[(f.date>=pd.Timestamp('2026-10-29',tz='UTC'))&(f.date<pd.Timestamp('2026-11-03',tz='UTC'))].reset_index(drop=True);f.to_feather(p)
        checks.append(dict(pair=pair,rows=len(f),sha256=sha(p),complete=bool(len(f)==7200 and f.date.diff().iloc[1:].eq(pd.Timedelta(minutes=1)).all())))
    write(OUT/'detail-manifest.json',dict(returncode=r.returncode,checks=checks,complete=all(c['complete'] for c in checks)))


if __name__=='__main__':globals()[sys.argv[1]]()
