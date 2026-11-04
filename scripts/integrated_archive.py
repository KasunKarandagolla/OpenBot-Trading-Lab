"""Hash-verified private research-input backup; no overwrite or unsafe tar extraction."""
import io
import tarfile
from pathlib import PurePosixPath
from integrated_common import *

PREFIXES=('user_data/data/integrated/','work/integrated/features/','work/integrated/plans/','work/integrated/native/','work/integrated/strategies/')
MANIFEST='INTEGRATED-INPUT-MANIFEST.json'

def create(destination):
    destination=Path(destination)
    if destination.exists(): raise ValueError('preserve existing archive')
    roots=[DATA]+[WORK/x for x in ('features','plans','native','strategies')]
    paths=sorted({p for root in roots for p in root.rglob('*') if p.is_file()})
    if any(p.is_symlink() for p in paths): raise ValueError('no linked private input')
    manifest={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in paths}
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(destination,'w:gz',dereference=True) as archive:
        for p in paths: archive.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
        payload=json.dumps(manifest,sort_keys=True,indent=2).encode()
        member=tarfile.TarInfo(MANIFEST);member.size=len(payload);archive.addfile(member,io.BytesIO(payload))
    return dict(archive=destination.name,files=len(paths),bytes=destination.stat().st_size,sha256=sha(destination),raw_bytes=sum(x['bytes'] for x in manifest.values()))

def restore(archive,destination,expected_sha256):
    archive=Path(archive);destination=Path(destination).resolve()
    if sha(archive)!=expected_sha256: raise ValueError('archive checksum mismatch')
    with tarfile.open(archive,'r:gz') as source:
        members=source.getmembers();names=[m.name for m in members]
        if len(names)!=len(set(names)): raise ValueError('duplicate tar member')
        for member in members:
            name=PurePosixPath(member.name)
            if not member.isfile() or name.is_absolute() or '..' in name.parts or (member.name!=MANIFEST and not member.name.startswith(PREFIXES)):
                raise ValueError('unsafe or out-of-scope tar member')
        manifest=json.load(source.extractfile(MANIFEST))
        if set(names)-{MANIFEST}!=set(manifest) or sum(x['bytes'] for x in manifest.values())>2_000_000_000: raise ValueError('manifest coverage or size')
        # Preflight every member and destination before writing any file.
        for member in members:
            if member.name==MANIFEST: continue
            target=destination/member.name
            if not target.resolve().is_relative_to(destination) or target.is_symlink(): raise ValueError('destination escape')
            data=source.extractfile(member).read()
            info=manifest[member.name]
            if len(data)!=info['bytes'] or __import__('hashlib').sha256(data).hexdigest()!=info['sha256']: raise ValueError('member checksum mismatch')
            if target.exists() and sha(target)!=info['sha256']: raise ValueError('refuse differing existing file '+member.name)
        restored=0;identical=0
        for member in members:
            if member.name==MANIFEST: continue
            target=destination/member.name
            if target.exists(): identical+=1;continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as handle: handle.write(source.extractfile(member).read())
            restored+=1
    return dict(verified_files=len(manifest),restored=restored,identical_existing=identical,overwrites=0)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('create');c.add_argument('destination')
    r=sub.add_parser('restore');r.add_argument('archive');r.add_argument('destination');r.add_argument('--sha256',required=True)
    a=p.parse_args()
    print(json.dumps(create(a.destination) if a.action=='create' else restore(a.archive,a.destination,a.sha256),indent=2))
