"""Completed UTC4h map; pivot availability is never moved to its center bar."""
import numpy as np
import pandas as pd
import talib.abstract as ta
from causal_structure import structure

def four_hour_map(hours):
    h=hours.copy().sort_values('date')
    h['date']=pd.to_datetime(h.date,utc=True)
    if h.empty:return pd.DataFrame(columns=['known4h','map4h_ready','map4h_reason'])
    h['_group']=h.date.dt.floor('4h')
    grid=pd.date_range(h._group.min(),h._group.max(),freq='4h',tz='UTC')
    rows=[]
    for start in grid:
        q=h.loc[h._group.eq(start)];expected=pd.date_range(start,periods=4,freq='h')
        stamps=pd.DatetimeIndex(q.date)
        if stamps.duplicated().any():reason='DUPLICATE_SOURCE_HOUR'
        elif len(q)!=4 or not stamps.equals(expected):reason='GAP_OR_PARTIAL_4H'
        elif not np.isfinite(q[['open','high','low','close','volume']]).all().all():reason='INVALID_SOURCE_HOUR'
        elif not ((q.low>0)&(q.volume>=0)&(q.low<=q[['open','close']].min(axis=1))&(q.high>=q[['open','close']].max(axis=1))).all():reason='INVALID_SOURCE_OHLC'
        else:reason='COMPLETE'
        good=reason=='COMPLETE'
        rows.append(dict(date=start,open=float(q.open.iloc[0]) if good else np.nan,
            high=float(q.high.max()) if good else np.nan,low=float(q.low.min()) if good else np.nan,
            close=float(q.close.iloc[-1]) if good else np.nan,volume=float(q.volume.sum()) if good else np.nan,
            input4h_valid=good,input4h_reason=reason))
    f=pd.DataFrame(rows);f=structure(f,'4h')
    f['bias4h']=ta.EMA(f,timeperiod=20)-ta.EMA(f,timeperiod=50) # telemetry only
    runs=f.input4h_valid.astype(int).groupby((~f.input4h_valid).cumsum()).cumsum()
    f['map4h_ready']=f.input4h_valid & runs.ge(5)
    f['map4h_reason']=np.where(f.map4h_ready,'READY',np.where(f.input4h_valid,'PIVOT_WINDOW_WARMUP',f.input4h_reason))
    f['known4h']=f.date+pd.Timedelta(hours=4)
    return f.rename(columns={c:c+'_4h' for c in f if c.startswith(('swing_','prior_swing_','struct_'))})
