"""Bounded hash-verified owner backup; no credentials, symlinks or overwrites."""
from pathlib import Path,PurePosixPath
import hashlib
import io
import json
import sys
import tarfile
from session4_common import ROOT,DATA,STATE

MANIFEST='SESSION4-BACKUP-MANIFEST.json'
PREFIXES=('user_data/data/session4/','user_data/backtest_results/session4/','user_data/runtime/session4/','work/session4/')


def create(target):
    target=Path(target)
    if target.exists():raise ValueError('preserve existing backup')
    files=[]
    for directory in [DATA.parent,ROOT/'user_data/backtest_results/session4',ROOT/'user_data/runtime/session4',STATE]:
        files.extend(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.is_symlink())
    files=sorted(set(files))
    manifest=dict(files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        credentials_included=False,scope='actual public raw sources, native ZIPs, immutable staged inputs and simulated SQLite state')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(target,'x:gz') as archive:
        raw=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode();info=tarfile.TarInfo(MANIFEST);info.size=len(raw);archive.addfile(info,io.BytesIO(raw))
        for p in files:archive.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
    return dict(files=len(files),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),archive=str(target))


def restore(bundle,destination):
    destination=Path(destination)
    if destination.exists() and any(destination.iterdir()):raise ValueError('restore destination must be empty')
    with tarfile.open(bundle,'r:gz') as archive:
        members=archive.getmembers();names=[m.name for m in members]
        if len(names)!=len(set(names)) or sum(m.size for m in members)>512*1024*1024:raise ValueError('invalid/oversized backup')
        for member in members:
            p=PurePosixPath(member.name)
            if not member.isfile() or p.is_absolute() or '..' in p.parts or (member.name!=MANIFEST and not member.name.startswith(PREFIXES)):raise ValueError('unsafe archive member')
        manifest=json.load(archive.extractfile(MANIFEST))
        if set(names)!={MANIFEST,*manifest['files']}:raise ValueError('manifest membership differs')
        for name,digest in manifest['files'].items():
            if hashlib.sha256(archive.extractfile(name).read()).hexdigest()!=digest:raise ValueError('backup digest mismatch')
        destination.mkdir(parents=True,exist_ok=True)
        for member in members:
            target=destination/member.name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as file:file.write(archive.extractfile(member).read())
    return dict(verified_files=len(manifest['files']),overwritten_files=0,destination=str(destination))


if __name__=='__main__':print(json.dumps(create(sys.argv[2]) if sys.argv[1]=='create' else restore(sys.argv[2],sys.argv[3]),indent=2))
