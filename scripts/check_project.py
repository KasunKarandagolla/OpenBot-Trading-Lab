import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,'/lab/scripts')
from guard import validate,merge
root=Path('/lab')
for name in ['research','scanner','paper','ui']:
 c=json.loads((root/f'configs/{name}.json').read_text())
 if name in ('paper','ui'):
  merge(c,json.loads((root/'user_data/runtime/api.json').read_text()))
 validate(c)
for line in (root/'evidence/session-1/freeze.sha256').read_text().splitlines():
 sha,path=line.split(maxsplit=1)
 assert hashlib.sha256((root/path).read_bytes()).hexdigest()==sha, 'frozen strategy/protocol changed'
print('PASS: four configurations safe; no exchange keys; frozen strategy/protocol hashes match.')
