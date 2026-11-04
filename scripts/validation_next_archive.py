"""Reuse audited restore preflight with a new, tightly scoped namespace."""
from validation_next_common import *
import tarfile,io,argparse
MANIFEST='VALIDATION-NEXT-INPUT-MANIFEST.json'
PREFIXES=('user_data/data/validation_next/','work/validation_next/')

def create(destination):
 destination=Path(destination)
 if destination.exists():raise ValueError('preserve existing archive')
 paths=sorted(p for root in [DATA,WORK] for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 if any(p.is_symlink() for p in paths):raise ValueError('linked inputs forbidden')
 manifest={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in paths}
 if sum(x['bytes'] for x in manifest.values())>500_000_000:raise ValueError('500MB input budget exceeded')
 destination.parent.mkdir(parents=True,exist_ok=True)
 with tarfile.open(destination,'w:gz',dereference=True) as t:
  for p in paths:t.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
  payload=__import__('json').dumps(manifest,indent=2,sort_keys=True).encode();m=tarfile.TarInfo(MANIFEST);m.size=len(payload);t.addfile(m,io.BytesIO(payload))
 return dict(file=destination.name,files=len(paths),bytes=destination.stat().st_size,raw_bytes=sum(x['bytes'] for x in manifest.values()),sha256=sha(destination))

def restore(archive,destination,expected):
 import integrated_archive
 old_prefix,old_manifest=integrated_archive.PREFIXES,integrated_archive.MANIFEST
 try:
  integrated_archive.PREFIXES=PREFIXES;integrated_archive.MANIFEST=MANIFEST
  return integrated_archive.restore(archive,destination,expected)
 finally:integrated_archive.PREFIXES=old_prefix;integrated_archive.MANIFEST=old_manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True);a=sub.add_parser('create');a.add_argument('destination');a=sub.add_parser('restore');a.add_argument('archive');a.add_argument('destination');a.add_argument('--sha256',required=True);a=p.parse_args()
 print(__import__('json').dumps(create(a.destination) if a.action=='create' else restore(a.archive,a.destination,a.sha256),indent=2))
