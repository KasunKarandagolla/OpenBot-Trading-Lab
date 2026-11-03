"""Session3 identities, additive freezes and isolated strategy staging."""
from pathlib import Path
import hashlib,json,os,shutil,re
ROOT=Path('/lab') if Path('/lab/research').exists() else Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/session-3'
STAGE=ROOT/'work/session3-strategies'
NAMES=['TrendPullbackBaselineV1','VWAPTrendContinuationV1','LiquiditySweepReversalV1','StructureAwareSweepV1','SweepThinningControlV1']
SOURCE_MAP={n+'.py':'user_data/strategies/'+n+'.py' for n in NAMES[:3]}
SOURCE_MAP.update({'PlaybookRiskV1.py':'user_data/strategies/PlaybookRiskV1.py',**{n+'.py':'research/session3/'+n+'.py' for n in NAMES[3:]},'causal_structure.py':'research/session3/causal_structure.py'})
def read(p):return json.loads(p.read_text())
def write(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cohort(cid):
 if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,60}',cid):raise ValueError('invalid cohort ID')
 c=read(ROOT/'research/cohorts'/ (cid+'.json'))
 validate_cohort(c)
 if c['cohort_id']!=cid:raise ValueError('cohort ID mismatch')
 registration=OUT/'cohorts'/cid/'registration.json'
 initial={'s3-development-v1','s3-transfer-v1'}
 if cid not in initial:
  if not registration.exists():raise ValueError('new cohort must be registered before use')
  r=read(registration)
  if r['cohort_sha256']!=sha(ROOT/'research/cohorts'/(cid+'.json')) or r['strategy_freeze_sha256']!=sha(OUT/'freeze.sha256') or r['protocol_sha256']!=sha(ROOT/'research/session-3-protocol.json'):raise ValueError('registered cohort or frozen strategy changed')
 return c
def validate_cohort(c):
 from datetime import datetime
 if c.get('schema_version')!=1 or c.get('venue')!='gate':raise ValueError('unreviewed cohort schema/venue')
 if c.get('classification') not in {'WARMUP_CORRECTED_DEVELOPMENT','SHARED_CALENDAR_MARKET_TRANSFER','PROSPECTIVE_RESERVED'}:raise ValueError('unreviewed cohort classification')
 pairs=c.get('pairs',[])
 if not 1<=len(pairs)<=5 or len(set(pairs))!=len(pairs) or any(not re.fullmatch(r'[A-Z0-9]+/USDT:USDT',s) for s in pairs):raise ValueError('invalid or oversized pair universe')
 parse=lambda s:datetime.strptime(s,'%Y%m%d')
 start,end=map(parse,c['download_timerange'].split('-'));ev,ee=map(parse,c['evaluation_timerange'].split('-'))
 if ee!=end or not start<ev<end or (end-start).days>100:raise ValueError('invalid/beyond bounded100day cohort')
 if c.get('warmup_hours')!=240 or (ev-start).total_seconds()<240*3600:raise ValueError('strict240hour warmup required')
 if c.get('funding_interval_seconds') not in {3600,14400,28800}:raise ValueError('unsupported funding interval')
 return c
def destination(cid):return OUT/'cohorts'/cohort(cid)['cohort_id']
def datadir(cid):return ROOT/'user_data/data/session-3'/cohort(cid)['cohort_id']/'gate'
def frozen():
 for session in ('session-1','session-2','session-3'):
  f=ROOT/'evidence'/session/'freeze.sha256'
  if not f.exists():raise ValueError('missing source freeze: '+session)
  for line in f.read_text().splitlines():
   h,p=line.split(maxsplit=1)
   if sha(ROOT/p)!=h:
    if p=='scripts/guard.py':
     from session4_safety import verify_frozen
     verify_frozen()
    else:raise ValueError('frozen source/config/protocol changed: '+p)
def stage():
 frozen();STAGE.mkdir(parents=True,exist_ok=True)
 registry=read(ROOT/'research/session-3-registry.json')
 if set(registry['strategies'])!=set(NAMES) or registry['persistent_paper_allowed'] is not False or any(s['paper_via_session3'] is not False for s in registry['strategies'].values()):raise ValueError('research registry mismatch/permission change')
 if any(p.suffix in ('.py','.json') and p.name not in SOURCE_MAP for p in STAGE.iterdir()):raise ValueError('unregistered/impersonator module in staging')
 for name,source in SOURCE_MAP.items():
  target=STAGE/name
  if target.exists() and sha(target)!=sha(ROOT/source):raise ValueError('staged module changed: '+name)
  if not target.exists():shutil.copyfile(ROOT/source,target)
 return STAGE
def config(cid,name):
 if name not in NAMES:raise ValueError('unknown research strategy')
 c=cohort(cid)
 file={'TrendPullbackBaselineV1':'research.json','VWAPTrendContinuationV1':'research-vwap.json'}.get(name,'research-sweep.json')
 cfg=read(ROOT/'configs'/file)
 cfg['strategy']=name;cfg['strategy_path']=str(STAGE);cfg['exchange']['pair_whitelist']=c['pairs']
 cfg['lab_audit']=False # preserve frozen callback code; prevent cross-session event file writes
 cfg.pop('api_server',None) # no server is initialized by these research subcommands
 # Validate frozen risk controls through existing implementation without extending its allowlist.
 from guard import validate
 check=json.loads(json.dumps(cfg));check['strategy_path']='/lab/user_data/strategies'
 if name in NAMES[3:]:check['strategy']='LiquiditySweepReversalV1'
 validate(check)
 overlay=ROOT/'user_data/runtime/cloud.json'
 if overlay.exists():
  net=read(overlay)
  if set(net)!={'exchange'} or not set(net['exchange'])<={'ccxt_config','ccxt_async_config','ccxt_sync_config'}:raise ValueError('unsafe network overlay')
  for k,v in net['exchange'].items():
   if not set(v)<={'enableRateLimit','timeout','httpsProxy','httpProxy','cafile','requests_trust_env','aiohttp_trust_env'}:raise ValueError('unsafe network option')
   cfg['exchange'].setdefault(k,{}).update(v)
 return cfg
def sanitized_env():
 if any(k.startswith('FREQTRADE__') for k in os.environ):raise ValueError('FREQTRADE__ overrides forbidden')
 return {k:v for k,v in os.environ.items() if k in {'PATH','LANG','LC_ALL','TZ','HTTP_PROXY','HTTPS_PROXY','NO_PROXY','http_proxy','https_proxy','no_proxy','SSL_CERT_FILE','REQUESTS_CA_BUNDLE'}}
