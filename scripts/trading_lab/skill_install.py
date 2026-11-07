"""Prepare and transactionally install exactly the scoped assignments; opt-in only.

No profile/database/model/permission changes. Stop agent writes before apply/rollback.
Multiple filesystem directories cannot be replaced with one OS-atomic operation;
the durable journal permits rollback after interruption. Never auto-invoked.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from binance_research_data import DataError
import openbot_current_market as market
from trading_lab.skills import PACK, check_pack, sha
from trading_lab.public import write_new
from trading_lab.workflow import atomic_reply


def inventory(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise DataError('INSTALL_DIRECTORY_REQUIRED')
    result = {}
    for p in directory.rglob('*'):
        if p.is_symlink():
            raise DataError('INSTALL_SYMLINK_REJECTED')
        if p.is_file(): result[p.relative_to(directory).as_posix()] = sha(p)
    return result


def validate_plan(plan, transaction):
    """Bind a private transaction to the exact pack and canonical original roots."""
    contract = market.load(PACK / 'contract.json')
    owners = {a['owner']: a for a in contract['assignments']}
    if (plan.get('schema') != 'openbot.skills.transaction.v2'
            or plan.get('contract_sha256') != sha(PACK / 'contract.json')
            or set(plan.get('roots', {})) != set(owners)):
        raise DataError('TRANSACTION_SCHEMA_OR_ROOTS')
    expected = {(a['owner'], sid) for a in owners.values() for sid in a['skills']}
    actual = [(e.get('owner'), e.get('skill_id')) for e in plan.get('entries', [])]
    if len(actual) != 27 or set(actual) != expected:
        raise DataError('TRANSACTION_EXACT_27_ASSIGNMENTS_REQUIRED')
    for owner, raw in plan['roots'].items():
        root = Path(raw).absolute()
        if (str(root) != raw or root.resolve() != root
                or any(p.is_symlink() for p in [root, *root.parents])
                or [root.stat().st_dev, root.stat().st_ino] != plan['root_identity'][owner]):
            raise DataError('INSTALL_ROOT_IDENTITY_OR_SYMLINK_CHANGED')
    tx = Path(transaction).absolute()
    if (tx.resolve() != tx or any(p.is_symlink() for p in [tx, *tx.parents])
            or any(p.is_symlink() for p in tx.rglob('*'))):
        raise DataError('TRANSACTION_SYMLINK_REJECTED')
    for e in plan['entries']:
        target = Path(plan['roots'][e['owner']]) / e['skill_id']
        source = PACK / 'agents' / e['owner'] / 'skills' / e['skill_id']
        if e['target'] != str(target) or e['after'] != inventory(source):
            raise DataError('TRANSACTION_TARGET_OR_PACK_INVENTORY_CHANGED')
        for relative in e['before']:
            p = Path(relative)
            if p.is_absolute() or '..' in p.parts: raise DataError('TRANSACTION_FILE_PATH')
    for key in ['originals_moved', 'applied']:
        indices = plan.get(key, [])
        if (not isinstance(indices, list) or len(set(indices)) != len(indices)
                or any(type(i) is not int or not 0 <= i < 27 for i in indices)):
            raise DataError('TRANSACTION_JOURNAL_INDICES')


def prepare(roots, transaction):
    check_pack()
    transaction = Path(transaction).resolve()
    if transaction.exists(): raise DataError('NEW_TRANSACTION_REQUIRED')
    contract = market.load(PACK / 'contract.json')
    expected = {a['owner'] for a in contract['assignments']}
    if set(roots) != expected: raise DataError('EXACT_FIVE_OWNER_MAP_REQUIRED')
    paths = [Path(roots[k]).resolve() for k in sorted(roots)]
    if len(set(paths)) != 5 or any(a in b.parents for a in paths for b in paths if a != b):
        raise DataError('SEPARATE_OWNER_ROOTS_REQUIRED')
    # Resolve is not permission to follow a junction/symlink supplied by a caller.
    for root in roots.values():
        p = Path(root).absolute()
        if any(q.is_symlink() for q in [p, *p.parents]): raise DataError('ROOT_SYMLINK_REJECTED')
    if any(transaction == p or transaction in p.parents or p in transaction.parents for p in paths):
        raise DataError('TRANSACTION_MUST_BE_OUTSIDE_INSTALLED_ROOTS')
    entries = []
    for owner in contract['assignments']:
        for sid in owner['skills']:
            target = Path(roots[owner['owner']]).resolve() / sid
            source = PACK / 'agents' / owner['owner'] / 'skills' / sid
            before = inventory(target)
            entries.append(dict(owner=owner['owner'], skill_id=sid, target=str(target),
                                before=before, after=inventory(source)))
    transaction.mkdir(parents=True)
    for e in entries:
        prefix = Path(e['owner']) / e['skill_id']
        shutil.copytree(Path(e['target']), transaction / 'backup' / prefix)
        shutil.copytree(PACK / 'agents' / prefix.parent / 'skills' / prefix.name, transaction / 'staged' / prefix)
        if inventory(transaction / 'backup' / prefix) != e['before']: raise DataError('BACKUP_VERIFY_FAILED')
        if inventory(transaction / 'staged' / prefix) != e['after']: raise DataError('STAGE_VERIFY_FAILED')
    plan = dict(schema='openbot.skills.transaction.v2', state='PREPARED', entries=entries,
                roots={k:str(Path(v).resolve()) for k,v in roots.items()},
                root_identity={k:[Path(v).stat().st_dev,Path(v).stat().st_ino] for k,v in roots.items()},
                contract_sha256=sha(PACK / 'contract.json'), originals_moved=[], applied=[],
                authorization='PENDING_OWNER_APPROVAL', provider_mirrors='NOT_TOUCHED',
                backup_verified=True)
    write_new(transaction / 'transaction.private.json', plan)
    return dict(status='PREPARED', assignments=len(entries), backup_verified=True,
                authorization='PENDING_OWNER_APPROVAL', private_plan=str(transaction / 'transaction.private.json'))


def apply(transaction, owner_authorized=False):
    if not owner_authorized: raise DataError('EXPLICIT_OWNER_OPT_IN_REQUIRED')
    check_pack()
    transaction = Path(transaction)
    path = transaction / 'transaction.private.json'
    plan = market.load(path)
    validate_plan(plan, transaction)
    if plan['state'] != 'PREPARED' or plan['contract_sha256'] != sha(PACK / 'contract.json'):
        raise DataError('INSTALL_STATE_OR_CONTRACT_DRIFT')
    # All preconditions checked before the first write to any installed directory.
    for e in plan['entries']:
        prefix = Path(e['owner']) / e['skill_id']
        if (inventory(e['target']) != e['before'] or inventory(transaction / 'backup' / prefix) != e['before']
                or inventory(transaction / 'staged' / prefix) != e['after']):
            raise DataError('INSTALL_PRECONDITION_HASH_MISMATCH')
        if Path(e['target']).stat().st_dev != (transaction / 'staged' / prefix).stat().st_dev:
            raise DataError('INSTALL_REQUIRES_SAME_FILESYSTEM')
    plan.update(state='APPLYING', authorization='EXPLICIT_OWNER_OPT_IN')
    atomic_reply(path, plan)
    try:
        for index, e in enumerate(plan['entries']):
            target = Path(e['target']); prefix = Path(e['owner']) / e['skill_id']
            original = transaction / 'originals' / prefix
            original.parent.mkdir(parents=True, exist_ok=True)
            # Journal intent before rename. Recovery inspects actual directory state.
            plan['originals_moved'].append(index); atomic_reply(path, plan)
            os.replace(target, original)
            os.replace(transaction / 'staged' / prefix, target)
            plan['applied'].append(index); atomic_reply(path, plan)
            if inventory(target) != e['after']: raise DataError('INSTALL_POSTCONDITION_FAILED')
        plan['state'] = 'APPLIED'; atomic_reply(path, plan)
    except BaseException:
        rollback(transaction, owner_authorized=True)
        raise
    return dict(status='APPLIED', assignments=27, profiles_changed=False, native_state='NOT_VERIFIED')


def rollback(transaction, owner_authorized=False):
    if not owner_authorized: raise DataError('EXPLICIT_OWNER_OPT_IN_REQUIRED')
    transaction = Path(transaction); path = transaction / 'transaction.private.json'; plan = market.load(path)
    validate_plan(plan, transaction)
    if plan['state'] not in {'APPLYING', 'APPLIED', 'ROLLING_BACK'}: raise DataError('ROLLBACK_STATE')
    # Verify every recoverable original and detect user changes before mutations.
    for index in plan['originals_moved']:
        e = plan['entries'][index]; prefix = Path(e['owner']) / e['skill_id']; target = Path(e['target'])
        original = transaction / 'originals' / prefix
        if original.exists():
            if inventory(original) != e['before']: raise DataError('ROLLBACK_ORIGINAL_TAMPER')
            if target.exists() and inventory(target) != e['after']: raise DataError('ROLLBACK_WOULD_OVERWRITE_DRIFT')
        elif not target.exists() or inventory(target) != e['before']:
            raise DataError('ROLLBACK_ORIGINAL_MISSING')
    plan['state'] = 'ROLLING_BACK'; atomic_reply(path, plan)
    for index in reversed(plan['originals_moved']):
        e = plan['entries'][index]; prefix = Path(e['owner']) / e['skill_id']; target = Path(e['target'])
        original = transaction / 'originals' / prefix
        if original.exists():
            if target.exists():
                removed = transaction / 'removed' / prefix; removed.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, removed)
            os.replace(original, target)
        if inventory(target) != e['before']: raise DataError('ROLLBACK_HASH_FAILED')
    plan['state'] = 'ROLLED_BACK'; atomic_reply(path, plan)
    return dict(status='ROLLED_BACK', originals_restored=True, assignments=27)


def main():
    p = argparse.ArgumentParser(description=__doc__); actions = p.add_subparsers(dest='action', required=True)
    a = actions.add_parser('prepare'); a.add_argument('roots_json', type=Path); a.add_argument('transaction', type=Path)
    for name in ['apply', 'rollback']:
        a = actions.add_parser(name); a.add_argument('transaction', type=Path); a.add_argument('--owner-authorized', action='store_true')
    args = p.parse_args()
    if args.action == 'prepare': result = prepare(market.load(args.roots_json), args.transaction)
    else: result = globals()[args.action](args.transaction, args.owner_authorized)
    print(json.dumps(result, indent=2)); return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (DataError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status':'BLOCKED','reason':str(error) if isinstance(error,DataError) else type(error).__name__}));sys.exit(1)
