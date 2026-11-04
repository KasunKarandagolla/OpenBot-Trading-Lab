from setup_common import *
from recovery_data import client
import pandas as pd
ex=client();results=[]
for start in ['2026-08-31T12:00:00Z','2026-11-02T12:00:00Z']:
 a=pd.Timestamp(start);b=a+pd.Timedelta(minutes=1)
 try:
  raw=ex.public_futures_get_settle_trades(dict(settle='usdt',contract='BTC_USDT',**{'from':int(a.timestamp()),'to':int(b.timestamp()),'limit':1000}))
  file=DATA/('tape-probe-'+a.strftime('%Y%m%d')+'.json');write(file,raw)
  results.append(dict(start=a.isoformat(),end=b.isoformat(),rows=len(raw),sha256=sha(file),coverage='UNKNOWN_CAPPED_RESPONSE_NO_COMPLETE_SESSION_CLAIM'))
 except Exception as e:results.append(dict(start=a.isoformat(),end=b.isoformat(),status='UNAVAILABLE',error=str(e)))
write(OUT/'historical-tape-probe.json',dict(results=results,source='GATE_PUBLIC_FUTURES_TRADES_FROM_TO',calls=2,full_historical_profile='NOT_TESTED',note='Two boundedminute probes;no complete8h/day reference tape was obtained'))
print(results)
