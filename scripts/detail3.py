"""Bounded optional finer-candle/native fill sensitivity; separate source directory."""
import csv,shutil,sys,subprocess,zipfile
import pandas as pd
from session3_common import *
from validate_data import inspect
from economics3 import metric

def spec():
 p=OUT/'execution-sensitivity-protocol.json'
 expected=(OUT/'execution-sensitivity-protocol.sha256').read_text().split()[0]
 if sha(p)!=expected:raise ValueError('detail experiment freeze mismatch')
 return read(p)

def detail_dir():return ROOT/'user_data/data/session-3/detail-v1/gate'

def verify_detail():
 m=read(OUT/'detail-source-manifest.json')
 if not m['valid']:raise ValueError('invalid detail source')
 for r in m['files']:
  if sha(ROOT/r['path'])!=r['sha256']:raise ValueError('detail source changed')
 return m

def acquire():
 from data_session3 import verify
 from public_exchange import public_exchange
 frozen();p=spec();m=verify(p['cohort_id']);folder=detail_dir()/'futures'
 if folder.exists() and any(folder.glob('*.feather')):raise ValueError('detail sources exist; preserve them')
 folder.mkdir(parents=True,exist_ok=True);files=[];total=0;e=public_exchange()
 start=pd.Timestamp('2026-10-01',tz='UTC');end=pd.Timestamp('2026-10-30',tz='UTC')
 for r in m['files']:
  dest=folder/Path(r['path']).name;shutil.copyfile(ROOT/r['path'],dest);files.append({'path':str(dest.relative_to(ROOT)),'sha256':sha(dest),'copied_from_sha256':r['sha256']})
 for symbol in cohort(p['cohort_id'])['pairs']:
  cursor=int(start.timestamp()*1000);endms=int(end.timestamp()*1000);rows=[];pages=0
  while cursor<endms:
   if pages>=p['download_limit_pages_per_symbol']:raise ValueError('bounded detail pagination exhausted')
   page=e.fetch_ohlcv(symbol,'5m',since=cursor,limit=1000);pages+=1
   if not page or page[0][0]!=cursor:raise ValueError('missing detail page/start')
   selected=[r for r in page if cursor<=r[0]<endms];rows.extend(selected)
   if not selected:raise ValueError('empty detail page')
   cursor=selected[-1][0]+300000
  d=pd.DataFrame(rows,columns=['date','open','high','low','close','volume']);d['date']=pd.to_datetime(d.date,unit='ms',utc=True)
  report=inspect(d,300,start,end,pd.Timestamp.now(tz='UTC'))
  if report['errors']:raise ValueError('invalid detail source: '+str(report['errors']))
  path=folder/(symbol.replace('/','_').replace(':','_')+'-5m-futures.feather');d.to_feather(path);total+=path.stat().st_size
  if total>p['max_bytes']:raise ValueError('detail source byte bound')
  files.append(report|{'symbol':symbol,'path':str(path.relative_to(ROOT)),'sha256':sha(path),'requests':pages,'bytes':path.stat().st_size})
 write(OUT/'detail-source-manifest.json',{'schema_version':1,'valid':True,'received_at_utc':pd.Timestamp.now(tz='UTC').isoformat(),'source':'Gate CCXT public fetch_ohlcv 5m; no credentials','source_window':'20261001-20261030','detail_bytes':total,'files':files,'raw_local_only':True})

def run():
 p=spec();verify_detail();dest=OUT/'execution-detail';dest.mkdir(parents=True,exist_ok=True);results={}
 for name in p['strategies']:
  results[name]={}
  for mode in ['coarse','fine']:
   stem=name+'-'+mode;artifact=dest/(stem+'.json')
   if artifact.exists():raise ValueError('detail run exists; preserve it')
   args=[sys.executable,str(ROOT/'scripts/engine3.py'),'detail-'+mode,p['cohort_id'],name]
   with (dest/(stem+'-output.txt')).open('w') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
   if r.returncode:raise ValueError('detail native failure')
   runpath=ROOT/'user_data/backtest_results/session-3/detail'/stem
   archive=runpath/read(runpath/'.last_result.json')['latest_backtest']
   with zipfile.ZipFile(archive) as z:raw=z.read(next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n))
   artifact.write_bytes(raw);native=json.loads(raw)['strategy'][name];trades=native['trades']
   results[name][mode]=metric(trades,native,[],[])
   fields=['pair','is_short','open_date','close_date','open_rate','close_rate','stake_amount','profit_abs','trade_duration','exit_reason','funding_fees']
   with (dest/(stem+'-trades.csv')).open('w') as f:w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(trades)
   write(dest/(stem+'-provenance.json'),{'native_sha256':sha(artifact),'native_zip_sha256':sha(archive),'spec_sha256':sha(OUT/'execution-sensitivity-protocol.json'),'detail_manifest_sha256':sha(OUT/'detail-source-manifest.json'),'source_freeze_sha256':sha(OUT/'freeze.sha256'),'config_sha256':sha(ROOT/'work/session3-configs'/p['cohort_id']/(name+'.json')),'exit_code':r.returncode})
   print(stem,len(trades),results[name][mode]['net_usdt'],flush=True)
 write(OUT/'execution-sensitivity.json',{'schema_version':1,'environment':'RESEARCH_ONLY','protocol':p,'strategies':results,'limitations':['5m detail changes native timing and callback cadence, not observed order-book fills','No historical quote or queue/partial-fill model','Common inspected short development window; no independent qualification']})
