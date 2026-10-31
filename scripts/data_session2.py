"""Seal/validate a separate reacquisition without modifying Session 1 evidence."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import pandas as pd
from validate_data import inspect
ROOT=Path('/lab')
OUT=ROOT/'evidence/session-2'
MANIFEST=OUT/'source-data-manifest.json'


def verify():
    m=json.loads(MANIFEST.read_text())
    if not m['valid_for_backtest']:
        raise ValueError('invalid Session 2 sample')
    for r in m['files']:
        if hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()!=r['sha256']:
            raise ValueError('data changed: '+r['path'])
    return m


def seal():
    old=json.loads((ROOT/'evidence/session-1/market-data-manifest.json').read_text())
    contracts=json.loads((ROOT/'user_data/runtime/contracts.json').read_text())
    start=pd.Timestamp('2026-07-26',tz='UTC'); end=pd.Timestamp('2026-10-30',tz='UTC')
    rows=[]
    for original in old['files']:
        p=ROOT/original['path'].replace('data/research/','data/session-2/')
        if not p.exists():
            raise ValueError('missing native acquisition: '+str(p))
        df=pd.read_feather(p); before=hashlib.sha256(p.read_bytes()).hexdigest()
        dates=pd.to_datetime(df.date,utc=True)
        trimmed=df.loc[(dates>=start)&(dates<end)].reset_index(drop=True)
        if len(trimmed)!=len(df):
            trimmed.to_feather(p)
        interval=28800 if original['candle_type']=='funding_rate' else (900 if original['timeframe']=='15m' else 3600)
        r=inspect(trimmed,interval,start,end,pd.Timestamp.now(tz='UTC'),original['candle_type']=='funding_rate')
        if original['candle_type']=='funding_rate':
            if r.get('irregular_intervals') or trimmed.empty or trimmed.date.iloc[0]>start or trimmed.date.iloc[-1]+pd.Timedelta(seconds=interval)<end:
                r['errors'].append('FUNDING_COVERAGE_OR_SCHEDULE')
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        r.update(path=str(p.relative_to(ROOT)),symbol=original['symbol'],candle_type=original['candle_type'],timeframe=original['timeframe'],
            bytes=p.stat().st_size,sha256=sha,original_session1_sha256=original['sha256'],matches_session1=sha==original['sha256'],
            native_acquisition_sha256=before,native_rows=len(df),trimmed_rows=len(df)-len(trimmed),contract=contracts[original['symbol']])
        rows.append(r)
    m={'schema_version':1,'fidelity':'ACTUAL_PUBLIC_MARKET','source':'Gate public REST / Freqtrade 2026.10 / CCXT 4.5.90',
       'acquired_utc':datetime.now(timezone.utc).isoformat(),'download_timerange':'20260726-20261030','evaluation_timerange':'20260730-20261030',
       'pairs':old['protocol']['pairs'],'files':rows,'valid_for_backtest':all(not r['errors'] for r in rows),
       'identical_to_session1':all(r['matches_session1'] for r in rows),'source_rights':'evidence/session-1/source-rights.md',
       'redistribution':'Raw source files local only; derived metrics/trades may be committed.',
       'sample_class':'INSPECTED DEVELOPMENT DATA; no untouched holdout','total_bytes':sum(r['bytes'] for r in rows)}
    MANIFEST.write_text(json.dumps(m,indent=2)+'\n')
    print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
    if not m['valid_for_backtest']:
        raise ValueError('exact-window reacquisition invalid; preserve failed manifest and declare a new cohort before retry')

if __name__=='__main__':
    if '--verify' in sys.argv:
        verify(); print('Session 2 source hashes verified.')
    else:
        seal()
