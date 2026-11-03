"""Finite declared experiment matrix. Preserve every completed result and failure."""
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from recovery_common import *

def jobs(group):
    result=[]
    if group=='primary':
        for w,variants in [('development',['reference','structure','context','context-smc','momentum','liquid-momentum']),
                           ('hourly-development',['momentum','liquid-momentum']),('hourly-independent',['momentum','liquid-momentum'])]:
            for v in variants:
                for risk in [False,True]:
                    for fee in [.00075,.00175]:result.append([w,v]+(['--risk'] if risk else [])+['--fee',str(fee)])
    if group=='null':result=[['development','rank-'+str(i)] for i in range(1,32)]
    if group=='validation':
        # Required qualification checks for predeclared execution sensitivities,
        # with identical reference controls;no new rule or threshold is fitted.
        for v in ['reference','structure']:
            for execution in ['open','drop25']:
                result.append(['development',v,'--execution',execution,'--risk'])
                result.append(['development',v,'--execution',execution,'--risk','--fee','.00175'])
                result.append(['development',v,'--execution',execution,'--fee','.00175'])
    if group=='execution':
        result.extend([['development','parent-reference-plans'],['development','parent-structure-plans']])
        for v in ['reference','structure','context']:
            for execution in ['through','open','market','drop25']:result.append(['development',v,'--execution',execution])
        for v in ['reference','context','momentum']:result.append(['development',v,'--half'])
        result.append(['development','reference','--barriers'])
        for v in ['reference','structure','context','context-smc','momentum','liquid-momentum']:
            result.append(['development',v,'--detail'])
            # Worst instantaneous observed half-spread + public5bp taker +
            # hypothetical2bp slippage, rounded UP to0.1bp;source,not PnL,selects cost.
            import math
            fee=math.ceil((.0005+.0002+max(x['spread_bp']/2 for x in read(OUT/'current-spreads.json'))/1e4)*1e5)/1e5
            result.append(['development',v,'--fee',str(fee),'--execution','market'])
    return result

def run(group):
    from recovery_native import stage
    stage()
    matrix=jobs(group);p=OUT/('matrix-'+group+'.json')
    if not p.exists():write(p,dict(at=now(),commands=matrix,adaptive=False))
    def job(args):
        # Let the native runner enforce no overwrite. Known completed jobs are
        # skipped only by their exact expected label, retaining source provenance.
        w,v=args[:2];risk='--risk' in args;execution=args[args.index('--execution')+1] if '--execution' in args else 'touch'
        fee=float(args[args.index('--fee')+1]) if '--fee' in args else .00075
        label=f'{v}-'+('risk' if risk else 'fixed')+'-'+execution+'-fee'+str(round(fee*1e6))+('-1m' if '--detail' in args else '')+('-half' if '--half' in args else '')+('-barriers' if '--barriers' in args else '')
        if (OUT/'native'/w/label/'result.json').exists():return dict(label=label,window=w,status='EXISTING_IMMUTABLE')
        logs=OUT/'logs'/group;logs.mkdir(parents=True,exist_ok=True)
        log=logs/(w+'--'+label+'.txt')
        if log.exists():log=log.with_name(log.stem+'-retry-'+str(len(list(logs.glob(log.stem+'*'))))+'.txt')
        with log.open('x') as f:r=subprocess.run([sys.executable,str(ROOT/'scripts/recovery_native.py'),*args],stdout=f,stderr=subprocess.STDOUT)
        print(w,label,'PASS' if r.returncode==0 else 'FAILED',flush=True)
        return dict(label=label,window=w,returncode=r.returncode,log=str(log.relative_to(ROOT)))
    with ThreadPoolExecutor(max_workers=2 if group=='validation' else 4) as pool:results=list(pool.map(job,matrix))
    path=OUT/('matrix-'+group+'-results.json')
    if path.exists():path=OUT/(path.stem+'-retry.json')
    write(path,results)
    if any(r.get('returncode',0) for r in results):raise ValueError('retained experiment failures')

if __name__=='__main__':run(sys.argv[1])
