"""Feature-level parent/structural decisions; distinct from fills and admissions."""
import csv
import pandas as pd
from session3_common import *
from data_session3 import verify
from opportunity3 import analyze

def census(cid):
 frozen();m=verify(cid);c=cohort(cid);out=destination(cid)
 start=pd.to_datetime(c['evaluation_timerange'].split('-')[0],format='%Y%m%d',utc=True);end=pd.to_datetime(c['evaluation_timerange'].split('-')[1],format='%Y%m%d',utc=True)
 rows=[];counts={}
 for symbol in c['pairs']:
  files={tf:next(r for r in m['files'] if r['symbol']==symbol and r['timeframe']==tf and r['candle_type']=='futures') for tf in ['15m','1h']}
  base=pd.read_feather(ROOT/files['15m']['path']);hour=pd.read_feather(ROOT/files['1h']['path'])
  d=analyze(base,hour,end);d=d.loc[(d.date+pd.Timedelta(minutes=15)>=start)&(d.date+pd.Timedelta(minutes=15)<end)]
  counts[symbol]={'parent_signal_long':int(d.parent_enter_long.sum()),'parent_signal_short':int(d.parent_enter_short.sum()),'advanced_signal_long':int(d.enter_long.sum()),'advanced_signal_short':int(d.enter_short.sum()),'advanced_reason_counts':{str(k):int(v) for k,v in d.reason.value_counts().items()}}
  selected=d.loc[(d.candidate_long+d.candidate_short+d.parent_enter_long+d.parent_enter_short)>0]
  for _,r in selected.iterrows():
   rows.append({'symbol':symbol,'signal_open_utc':r.date.isoformat(),'known_at_utc':(r.date+pd.Timedelta(minutes=15)).isoformat(),'expiry_utc':(r.date+pd.Timedelta(minutes=20)).isoformat(),'parent_long':int(r.parent_enter_long),'parent_short':int(r.parent_enter_short),'advanced_long':int(r.enter_long),'advanced_short':int(r.enter_short),'reason':r.reason,'hourly_structure':r.struct_direction_1h,'hourly_adx':float(r.adx_1h),'relative_volume':float(r.rvol),'close_reference_usdt':float(r.close),'atr_quote_units':float(r.atr14)})
 fields=['symbol','signal_open_utc','known_at_utc','expiry_utc','parent_long','parent_short','advanced_long','advanced_short','reason','hourly_structure','hourly_adx','relative_volume','close_reference_usdt','atr_quote_units']
 with (out/'candidate-ledger.csv').open('w') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
 obj={'schema_version':1,'environment':'RESEARCH_ONLY','cohort_id':cid,'counts':counts,'ledger_rows':len(rows),'source_manifest_sha256':sha(out/'source-data-manifest.json'),'strategy_sha256':sha(ROOT/'research/session3/StructureAwareSweepV1.py'),'definitions':'Completed signal eligible at open+15m; decision times >=start and <end. Candidate ledger includes parent raw setup candidates, geometry failures and structural rejections; all other bars aggregated by reason. Not counts of canceled orders or hypothetical fills. Native slot/callback rejections and fills overlap; do not add them.'}
 write(out/'signal-census.json',obj);print(json.dumps(obj,indent=2))
