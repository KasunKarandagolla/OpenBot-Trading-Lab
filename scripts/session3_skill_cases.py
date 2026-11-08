import json,hashlib
from pathlib import Path
import pandas as pd
from trading_lab.panel import ArchivePanel
from local_recovery_convert import aggregate
from trading_lab.panel import ROOT
import argparse
a=argparse.ArgumentParser(description='Export four source-only skill cases without recommendations or outcomes')
a.add_argument('--plans',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
r=ROOT;doc=json.loads(args.plans.read_text());p=ArchivePanel()
selected=[]
for family in ['BREAKOUT_RETEST','SWEEP_RECLAIM']:
 for side in ['long','short']:
  found=next((q for q in doc['plans'] if q['family']==family and q['side']==side and q['diagnostics']=='GEOMETRY_PASS_RESEARCH_ONLY'),None)
  if found:selected.append(found)
out=args.out;out.mkdir(parents=True)
manifest=[]
for number,case in enumerate(selected,1):
 at=pd.Timestamp(case['decision_at']);symbol=case['symbol'];series={}
 for tf,count in [('1h',720),('15m',144),('5m',144)]:
  f=p.frame(symbol,tf);f=f.loc[f.date+pd.Timedelta(tf)<=at].tail(count)
  series[tf]=[dict(open_ms=int(x.date.value//1_000_000),available_ms=int((x.date+pd.Timedelta(tf)).value//1_000_000),open=float(x.open),high=float(x.high),low=float(x.low),close=float(x.close),volume=float(x.volume)) for x in f.itertuples()]
 hour=p.frame(symbol,'1h');hour=hour.loc[hour.date+pd.Timedelta(hours=1)<=at];f=aggregate(hour,'4h');f=f.loc[f.components.eq(4)].tail(120)
 series['4h']=[dict(open_ms=int(x.date.value//1_000_000),available_ms=int((x.date+pd.Timedelta(hours=4)).value//1_000_000),open=float(x.open),high=float(x.high),low=float(x.low),close=float(x.close),volume=float(x.volume)) for x in f.itertuples()]
 value=dict(case_id=f'F{number}',venue=p.venue,symbol=symbol,cutoff=case['decision_at'],source_id=p.identity,source_fidelity='CHECKSUM_VERIFIED_ARCHIVE_OHLCV',
            watch_definition={k:case[k] for k in ['family','side','armed_at','boundary','boundary_known_at']},numeric=series,known_inputs='No native account/Risk, spread or genuine flow; public candle-based research only',
            evaluation='Source-only preselected developing/trigger case; do not infer correctness or native authority. No future bars, outcome, recommendation, stop, target or RR supplied.')
 path=out/f'F{number}.json';path.write_text(json.dumps(value,indent=2)+'\n')
 manifest.append(dict(case_id=value['case_id'],symbol=symbol,cutoff=value['cutoff'],input_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(manifest)
