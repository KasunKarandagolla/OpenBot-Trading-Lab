"""Validate actual native files before Freqtrade can fill any missing bars on load."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path('/lab')


def inspect(df, interval_seconds, start, end, now, funding=False):
    errors=[]
    required={'date','funding_rate'} if funding else {'date','open','high','low','close','volume'}
    if not required.issubset(df.columns): return {'rows':len(df),'errors':['SCHEMA_MISMATCH']}
    if df.empty: return {'rows':0,'errors':['EMPTY']}
    df=df.reset_index(drop=True)
    if not isinstance(df['date'].dtype,pd.DatetimeTZDtype) or str(df['date'].dt.tz) != 'UTC':
        errors.append('SOURCE_TIMEZONE_NOT_UTC')
    dates=pd.to_datetime(df['date'],utc=True,errors='coerce').dt.as_unit('ns')
    if dates.isna().any(): return {'rows':len(df),'errors':errors+['INVALID_TIMESTAMP']}
    if dates.duplicated().any(): errors.append('DUPLICATE_TIMESTAMP')
    if not dates.is_monotonic_increasing: errors.append('UNORDERED_TIMESTAMP')
    if dates.isna().any(): errors.append('INVALID_TIMESTAMP')
    if ((dates.astype('int64')//10**9) % interval_seconds != 0).any(): errors.append('MISALIGNED_TIMESTAMP')
    # Funding may use event intervals that change over history. Report all gaps explicitly.
    gaps=dates.diff().dt.total_seconds().dropna()
    gap_rows=[{'after_utc':dates.iloc[i-1].isoformat(),'before_utc':dates.iloc[i].isoformat(),
               'seconds':float(gaps.loc[i])} for i in gaps.index if gaps.loc[i] != interval_seconds]
    if gap_rows and not funding: errors.append('MISSING_OR_IRREGULAR_BARS')
    if funding:
        if not np.isfinite(df['funding_rate'].to_numpy(dtype=float)).all(): errors.append('NONFINITE_FUNDING_RATE')
        return {'rows':len(df),'start_utc':dates.iloc[0].isoformat(),'last_open_utc':dates.iloc[-1].isoformat(),
                'irregular_intervals':gap_rows,'errors':errors,'rate_min':float(df.funding_rate.min()),'rate_max':float(df.funding_rate.max())}
    vals=df[['open','high','low','close','volume']].to_numpy(dtype=float)
    if not np.isfinite(vals).all(): errors.append('NONFINITE_OHLCV')
    if not funding:
        if (vals[:,:4] <= 0).any(): errors.append('NONPOSITIVE_PRICE')
        if (vals[:,4] < 0).any(): errors.append('NEGATIVE_VOLUME')
        if ((df['high'] < df[['open','close','low']].max(axis=1)) | (df['low'] > df[['open','close','high']].min(axis=1))).any(): errors.append('INVALID_OHLC_RANGE')
        if dates.iloc[0] > start: errors.append('MISSING_START_OR_WARMUP')
        if dates.iloc[-1]+pd.Timedelta(seconds=interval_seconds) < end: errors.append('MISSING_END')
        if (dates+pd.Timedelta(seconds=interval_seconds) > now).any(): errors.append('INCOMPLETE_CANDLE')
    return {'rows':len(df),'start_utc':dates.iloc[0].isoformat(),'last_open_utc':dates.iloc[-1].isoformat(),
            'zero_volume_rows':int((df['volume']==0).sum()),'irregular_intervals':gap_rows,'errors':errors}


def main(verify=False):
    protocol=json.loads((ROOT/'research/protocol.json').read_text())
    manifest_path=ROOT/'evidence/session-1/market-data-manifest.json'
    if verify:
        m=json.loads(manifest_path.read_text())
        if not m['valid_for_backtest']: raise ValueError('dataset validation failed')
        for row in m['files']:
            if hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()!=row['sha256']:
                raise ValueError('immutable research file changed: '+row['path'])
        print('Research sample hashes verified.'); return
    # Read actual public instrument metadata saved at acquisition; never infer spot/futures from name alone.
    contracts=json.loads((ROOT/'user_data/runtime/contracts.json').read_text())
    files=[]
    start=pd.Timestamp('2026-07-26',tz='UTC'); end=pd.Timestamp('2026-10-30',tz='UTC')
    now=pd.Timestamp.now(tz='UTC')
    for path in sorted((ROOT/'user_data/data/research/gate').rglob('*.feather')):
        stem=path.stem; symbol=next((s for s in protocol['pairs'] if stem.startswith(s.replace('/','_').replace(':','_')+'-')),None)
        if not symbol: raise ValueError('unexpected dataset contract '+stem)
        rest=stem.split('-',1)[1]; tf,ctype=rest.split('-',1)
        seconds=int(tf[:-1])*{'m':60,'h':3600,'d':86400}[tf[-1]]
        df=pd.read_feather(path)
        expected_interval=contracts[symbol].get('funding_interval_seconds',28800) if ctype=='funding_rate' else seconds
        row=inspect(df,expected_interval,start,end,now,ctype=='funding_rate')
        if ctype=='funding_rate':
            row['observed_schedule_reference_seconds']=expected_interval
            if row['irregular_intervals']: row['errors'].append('FUNDING_EVENT_GAPS_OR_SCHEDULE_CHANGES')
            if pd.to_datetime(df.date,utc=True).iloc[0] > start or pd.to_datetime(df.date,utc=True).iloc[-1]+pd.Timedelta(seconds=expected_interval) < end:
                row['errors'].append('FUNDING_BOUNDARY_COVERAGE_MISSING')
        row.update(path=str(path.relative_to(ROOT)),symbol=symbol,candle_type=ctype,timeframe=tf,
                   sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,
                   source='ACTUAL Gate public REST via official Freqtrade/CCXT',contract=contracts[symbol])
        files.append(row)
    required={(s,t,'futures') for s in protocol['pairs'] for t in protocol['timeframes']}
    required|={(s,'1h',ctype) for s in protocol['pairs'] for ctype in ['mark','funding_rate']}
    found={(r['symbol'],r['timeframe'],r['candle_type']) for r in files if not r['errors']}
    missing=sorted(required-found)
    valid=bool(files) and not missing and not any(r['errors'] for r in files)
    funding={s:{'funding_files':[r['path'] for r in files if r['symbol']==s and r['candle_type']=='funding_rate'],
                'mark_files':[r['path'] for r in files if r['symbol']==s and r['candle_type']=='mark']} for s in protocol['pairs']}
    manifest={'schema':'dataset-v1','fidelity':'ACTUAL_PUBLIC_MARKET','exchange':'gate','settlement':'linear USDT perpetual',
      'download_completed_utc':datetime.now(timezone.utc).isoformat(),'engine':'2026.10','ccxt':'4.5.90',
      'acquisition_command':'./scripts/lab.sh download','protocol':protocol,'files':files,
      'missing_required':missing,'valid_for_backtest':valid,'total_bytes':sum(r['bytes'] for r in files),
      'funding_and_mark':funding,'source_rights':'evidence/session-1/source-rights.md',
      'warmup':'200x15m bars; July 26–29 reserved outside July 30 evaluation start.',
      'funding_limitations':'Event interval irregularities are reported, not interpolated; compare actual events against venue schedule before claiming full economics.',
      'raw_data_redistribution':'PROHIBITED by project policy; local files excluded from Git'}
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'{len(files)} real data files, {manifest["total_bytes"]} bytes, valid_for_backtest={valid}')
    for r in files: print(r['path'],r['rows'],r['start_utc'],r['last_open_utc'],r['errors'])
    if not valid: raise ValueError('dataset fails validation; see manifest')

if __name__=='__main__': main('--verify' in sys.argv)
