"""Bounded deterministic assessments; future rows are masked before any feature calculation."""
import sys,math
from datetime import datetime,timezone
import pandas as pd
import numpy as np
from session3_common import *
sys.path[:0]=[str(ROOT/'research/session3'),str(ROOT/'user_data/strategies')]
from StructureAwareSweepV1 import StructureAwareSweepV1
from PlaybookRiskV1 import geometry,COST_ALLOWANCE
from causal_structure import closed_merge
from freqtrade.enums import CandleType

def utc(value):
 t=pd.Timestamp(value)
 if t.tzinfo is None:raise ValueError('explicit UTC timestamp required')
 if t.utcoffset().total_seconds()!=0:raise ValueError('timestamp must be UTC')
 if t>pd.Timestamp.now(tz='UTC'):raise ValueError('future as-of forbidden')
 return t

def finite(x):
 try:return float(x) if math.isfinite(float(x)) else None
 except (ValueError,TypeError):return None

def iso(x):return None if x is None or pd.isna(x) else pd.Timestamp(x).isoformat()

def analyze(base,hour,asof):
 # The only frames passed to indicators have completed rows at/before asof.
 for frame in [base,hour]:
  if not {'date','open','high','low','close','volume'}.issubset(frame.columns):raise ValueError('MISSING_SOURCE_COLUMNS')
  if not isinstance(frame.date.dtype,pd.DatetimeTZDtype) or str(frame.date.dt.tz)!='UTC' or frame.date.isna().any():raise ValueError('MISSING_OR_NON_UTC_CANDLE_TIMESTAMP')
 b=base.loc[base.date+pd.Timedelta(minutes=15)<=asof].copy().reset_index(drop=True)
 h=hour.loc[hour.date+pd.Timedelta(hours=1)<=asof].copy().reset_index(drop=True)
 for d,step in [(b,pd.Timedelta(minutes=15)),(h,pd.Timedelta(hours=1))]:
  if d.empty:raise ValueError('MISSING_COMPLETED_DATA')
  if d.date.duplicated().any() or not d.date.is_monotonic_increasing or not d.date.diff().dropna().eq(step).all():raise ValueError('DATA_GAP_OR_DUPLICATE')
  if (d.date.dt.as_unit('ns').astype('int64') % step.value != 0).any():raise ValueError('MISALIGNED_CANDLES')
  values=d[['open','high','low','close','volume']].to_numpy(dtype=float)
  if not np.isfinite(values).all() or (values[:,:4]<=0).any() or (values[:,4]<0).any():raise ValueError('INVALID_OHLCV')
  if ((d.high<d[['open','close','low']].max(axis=1)) | (d.low>d[['open','close','high']].min(axis=1))).any():raise ValueError('INVALID_OHLCV')
 if len(b)<240 or len(h)<240:raise ValueError('INSUFFICIENT_WARMUP')
 if asof-(b.date.iloc[-1]+pd.Timedelta(minutes=15))>=pd.Timedelta(minutes=15):raise ValueError('STALE_CANDLES')
 if asof-(h.date.iloc[-1]+pd.Timedelta(hours=1))>=pd.Timedelta(hours=1):raise ValueError('STALE_HOURLY')
 s=StructureAwareSweepV1({'candle_type_def':CandleType.FUTURES})
 h=s.populate_indicators_1h(h,{});f=closed_merge(b,h)
 return s.populate_entry_trend(s.populate_indicators(f,{}),{})

def rejected(symbol,asof,source,reason,dataset):
 return {'schema_version':1,'environment':'RESEARCH_ONLY','symbol':symbol,'as_of_utc':asof.isoformat(),'last_closed_candle_utc':None,'source':source|{'status':'UNKNOWN'},'structure':{'direction':'UNKNOWN','last_confirmed_swing':None,'last_bos':None,'last_choch':None},'setup':{'strategy_id':'StructureAwareSweepV1','direction':'NONE','entry_reference':None,'stop':None,'target':None,'expiry_utc':None,'estimated_net_reward_risk':None,'decision':'REJECT','reason_codes':[reason]},'provenance':{'dataset_id':dataset,'strategy_hash':sha(ROOT/'research/session3/StructureAwareSweepV1.py'),'features_known_at_utc':None},'price_unit':'USDT per base unit','rank_score':0.}

def assess(symbol,base,hour,asof,dataset,receipt=None,mode='historical',ticker=None):
 source={'venue':'gate','timeframe':'15m','context_timeframe':'1h','fidelity':'OHLCV','status':'VALID','received_at_utc':receipt,'venue_timestamp_utc':None,'assessment_mode':mode}
 if mode=='current':
  if ticker is None or ticker.get('venue_timestamp_ms') is None:return rejected(symbol,asof,source,'TICKER_TIMESTAMP_UNKNOWN',dataset)
  ts=pd.to_datetime(ticker['venue_timestamp_ms'],unit='ms',utc=True);source['venue_timestamp_utc']=ts.isoformat()
  if not -pd.Timedelta(seconds=5)<=asof-ts<=pd.Timedelta(seconds=60):return rejected(symbol,asof,source,'TICKER_STALE_OR_FUTURE',dataset)
 try:d=analyze(base,hour,asof)
 except ValueError as e:return rejected(symbol,asof,source,str(e),dataset)
 r=d.iloc[-1];known=r.date+pd.Timedelta(minutes=15)
 side='long' if r.enter_long==1 else 'short' if r.enter_short==1 else None
 g=geometry(r,side,float(r.close),.15) if side else None
 reasons=[]
 if not side:reasons.append(str(r.reason))
 if not side:
  if r.rvol<1.2:reasons.append('RELATIVE_VOLUME_BELOW_1_2')
  if r.adx_1h>30:reasons.append('HOURLY_ADX_ABOVE_PARENT_LIMIT')
  if r.struct_direction_1h not in ['UP','DOWN']:reasons.append('HOURLY_STRUCTURE_UNKNOWN')
  if r.reason=='STRUCTURAL_ELIGIBILITY':
   for label,active in [('low',r.parent_enter_long==1),('high',r.parent_enter_short==1)]:
    if active:
     level=r['prior_swing_'+label]
     if pd.isna(level):reasons.append('CONFIRMED_SWING_MISSING')
     elif abs(r['prior_'+label]-level)>.5*r.atr14:reasons.append('STRUCTURAL_LEVEL_BEYOND_0_5_ATR')
     if r.adx_1h>=25 and r.struct_direction_1h==('DOWN' if label=='low' else 'UP'):reasons.append('HOURLY_STRUCTURE_CONTRADICTORY')
 if side and asof-known>=pd.Timedelta(minutes=5):reasons.append('SIGNAL_EXPIRED');side=None;g=None
 obj=rejected(symbol,asof,source,'NO_SETUP',dataset);obj['source']=source
 obj['last_closed_candle_utc']=known.isoformat();obj['last_candle_open_utc']=r.date.isoformat()
 swings=[]
 for direction in ['low','high']:
  if pd.notna(r['swing_'+direction]):swings.append({'pivot_at':iso(r['swing_'+direction+'_pivot_at']),'known_at':iso(r['swing_'+direction+'_known_at']),'first_eligible_decision_at':iso(r['swing_'+direction+'_known_at']),'price':float(r['swing_'+direction]),'direction':direction.upper(),'confirmation_bars':2,'source_timeframe':'15m'})
 # Strict public wick-only labels also exclude closes beyond already-consumed
 # levels. Internal event flags suppress repeat breaks of those consumed levels.
 obj['structure']={'direction':r.struct_direction,'hourly_direction':r.struct_direction_1h,'hourly_known_at_utc':iso(r.struct_known_at_1h),'last_confirmed_swing':max(swings,key=lambda x:x['known_at']) if swings else None,'confirmed_swings':swings,'last_bos':iso(r.struct_last_bos_at),'last_choch':iso(r.struct_last_choch_at),'wick_high_excursion':bool(pd.notna(r.prior_swing_high) and r.high>r.prior_swing_high and r.close<=r.prior_swing_high),'wick_low_excursion':bool(pd.notna(r.prior_swing_low) and r.low<r.prior_swing_low and r.close>=r.prior_swing_low)}
 obj['features']={k:finite(r[k]) for k in ['vwap','ema20','ema50','ema20_1h','ema50_1h','adx_1h','atr14','atr_ratio','rvol','prior_low','prior_high','prior_swing_low','prior_swing_high']}
 obj['features']['hourly_candle_open_utc']=iso(r.date_1h)
 if g:
  fee=.0006;roi=g['target_roi'];rate=g['reference']
  target=rate*(1-fee)*(1-roi)/(1+fee) if side=='short' else rate*(1+fee)*(1+roi)/(1-fee)
  obj['setup']={'strategy_id':'StructureAwareSweepV1','direction':side.upper(),'entry_reference':rate,'stop':g['stop'],'target':target,'target_semantics':'Approximate native fee-adjusted ROI reference, excludes realized future funding; not a fill promise','expiry_utc':(known+pd.Timedelta(minutes=5)).isoformat(),'estimated_net_reward_risk':(roi-.0023)/(g['risk_fraction']+COST_ALLOWANCE),'admission_reward_risk':roi/(g['risk_fraction']+COST_ALLOWANCE),'decision':'ACCEPT','reason_codes':['CAUSAL_SWEEP_STRUCTURAL_ELIGIBILITY'],'cost_assumptions':{'native_fee_per_side':fee,'extra_roundtrip_friction':.002,'adverse_funding_allowance':.0003}}
 else:obj['setup']['reason_codes']=reasons or ['INVALID_GEOMETRY']
 obj['provenance']['features_known_at_utc']=known.isoformat()
 obj['provenance']['structure_module_hash']=sha(ROOT/'research/session3/causal_structure.py')
 obj['rank_score']=min(5.,finite(r.rvol) or 0.) if g else 0.
 validate_report(obj)
 return obj

def validate_report(obj):
 import jsonschema
 jsonschema.validate(obj,read(ROOT/'research/session3/opportunity.schema.json'))
 payload=json.dumps(obj,allow_nan=False)
 if len(payload)>20000 or any(x in payload for x in ['/lab/','api_key','api_secret','/runtime/']):raise ValueError('unsafe/oversized opportunity')
 if obj['setup']['decision']=='ACCEPT':
  s=obj['setup'];e=s['entry_reference']
  if obj['source']['status']!='VALID' or e is None or s['stop'] is None or s['target'] is None:raise ValueError('unknown data cannot be accepted')
  if not (s['stop']<e<s['target'] if s['direction']=='LONG' else s['target']<e<s['stop']):raise ValueError('invalid opportunity geometry')
  known=obj['provenance']['features_known_at_utc']
  if known is None or pd.Timestamp(known)>pd.Timestamp(obj['as_of_utc']):raise ValueError('future/unknown feature availability')
 return obj

def historical(cid,symbol,asof):
 c=cohort(cid)
 if symbol not in c['pairs']:raise ValueError('symbol outside registered cohort')
 # Inspect manifest identity; do not load future market rows into the feature function.
 m=read(destination(cid)/'source-data-manifest.json')
 if not m['valid_for_backtest'] or m['cohort']!=c:raise ValueError('invalid manifest')
 frames={}
 for tf in ['15m','1h']:
  r=next(f for f in m['files'] if f['symbol']==symbol and f['timeframe']==tf and f['candle_type']=='futures')
  p=ROOT/r['path']
  if sha(p)!=r['sha256']:raise ValueError('source hash mismatch')
  # Arrow predicate filters at the storage boundary before pandas indicators.
  import pyarrow.dataset as ds
  step=pd.Timedelta(minutes=15) if tf=='15m' else pd.Timedelta(hours=1)
  table=ds.dataset(p,format='ipc').to_table(filter=ds.field('date')<=asof-step)
  frames[tf]=table.to_pandas()
 return assess(symbol,frames['15m'],frames['1h'],asof,cid,m['received_at_utc'])

def current():
 # Read existing scanner output; no second screener and no historical membership claim.
 scan=read(OUT/'scanner-snapshot.json');now=pd.Timestamp.now(tz='UTC')
 if scan.get('exchange')!='gate' or scan.get('schema')!='scan-v1':raise ValueError('scanner source/schema mismatch')
 age=now-utc(scan['as_of_utc'])
 if not pd.Timedelta(0)<=age<=pd.Timedelta(minutes=5):raise ValueError('scanner snapshot stale; run existing scanner into Session3 isolated capture')
 from public_exchange import public_exchange
 e=public_exchange();markets=e.load_markets();out=[]
 for candidate in scan['shortlisted'][:5]:
  symbol=candidate['symbol'];m=markets.get(symbol,{})
  if not (m.get('active') and m.get('swap') and m.get('linear') and m.get('settle')=='USDT'):
   out.append(rejected(symbol,now,{'venue':'gate','timeframe':'15m','fidelity':'OHLCV'},'CONTRACT_IDENTITY_UNKNOWN','current-scanner'));continue
  frames={}
  for tf,ms in [('15m',900000),('1h',3600000)]:
   raw=e.fetch_ohlcv(symbol,tf,since=int((now-pd.Timedelta(hours=250)).timestamp()*1000),limit=1000)
   d=pd.DataFrame(raw,columns=['date','open','high','low','close','volume']);d['date']=pd.to_datetime(d.date,unit='ms',utc=True);frames[tf]=d
  at=pd.Timestamp.now(tz='UTC')
  out.append(assess(symbol,frames['15m'],frames['1h'],at,'current-scanner',at.isoformat(),'current',candidate))
 return sorted(out,key=lambda x:(-int(x['setup']['decision']=='ACCEPT'),-x['rank_score'],x['symbol']))
