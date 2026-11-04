"""Isolated integrated-research paths; never mutate completed setup runs."""
from pathlib import Path
import hashlib
import json
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/integrated/run-001'
WORK = ROOT / 'work/integrated'
DATA = ROOT / 'user_data/data/integrated'
for folder in ['research/setup', 'research/integrated', 'research/session4',
               'research/policy', 'research/recovery', 'research/session3',
               'research/bonus', 'research/master_audit', 'research/foundation',
               'research/intelligence', 'user_data/strategies']:
    sys.path.insert(0, str(ROOT / folder))

def read(path):
    return json.loads(Path(path).read_text())

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def slug(pair):
    return pair.replace('/', '_').replace(':', '_')

def protocol():
    return read(ROOT / 'research/integrated/protocol.json')

def pairs():
    return protocol()['pairs']
