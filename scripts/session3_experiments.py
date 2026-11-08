"""Run the registered v3 windows/entry variants with one verified source/feature cache."""
import argparse
import json
from pathlib import Path
import time
import pandas as pd
from trading_lab.panel import ArchivePanel
from trading_lab.rehearsal import scan,experiments
from local_recovery_data import write_json

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);a=p.parse_args()
    if a.out.exists():raise ValueError('PRESERVE_EXPERIMENT_DIRECTORY')
    a.out.mkdir(parents=True)
    panel=ArchivePanel();times=[]
    panel.feature_window=(pd.Timestamp('2026-08-01T00:00Z')-pd.Timedelta(days=40),pd.Timestamp('2026-08-15T00:00Z'))
    # Cold/warm scans on exactly the same snapshot; cached work changes no result.
    start=time.perf_counter();first=scan(panel,'2026-08-01T12:00Z');cold=time.perf_counter()-start
    start=time.perf_counter();second=scan(panel,'2026-08-01T12:00Z');warm=time.perf_counter()-start
    assert first==second
    write_json(a.out/'broad-scan.json',first)
    write_json(a.out/'efficiency.json',dict(cold_seconds=cold,warm_seconds=warm,same_snapshot_output_equal=True,
               metrics=panel.metrics.copy(),charts=0,native_agent_requests=0,model_requests='NOT_MEASURED',scope='Within-process feature cache; not a live HTTP or native-agent latency comparison'))
    for window,(begin,end) in enumerate([('2026-08-01','2026-08-08'),('2026-08-08','2026-08-15')],1):
        for variant in (['retest','immediate','early'] if window==1 else ['retest']):
            result=experiments(panel,begin,end,a.out/f'w{window}-{variant}',variant)
            print(json.dumps(result),flush=True)
