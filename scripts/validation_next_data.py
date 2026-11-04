"""Bounded official archive ingestion; no strategy outputs are read here."""
import concurrent.futures,datetime,hashlib,json,urllib.request,zipfile,io,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/validation_next/run-001';DATA=ROOT/'user_data/data/validation_next'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def get(u):
 with urllib.request.urlopen(u,timeout=40) as r:return r.read(20_000_000)
def run():
 spec=json.loads((ROOT/'research/validation_next/protocol.json').read_text());reg=OUT/'ingestion-registration.json'
 record=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),protocol_sha256=sha(ROOT/'research/validation_next/protocol.json'),partitions=spec['partitions'],outcomes_inspected=False)
 if not reg.exists():write(reg,record)
 elif json.loads(reg.read_text())['protocol_sha256']!=record['protocol_sha256']:raise ValueError('protocol changed')
 jobs=[]
 for pair in spec['universe']:
  symbol=pair.split('/')[0]+'USDT'
  for month in ['2026-01','2026-02','2026-03','2026-04']:
   for kind,tf in [('klines','15m'),('klines','1h'),('klines','5m'),('markPriceKlines','1h'),('fundingRate',None)]:
    tail=f'{symbol}/{tf}/{symbol}-{tf}-{month}.zip' if tf else f'{symbol}/{symbol}-fundingRate-{month}.zip'
    jobs.append((pair,kind,tf,month,'https://data.binance.vision/data/futures/um/monthly/'+kind+'/'+tail))
 def one(j):
  pair,kind,tf,month,url=j;path=DATA/'archives'/kind/(tf or 'events')/url.split('/')[-1];receipt=OUT/'sources'/kind/(tf or 'events')/(path.stem+'.json')
  if receipt.exists():
   r=json.loads(receipt.read_text())
   if sha(path)!=r['sha256']:raise ValueError('changed source')
   return r
  b=get(url);checksum=get(url+'.CHECKSUM').decode();expected=checksum.split()[0]
  if hashlib.sha256(b).hexdigest()!=expected:raise ValueError('bad official checksum '+url)
  with zipfile.ZipFile(io.BytesIO(b)) as z:
   if len(z.namelist())!=1:raise ValueError('unexpected ZIP members')
   member=z.namelist()[0];body=z.read(member)
  rows=list(csv.reader(io.StringIO(body.decode())));header=rows[0];values=rows[1:]
  stamps=[int(float(r[0])) for r in values]
  start=datetime.datetime.fromisoformat(month+'-01').replace(tzinfo=datetime.timezone.utc);next_month=start.replace(month=start.month+1)
  a=int(start.timestamp()*1000);end=int(next_month.timestamp()*1000)
  if not stamps or min(stamps)<a or max(stamps)>=end or len(set(stamps))!=len(stamps) or stamps!=sorted(stamps):raise ValueError('clock/range/duplicate error')
  gaps=None
  if tf:
   width={'5m':300000,'15m':900000,'1h':3600000}[tf];gaps=sum(y-x!=width for x,y in zip(stamps,stamps[1:]))
   if stamps[0]!=a or stamps[-1]+width!=end or len(stamps)!=(end-a)//width or gaps:raise ValueError('incomplete candles')
   for r in values:
    o,h,l,c,v=map(float,r[1:6])
    if not (0<l<=min(o,c)<=max(o,c)<=h and v>=0):raise ValueError('bad candle')
    if int(r[6])!=int(r[0])+width-1:raise ValueError('bad close convention')
  else:
   for r in values:
    if not 0<float(r[1])<=24 or abs(float(r[2]))>.05:raise ValueError('bad funding')
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b);Path(str(path)+'.CHECKSUM').write_text(checksum)
  r=dict(pair=pair,contract_id=pair.split('/')[0]+'USDT',venue='binance',market_type='linear USDT perpetual',kind=kind,timeframe=tf,month=month,url=url,checksum_url=url+'.CHECKSUM',retrieved_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=sha(path),source_csv_sha256=hashlib.sha256(body).hexdigest(),bytes=len(b),rows=len(values),first_ms=stamps[0],last_ms=stamps[-1],gaps=gaps,duplicates=0,bad_ticks=0,header=header,timestamp_unit='UTC milliseconds',close_convention='open+interval-1ms; features known at open+interval',path=str(path.relative_to(ROOT)),market_membership='PRESELECTED_SURVIVORS; archive confirms existence only',signed_flow='CANDLE_TAKER_BUY_FIELDS_ONLY' if kind=='klines' else 'NOT_APPLICABLE')
  write(receipt,r);print(pair,kind,tf,month,len(values),flush=True);return r
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:receipts=list(pool.map(one,jobs))
 write(OUT/'data-manifest.json',dict(protocol_sha256=record['protocol_sha256'],source_files=receipts,archive_bytes=sum(x['bytes'] for x in receipts),partitions=spec['partitions'],metadata_status='UNQUALIFIED_CCXT_FIXTURE_ONLY',economic_status='PARTIAL_COST_MODEL / INSUFFICIENT_ECONOMIC_VALIDATION',attribution='Binance Vision; CC BY-NC-SA4.0; personal non-production historical research only; outputs derived from archive carry same attribution/license. No commercial use or raw data publication.'))
if __name__=='__main__':run()
