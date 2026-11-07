import hashlib,json,tempfile,sys,datetime
sys.path.insert(0,'scripts')
from trading_lab.watchlist import connect,create,observe,encode
from pathlib import Path
p=Path('evidence/skills-v2/20261107/casebook/agent-inputs/B01/input.json')
raw=p.read_bytes(); case=json.loads(raw); seal=json.loads((p.parent/'decision-seal.json').read_text())
assert hashlib.sha256(raw).hexdigest()==seal['input_sha256']
record=case['numeric']['5m']; bars=record['bars']
assert hashlib.sha256(encode(bars).encode()).hexdigest()==record['bars_sha256']
# Fixed example: decision after the first 300 bars, level from the 24 bars immediately preceding it.
# Not a registered prospective experiment; source already studied and eligibility unknown.
past=bars[276:300]; cutoff=past[-1][6]+1
level=max(float(b[2]) for b in past); stop=min(float(b[3]) for b in past)
definition=dict(symbol=case['symbol'],venue=case['venue'],direction='LONG',family='BREAKOUT_RETEST',source_cutoff_ms=cutoff,source_sha256=record['bars_sha256'],level=level,invalidation=stop,expires_ms=cutoff+13*300000,hypothesis='Prior 24-bar high may become a breakout decision level.',opposition='Prior high may reject price; no acceptance is established.',confirmation='Observe completed bars around the prior high; full playbook confirmation remains undefined.',feature_version='fixed-24x5m-prototype-v1')
with tempfile.TemporaryDirectory() as root:
 db=connect(root); sid=create(db,definition); db.close()
 # Freeze definition before accessing the selected later bars.
 future=bars[300:312]; assert len(future)==12
 source_hash=hashlib.sha256(encode(future).encode()).hexdigest()
 db=connect(root)
 for bar in future:
  try: observe(db,sid,[bar],source_hash,as_of_ms=bar[6]+1,mode='HISTORICAL')
  except ValueError as e:
   if str(e)=='Terminal state or missing bar': break
   raise
 events=[dict(at_ms=r[0],state=r[1],body=json.loads(r[2])) for r in db.execute('SELECT at_ms,state,body FROM events WHERE setup_id=? ORDER BY seq',(sid,))]
 db.close(); db=connect(root); recovered=db.execute('SELECT COUNT(*) FROM events WHERE setup_id=?',(sid,)).fetchone()[0]; db.close()
 result=dict(status='HISTORICAL_PROTOTYPE_NOT_TRADE',case='B01',input_sha256=seal['input_sha256'],bar_array_sha256=record['bars_sha256'],archive_sources=record['sources'],definition=definition,setup_id=sid,events=events,restart_event_count=recovered,limitations=['Not a broad universe scan','Previously studied data; not an independent holdout','Historical eligibility, spread and account metadata unqualified','No playbook trigger or economics evaluated','Raw archive comparison was documented by inherited casebook; this run checks sealed export hashes only'])
 Path('evidence/watchlist-s1/historical-example.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'symbol':case['symbol'],'cutoff_ms':cutoff,'level':level,'invalidation':stop,'events':[(x['at_ms'],x['state']) for x in events],'recovered':recovered,'archive':record['sources']},indent=2))
