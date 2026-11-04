"""Fixed trial list: three correction hypotheses, isolated controls and fidelity tests."""
import subprocess
import sys
from diagnosis_common import *

def jobs():
    full=['v4','pr12','passive','structural','conditional-entry','passive-30m','ema-eligibility-only','rank-only','ema-both','rank-qualified-only','continuation-only','thesis-compatible']
    tasks=[('primary',['development',v]) for v in full]
    for detail in (False,True):
        for v in ('v4','passive','conditional-entry','passive-30m'):
            tasks.append(('fidelity',['development',v,'--short']+(['--detail'] if detail else [])))
    for v in ('v4','conditional-entry','rank-qualified-only','thesis-compatible'):
        tasks.append(('stress',['development',v,'--fee','.00175']))
        tasks.append(('stress',['development',v,'--through']))
    for c in ('earlier','later'):
        for v in (x for x in full if x!='pr12'):tasks.append(('validation',[c,v]))
    return tasks

def label(args):
    cohort,variant=args[:2]
    fee=float(args[args.index('--fee')+1]) if '--fee' in args else .00075
    return f'{cohort}-{variant}'+('-oct5' if '--short' in args else '')+('-detail5m' if '--detail' in args else '')+('-through' if '--through' in args else '-touch')+'-'+str(round(fee*1e6))

def run(phase='all'):
    history=WORK/'command-history.jsonl';history.parent.mkdir(parents=True,exist_ok=True)
    for category,args in jobs():
        if phase!='all' and category!=phase:continue
        name=label(args);log=WORK/'logs'/(name+'.txt');log.parent.mkdir(parents=True,exist_ok=True)
        if (OUT/'native'/name/'result.json').exists():
            print('PRESERVED_EXISTING',name,flush=True);continue
        command=[sys.executable,str(ROOT/'scripts/diagnosis_native.py'),*args]
        print('START',name,flush=True)
        with log.open('x') as output:result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
        with history.open('a') as h:h.write(__import__('json').dumps(dict(at=now(),category=category,args=command,returncode=result.returncode,log=str(log.relative_to(ROOT))))+'\n')
        print('DONE',name,'exit',result.returncode,flush=True)
        if result.returncode:
            print(log.read_text()[-6000:],flush=True);raise SystemExit(result.returncode)
    print('COMPLETE_FIXED_MATRIX',phase,flush=True)

if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'all')
