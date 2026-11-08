import json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
R=Path(__file__).resolve().parent
manifest={x['case_id']:x for x in json.loads((R/'source-only-inputs/manifest.json').read_text())}

def features(rows,tf):
 f=pd.DataFrame(rows);f['date']=pd.to_datetime(f.open_ms,unit='ms',utc=True);f['at']=pd.to_datetime(f.available_ms,unit='ms',utc=True)
 prev=f.close.shift();f['atr14']=pd.concat([f.high-f.low,(f.high-prev).abs(),(f.low-prev).abs()],axis=1).max(axis=1).rolling(14).mean();f['ema20']=f.close.ewm(span=20,adjust=False,min_periods=20).mean();f['ema50']=f.close.ewm(span=50,adjust=False,min_periods=50).mean();f['rvol']=f.volume/f.volume.shift().rolling(20).mean();return f

def active_pivots(f,at):
 f=f[f['at'].le(at)].reset_index(drop=True);levels=[]
 for i in range(2,len(f)-2):
  pivot=f.iloc[i]; w=f.iloc[i-2:i+3];known=f.iloc[i+2]['at']
  for col,kind in [('high','resistance'),('low','support')]:
   val=float(pivot[col]); ex=w[col].max() if col=='high' else w[col].min()
   if val!=ex or int(w[col].eq(val).sum())!=1:continue
   later=f[f['at']>known]
   consumed=later[later.close.gt(val) if col=='high' else later.close.lt(val)]
   levels.append(dict(kind=kind,price=val,pivot_at=pivot.date.isoformat(),known_at=known.isoformat(),consumed_at=None if consumed.empty else consumed.iloc[0]['at'].isoformat()))
 return levels

def structure_direction(f,at):
 # Independent sequential strict pivots and close-only breaks of last-known active levels.
 f=f[f['at'].le(at)].reset_index(drop=True);direction='UNKNOWN';levels={};events=[]
 for j in range(len(f)):
  row=f.iloc[j]
  up='high' in levels and not levels['high']['consumed'] and row.close>levels['high']['price']
  down='low' in levels and not levels['low']['consumed'] and row.close<levels['low']['price']
  if up!=down:
   side='high' if up else 'low';new='UP' if up else 'DOWN';events.append(dict(at=row['at'].isoformat(),type='INITIAL_BREAK' if direction=='UNKNOWN' else 'BOS' if direction==new else 'CHOCH',direction=new,level=levels[side]));direction=new;levels[side]['consumed']=True
  if j>=4:
   w=f.iloc[j-4:j+1];p=f.iloc[j-2]
   for col in ['high','low']:
    v=float(p[col]);extreme=w[col].max() if col=='high' else w[col].min()
    if v==extreme and int(w[col].eq(v).sum())==1:levels[col]=dict(price=v,known_at=row['at'].isoformat(),consumed=False)
 return direction,events[-8:]

results=[]
for key in ['F1','F2','F3','F4']:
 p=R/'source-only-inputs'/f'{key}.json';raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==manifest[key]['input_sha256'];d=json.loads(raw);cut=pd.Timestamp(d['cutoff']);arm=pd.Timestamp(d['watch_definition']['armed_at']);frames={tf:features(rows,tf) for tf,rows in d['numeric'].items()}
 for tf,f in frames.items():
  width=pd.Timedelta(tf);assert bool(f['at'].le(cut).all()) and bool(f['at'].eq(f.date+width).all()) and bool(f.date.diff().iloc[1:].eq(width).all())
 h=frames['1h'];prior=h[h['at'].le(arm-pd.Timedelta(hours=1))].tail(24);hr=h[h['at'].le(arm)].iloc[-1];side=d['watch_definition']['side'];sign=1 if side=='long' else -1
 all_levels=[]
 for tf in ['1h','4h']:
  for lev in active_pivots(frames[tf],arm):
   lev['timeframe']=tf;all_levels.append(lev)
 active=[x for x in all_levels if x['consumed_at'] is None and pd.Timestamp(x['known_at'])>=arm-pd.Timedelta(days=7)]
 relevant=[x for x in active if x['kind']==('resistance' if side=='long' else 'support')]
 recent=frames['5m'][frames['5m']['at'].gt(arm)]
 contexts={tf:dict(close=float(frames[tf].iloc[-1].close),ema20=float(frames[tf].iloc[-1].ema20),ema50=float(frames[tf].iloc[-1].ema50),atr14=float(frames[tf].iloc[-1].atr14),rvol=float(frames[tf].iloc[-1].rvol),known_at=frames[tf].iloc[-1]['at'].isoformat()) for tf in ['1h','4h','15m','5m']}
 direction,events=structure_direction(h,arm)
 r=dict(case_id=key,symbol=d['symbol'],cutoff=d['cutoff'],input_sha256=hashlib.sha256(raw).hexdigest(),watch=d['watch_definition'],atr1h_armed=float(hr.atr14),arming_1h_ema20=float(hr.ema20),arming_1h_ema50=float(hr.ema50),arming_1h_structure=direction,structure_events_at_arm=events,prior24h=dict(high=float(prior.high.max()),low=float(prior.low.min()),midpoint=float((prior.high.max()+prior.low.min())/2),first=prior.iloc[0].date.isoformat(),known_at=prior.iloc[-1]['at'].isoformat()),contexts=contexts,active_relevant_pivots=relevant,all_pivots=all_levels,trigger_bars=[{k:(x[k].isoformat() if k in ['date','at'] else float(x[k])) for k in ['date','at','open','high','low','close','volume','rvol']} for x in recent.to_dict('records')]);results.append(r)
 print('\nCASE',key,r['symbol'],r['cutoff'],r['watch'],'ATR',r['atr1h_armed']);print('map',contexts,'arm_structure',direction,'range',r['prior24h']);print('ACTIVE RELEVANT',relevant)
 print('TRIGGER BARS',r['trigger_bars'])
(R/'recomputed-additional-numeric.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
