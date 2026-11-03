"""Source availability and exact decision/input reconciliation; no missing rows invented."""
import pandas as pd
import numpy as np
from recovery_common import *

def report():
    old=read(ROOT/'evidence/session4/run-001/data-manifest.json')['files'];rows=[]
    for r in old:
        p=DATA/'development/gate/futures'/Path(r['path']).name
        if not p.exists():continue
        f=pd.read_feather(p)
        rows.append(dict(parent_path=r['path'],parent_sha256=r['sha256'],reacquired_path=str(p.relative_to(ROOT)),
            reacquired_sha256=sha(p),byte_equal=sha(p)==r['sha256'],parent_rows=r['rows'],reacquired_rows=len(f),
            first=str(f.date.min()),last=str(f.date.max()),duplicate_rows=int(f.date.duplicated().sum()),
            original_raw_rows_available=False,row_level_ohlcv_volume_mark_differences='UNCOMPUTABLE_WITHOUT_ORIGINAL_ARCHIVE',
            funding_clocks='ACTUAL_SECOND_OFFSET_EVENTS_PRESERVED;parent manifest reports canonical hour boundaries' if 'funding_rate' in p.name else None))
    correlations={}
    for w in ['development','hourly-independent']:
        d={}
        for pair in pairs():
            q=pd.read_feather(DATA/w/'gate/futures'/(slug(pair)+'-1h-futures.feather')).set_index('date').close
            d[pair]=q.resample('D').last().pct_change()
        corr=pd.DataFrame(d).corr().to_numpy();v=corr[np.triu_indices_from(corr,1)]
        correlations[w]=dict(markets=len(d),mean_pairwise_daily_return_correlation=float(np.nanmean(v)),
            min=float(np.nanmin(v)),max=float(np.nanmax(v)),warning='Correlated markets and overlapping opportunities do not multiply independent sample size.')
    replay={}
    for mode in ['reference','structure']:
        path=OUT/'native/development'/('parent-'+mode+'-plans-fixed-touch-fee750')/'result.json'
        if not path.exists():continue
        old=read(ROOT/'evidence/session4/run-001/native-results'/(mode+'.json'))['strategy']['Session4Replay']['trades']
        new=next(iter(read(path)['strategy'].values()))['trades']
        a={(t['pair'],t['open_date']):t for t in old};b={(t['pair'],t['open_date']):t for t in new}
        common=set(a)&set(b)
        replay[mode]=dict(parent_fills=len(a),new_fills=len(b),shared_entries=len(common),
            parent_only=[list(k) for k in sorted(set(a)-set(b))],new_only=[list(k) for k in sorted(set(b)-set(a))],
            same_quantity_and_entry_price=sum(abs(a[k]['amount']-b[k]['amount'])<1e-12 and a[k]['open_rate']==b[k]['open_rate'] for k in common),
            same_exit_price_clock=sum(a[k]['close_rate']==b[k]['close_rate'] and a[k]['close_date']==b[k]['close_date'] for k in common),
            parent_native_net=sum(t['profit_abs'] for t in old),new_native_net=sum(t['profit_abs'] for t in new),
            funding_difference_shared=sum((b[k].get('funding_fees') or 0)-(a[k].get('funding_fees') or 0) for k in common),
            note='Exact parent decision-plan hashes restored;raw sources/feature caches independently reacquired. Counts alone cannot prove complete source-row identity.')
    sources={}
    for w in ['development','independent','hourly-independent']:
        p=OUT/('data-'+w+'.json')
        if p.exists():
            files=read(p)['files'];sources[w]=dict(files=len(files),rows=sum(x['rows'] for x in files),sha256=sha(p))
    write(OUT/'source-reconciliation.json',dict(at=now(),parent_archive_provided=False,parent_sources_overwritten=False,
        original_manifest_preserved=True,files=rows,source_coverage=sources,correlations=correlations,parent_decision_replay=replay,
        future_holdout_acquired=False,binance_prices_used=False,
        blockers=read(OUT/'hourly-freeze.json')['reason']))

if __name__=='__main__':report()
