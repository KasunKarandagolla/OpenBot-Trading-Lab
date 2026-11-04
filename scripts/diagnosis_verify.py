"""Read-only verification of parent, current experiment seals and delivery hashes."""
from diagnosis_common import *

def verify():
    parent=verify_parent();seal=read(OUT/'final-seal.json')
    for group in ('source_hashes','evidence_hashes'):
        for name,expected in seal[group].items():
            if sha(ROOT/name)!=expected:raise ValueError('diagnosis final seal mismatch '+name)
    # Reuse the native runner's input/feature/preregistration verification. Import
    # needs the pinned research image; it performs no exchange calls or execution.
    from diagnosis_native import verify as native_verify
    for cohort in ('development','earlier','later'):native_verify(cohort)
    for path in (OUT/'native').glob('*/provenance.json'):
        p=read(path);archive=ROOT/p['archive']
        if sha(archive)!=p['archive_sha256'] or sha(archive.parent/'config.json')!=p['config_sha256']:raise ValueError('native private export mismatch')
    answer=dict(parent=parent,sealed_sources=len(seal['source_hashes']),sealed_evidence=len(seal['evidence_hashes']),native_records=len(list((OUT/'native').glob('*/provenance.json'))),changed=[])
    print(__import__('json').dumps(answer,indent=2));return answer

if __name__=='__main__':verify()
