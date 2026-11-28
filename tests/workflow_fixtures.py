"""Deterministic fake source adapters; all numbers are test data."""
import math,json
from test_session5 import FakeAPI,FakeClient,fake_pack,AT
from researcher.discovery import scan_market_research
from researcher.contracts import utc,encode,digest
from researcher.numerics import Bar
from researcher.observations import WIDTHS
from decimal import Decimal as D
from unittest.mock import patch
class ScenarioAPI(FakeAPI):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.http.request=self.request
  self.books=0;self.point_shift=D(0);self.http_limit=80
  self.max_sample_calls=68
 def klines(self,i,*,timeframe,cutoff,bars=300):
  self.sample_calls+=1
  self.record('binance_klines')
  if i.native_symbol=='BBBUSDT' and timeframe=='15m':
   from researcher.transport import ProviderError
   raise ProviderError('OFFLINE_REQUESTED_HISTORY_MISSING')
  width=WIDTHS[timeframe]*1000;end=int(utc(cutoff).timestamp()*1000)
  series=[]
  for j in range(bars):
   p=D(100)+D(str(round(math.sin(j*.8)*.6,4)));o=p;h=p+D('.4');l=p-D('.4');c=p
   if j==bars-18 and i.native_symbol not in {'BTCUSDT','ETHUSDT'}:h=D(115)
   if j>=bars-12 and i.native_symbol not in {'BTCUSDT','ETHUSDT'}:
    rows=[(100,101,99,100),(100,101,99,100),(100,104,99,100),(100,101,99,100),(100,101,99,100),(100,101,99,100),(100,103,99,102),(102,104,101,103),(103,105,102,104),('104','105','103','104.2'),('104.2','105','103','104.4'),('104.4','105','103','104.6')]
    if i.native_symbol=='DDDUSDT':
     rows=[(100,101,99,100),(100,104,99,100),(100,101,99,100),(100,101,99,100),('101','105','100','104.5'),(103,'103.5',102,103),(103,103,99,100),(104,106,104,105),(105,106,'104.5','105.5'),('105.5','106.2',105,106),(106,'106.4',105,'106.1'),('106.1','106.5',105,'106.2')]
    o,h,l,c=map(D,rows[j-(bars-12)])
   if i.native_symbol.startswith('BEAR'):o,h,l,c=200-o,200-l,200-h,200-c
   series.append(Bar(i.native_symbol,timeframe,end-(bars-j)*width,o,h,l,c,D(10),c*10,D(5),c*5,10,'OFFLINE_SCENARIO',self.at))
  sha=digest(encode(series).encode());return series,{'native_symbol':i.native_symbol,'timeframe':timeframe,'cutoff':cutoff,'source_response_sha256':sha,'receipt':{'received_at_utc':self.at,'response_sha256':sha}}
 def pulse(self,inventory,partial=False,kinds=('ticker','book','premium')):
  out=[]
  for k in kinds:
   self.record('binance_'+k)
   obs=[]
   if k=='book':
    self.books+=1
    for i in inventory.instruments:
     p=D('95.4') if i.native_symbol.startswith('BEAR') else D('106.2') if i.native_symbol=='DDDUSDT' else D('104.6')
     if i.native_symbol=='AAAUSDT':p+=self.point_shift
     obs.append({'native_symbol':i.native_symbol,'values':{'bid':p-D('.01'),'ask':p+D('.01'),'spread_bps':D(2)},'source_time_utc':self.at,'received_at_utc':self.at,'source_response_sha256':'BOOKFIXTURE'})
   out.append({'kind':k,'observations':obs})
  return out

 def request(self,endpoint,*,query):
  from researcher.transport import Response,ProviderError
  if endpoint!='binance_depth':raise ProviderError('SOURCE_UNQUALIFIED')
  n=query['symbol'];p=D('95.4') if n.startswith('BEAR') else D('106.2') if n=='DDDUSDT' else D('104.6')
  if n=='AAAUSDT':p+=self.point_shift
  data={'T':int(utc(self.at).timestamp()*1000),'bids':[[str(p-D('.01')),'1000']],
    'asks':[[str(p+D('.01')),'1000']]}
  raw=encode(data).encode();receipt={'received_at_utc':self.at,'response_sha256':digest(raw),
    'elapsed_ms':1,'response_bytes':len(raw),'requested_query':query}
  self.record(endpoint,receipt)
  return Response(raw,{},receipt)

 def record(self,endpoint,receipt=None):
  from researcher.contracts import ContractError
  if len(self.http.receipts)>=self.http_limit:raise ContractError('REQUEST_BUDGET_EXHAUSTED')
  self.http.receipts.append(receipt or {'endpoint':endpoint,'received_at_utc':self.at,
    'response_sha256':digest((endpoint+self.at).encode()),'elapsed_ms':1,'response_bytes':100})

 def inventory(self):
  self.record('binance_inventory')
  from dataclasses import replace
  inv=super().inventory()
  rules=({'filterType':'LOT_SIZE','minQty':'.001','maxQty':'10000','stepSize':'.001'},
    {'filterType':'MIN_NOTIONAL','notional':'5'})
  return replace(inv,instruments=tuple(replace(i,quantity_rules={'LOT_SIZE':rules[0]},exchange_rules=rules)
    for i in inv.instruments))


class ScenarioScreen:
 """Provider-shaped scalar rows, validated by the real PartitionEngine."""
 def __init__(self,api,client):self.api=api;self.client=client;self.calls=[]
 def screen(self,names,spec):
  from researcher.core import EXPORT_SCALE
  self.calls.append((names,spec));cols=spec.columns
  values={'atr_explicit':D(2),'width16':D('.01'),'quiet_percentile':D('.1'),
   'efficiency16':D('.2'),'progress16':D('1.01'),'prior_high16':D(108),
   'prior_low16':D(98),'upper_distance':D('.02'),'lower_distance':D('.02'),
   'tr_fraction':D('.01'),'displacement':D(1),'body_fraction':D('.5'),
   'pressure_upper':D(1),'pressure_lower':D(0),'close':D(100),'quote_rvol32':D(2)}
  at=self.api.at;tf=spec.timeframe;end=int(utc(at).timestamp())//WIDTHS[tf]*WIDTHS[tf]
  rules=[{'id':f'r{j}','left':{'kind':'formula','expression':c[1]},'operator':'atOrAbove',
    'right':{'kind':'constant','value':0}} for j,c in enumerate(cols)]
  rows=[{'symbol':n,'last':100,'observationTime':end-WIDTHS[tf],
    'values':[{'ruleId':f'r{j}','left':float(values[c[0]]*EXPORT_SCALE),'right':0,'matched':True}
      for j,c in enumerate(cols)]} for n in names]
  data={'exchange':'binance','market':'futures','quote':'USDT','timeframe':tf,
   'screened':len(names),'evaluated':len(names),'matched':len(names),'couldNotEvaluate':0,
   'returned':len(names),'truncated':False,'rules':rules,'results':rows}
  raw=encode(data).encode();receipt={'received_at_utc':at,'response_sha256':digest(raw),
    'elapsed_ms':1,'response_bytes':len(raw),'schema_sha256':'OFFLINE_SCHEMA','request_dispatched':True}
  self.client.http.receipts.append(receipt)
  return data,receipt
