"""Finite preregistered alternatives, never a parameter search."""
from concurrent.futures import ProcessPoolExecutor
from setup_common import *
def job(spec):
    import subprocess
    v=spec[0];risk='--risk' in spec;half='--half' in spec
    fee=float(spec[spec.index('--fee')+1]) if '--fee' in spec else .00075
    execution=spec[spec.index('--execution')+1] if '--execution' in spec else 'touch'
    key=v+('-risk' if risk else '-fixed')+'-'+execution+'-'+str(round(fee*1e6))+('-half' if half else '')
    if (OUT/'native'/key/'result.json').exists():
        provenance=read(OUT/'native'/key/'provenance.json')
        if provenance['freeze_sha256']!=sha(OUT/'freeze.json'):raise ValueError('existing result has different freeze')
        return dict(args=spec,exit_code=0,reused_immutable_result=key)
    label='-'.join(spec).replace('/','_');log=WORK/'matrix-logs'/(label+'.txt');log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as f:
        p=subprocess.run([sys.executable,str(ROOT/'scripts/setup_native.py'),*spec],stdout=f,stderr=subprocess.STDOUT)
    return dict(args=spec,exit_code=p.returncode,log=str(log.relative_to(ROOT)))
def run():
    specs=[[v] for v in protocol()['variants']]
    specs += [[v,'--risk'] for v in ['setup','v4-reference']]
    specs += [[v,'--fee','0.00175'] for v in ['setup','v4-reference']]
    specs += [['setup','--execution',x] for x in ['through','drop25']]
    specs += [['setup','--half']]
    with ProcessPoolExecutor(max_workers=3) as pool:
        results=[]
        for r in pool.map(job,specs):results.append(r);write(OUT/'matrix-commands.json',results);print(r,flush=True)
    if any(r['exit_code'] for r in results):raise RuntimeError('matrix failure; inspect logs')
if __name__=='__main__':run()
