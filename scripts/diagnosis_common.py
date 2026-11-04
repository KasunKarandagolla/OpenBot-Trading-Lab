"""Additive deep-diagnosis session. PR13 inputs and evidence are read-only."""
from integrated_common import ROOT,read,write,sha,now,slug
from pathlib import Path
import sys
sys.path.insert(0,str(ROOT/'research/diagnosis'))
OUT=ROOT/'evidence/diagnosis/run-001'
WORK=ROOT/'work/diagnosis'
PARENT=ROOT/'evidence/integrated/run-001'
PWORK=ROOT/'work/integrated'
DATA=ROOT/'user_data/data/integrated'
NATIVE_LABELS={'v4':'control-v4-touch-750-order-audit','pr12':'control-pr12-touch-750',
    'relaxed':'ema-context-touch-750','passive':'entry-passive-touch-750','structural':'thesis-exit-touch-750'}
def pairs():return read(ROOT/'research/integrated/protocol.json')['pairs']
def opportunity_key(pair,g):return '|'.join([pair,g['available_at'],g['recipe'],g['side']])
def verify_parent():
    frozen=read(OUT/'starting-freeze.json')['preexisting_files']
    bad=[p for p,h in frozen.items() if sha(ROOT/p)!=h]
    if bad:raise ValueError('immutable parent changed: '+str(bad))
    from integrated_native import verify
    verify()
    return dict(files=len(frozen),evidence_files=sum(p.startswith('evidence/') for p in frozen),changed=[])
