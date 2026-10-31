"""Normalize a NEW download exactly as frozen acquisition did; preserve originals."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_data import inspect


def main():
    out=ROOT/'evidence/master-audit/source-identity.json'
    if out.exists():
        raise ValueError('preserve source check')
    manifest=json.loads((ROOT/'evidence/bonus/source-manifest.json').read_text())
    data=ROOT/'user_data/data/bonus/gate/futures'
    retained=ROOT/'work/master-native-downloaded'
    if retained.exists():
        raise ValueError('preserve original download')
    shutil.move(data,retained)
    data.mkdir()
    start=pd.Timestamp('2026-07-26',tz='UTC');end=pd.Timestamp('2026-10-30',tz='UTC')
    rows=[]
    for old in manifest['files']:
        path=ROOT/old['path'];source=retained/path.name
        frame=pd.read_feather(source)
        normalized=frame.loc[(frame.date>=start)&(frame.date<end)].reset_index(drop=True)
        normalized.to_feather(path)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        interval=28800 if old['candle_type']=='funding_rate' else 900 if old['timeframe']=='15m' else 3600
        report=inspect(normalized,interval,start,end,pd.Timestamp.now(tz='UTC'),old['candle_type']=='funding_rate')
        rows.append(dict(path=old['path'],source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                         normalized_sha256=digest,expected_sha256=old['sha256'],
                         exact_original_bytes=digest==old['sha256'],validation=report))
    result=dict(files=rows,exact_original_bytes=all(x['exact_original_bytes'] for x in rows),
                all_valid=all(not x['validation']['errors'] for x in rows),
                normalization='Same UTC end-exclusive trim and pandas.to_feather as original bonus_data.acquire; downloaded files retained separately')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))


if __name__=='__main__':
    main()
