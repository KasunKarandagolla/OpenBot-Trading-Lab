"""Incremental private-input bundle; restore PR13's verified bundle first.

Uses the parent archive's already-tested safe preflight extractor with an explicit
new prefix allowlist. Parent code and parent archive bytes are never changed.
"""
import io
import json
import tarfile
from diagnosis_common import *
import integrated_archive as parent_archive

PREFIXES=('user_data/data/diagnosis/','work/diagnosis/development/','work/diagnosis/earlier/','work/diagnosis/later/',
    'work/diagnosis/native/','work/diagnosis/strategies/','work/diagnosis/chart-inputs/')
MANIFEST='DIAGNOSIS-INPUT-MANIFEST.json'
PARENT_SHA='5a82c65ebbe06cf4ecbef8e11c02ab090b3687676cd5a31cbad4a105ef16b5f6'

def create(destination):
    destination=Path(destination)
    if destination.exists():raise ValueError('preserve existing archive')
    roots=[ROOT/'user_data/data/diagnosis']+[WORK/x for x in ('development','earlier','later','native','strategies','chart-inputs')]
    paths=sorted({p for root in roots for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    if any(p.is_symlink() for p in paths):raise ValueError('no linked private input')
    manifest={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in paths}
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(destination,'w:gz',dereference=True) as archive:
        for path in paths:archive.add(path,arcname=str(path.relative_to(ROOT)),recursive=False)
        payload=json.dumps(manifest,sort_keys=True,indent=2).encode();member=tarfile.TarInfo(MANIFEST);member.size=len(payload);archive.addfile(member,io.BytesIO(payload))
    return dict(archive=destination.name,files=len(paths),bytes=destination.stat().st_size,sha256=sha(destination),raw_bytes=sum(x['bytes'] for x in manifest.values()),
        prerequisite=dict(archive='OpenBot-Integrated-Private-Inputs.tar.gz',sha256=PARENT_SHA),
        interpretation='Incremental diagnosis inputs. Original PR13 raw candles/features/plans require the unchanged parent bundle first. No archive file overwrites differing existing bytes.')

def restore(archive,destination,expected_sha256):
    old_prefixes,old_manifest=parent_archive.PREFIXES,parent_archive.MANIFEST
    parent_archive.PREFIXES,parent_archive.MANIFEST=PREFIXES,MANIFEST
    try:return parent_archive.restore(archive,destination,expected_sha256)
    finally:parent_archive.PREFIXES,parent_archive.MANIFEST=old_prefixes,old_manifest

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('create');c.add_argument('destination')
    r=sub.add_parser('restore');r.add_argument('archive');r.add_argument('destination');r.add_argument('--sha256',required=True)
    a=p.parse_args();print(json.dumps(create(a.destination) if a.action=='create' else restore(a.archive,a.destination,a.sha256),indent=2))
