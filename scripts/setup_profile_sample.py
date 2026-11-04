from setup_common import *
from recovery_data import client
from setup_profile import verified_profile
import pandas as pd,time,hashlib,json
pair='LTC/USDT:USDT';contract='LTC_USDT';start=pd.Timestamp('2026-08-31T16:00:00Z');end=start+pd.Timedelta(hours=8)
ex=client();pending=[(int(start.timestamp()),int(end.timestamp()))];rows={};calls=0;parts=[];errors=[]
while pending and calls<128:
 a,b=pending.pop();calls+=1
 try:raw=ex.public_futures_get_settle_trades(dict(settle='usdt',contract=contract,**{'from':a,'to':b,'limit':1000}))
 except Exception as e:errors.append(str(e));break
 if len(raw)>=1000:
  if b-a<=1:errors.append('CAPPED_AT_ONE_SECOND');break
  m=(a+b)//2;pending.extend([(a,m),(m,b)]);continue
 parts.append(dict(start=a,end=b,rows=len(raw),uncapped=True))
 for t in raw:
  stamp=float(t.get('create_time_ms') or t['create_time'])*1000
  if a*1000<=stamp<b*1000:rows[str(t['id'])]=t
received=time.time()*1000;mult=read(DATA/'contract-source.json')[pair]['market']['contractSize']
trades=sorted([dict(id=k,event_ms=float(t.get('create_time_ms') or t['create_time'])*1000,received_ms=received,price=float(t['price']),amount=abs(float(t['size']))*mult) for k,t in rows.items()],key=lambda t:(t['event_ms'],t['id']))
write(DATA/'verified-profile-sample-trades.json',trades)
candles=pd.read_feather(DATA/'development/gate/futures/LTC_USDT_USDT-15m-futures.feather');candles=candles.loc[(candles.date>=start)&(candles.date<end)]
obs=pd.DataFrame(trades);differences=[]
if len(obs):
 obs['bar']=pd.to_datetime(obs.event_ms,unit='ms',utc=True).dt.floor('15min');totals=obs.groupby('bar').amount.sum()
 for _,r in candles.iterrows():differences.append(dict(at=r.date.isoformat(),ohlcv_volume=float(r.volume),trade_volume=float(totals.get(r.date,0)),relative_error=abs(float(totals.get(r.date,0))-r.volume)/max(r.volume,1e-12)))
complete=not pending and not errors and len(candles)==32 and len(differences)==32 and max(x['relative_error'] for x in differences)<1e-5
receipt=dict(source='GATE_PUBLIC_FUTURES_TRADES_ADAPTIVE_UNCAPPED_TIME_PARTITIONS_AND_OHLCV_VOLUME_RECONCILIATION',venue='gate',pair=pair,fidelity='EXECUTED_TRADES',coverage='COMPLETE_VERIFIED' if complete else 'PARTIAL',start=start.isoformat(),end=end.isoformat(),known_at=pd.Timestamp(received,unit='ms',tz='UTC').isoformat(),sha256=hashlib.sha256(json.dumps(trades,sort_keys=True,separators=(',',':')).encode()).hexdigest())
write(DATA/'verified-profile-sample-receipt.json',receipt)
result=verified_profile(trades,receipt,receipt['known_at'])
write(OUT/'verified-profile-sample.json',dict(calls=calls,call_cap=128,pair=pair,trades=len(trades),parts=parts,remaining_intervals=len(pending),errors=errors,volume_reconciliation=differences,contract_result=result,coverage_complete_verified=complete,source_sha256=sha(DATA/'verified-profile-sample-trades.json'),economic_status='NOT_TESTED_FULL_COHORT',availability='Receipt is actual acquisition time. No historical receipt time is invented; sample is not injected into earlier decisions.'))
print('Calls',calls,'Trades',len(trades),'Complete verified',complete,'Contract',result['status'])
