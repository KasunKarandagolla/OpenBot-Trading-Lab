"""Owner-invoked registered native comparison; no trading or resident service."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import time
from trading_lab.panel import ROOT,ArchivePanel
from session3_gate import qualify
from session3_verify import audit

JOBS=[
 ('BreakoutAcceptanceRetest','2026-08-01','2026-08-08','final-w1-breakout','w1-retest','through'),
 ('SweepReclaimReversal','2026-08-01','2026-08-08','final-w1-reversal','w1-retest','through'),
 ('BreakoutAcceptanceRetest','2026-08-08','2026-08-15','final-w2-breakout','w2-retest','through'),
 ('SweepReclaimReversal','2026-08-08','2026-08-15','final-w2-reversal','w2-retest','through'),
 ('BreakoutImmediate','2026-08-01','2026-08-08','final-w1-immediate','w1-immediate','through'),
 ('SweepReclaimEarly','2026-08-01','2026-08-08','final-w1-early','w1-early','through'),
 ('BreakoutAcceptanceRetest','2026-08-01','2026-08-08','final-w1-breakout-touch','w1-retest','touch'),
 ('SweepReclaimReversal','2026-08-01','2026-08-08','final-w1-reversal-touch','w1-retest','touch'),
 ('TrendPullbackBaselineV1','2026-08-01','2026-08-08','final-w1-trend',None,'through'),
 ('VWAPTrendContinuationV1','2026-08-01','2026-08-08','final-w1-vwap',None,'through'),
 ('LiquiditySweepReversalV1','2026-08-01','2026-08-08','final-w1-sweep',None,'through'),
 ('TrendPullbackBaselineV1','2026-08-08','2026-08-15','final-w2-trend',None,'through'),
 ('VWAPTrendContinuationV1','2026-08-08','2026-08-15','final-w2-vwap',None,'through'),
 ('LiquiditySweepReversalV1','2026-08-08','2026-08-15','final-w2-sweep',None,'through'),
]


def commands(root):
    root=Path(root).absolute()
    if any(p.is_symlink() for p in [root,*root.parents]) or not root.is_relative_to(ROOT/'evidence/session3'):
        raise ValueError('DEDICATED_SESSION3_EVIDENCE_ROOT_REQUIRED')
    rel=root.relative_to(ROOT)
    return [(job,['bash','scripts/lab-session3.sh','native',job[0],job[1],job[2],'/lab/'+str(rel/job[3]),
                  '/lab/'+str(rel/'registered-final'/job[4]/'plans.json') if job[4] else '',job[5]]) for job in JOBS]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--describe',action='store_true');a=p.parse_args()
    root=a.root.absolute();jobs=commands(root)
    if a.describe:print(json.dumps([cmd for _,cmd in jobs],indent=2));raise SystemExit(0)
    for job,_ in jobs:
        if (root/job[3]).exists():raise ValueError('PRESERVE_NATIVE_RESULT_USE_NEW_ROOT')
    panel=ArchivePanel()
    for phase in ['w1-retest','w1-immediate','w1-early','w2-retest']:
        folder=root/'registered-final'/phase;value=qualify(json.loads((folder/'plans.json').read_text()),panel)
        destination=folder/'risk-diagnostics.json'
        if destination.exists() and json.loads(destination.read_text())!=value:raise ValueError('RISK_DIAGNOSTIC_DRIFT')
        destination.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    def run(item):
        job,cmd=item;label=job[3];begin=time.perf_counter()
        with (root/(label+'-stdout.txt')).open('w') as stream:
            result=subprocess.run(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,env=os.environ.copy())
        (root/(label+'-exit-code.txt')).write_text(str(result.returncode)+'\n')
        if result.returncode==0:audit(root/label)
        print(label,result.returncode,flush=True)
        return dict(command=cmd,exit_code=result.returncode,wall_seconds=time.perf_counter()-begin)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(run,jobs))
    (root/'native-matrix-commands.json').write_text(json.dumps(values,indent=2)+'\n')
    if any(x['exit_code'] for x in values):raise SystemExit(1)
