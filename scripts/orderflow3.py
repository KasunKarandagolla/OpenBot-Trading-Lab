"""Finite real public print capture. Public signed-size aggressor semantics unresolved."""
from decimal import Decimal
from datetime import datetime,timezone
import pandas as pd
from session3_common import *

def aggregate(rows,multiplier,asof,aggressor_confirmed=False):
 seen={};duplicates=0;buy=Decimal(0);sell=Decimal(0);total=Decimal(0);retained=[]
 for r in rows:
  ident=str(r['id']);fingerprint=(str(r['create_time']),str(r['price']),str(r['size']),r['contract'])
  if ident in seen:
   if seen[ident]!=fingerprint:raise ValueError('conflicting duplicate trade ID')
   duplicates+=1;continue
  seen[ident]=fingerprint
  stamp=pd.to_datetime(float(r['create_time']),unit='s',utc=True)
  if stamp>asof:continue
  price=Decimal(str(r['price']));size=Decimal(str(r['size']))
  if not price.is_finite() or not size.is_finite() or price<=0 or size==0 or r['contract']!='BTC_USDT':raise ValueError('invalid trade print/contract')
  if r.get('is_internal'):continue
  qty=abs(size)*Decimal(str(multiplier));total+=qty
  if aggressor_confirmed:
   if size>0:buy+=qty
   else:sell+=qty
  retained.append(stamp)
 return {'distinct_available_prints':len(retained),'duplicate_ids':duplicates,'total_base_btc':float(total),'buy_aggressor_btc':float(buy) if aggressor_confirmed else None,'sell_aggressor_btc':float(sell) if aggressor_confirmed else None,'signed_delta_btc':float(buy-sell) if aggressor_confirmed else None,'first_execution_utc':min(retained).isoformat() if retained else None,'last_execution_utc':max(retained).isoformat() if retained else None,'side_status':'DOCUMENTED' if aggressor_confirmed else 'AGGRESSOR_SIDE_UNKNOWN'}

def sample():
 from public_exchange import public_exchange
 now=pd.Timestamp.now(tz='UTC');start=now.floor('s')-pd.Timedelta(seconds=60);end=now.floor('s')
 folder=ROOT/'user_data/data/session-3/orderflow';folder.mkdir(parents=True,exist_ok=True)
 path=folder/(end.strftime('%Y%m%dT%H%M%S')+'.json')
 if path.exists():raise ValueError('sample ID exists')
 request={'settle':'usdt','contract':'BTC_USDT','from':int(start.timestamp()),'to':int(end.timestamp()),'limit':1000}
 # Declaration receipt precedes the single public-trade request.
 declaration={'schema_version':1,'declared_at_utc':now.isoformat(),'requested_from_utc':start.isoformat(),'requested_to_utc':end.isoformat(),'max_pages':1,'max_prints':1000,'max_bytes':2000000,'public_only':True}
 write(OUT/'orderflow-declaration.json',declaration)
 e=public_exchange();raw=e.publicFuturesGetSettleTrades(request);received=pd.Timestamp.now(tz='UTC')
 payload=json.dumps(raw,sort_keys=True).encode()
 if len(payload)>2000000 or not isinstance(raw,list) or len(raw)>1000:raise ValueError('public sample exceeds declared bounds')
 path.write_bytes(payload)
 source=read(destination('s3-development-v1')/'source-data-manifest.json')
 contract=next(r['contract'] for r in source['files'] if r['symbol']=='BTC/USDT:USDT');multiplier=contract['contractSize']
 # Current public REST docs call size 'Trading size'. CCXT maps sign to buy/sell,
 # but this does not independently document that sign is PUBLIC aggressor side.
 summary=aggregate(raw,multiplier,received,aggressor_confirmed=False)
 obj=declaration|{'environment':'RESEARCH_ONLY','symbol':'BTC/USDT:USDT','received_at_utc':received.isoformat(),'source':'Gate public futures/usdt/trades via CCXT4.5.90','source_status':'ACTUAL_PUBLIC_TRADE_PRINTS','fidelity':'TRADE_PRINTS','coverage_status':'PARTIAL_COVERAGE','coverage_reasons':['Single bounded page; unproven start/end boundary completeness','Trade-ID sequence continuity not established for this endpoint; no missing-page assertion'],'raw_rows':len(raw),'raw_bytes':len(payload),'raw_sha256':sha(path),'raw_local_only':True,'contract_multiplier_btc_per_contract':multiplier,'price_unit':'USDT/BTC','quantity_unit':'contracts converted to BTC','aggregation_available_at_utc':received.isoformat(),'summary':summary,'aggressor_semantics':'UNVALIDATED: current Gate public FuturesTrade schema does not explicitly define taker mapping; CCXT sign convention alone insufficient','docs':'https://www.gate.com/docs/developers/apiv4/en/futures/#futures-trade','strategy_feature_eligible':False}
 write(OUT/'orderflow-proof.json',obj);print(json.dumps(obj,indent=2))
