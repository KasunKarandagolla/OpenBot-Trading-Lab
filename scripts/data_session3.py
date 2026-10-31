"""Bounded native download, strict validation and immutable cohort manifests."""
import sys,subprocess
from datetime import datetime,timezone
import pandas as pd
from session3_common import *
from validate_data import inspect

def verify(cid):
 c=cohort(cid);p=destination(cid)/'source-data-manifest.json';m=read(p)
 if m['cohort']!=c or not m['valid_for_backtest']:raise ValueError('invalid cohort/source identity')
 if len(m['files'])!=len(c['pairs'])*4:raise ValueError('missing source series')
 for r in m['files']:
  if sha(ROOT/r['path'])!=r['sha256']:raise ValueError('immutable source changed: '+r['path'])
 return m

def acquire(cid):
 frozen();c=cohort(cid);out=destination(cid);folder=datadir(cid)/'futures'
 if pd.to_datetime(c['download_timerange'].split('-')[1],format='%Y%m%d',utc=True)>pd.Timestamp.now(tz='UTC'):raise ValueError('cohort end has not occurred; future data cannot be acquired')
 if folder.exists() and any(folder.glob('*.feather')):raise ValueError('data exist; preserving; validate recorded manifest instead')
 from public_exchange import public_exchange
 e=public_exchange();markets=e.load_markets();contracts={}
 for s in c['pairs']:
  m=markets[s];info=m['info']
  if not (m['active'] and m['swap'] and m['linear'] and m['quote']=='USDT' and m['settle']=='USDT' and info.get('in_delisting') is False and info.get('contract_type')==''):raise ValueError('invalid contract '+s)
  if info.get('funding_interval')!=c['funding_interval_seconds']:raise ValueError('unregistered funding schedule')
  contracts[s]={k:m.get(k) for k in ['id','symbol','active','swap','linear','settle','quote','contractSize']}
  contracts[s].update(funding_interval_seconds=info['funding_interval'],launch_time=info.get('launch_time'))
 args=[sys.executable,str(ROOT/'scripts/engine3.py'),'download-data',cid,NAMES[0]]
 out.mkdir(parents=True,exist_ok=True)
 log=out/'acquisition-output.txt'
 if log.exists():log=out/('acquisition-attempt-'+str(len(list(out.glob('acquisition*')))+1)+'.txt')
 with log.open('w') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
 if r.returncode:raise ValueError('native acquisition failed, preserve log')
 start=pd.to_datetime(c['download_timerange'].split('-')[0],format='%Y%m%d',utc=True);end=pd.to_datetime(c['download_timerange'].split('-')[1],format='%Y%m%d',utc=True)
 eval_start=pd.to_datetime(c['evaluation_timerange'].split('-')[0],format='%Y%m%d',utc=True)
 if eval_start-start<pd.Timedelta(hours=c['warmup_hours']):raise ValueError('insufficient declared hourly warmup')
 files=[];old={r['symbol']+'|'+r['timeframe']+'|'+r['candle_type']:r['sha256'] for r in read(ROOT/'evidence/session-2/source-data-manifest.json')['files']}
 for s in c['pairs']:
  for tf,typ in [('15m','futures'),('1h','futures'),('1h','mark'),('1h','funding_rate')]:
   p=folder/(s.replace('/','_').replace(':','_')+'-'+tf+'-'+typ+'.feather')
   df=pd.read_feather(p);original_sha=sha(p);original_rows=len(df)
   df=df.loc[(df.date>=start)&(df.date<end)].reset_index(drop=True)
   if len(df)!=original_rows:df.to_feather(p)
   seconds=c['funding_interval_seconds'] if typ=='funding_rate' else 900 if tf=='15m' else 3600
   r=inspect(df,seconds,start,end,pd.Timestamp.now(tz='UTC'),typ=='funding_rate')
   if typ=='funding_rate' and (r.get('irregular_intervals') or df.empty or df.date.iloc[0]>start or df.date.iloc[-1]+pd.Timedelta(seconds=seconds)<end):r['errors'].append('FUNDING_COVERAGE')
   if typ=='futures' and tf=='1h' and len(df.loc[(df.date+pd.Timedelta(hours=1))<=eval_start])<c['warmup_hours']:r['errors'].append('HOURLY_WARMUP')
   h=sha(p);r.update(path=str(p.relative_to(ROOT)),symbol=s,timeframe=tf,candle_type=typ,sha256=h,bytes=p.stat().st_size,native_sha256=original_sha,native_rows=original_rows,contract=contracts[s],matches_session2=h==old.get(s+'|'+tf+'|'+typ),source_timestamp_semantics='UTC candle open; available after close; funding UTC event')
   files.append(r)
 m={'schema_version':1,'cohort':c,'dataset_id':cid,'received_at_utc':datetime.now(timezone.utc).isoformat(),'source':'Gate public REST via official Freqtrade2026.10/CCXT','fidelity':'ACTUAL_PUBLIC_MARKET','files':files,'valid_for_backtest':all(not f['errors'] for f in files),'total_bytes':sum(f['bytes'] for f in files),'warmup_hours':int((eval_start-start).total_seconds()/3600),'raw_redistribution':False,'source_rights':'evidence/session-1/source-rights.md; Session3 bounded named-cohort extension'}
 write(out/'source-data-manifest.json',m)
 print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
 if not m['valid_for_backtest']:raise ValueError('strict source validation failed; see manifest; no silent substitution')
 return m
if __name__=='__main__':acquire(sys.argv[1])
