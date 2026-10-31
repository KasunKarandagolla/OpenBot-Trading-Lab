"""Host-side Git object comparison; pinned native image need not install Git."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE='91ced4b32315793ddd08e52c80f572b39d76d700'


def main():
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    files=git('ls-tree','-r','--name-only',BASE).splitlines()
    changed=[];digests={}
    for path in files:
        if git('rev-parse',BASE+':'+path)!=git('hash-object',path):
            changed.append(path)
        digests[path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    result=dict(base_sha=BASE,files=digests,changed=changed)
    destination=ROOT/'evidence/master-audit/preservation-source.json'
    destination.write_text(json.dumps(result,indent=2)+'\n')
    assert not changed
    print(len(files),'original files unchanged')


if __name__=='__main__':
    main()
