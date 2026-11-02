"""Verify and extract a private source bundle to a NEW directory only."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile


def restore(bundle, target):
    target = Path(target)
    if target.exists():
        raise ValueError('restore target must not exist; never overwrite a source')
    with tarfile.open(bundle) as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise ValueError('unsafe archive member')
        archive.extractall(target, filter='data')
    manifest = json.loads((target/'data-manifest.json').read_text())
    for item in manifest['files']:
        source = target/'source/gate/futures'/Path(item['path']).name
        if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('restored source hash mismatch')
    print(f'Verified {len(manifest["files"])} restored source files; originals untouched')


if __name__ == '__main__':
    restore(*sys.argv[1:])
