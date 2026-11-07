# Security, preservation and recovery self-review

Scope: Codex subagent review of the v2 source and isolated temporary shadow roots. This is not native OpenBot application, a human audit, or independent exchange verification. No installed skills, profiles, conversations, credentials, databases or sixth-profile content were opened or modified by this reviewer.

Environment: `/tmp/openbot-v2-env/bin/python`, `PYTHONPATH=scripts`, current PR #18-derived checkout. All reproducers below exited 0; findings describe behavior before correction.

## P1 S01 — mutable transaction entries bypass the exact assignment scope

Location: `scripts/trading_lab/skill_install.py:78` and `:82`; unconditional receipt count at `:106` and `:133`.

Reproducer: copy the five versioned owners to temporary shadow roots; run `prepare`, obtaining PREPARED/27; retain only the first element of `transaction.private.json.entries`; call `apply(transaction, True)` and then `rollback(transaction, True)`.

Observed stdout:

```text
PREPARE PREPARED 27
TRUNCATED_PLAN {'status': 'APPLIED', 'assignments': 27, 'profiles_changed': False, 'native_state': 'NOT_VERIFIED'}
ROLLBACK {'status': 'ROLLED_BACK', 'originals_restored': True, 'assignments': 27}
```

The contract digest validates the pack, but does not bind the private plan entries, target paths or before/after inventories. A damaged or edited plan can therefore apply a subset and report a false complete operation. Changing the plan's `after` inventory together with staged files can also remove the intended relation to versioned skill bytes. The opt-in flag does not mean the owner approved such a changed scope.

Fix: before any apply/rollback mutation, validate the transaction schema, exactly 27 unique `(owner, skill_id)` pairs against the immutable contract, current staged/new inventories against the versioned pack/MIGRATION hashes, and each target's canonical root and expected skill basename. Preserve and validate a roots map. Reject missing, extra or duplicated entries. Report actual checked/applied counts.

Retest required: truncated, extra, duplicate and altered-after plans all fail before writes; complete prepare/apply/rollback remains successful.

## P1 S02 — parent symlink changes redirect the owner-opt-in installer

Location: `scripts/trading_lab/skill_install.py:44` checks parents only during prepare; `:84` and `:115` verify target contents without rechecking ancestor identity before apply/rollback.

Reproducer: prepare the same five temporary roots with a distinctive old marker in each SKILL.md. Move one mapped owner root aside, copy its original bytes to another temporary location, and replace the mapped root with a symlink to that other copy. Call apply. This uses only scratch directories.

Observed stdout:

```text
PARENT_CHANGED_TO_SYMLINK {'status': 'APPLIED', 'assignments': 27, 'profiles_changed': False, 'native_state': 'NOT_VERIFIED'}
UNRELATED_COPY_MODIFIED True
ORIGINAL_FOLDER_UNCHANGED True
```

Hash equality alone does not establish that the current parent is the owner root selected during prepare. All scratch changes were subsequently rolled back.

Fix: persist canonical roots, reject symlink/junction ancestors at every mutation boundary, require `absolute_path == resolved_path`, and bind each exact target to its prepared parent. Apply the same checks during recovery/rollback. Require stopped agent writers and document that multi-directory transactions are recoverable, not one OS-atomic replacement. For stronger adversarial race resistance, use anchored directory handles/no-follow operations; mere rechecks do not establish a cross-process security boundary.

Retest required: a changed parent symlink causes apply and rollback to fail closed before touching the redirected tree; unchanged roots complete normal rollback.

## P2 S03 — pack checker permits a symlinked owner directory

Location: `scripts/trading_lab/skills.py:39`, `:43` and leaf-only validation at `:59`.

Reproducer: copy PACK to a temporary folder; move `agents/astrabot-lead` outside that copy and replace it with a directory symlink to the moved copy. Point `skills.PACK` to this scratch pack and call `check_pack`.

Observed stdout: `SYMLINK_OWNER_CHECK PASS`.

All file bytes and link counts remain valid because the symlink is an ancestor. This violates the promised separate, non-symlink ownership folders even though content hashes pass.

Fix: explicitly reject symlinked pack/agents/owner/skills/assignment directories and any descendants before hashing. Validate no shared directory inode identities where supported. Retest a symlinked owner and symlinked skill root.

## Passing checks and limits

- Actual pack checker returned PASS with 5 owners, 27 assignments, 9 IDs and 55 skill files before mutation tests.
- `validate_envelope` rejected GATE with an `account` payload (`SKILL_SCHEMA_INVALID:payload`), READINESS with account input (same), and SHELL (`SKILL_SCHEMA_INVALID:kind`). Inbox does not pass account state to `gate`; signing remains a blocked stub. No inbox path to installer/admin/shell was found.
- Targeted privacy/credential scan of 73 new pack/source files returned zero private absolute path, agent UUID, private-key or credential-assignment matches. This targeted scan is not a complete secret detector; the root task should also run available gitleaks against the actual publication set.
- Native receipts remain separately marked; bridge replies explicitly say `NOT_CREATED_BY_FILE_BRIDGE`. Metadata cannot prove actual inference pixel delivery, and no such proof is asserted by these checks.
- Native agent state/permissions, power-loss durability across filesystems and live SQLite backup/restore were not tested by this reviewer. No installed activation is authorized or performed here.

Corrections/retests should be appended or incorporated by the primary agent before publication; the review's pre-fix failures must not be presented as final residual defects once verified fixes land.

## Fix verification — latest source, all focused commands exit 0

The primary agent added `validate_plan` to apply and rollback. It checks the exact 27 unique owner/skill pairs, target-to-owner-root mapping, expected versioned new inventories, canonical root paths and device/inode identity, legal journal indices, and symlinks in the transaction tree. `check_pack` now rejects symlinks anywhere in the pack before validating manifests.

The original three reproducers now fail closed before changing the shadow owner data:

```text
SUBSET PASS_REJECTED TRANSACTION_EXACT_27_ASSIGNMENTS_REQUIRED
ROOTSWAP PASS_REJECTED INSTALL_ROOT_IDENTITY_OR_SYMLINK_CHANGED
ROOTSWAP_OTHER_TREE_UNCHANGED True
PACKSYMLINK PASS_REJECTED PACK_SYMLINK_REJECTED
TX_ORIGINALS_SYMLINK PASS_REJECTED TRANSACTION_SYMLINK_REJECTED
```

An additional transaction-subdirectory issue was identified during retest: symlinks under `transaction/originals`, `removed`, `staged`, or `backup` could redirect recovery writes/renames if only the transaction root was checked. The primary agent added recursive rejection before apply/rollback. Focused `validate_plan` tests of all four subdirectory names confirmed:

```text
originals PASS_REJECTED TRANSACTION_SYMLINK_REJECTED
removed PASS_REJECTED TRANSACTION_SYMLINK_REJECTED
staged PASS_REJECTED TRANSACTION_SYMLINK_REJECTED
backup PASS_REJECTED TRANSACTION_SYMLINK_REJECTED
EXTERNAL_DIRECTORY_UNCHANGED True
```

Recovery was also tested with one injected `OSError` on the first staged-directory rename, after the original assignment directory had already moved. The normal exception recovery restored all 27 original inventories:

```text
INJECTED_FAILURE INJECTED_RENAME_FAILURE
RECOVERY_STATE ROLLED_BACK
ALL_27_ORIGINALS_RESTORED True
```

Final review result: **PASS for the reproduced scope/precondition/symlink/recovery cases**. Findings S01–S03 are fixed in the tested source. No installed activation occurred. Remaining limit: validation and path rechecks do not establish an OS isolation boundary against a concurrent process replacing paths between a check and a rename; stop agent writers as documented. No power-loss/fsync durability guarantee or Windows junction-specific execution test is inferred from these Linux temp tests.
