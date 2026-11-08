"""Restore only the repository-pinned public archive set into a fresh checkout.

The source is an existing local_recovery directory, never an account/credential root.
No network request, arbitrary digest argument, overwrite or persistent install exists.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from trading_lab.panel import ArchivePanel,ROOT,safe_file,PINS

def restore(source,target_root=ROOT):
    source=Path(source);target_root=Path(target_root);dest=target_root/'user_data/data/local_recovery'
    if dest.exists():raise ValueError('RESTORE_TARGET_EXISTS_PRESERVE_DATA')
    pins=json.loads(PINS.read_text())
    receipt=safe_file(source,'sources.json')
    if hashlib.sha256(receipt.read_bytes()).hexdigest()!=pins['sources_sha256']:raise ValueError('SOURCE_RECEIPT_NOT_PINNED')
    metadata=json.loads((ROOT/'research/session3_v3/native-metadata-pin.json').read_text())
    meta=safe_file(source,'current-exchangeinfo.json')
    if hashlib.sha256(meta.read_bytes()).hexdigest()!=metadata['sha256']:raise ValueError('METADATA_NOT_PINNED')
    jobs=[]
    for item in pins['archives']:
        rel=Path(item['path']).relative_to('user_data/data/local_recovery')
        path=safe_file(source,str(rel))
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('ARCHIVE_NOT_PINNED')
        jobs.append((path,rel))
    fixtures=json.loads((ROOT/'research/session3_v3/legacy-test-fixture-pins.json').read_text())
    for name,expected in fixtures.items():
        path=safe_file(source,name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('LEGACY_TEST_FIXTURE_NOT_PINNED')
        jobs.append((path,Path(name)))
    dest.mkdir(parents=True)
    # Preserve an interrupted copy for inspection; never erase the source.
    for path,rel in jobs:
        output=dest/rel;output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,output)
    shutil.copyfile(receipt,dest/'sources.json');shutil.copyfile(meta,dest/'current-exchangeinfo.json')
    panel=ArchivePanel(root=target_root)
    return dict(restored_archives=len(pins['archives']),restored_legacy_test_fixtures=len(fixtures),
                verified_bytes=panel.metrics['archive_bytes_verified'],next='Run pinned-container local_recovery_convert.py',execution_authority='NONE')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
    p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    if a.verify_only:
        panel=ArchivePanel();print(json.dumps(panel.metrics))
    else:print(json.dumps(restore(a.source)))
