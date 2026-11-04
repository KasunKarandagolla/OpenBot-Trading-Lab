"""Isolated, explicit scenario paths; prior research is read-only."""
from pathlib import Path
import sys,json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[1]
for d in ['scripts','user_data/strategies']+['research/'+x for x in ['session3','bonus','master_audit','foundation','intelligence','policy','session4','recovery','setup','integrated','diagnosis','validation_next']]:sys.path.insert(0,str(ROOT/d))
OUT=ROOT/'evidence/validation_next/run-001';WORK=ROOT/'work/validation_next';DATA=ROOT/'user_data/data/validation_next'
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False,default=str)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def slug(p):return p.replace('/','_').replace(':','_')
def spec():return read(ROOT/'research/validation_next/protocol.json')
def pairs():return spec()['universe']
def verify_old():
 seal=read(OUT/'starting-freeze.json');bad=[p for p,h in seal['files'].items() if sha(ROOT/p)!=h]
 if bad:raise ValueError('original bytes changed '+str(bad))
 return dict(files=len(seal['files']),evidence_files=sum(p.startswith('evidence/') for p in seal['files']),changed=[])
def verify_sources():
 if sha(ROOT/'research/validation_next/protocol.json')!=read(OUT/'ingestion-registration.json')['protocol_sha256']:raise ValueError('registered protocol changed')
 for r in read(OUT/'data-manifest.json')['source_files']:
  if sha(ROOT/r['path'])!=r['sha256']:raise ValueError('source hash '+r['path'])
