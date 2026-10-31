"""Predeclared October 5m native fill-order sensitivity, fixed policies and scope."""
import subprocess
import sys
import pandas as pd
from bonus_common import *

NAMES=['RouterOnlyV1','RouterOnlyM1V1']


def arguments(name,mode):
    if name not in NAMES or mode not in ('coarse','fine'):raise ValueError('unregistered detail variant')
    check();stage()
    from bonus_data import verify
    verify();m=read(OUT/'detail-manifest.json')
    for r in m['files']:
        if sha(ROOT/r['path'])!=r['sha256']:raise ValueError('detail source changed')
    cfg=ROOT/'work/bonus-configs'/(name+'.json');write(cfg,config(name))
    directory=ROOT/'user_data/backtest_results/bonus/detail'/(name+'-'+mode)
    directory.mkdir(parents=True,exist_ok=True)
    args=['backtesting','--config',str(cfg),'--datadir',str(DATA),'--timerange',spec()['detail_timerange'],
          '--fee','0.0006','--enable-protections','--cache','none','--export','trades',
          '--backtest-directory',str(directory)]
    if mode=='fine':args+=['--timeframe-detail','5m']
    return args


def run():
    from bonus_pipeline import extract
    dest=OUT/'detail-results';dest.mkdir(exist_ok=True);results={}
    for name in NAMES:
        results[name]={}
        for mode in ['coarse','fine']:
            stem=name+'-'+mode;artifact=dest/(stem+'.json');log=dest/(stem+'-output.txt')
            if artifact.exists():raise ValueError('preserve detail results')
            started=pd.Timestamp.now(tz='UTC')
            with log.open('x') as f:
                r=subprocess.run([sys.executable,str(ROOT/'scripts/bonus_detail.py'),name,mode],
                                 stdout=f,stderr=subprocess.STDOUT,env=sanitized_env())
            if r.returncode:raise ValueError('native detail failed')
            directory=ROOT/'user_data/backtest_results/bonus/detail'/stem
            archive=extract(name,directory,artifact)
            native=read(artifact)['strategy'][name]
            results[name][mode]={'trades':len(native['trades']),'net_usdt':sum(t['profit_abs'] for t in native['trades']),
                                 'fills':[{k:t[k] for k in ['pair','open_date','close_date','open_rate','close_rate','profit_abs','exit_reason']} for t in native['trades']]}
            write(dest/(stem+'-provenance.json'),{'started':started.isoformat(),'result_sha256':sha(artifact),
                                               'archive_sha256':sha(archive),'freeze_sha256':sha(OUT/'freeze.sha256'),
                                               'detail_manifest_sha256':sha(OUT/'detail-manifest.json'),'exit_code':r.returncode})
            print(stem,results[name][mode]['trades'],results[name][mode]['net_usdt'],flush=True)
    write(OUT/'detail-comparison.json',{'timerange':spec()['detail_timerange'],'results':results,
                                       'limitation':'Bounded October subset. Native candle prices, no queue or exchange partial-fill proof.'})


if __name__=='__main__':
    import os
    name,mode=sys.argv[1:]
    args=arguments(name,mode);env=sanitized_env();os.environ.clear();os.environ.update(env)
    from freqtrade.main import main
    raise SystemExit(main(args))
