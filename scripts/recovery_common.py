"""Additive profitability research. Parent evidence and operational settings stay frozen."""
from pathlib import Path
import hashlib
import json
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/recovery/run-001'
WORK = ROOT / 'work/recovery'
DATA = ROOT / 'user_data/data/recovery'
for name in ('policy', 'session4', 'session3', 'bonus', 'intelligence', 'foundation', 'master_audit'):
    sys.path.insert(0, str(ROOT / 'research' / name))
sys.path.insert(0, str(ROOT / 'user_data/strategies'))
sys.path.insert(0, str(ROOT / 'research/recovery'))

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=str) + '\n')
def now(): return datetime.now(timezone.utc).isoformat()
def slug(pair): return pair.replace('/', '_').replace(':', '_')
def pairs():
    manifest = read(ROOT/'evidence/session4/run-001/data-manifest.json')['files']
    names = {Path(x['path']).name for x in manifest}
    return [p for p in read(ROOT/'evidence/session4/run-001/cohort.json')['pairs']
            if all(slug(p)+'-'+s+'.feather' in names for s in
                   ('15m-futures','1h-futures','1h-mark','1h-funding_rate'))]

