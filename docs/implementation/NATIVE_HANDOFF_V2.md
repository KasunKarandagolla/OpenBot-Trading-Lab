# OpenBot native review handoff v2

## Runtime contract

OpenBot 0.71.0 advertises `openbot.start_task` through the main chat's
`openbot.tool_describe` and `openbot.tool_search`. Its Codex integration
deliberately excludes the `openbot` namespace from isolated `exec` catalogs.
Call `openbot.tool_call` in the main chat with `name: openbot.start_task` and
the runner's `start_task_arguments` as `arguments`.
[Discovery and routing](https://github.com/nightly-labs/openbot/blob/a0b754f8baa8fb49fb200ffb3759b17429a962a9/src/backend/agent/tool-catalog.ts)
· [Codex tool visibility](https://github.com/nightly-labs/openbot/blob/a0b754f8baa8fb49fb200ffb3759b17429a962a9/src/backend/agent/developer-instructions.ts#L496-L500)

`start_task` accepts only inline `title` and `brief` strings. Its schema trims
both and caps the title at 120 characters and the brief at 100,000 characters.
The mailbox also enforces 100,000 UTF-16 code units on the trimmed brief. The
95,759-character fixture fits both limits, but the full object exceeds a 64 KiB
console and the schema removes the old brief's terminal newline. The strict
schema rejects a file argument. Codex also caps persisted command output at
64 KiB. There is no documented file-to-dynamic-tool binding in this Codex
runtime. [OpenBot task schema and handler](https://github.com/nightly-labs/openbot/blob/a0b754f8baa8fb49fb200ffb3759b17429a962a9/src/backend/agent-tasks/agent-tasks.ts#L50-L55)
· [OpenBot input limits](https://github.com/nightly-labs/openbot/blob/a0b754f8baa8fb49fb200ffb3759b17429a962a9/packages/contracts/src/input-limits.ts#L75-L86)
· [Mailbox UTF-16 length check](https://github.com/nightly-labs/openbot/blob/a0b754f8baa8fb49fb200ffb3759b17429a962a9/src/backend/mailbox-store.ts#L606-L607)
· [Codex history bounds](https://github.com/openai/codex/blob/d32063f96c2dff1dc96af839b3952abb6acfeda4/codex-rs/rollout/src/policy.rs)

The runner publishes a compact, trim-stable `title` and `brief` in `PAGED_V2`.
The main agent passes that JSON object directly to the native tool. The brief
identifies the complete canonical packet by job, material and SHA-256. In the
isolated task, the same agent reads numbered ASCII JSON records through a fixed
WSL command. Decoding and concatenating the `text` fields reproduces the full
skill and evidence bytes. The reader associates each permitted command with its
provider output and verifies every page, the original app brief, the reserved
argument hash, the parent call, the task ID and the child provider/app final.
The child can use only these exact page reads. A changed or missing page cannot
produce accepted advice.

The runner observes submission for up to 90 seconds after publication. After an
observed attempt or acknowledgment it allows up to 30 seconds per phase for the
response or matching task, subject to the overall wait and freshness limits.
An in-flight native read can take up to 30 seconds. The 600-second freshness
envelope includes publication, page access, collection and import. A wall-clock
or elapsed-time discontinuity is evidence of an observation gap. Confirming
Modern Standby requires host power logs. No ticket reissue or automatic native
retry occurs. `REVIEW_RUNNING` requires a matching app task, `MODEL_EXECUTED`
requires the complete native provider receipt, and `REVIEW_VERIFIED` indicates
validated JSON. The job still requires reconciled advice and actual ZIP delivery
for live acceptance.

## Install into the existing Researcher

1. In the approved WSL checkout, verify the remote and branch, fetch the
   feature branch and fast-forward to the published commit on draft PR #24.
   Keep the previously approved WSL checkout path and the path-only private
   audit config. Use the same Windows OpenBot installation and configured model.

   ```bash
   git remote get-url origin
   test "$(git branch --show-current)" = feature/external-first-market-researcher &&
   test -z "$(git status --porcelain)" &&
   git fetch origin refs/heads/feature/external-first-market-researcher &&
   git merge-base --is-ancestor "$APPROVED_SHA" FETCH_HEAD &&
   git merge --ff-only "$APPROVED_SHA" &&
   test "$(git rev-parse HEAD)" = "$APPROVED_SHA"
   ```

   Set `APPROVED_SHA` to the exact published commit and confirm `origin` is
   `KasunKarandagolla/OpenBot-Trading-Lab` before running the fast-forward.
2. From that clean checkout, set `RESEARCHER_WORKSPACE_WSL` to the existing
   agent workspace as seen from WSL (for example, convert the existing Windows
   workspace path with `wslpath -u`). Run the following with WSL Python 3.11+
   to render and write both orchestration skill copies as UTF-8 bytes. The
   command checks the canonical orchestration hash and the protected analytical
   copy before updating either orchestration mirror.

   ```bash
   python3 - "$RESEARCHER_WORKSPACE_WSL" <<'PY'
   from hashlib import sha256
   from pathlib import Path
   import os
   import sys
   import tempfile

   root = Path.cwd().resolve()
   workspace = Path(sys.argv[1]).expanduser()
   if not workspace.is_absolute() or not workspace.is_dir():
       raise SystemExit('Use the existing absolute WSL agent workspace')
   source = (root / 'integration/openbot-market-research/SKILL.md').read_bytes()
   if sha256(source).hexdigest() != '1170500f182592cf6fe89f7aae04fb74fe68b7a0de96ae68b2bb2d601f318a27':
       raise SystemExit('Unexpected orchestration skill source')
   expected_review = '96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb'
   rendered = source.replace(b'@@RESEARCH_ROOT@@', str(root).encode('utf-8'))
   targets = [workspace / prefix / 'skills/openbot-market-research/SKILL.md'
              for prefix in ('.agents', '.claude')]
   review_found = False
   for target in targets:
       if any(path.is_symlink() for path in (target, *target.parents)):
           raise SystemExit(f'Symlinked skill path: {target}')
       review = target.parent.with_name('market-research-review') / 'SKILL.md'
       if review.is_file():
           if (any(path.is_symlink() for path in (review, *review.parents))
                   or sha256(review.read_bytes()).hexdigest() != expected_review):
               raise SystemExit(f'Protected skill hash mismatch: {review}')
           review_found = True
   if not review_found:
       raise SystemExit('Existing protected review skill is missing')
   for target in targets:
       target.parent.mkdir(parents=True, exist_ok=True)
       with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
           temporary = Path(stream.name)
           stream.write(rendered)
       try:
           os.replace(temporary, target)
       finally:
           temporary.unlink(missing_ok=True)
       if target.read_bytes() != rendered:
           raise SystemExit(f'Installed skill readback differs: {target}')
       print(sha256(rendered).hexdigest(), target)
   PY
   ```

3. In the existing Researcher's main OpenBot chat, run the native discovery
   check and the setup-only `wsl.exe --cd 'APPROVED_WSL_CHECKOUT' -- python3 -m
   researcher.openbot_runner preflight`. Expect
   `NATIVE_READER_AND_INSTALLED_SKILLS_VERIFIED`, zero model and market requests,
   and the installed hash printed by step 2. For owner-authorized live
   acceptance, render the exact prompt and send it to that same chat:

   ```bash
   sed "s/@@APPROVED_COMMIT@@/$(git rev-parse HEAD)/g" docs/implementation/OPENBOT_RECOVERY_ACCEPTANCE_PROMPT.txt
   ```

4. Check one observed native submission per material, matching OpenBot task ID,
   all page receipts, validated advice, reconciliation and the verified ZIP and
   final delivery. Fixture and archived transport counters are separate from
   current-market execution. Trading authority remains false.
