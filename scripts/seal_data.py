"""Restrict native downloads to the frozen UTC sample; never fills or alters candles."""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
root=Path('/lab')
protocol=json.loads((root/'research/protocol.json').read_text())
a,b=protocol['download_timerange'].split('-')
start=pd.to_datetime(a,format='%Y%m%d',utc=True);end=pd.to_datetime(b,format='%Y%m%d',utc=True)
rows=[]
for p in sorted((root/'user_data/data/research/gate').rglob('*.feather')):
    before=hashlib.sha256(p.read_bytes()).hexdigest();df=pd.read_feather(p)
    dates=pd.to_datetime(df.date,utc=True)
    sample=df.loc[(dates>=start)&(dates<end)].reset_index(drop=True)
    row={'path':str(p.relative_to(root)),'native_download_sha256':before,'native_rows':len(df),
         'discarded_before_start':int((dates<start).sum()),'discarded_at_or_after_end':int((dates>=end).sum()),
         'retained_rows':len(sample),'action':'UTC range restriction only; no filling, interpolation, duplicate removal or OHLCV edits'}
    if len(sample)!=len(df):sample.to_feather(p)
    row['sample_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();rows.append(row)
(root/'evidence/session-1/download-receipt.json').write_text(json.dumps({'sealed_utc':datetime.now(timezone.utc).isoformat(),'files':rows},indent=2)+'\n')
print('Sealed native observations to predeclared range. No missing bars repaired.')
