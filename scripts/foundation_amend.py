"""Explicit mechanical research amendments; preserve original registration.

Use only after retaining the failure and committing the previous source version.
No parameter search is performed. Every changed source hash and reason is public.
"""
import sys
from foundation_common import paths, read, source_files, sha, write, now, ROOT


def amend(run_id, reason):
    out, _ = paths(run_id)
    registration = read(out/'registration.json')
    hashes = dict(registration['source_hashes'])
    directory = out/'source-amendments'
    previous = sorted(directory.glob('*.json'))
    for path in previous:
        for name, change in read(path)['changes'].items(): hashes[name] = change['new_sha256']
    changes = {}
    for path in source_files():
        name = str(path.relative_to(ROOT)); digest = sha(path)
        if hashes.get(name) != digest:
            changes[name] = dict(old_sha256=hashes.get(name), new_sha256=digest)
    if not changes: raise ValueError('no source amendment needed')
    write(directory/f'{len(previous)+1:03d}.json', dict(schema_version=1, observed_at=now(), reason=reason,
          registration_sha256=sha(out/'registration.json'), changes=changes))
    print('Recorded source amendment:', len(changes), 'files')


if __name__ == '__main__':
    amend(*sys.argv[1:])
