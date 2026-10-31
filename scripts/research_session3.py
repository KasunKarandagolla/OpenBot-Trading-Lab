"""Operator entrypoints for the bounded, research-only Session3 workflow."""
import argparse,csv,subprocess,sys,zipfile
from datetime import datetime,timezone
from session3_common import *

def native_run(cid):
 from data_session3 import verify
 from opportunity3 import analyze
 import pandas as pd
 frozen();m=verify(cid);out=destination(cid)
 for name in NAMES:
  dest=out/'native-results';dest.mkdir(parents=True,exist_ok=True)
  artifact=dest/(name+'.json')
  if artifact.exists():raise ValueError('recorded run exists; preserve it; version a new experiment for rerun')
  args=[sys.executable,str(ROOT/'scripts/engine3.py'),'backtesting',cid,name]
  started=datetime.now(timezone.utc).isoformat()
  log=dest/(name+'-output.txt')
  with log.open('w') as f:result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
  with (OUT/'commands-and-results.txt').open('a') as f:f.write(started+' '+' '.join(args)+'\nexit='+str(result.returncode)+'\n')
  if result.returncode:raise ValueError('native run failed: '+name)
  runpath=ROOT/'user_data/backtest_results/session-3'/cid/name
  pointer=read(runpath/'.last_result.json');archive=runpath/pointer['latest_backtest']
  if archive.stat().st_mtime<pd.Timestamp(started).timestamp():raise ValueError('native result is stale')
  with zipfile.ZipFile(archive) as z:
   member=next(n for n in z.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
   raw=z.read(member)
  artifact.write_bytes(raw);native=json.loads(raw)['strategy'][name];trades=native['trades']
  # Causal tags from the exact entry signal's completed hourly context.
  frames={};tags=[]
  for s in cohort(cid)['pairs']:
   files={tf:next(f for f in m['files'] if f['symbol']==s and f['timeframe']==tf and f['candle_type']=='futures') for tf in ['15m','1h']}
   b=pd.read_feather(ROOT/files['15m']['path']);h=pd.read_feather(ROOT/files['1h']['path'])
   frames[s]=analyze(b,h,pd.Timestamp(b.date.iloc[-1])+pd.Timedelta(minutes=15)).set_index('date')
  for t in trades:
   at=pd.Timestamp(t['open_date'])-pd.Timedelta(minutes=15);row=frames[t['pair']].loc[at]
   # Regime depends only on the previous completed hourly ADX/EMAs.
   regime=('TREND_UP' if row.ema20_1h>row.ema50_1h else 'TREND_DOWN') if row.adx_1h>=25 else 'RANGE_LOW_ADX'
   risk=t['stake_amount']*(abs(t['open_rate']-t['stop_loss_abs'])/t['open_rate']+.0035)
   tags.append({'pair':t['pair'],'open_date':t['open_date'],'profit_abs':t['profit_abs'],'regime':regime,'regime_known_at_utc':row.struct_known_at_1h.isoformat(),'signal_known_at_utc':(at+pd.Timedelta(minutes=15)).isoformat(),'initial_modeled_risk_usdt':risk,'net_R':t['profit_abs']/risk if risk>0 else None})
  tagpath=out/'trade-ledgers'/(name+'-tags.json');write(tagpath,tags)
  fields=['pair','is_short','open_date','close_date','open_rate','close_rate','amount','stake_amount','leverage','fee_open','fee_close','funding_fees','trade_duration','exit_reason','profit_ratio','profit_abs','is_open','initial_stop_loss_abs','stop_loss_abs']
  with (out/'trade-ledgers'/(name+'.csv')).open('w') as f:
   w=csv.DictWriter(f,fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(trades)
  write(dest/(name+'-provenance.json'),{'experiment_id':cid+'-'+name,'started_utc':started,'completed_utc':datetime.now(timezone.utc).isoformat(),'engine':'2026.10','engine_image':'freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7','base_sha':read(ROOT/'research/session-3-protocol.json')['base_sha'],'native_result_sha256':sha(artifact),'native_zip_sha256':sha(archive),'native_zip_local_only':True,'tags_sha256':sha(tagpath),'source_manifest_sha256':sha(out/'source-data-manifest.json'),'protocol_sha256':sha(ROOT/'research/session-3-protocol.json'),'cohort_sha256':sha(ROOT/'research/cohorts'/(cid+'.json')),'strategy_hashes':{p:sha(ROOT/p) for p in SOURCE_MAP.values()},'config_sha256':sha(ROOT/'work/session3-configs'/cid/(name+'.json')),'exit_code':result.returncode})
  print(name+': '+str(len(trades))+' native trades, net '+str(sum(t['profit_abs'] for t in trades)),flush=True)
 from economics3 import compare
 compare(cid)

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 registered=sorted(x.stem for x in (ROOT/'research/cohorts').glob('*.json'))
 for command in ['research-download','research-run','economic-compare','validation-report','lookahead','recursive-check','candidate-census','native-replay']:
  s=sub.add_parser(command);s.add_argument('cohort',choices=registered)
 s=sub.add_parser('opportunity-asof');s.add_argument('symbol');s.add_argument('timestamp');s.add_argument('--cohort',default='s3-development-v1',choices=registered)
 s=sub.add_parser('cohort-register');s.add_argument('id');s.add_argument('download_start',help='YYYYMMDD');s.add_argument('evaluation_start');s.add_argument('end');s.add_argument('symbols',nargs='+');s.add_argument('--classification',choices=['WARMUP_CORRECTED_DEVELOPMENT','SHARED_CALENDAR_MARKET_TRANSFER','PROSPECTIVE_RESERVED'],required=True)
 scan=sub.add_parser('opportunity-scan');scan.add_argument('--cohort',choices=registered);scan.add_argument('--as-of')
 sub.add_parser('scanner-refresh');sub.add_parser('structure-check');sub.add_parser('test');sub.add_parser('orderflow-sample');sub.add_parser('prospective-plan');sub.add_parser('detail-download');sub.add_parser('execution-sensitivity')
 a=p.parse_args()
 # All command families reject mode overrides, even when no engine is needed.
 sanitized_env();OUT.mkdir(parents=True,exist_ok=True)
 if a.command=='research-download':
  from data_session3 import acquire
  acquire(a.cohort)
 elif a.command=='cohort-register':
  import re
  frozen()
  if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,60}',a.id):raise ValueError('invalid cohort ID')
  c={'schema_version':1,'cohort_id':a.id,'venue':'gate','classification':a.classification,'pairs':a.symbols,'download_timerange':a.download_start+'-'+a.end,'evaluation_timerange':a.evaluation_start+'-'+a.end,'warmup_hours':240,'funding_interval_seconds':28800,'rights':'Bounded personal/noncommercial Gate public API, no raw redistribution','selection':'Explicit operator registration; historical membership not inferred'}
  validate_cohort(c)
  at=datetime.now(timezone.utc)
  if a.classification=='PROSPECTIVE_RESERVED' and datetime.strptime(a.evaluation_start,'%Y%m%d').replace(tzinfo=timezone.utc)<=at:raise ValueError('prospective evaluation must start after registration')
  path=ROOT/'research/cohorts'/(a.id+'.json')
  if path.exists():raise ValueError('cohort already registered; preserve immutable definition')
  # Exclusive creation preserves IDs even under concurrent operator calls.
  with path.open('x') as f:f.write(json.dumps(c,indent=2,sort_keys=True)+'\n')
  write(OUT/'cohorts'/a.id/'registration.json',{'registered_at_utc':at.isoformat(),'cohort_sha256':sha(path),'strategy_freeze_sha256':sha(OUT/'freeze.sha256'),'protocol_sha256':sha(ROOT/'research/session-3-protocol.json'),'outcomes_inspected':False if a.classification=='PROSPECTIVE_RESERVED' else 'NOT_ASSERTED'})
  print(json.dumps(c,indent=2))
 elif a.command=='research-run':native_run(a.cohort)
 elif a.command=='candidate-census':
  from census3 import census
  census(a.cohort)
 elif a.command=='native-replay':
  from replay3 import replay
  replay(a.cohort)
 elif a.command in ['economic-compare','validation-report']:
  from economics3 import compare
  obj=compare(a.cohort)
  if a.command=='validation-report':write(destination(a.cohort)/'validation-report.json',{'schema_version':1,'environment':'RESEARCH_ONLY','cohort_id':a.cohort,'strategies':{n:{'trades':m['trades'],'net_usdt':m['net_usdt'],'classification':m['evidence_classification'],'decision':'NO_PROMOTION'} for n,m in obj['strategies'].items()},'parent_challenger':obj['parent_challenger']})
  print(json.dumps({n:{k:m[k] for k in ['trades','net_usdt','profit_factor','evidence_classification']} for n,m in obj['strategies'].items()},indent=2))
 elif a.command=='opportunity-asof':
  from opportunity3 import historical,utc
  obj=historical(a.cohort,a.symbol,utc(a.timestamp));print(json.dumps(obj,indent=2,allow_nan=False))
 elif a.command=='opportunity-scan':
  from opportunity3 import current,historical,utc
  if bool(a.cohort)!=bool(a.as_of):raise ValueError('historical scan needs both --cohort and --as-of')
  if a.cohort:
   obj=[historical(a.cohort,s,utc(a.as_of)) for s in cohort(a.cohort)['pairs']]
   obj.sort(key=lambda x:(-int(x['setup']['decision']=='ACCEPT'),-x['rank_score'],x['symbol']))
   write(OUT/'opportunity-historical.json',obj)
  else:obj=current();write(OUT/'opportunity-current.json',obj)
  print(json.dumps(obj,indent=2))
 elif a.command=='scanner-refresh':
  # Reuse both existing native scanner and exporter in an isolated output tree.
  import shutil
  mirror=ROOT/'work/session3-scanner'
  for folder in ['user_data/logs','configs','evidence/session-1']:(mirror/folder).mkdir(parents=True,exist_ok=True)
  shutil.copyfile(ROOT/'configs/scan-rules.json',mirror/'configs/scan-rules.json')
  args=[sys.executable,str(ROOT/'scripts/guard.py'),'test-pairlist','--config',str(ROOT/'configs/scanner.json'),'--print-json']
  if (ROOT/'user_data/runtime/cloud.json').exists():args+=['--config',str(ROOT/'user_data/runtime/cloud.json')]
  with (mirror/'user_data/logs/scan-native.log').open('w') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
  if r.returncode:raise ValueError('existing native scanner failed')
  import scan_export
  scan_export.ROOT=mirror;scan_export.main()
  shutil.copyfile(mirror/'evidence/session-1/scan-snapshot.json',OUT/'scanner-snapshot.json')
 elif a.command in ['structure-check','test']:
  tests=['test_session3_structure','test_session3_workflow'] if a.command=='structure-check' else []
  args=[sys.executable,'-m','unittest']+(['discover','-s',str(ROOT/'tests'),'-v'] if not tests else ['-v']+tests)
  if tests:
   env=sanitized_env();env['PYTHONPATH']=str(ROOT/'tests');return subprocess.call(args,env=env)
  return subprocess.call(args,env=sanitized_env())
 elif a.command in ['lookahead','recursive-check']:
  return subprocess.call([sys.executable,str(ROOT/'scripts/engine3.py'),'lookahead-analysis' if a.command=='lookahead' else 'recursive-analysis',a.cohort,'StructureAwareSweepV1'],env=sanitized_env())
 elif a.command=='orderflow-sample':
  from orderflow3 import sample
  sample()
 elif a.command in ['detail-download','execution-sensitivity']:
  from detail3 import acquire,run
  acquire() if a.command=='detail-download' else run()
 elif a.command=='prospective-plan':
  plan={'schema_version':1,'environment':'RESEARCH_ONLY','classification':'PROSPECTIVE_RESERVED_NOT_EVALUATED','earliest_evaluation_utc':'2026-10-31T14:00:00Z','protocol_sha256':sha(ROOT/'research/session-3-protocol.json'),'freeze_sha256':sha(OUT/'freeze.sha256'),'source':'Gate bounded public REST','pairs':cohort('s3-development-v1')['pairs'],'required_warmup_hours':240,'collection':'Use a new immutable registered cohort after end is past; research-download refuses overwrites. Do not relabel inspected samples as prospective. No daemon or paper execution.'}
  write(OUT/'prospective-plan.json',plan);print(json.dumps(plan,indent=2))
 return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except (ValueError,KeyError,FileNotFoundError) as exc:print('RESEARCH REFUSAL: '+str(exc),file=sys.stderr);raise SystemExit(2)
