"""Verify an owner-private backup into an empty staging directory; never overwrite."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import tarfile
import sys


def restore(bundle,destination):
    destination=Path(destination)
    if destination.exists() and any(destination.iterdir()):raise ValueError('restore destination must be empty')
    with tarfile.open(bundle,'r:gz') as archive:
        members=archive.getmembers();names=[m.name for m in members]
        if len(names)!=len(set(names)):raise ValueError('duplicate backup member')
        if sum(m.size for m in members)>128*1024*1024:raise ValueError('backup exceeds128MiB bound')
        for m in members:
            p=PurePosixPath(m.name)
            if p.is_absolute() or '..' in p.parts or not m.isfile():raise ValueError('unsafe backup member')
            if m.name!='BACKUP-MANIFEST.json' and not m.name.startswith(('user_data/data/policy/','user_data/backtest_results/policy/','work/policy-strategies/','work/policy-configs/','work/policy-state/')):raise ValueError('unexpected backup path')
        manifest=json.load(archive.extractfile('BACKUP-MANIFEST.json'))
        files=manifest['files']
        if set(names)!={*files,'BACKUP-MANIFEST.json'}:raise ValueError('manifest membership mismatch')
        # Verify everything before creating any user output.
        for name,expected in files.items():
            raw=archive.extractfile(name).read()
            if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('backup digest mismatch')
        destination.mkdir(parents=True,exist_ok=True)
        for m in members:
            target=destination/m.name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as file:file.write(archive.extractfile(m).read())
    return dict(verified_files=len(files),destination=str(destination),overwritten_files=0)

if __name__=='__main__':print(json.dumps(restore(sys.argv[1],sys.argv[2]),indent=2))
