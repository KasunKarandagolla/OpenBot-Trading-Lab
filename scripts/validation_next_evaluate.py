"""One-shot evaluation; no threshold selection or second holdout opening."""
from validation_next_common import *
import subprocess,sys
VARIANTS=['v4-transfer','passive-transfer','structural-transfer','thesis-compatible-transfer','continuation-only-diagnostic','parent-target']

def command(args,label):
 p=WORK/'commands'/(label+'.txt');p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise ValueError('preserve command label')
 with p.open('w') as f:r=subprocess.run([sys.executable,*args],stdout=f,stderr=subprocess.STDOUT)
 record=dict(at=now(),argv=args,exit_code=r.returncode,log=str(p.relative_to(ROOT)),log_sha256=sha(p))
 with (OUT/'execution-history.jsonl').open('a') as f:f.write(__import__('json').dumps(record)+'\n')
 if r.returncode:raise RuntimeError('command failed '+str(p))

def validation():
 command(['scripts/validation_next_prepare.py','validation'],'prepare-validation-exactclock')
 for v in VARIANTS:
  if (OUT/'native'/('validation-'+v+'-detail5m-touch-fee500-exactclock')/'result.json').exists():continue
  command(['scripts/validation_next_native.py','validation',v,'--detail'],'validation-'+v+'-exactclock')

def freeze():
 if (OUT/'evaluation-freeze.json').exists():raise ValueError('evaluation freeze exists')
 if not (OUT/'causal-prefix-checks.json').exists() or not (OUT/'native/validation-parent-target-detail5m-touch-fee500-exactclock/result.json').exists():raise ValueError('complete validation before freeze')
 paths=list((ROOT/'research/validation_next').glob('*'))+list((ROOT/'scripts').glob('validation_next_*.py'))+[ROOT/'scripts/lab-validation-next.sh',ROOT/'tests/test_validation_next.py']
 source=read(OUT/'converted-inputs.json')
 write(OUT/'evaluation-freeze.json',dict(at=now(),code_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths if p.is_file()},converted_input_hashes=source,archive_manifest_sha256=sha(OUT/'data-manifest.json'),scenario_contracts_sha256=sha(OUT/'scenario-contracts.json'),variants=VARIANTS,decision='No promotion; all preregistered comparisons retained, including failed development hypotheses as negative controls. No parameter changes after development or validation.',configuration='Native runner code + pinned configs/research-vwap.json + fixture snapshot + source/data hashes determine all native configs. Wallet1000,cap25,1x,two positions,5m expiry,0.0005 per-side fee; all holdout portfolios use5m detail.',baseline_config_sha256=sha(ROOT/'configs/research-vwap.json'),holdout_unopened=not (OUT/'holdout-opened.json').exists()))

def holdout():
 frozen=read(OUT/'evaluation-freeze.json')
 for p,h in frozen['code_hashes'].items():
  if sha(ROOT/p)!=h:raise ValueError('evaluation source changed '+p)
 for p,h in frozen['converted_input_hashes'].items():
  if sha(ROOT/p)!=h:raise ValueError('converted source changed '+p)
 if sha(OUT/'scenario-contracts.json')!=frozen['scenario_contracts_sha256']:raise ValueError('contract fixture changed')
 # Atomic exclusive receipt. An interrupted evaluation is preserved and cannot silently reopen.
 path=OUT/'holdout-opened.json'
 with path.open('x') as f:__import__('json').dump(dict(opened_at_utc=now(),evaluation_freeze_sha256=sha(OUT/'evaluation-freeze.json'),window=spec()['partitions']['holdout'],variants=VARIANTS,open_count=1,retuning_permitted=False),f,indent=2)
 command(['scripts/validation_next_prepare.py','holdout'],'prepare-holdout')
 for v in VARIANTS:command(['scripts/validation_next_native.py','holdout',v,'--detail'],'holdout-'+v)
 write(OUT/'holdout-completed.json',dict(at=now(),freeze_sha256=sha(OUT/'evaluation-freeze.json'),open_count=1,variants=VARIANTS))
if __name__=='__main__':{'validation':validation,'freeze':freeze,'holdout':holdout}[sys.argv[1]]()
