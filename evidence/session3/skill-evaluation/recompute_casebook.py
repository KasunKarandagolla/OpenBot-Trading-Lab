import json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[3]
fields=['open','high','low','close','volume','quote_volume']
def frame(spec):
 bars=spec['bars'];f=pd.DataFrame([dict(date=pd.Timestamp(b[0],unit='ms',tz='UTC'),available=pd.Timestamp(b[6]+1,unit='ms',tz='UTC'),**dict(zip(fields,[float(b[k]) for k in [1,2,3,4,5,7]]))) for b in bars]);return f

def calc(f,width):
 f=f.copy();previous=f.close.shift();f['atr14']=pd.concat([f.high-f.low,(f.high-previous).abs(),(f.low-previous).abs()],axis=1).max(axis=1).rolling(14).mean();f['ema20']=f.close.ewm(span=20,adjust=False,min_periods=20).mean();f['ema50']=f.close.ewm(span=50,adjust=False,min_periods=50).mean();f['rvol']=f.volume/f.volume.shift().rolling(20).mean();p=[]
 for i in range(2,len(f)-2):
  w=f.iloc[i-2:i+3];at=f.iloc[i].date;known=f.iloc[i+2].available
  for name,kind in [('high','resistance'),('low','support')]:
   v=f.iloc[i][name]
   if (v==getattr(w[name],'max' if name=='high' else 'min')()) and int(w[name].eq(v).sum())==1:p.append(dict(kind=kind,price=float(v),pivot_at=at.isoformat(),known_at=known.isoformat()))
 return f,p

def brief(f,p):
 x=f.iloc[-1];return dict(last=x.date.isoformat(),known=x.available.isoformat(),close=x.close,ema20=x.ema20,ema50=x.ema50,atr14=x.atr14,rvol=x.rvol,last_bars=f.tail(8).astype({'date':str,'available':str}).round(8).to_dict('records'),recent_pivots=p[-10:])
(ROOT/'work/v3-forward-inputs').mkdir(parents=True,exist_ok=True)
results=[]
for key in ['B01','B02','B03','B04','B05','B06','B07','B08','B09','B10','B11','B12']:
 path=ROOT/'evidence/skills-v2/20261107/casebook/agent-inputs'/key/'input.json';raw=path.read_bytes();obj=json.loads(raw)
 d={k:obj[k] for k in ['case_id','cutoff_ms','symbol','venue','numeric','execution_authority','later_bars','source_limit']}
 out=ROOT/'work/v3-forward-inputs'/f'{key}.json';out.write_text(json.dumps(d,sort_keys=True))
 cutoff=pd.Timestamp(d['cutoff_ms'],unit='ms',tz='UTC');frames={}; pivots={}
 for tf in ['5m','15m','1h']:
  f=frame(d['numeric'][tf]);assert bool(f.available.le(cutoff).all());frames[tf],pivots[tf]=calc(f,tf)
 h=frames['1h'];g=h.groupby(h.date.dt.floor('4h'));q=g.agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum','quote_volume':'sum','date':'first'}).rename_axis('group').reset_index(drop=True);q['n']=g.size().to_numpy();q=q[q.n.eq(4)].drop(columns='n');q['available']=q.date+pd.Timedelta(hours=4);q=q[q.available.le(cutoff)].reset_index(drop=True);q,qp=calc(q,'4h')
 daily=h[h.available.le(cutoff.floor('D')) & h.date.ge(cutoff.floor('D')-pd.Timedelta(days=1))]
 results.append(dict(case=key,symbol=d['symbol'],cutoff=cutoff.isoformat(),input_sha256=hashlib.sha256(raw).hexdigest(),clean_input_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),source_limit=d['source_limit'],contexts={tf:brief(frames[tf],pivots[tf]) for tf in ['5m','15m','1h']},four_hour=brief(q,qp),prior_utc_day=dict(high=daily.high.max(),low=daily.low.min(),components=len(daily))))
(Path(__file__).resolve().parent/'recomputed-casebook-numeric.json').write_text(json.dumps(results,indent=2,allow_nan=False))
for r in results:
 if r['case'] not in ['B01','B02','B03','B06','B09','B11']:continue
 print('\nCASE',r['case'],r['symbol'],r['cutoff']);print('prior day',r['prior_utc_day'])
 for tf in ['four_hour','1h','15m','5m']:
  v=r['four_hour'] if tf=='four_hour' else r['contexts'][tf]
  print(tf,'close',v['close'],'ema20',v['ema20'],'ema50',v['ema50'],'ATR',v['atr14'],'rvol',v['rvol'])
  print('pivots',v['recent_pivots'][-5:])
  print('lastbars',[{k:b[k] for k in ['date','open','high','low','close']} for b in v['last_bars'][-6:]])
