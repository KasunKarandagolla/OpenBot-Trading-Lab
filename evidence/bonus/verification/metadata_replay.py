"""Reproduce the post-outcome annotation correction's zero admission impact."""
import sys,shutil,json
from pathlib import Path
sys.path.insert(0,'/lab/scripts')
from bonus_common import ROOT,OUT,sha,write,read
import bonus_pipeline as pipeline
new=ROOT/'work/metadata-replay'
if new.exists():raise ValueError('preserve prior metadata replay; use a fresh reproduction checkout')
new.mkdir(parents=True)
shutil.copyfile(OUT/'source-manifest.json',new/'source-manifest.json')
pipeline.OUT=new
pipeline.candidates()
files=['opportunity-ledger.csv','opportunity-summary.json','trade-plans.json']
comparisons={name:{'before':sha(OUT/name),'after':sha(new/name),'identical':sha(OUT/name)==sha(new/name)} for name in files}
if not all(r['identical'] for r in comparisons.values()):raise ValueError('metadata fix changed an admission artifact')
write(OUT/'metadata-admission-verification.json',{'pass':True,'comparisons':comparisons,'thresholds_changed':False})
