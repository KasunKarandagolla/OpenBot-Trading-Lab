"""Private source/input/native archive with safe restore and independent file hashes."""
import io
import json
import tarfile
import gzip
import hashlib
import sys
from pathlib import Path,PurePosixPath
from recovery_common import ROOT,WORK,DATA,OUT,sha,write,now

PREFIXES=('user_data/data/recovery/','work/recovery/')
MANIFEST='RECOVERY-BACKUP-MANIFEST.json'

def create(target):
    target=Path(target)
    if target.exists():raise ValueError('preserve existing backup')
    files=sorted({p for base in [WORK,DATA] for p in base.rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts})
    entries={}
    for p in files:
        name=str(p.relative_to(ROOT));compressed=name.endswith('.sqlite.gz')
        if compressed:name=name[:-3]
        if name in entries:raise ValueError('duplicate expanded archive path')
        raw=gzip.decompress(p.read_bytes()) if compressed else None
        entries[name]=(p,compressed,len(raw) if compressed else p.stat().st_size,hashlib.sha256(raw).hexdigest() if compressed else sha(p))
    manifest=dict(at=now(),files={name:e[3] for name,e in entries.items()},
        scope='Actual public sources,raw contract-volume quarantine,CCXT snapshot,causal feature/plan stages,all native ZIPs/configs/simulated states and retained attempts',
        credentials_included=False,external_orders=False,parent_session4_archive_available=False)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(target,'x:gz') as t:
        raw=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode();info=tarfile.TarInfo(MANIFEST);info.size=len(raw);t.addfile(info,io.BytesIO(raw))
        for name,(p,compressed,size,digest) in entries.items():
            if compressed:
                info=tarfile.TarInfo(name);info.size=size
                with gzip.open(p,'rb') as f:t.addfile(info,f)
            else:t.add(p,arcname=name,recursive=False)
    return dict(archive=target.name,files=len(files),bytes=target.stat().st_size,sha256=sha(target))

def restore(bundle,destination):
    destination=Path(destination)
    if destination.exists() and any(destination.iterdir()):raise ValueError('destination must be empty')
    with tarfile.open(bundle,'r:gz') as t:
        members=t.getmembers();names=[m.name for m in members]
        if len(names)!=len(set(names)) or sum(m.size for m in members)>1024**3:raise ValueError('invalid or oversized archive')
        for m in members:
            p=PurePosixPath(m.name)
            if not m.isfile() or p.is_absolute() or '..' in p.parts or (m.name!=MANIFEST and not m.name.startswith(PREFIXES)):raise ValueError('unsafe archive member')
        manifest=json.load(t.extractfile(MANIFEST))
        if set(names)!={MANIFEST,*manifest['files']}:raise ValueError('membership mismatch')
        import hashlib
        for name,h in manifest['files'].items():
            if hashlib.sha256(t.extractfile(name).read()).hexdigest()!=h:raise ValueError('source digest mismatch')
        for m in members:
            p=destination/m.name;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(t.extractfile(m).read())
    return dict(verified_files=len(manifest['files']),overwrites=0,destination=str(destination))

def hydrate(source,destination):
    """Copy verified inputs into a checkout; reject differing existing files first."""
    source=Path(source);destination=Path(destination);manifest=json.loads((source/MANIFEST).read_text())
    planned=[];identical=0;compressed_identical=0
    for name,h in manifest['files'].items():
        key=PurePosixPath(name)
        if key.is_absolute() or '..' in key.parts or not name.startswith(PREFIXES):raise ValueError('unsafe manifest path')
        src=source/name;target=destination/name
        if src.is_symlink() or sha(src)!=h:raise ValueError('restored source differs')
        if any(p.is_symlink() for p in [target,*target.parents]):raise ValueError('symlink destination forbidden')
        if target.exists():
            if sha(target)!=h:raise ValueError('existing input differs;no overwrite '+name)
            identical+=1
        elif str(target).endswith('.sqlite') and Path(str(target)+'.gz').exists():
            if hashlib.sha256(gzip.decompress(Path(str(target)+'.gz').read_bytes())).hexdigest()!=h:raise ValueError('compressed existing state differs')
            compressed_identical+=1
        else:planned.append((src,target))
    for src,target in planned:
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(src.read_bytes())
    return dict(copied_files=len(planned),existing_identical=identical,existing_lossless_compressed_identical=compressed_identical,overwrites=0)

if __name__=='__main__':
    result=create(sys.argv[2]) if sys.argv[1]=='create' else hydrate(sys.argv[2],sys.argv[3]) if sys.argv[1]=='hydrate' else restore(sys.argv[2],sys.argv[3])
    print(json.dumps(result,indent=2))
