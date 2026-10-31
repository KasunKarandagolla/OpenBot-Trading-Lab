"""Run the eight registered development comparisons with native Freqtrade."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NAMES=['VWAPTrendContinuationV1','LiquiditySweepReversalV1','RouterOnlyV1',
       'AuditRankingVWAPV1','AuditRankingSweepV1','AuditRegimeOnlyM0V1',
       'AuditStructuralCloseM0V1','AuditNearestObjectiveM0V1',
       'AuditRegimeVWAPV1','AuditRegimeSweepV1']


def main():
    resume='--resume' in sys.argv
    supplement=ROOT/'evidence/master-audit/ablation-attribution-supplement.json'
    registration=json.loads((supplement if supplement.exists() else ROOT/'evidence/master-audit'/('ablation-mechanical-amendment.json' if resume else 'ablation-registration.json')).read_text())
    for path,digest in registration['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('registered source changed: '+path)
    out=ROOT/'evidence/master-audit/native-results'
    out.mkdir(exist_ok=resume)
    rows=json.loads((out/'summary.json').read_text()) if resume else []
    for name in NAMES:
        if any(x['strategy']==name and x['exit_code']==0 for x in rows):
            continue
        log_path=out/(name+'.txt')
        retry=0
        while log_path.exists():
            retry+=1
            log_path=out/(name+f'.retry-{retry:03d}.txt')
        directory=ROOT/'work/master-backtests'/name
        if directory.exists():
            # A failed report can leave a native directory without an archive.
            # Preserve it under a new failure name before retrying that policy.
            if (directory/'.last_result.json').exists():
                raise ValueError('Unregistered completed result; inspect before retry')
            failed=directory.with_name('failed-'+name+f'-{retry:03d}')
            if failed.exists():
                raise ValueError('Preserve failed output; use a new retry identity')
            shutil.move(directory,failed)
        with log_path.open('x') as log:
            result=subprocess.run([sys.executable,str(ROOT/'scripts/master_native.py'),'backtest',name],
                                  stdout=log,stderr=subprocess.STDOUT)
        row=dict(strategy=name,exit_code=result.returncode,log=log_path.name)
        if result.returncode==0:
            directory=ROOT/'work/master-backtests'/name
            archive=directory/json.loads((directory/'.last_result.json').read_text())['latest_backtest']
            with zipfile.ZipFile(archive) as source:
                member=next(n for n in source.namelist() if n.endswith('.json') and not n.endswith('_config.json') and '.meta.' not in n)
                content=source.read(member)
            (out/(name+'.json')).write_bytes(content)
            native=json.loads(content)['strategy'][name]
            trades=native['trades']
            row.update(trades=len(trades),net=sum(t['profit_abs'] for t in trades),
                       archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                       result_sha256=hashlib.sha256(content).hexdigest())
            original=ROOT/'evidence/bonus/native-results'/(name+'.json')
            if original.exists():
                row['original_trade_fields_equal']=trades==json.loads(original.read_text())['strategy'][name]['trades']
        rows.append(row)
        (out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps(row),flush=True)
        if result.returncode:
            raise ValueError('Native failure preserved: '+name)


if __name__=='__main__':
    main()
