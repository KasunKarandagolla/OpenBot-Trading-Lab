"""Restore absent test-source copies only when original manifest hashes match."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def main():
    manifest=json.loads((ROOT/'evidence/bonus/source-manifest.json').read_text())
    lookup={(r['symbol'],r['timeframe'],r['candle_type']):r for r in manifest['files']}
    rows=[]
    for name in ['evidence/session-1/market-data-manifest.json','evidence/session-2/source-data-manifest.json',
                 'evidence/session-3/cohorts/s3-development-v1/source-data-manifest.json',
                 'evidence/session-3/cohorts/s3-transfer-v1/source-data-manifest.json']:
        for old in json.loads((ROOT/name).read_text()).get('files',[]):
            row=lookup.get((old.get('symbol'),old.get('timeframe'),old.get('candle_type')))
            if row and row['sha256']==old.get('sha256'):
                source=ROOT/row['path'];destination=ROOT/old['path']
                assert hashlib.sha256(source.read_bytes()).hexdigest()==old['sha256']
                if destination.exists():
                    assert hashlib.sha256(destination.read_bytes()).hexdigest()==old['sha256']
                else:
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(source,destination)
                rows.append(dict(path=old['path'],exact_match=True))
    destination=ROOT/'evidence/master-audit/test-source-restoration.json'
    if destination.exists():
        assert json.loads(destination.read_text())==rows
    else:destination.write_text(json.dumps(rows,indent=2)+'\n')
    print(len(rows),'exact source copies')


if __name__=='__main__':main()
