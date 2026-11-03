"""Reproducible bounded native vertical slice; all attempts retained."""
import subprocess
import sys
from policy_common import ROOT,paths,read,write,now,verify


def run(run_id,resume=False):
    out,_=paths(run_id)
    if out.exists() and not resume:raise ValueError('use a new run ID or explicit resume; completed evidence is immutable')
    if resume:
        _,_,_=verify(run_id)
        for row in read(out/'data-manifest.json')['files']:
            from policy_common import sha
            if sha(ROOT/row['path'])!=row['sha256']:raise ValueError('cannot resume changed historical source')
    def call(action,*extra):
        cmd=[sys.executable,str(ROOT/'scripts/policy_session.py'),action,run_id,*extra]
        print('Policy step:',action,*extra,flush=True)
        if action=='register':subprocess.run(cmd,check=True);return
        log=out/'command-logs'/('-'.join([action,*extra])+'.txt');log.parent.mkdir(exist_ok=True)
        if log.exists():
            attempt=1
            while log.with_suffix(f'.attempt-{attempt:03}.txt').exists():attempt+=1
            log.rename(log.with_suffix(f'.attempt-{attempt:03}.txt'))
        with log.open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError(f'{action} failed; inspect {log.name}')
    if not resume:call('register')
    completed=dict(scan='scan.json',acquire='data-manifest.json',detail='detail-manifest.json',assess='opportunities.json',flow='orderflow.json',events='event-briefing.json',schedule='opportunity-ledger.json')
    for step in ['scan','acquire','detail','assess','flow','events','schedule']:
        if resume and (out/completed[step]).exists():print('Verified/reused immutable step:',step,flush=True)
        else:call(step)
    _,_,spec=verify(run_id)
    for period in ['all','october','detail','newday']:
        for name in spec['variants']:
            if resume and (out/'native-results'/(name+'-'+period+'-1.json')).exists():continue
            call('native',name,period)
    for lev in ['10','20']:
        if not (out/'native-results'/('PolicyManagedV3-all-'+lev+'.json')).exists():call('native','PolicyManagedV3','all',lev)
    if not (out/'leverage-scenarios.json').exists():call('scenarios')
    if not (out/'economic-report.json').exists():call('report')
    if (out/'lifecycle-tests.txt').exists(): (out/'lifecycle-tests.txt').rename(out/'lifecycle-tests-attempt-001.txt')
    with (out/'lifecycle-tests.txt').open('x') as f:
        subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_policy.py','-v'],stdout=f,stderr=subprocess.STDOUT,check=True)
    if not (out/'openbot/research-snapshot.json').exists():call('export')
    write(out/'completion.json',dict(completed_at=now(),persistent_service_started=False,exchange_orders=False,
        lifecycle='Native Freqtrade fixtures; no observed forward paper fill claim',economic_qualification='PENDING'))

if __name__=='__main__':run(sys.argv[1],len(sys.argv)>2 and sys.argv[2]=='resume')
