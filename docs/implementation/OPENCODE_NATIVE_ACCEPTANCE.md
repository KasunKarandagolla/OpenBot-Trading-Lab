# OpenCode native acceptance - prepared, not run

Status: **CODE_IMPLEMENTED / OFFLINE_VERIFIED / READY_FOR_NATIVE_ACCEPTANCE /
NATIVE_ACCEPTANCE_NOT_CLAIMED**. Nothing in this document authorizes a run.
Each test below needs its own explicit owner message in the existing Researcher
main chat, and each stops on the first identity, schema, evidence or skill
failure. Do not switch provider or model to make a test pass. Keep
`trade_authorization=false`.

The adapter accepts OpenCode session record version `2.4.1` only. The exact
provider, model and effort are frozen from the configured agent at job start
and compared with the retained provider session. A different version, model,
effort, turn window, part order or page hash fails closed. Reasoning text is
validated structurally and never returned or published.

## 1. Prepare the existing checkout

Use the existing WSL checkout and its private path-only audit configuration.
Do not create a second checkout or a second Researcher.

```bash
git status --porcelain
git fetch origin feature/external-first-market-researcher
git checkout feature/external-first-market-researcher
git merge --ff-only origin/feature/external-first-market-researcher
git rev-parse HEAD
```

Require an empty status, the expected repository and branch, and the exact
published commit. Stop on divergence, local changes, a different remote or a
missing authorization. Do not reset, force, merge main or discard work. Keep
ignored research state and historical job/provider records.

## 2. Install the orchestration skill

Render the checkout path and install the skill through the protected procedure
in [Native handoff v2](NATIVE_HANDOFF_V2.md):

```bash
sed "s|@@RESEARCH_ROOT@@|$PWD|g" integration/openbot-market-research/SKILL.md
```

Install the rendered file as the `openbot-market-research` skill, then read back
the installed revision and hash. Keep the protected `market-research-review`
skill unchanged. A repository change does not install or register a host skill.

## 3. Point the private audit config at the active provider

The private file is `work/openbot-integration/native-audit-local.json`; it is
ignored and must never be committed or pasted into chat. It holds one
`provider_db`:

- OpenCode: `%USERPROFILE%\.local\share\opencode\opencode.db`
- Codex: `%USERPROFILE%\.codex\state_5.sqlite`

Keep `native_python` pointing at the installed Windows `python.exe` so WSL
delegates WAL reads instead of opening the database across `/mnt/c`. Do not copy
the database or open it read-write. Restore the Codex path before a Codex run.

## 4. Preflight - no model and no market request

```bash
wsl.exe --cd '<checkout>' -- python3 -m researcher.openbot_runner provider-status
wsl.exe --cd '<checkout>' -- python3 -m researcher.openbot_runner preflight
```

`provider-status` must report `native_adapter: NATIVE_ADAPTER_SUPPORTED` and
`adapter: OPENCODE_V2_SESSION_PART` with `native_receipt: NOT_CHECKED`.
`preflight` must report `provider_schema: OPENCODE_V2_SESSION_PART`, the
installed skill hashes, and zero model and market requests. Stop on any
identity, provider, schema or skill failure.

## 5. Test 1 - synthetic compact paged Discovery

Run only after the owner sends the exact canonical message in
`OPENCODE_TEST1_COMPACT_PROMPT.txt`, replacing `@@APPROVED_COMMIT@@` with the
published commit. This file is the single source of truth for the owner message.
It selects the existing `COMPACT_POLL_TEST` runner mode and proves the compact
parent task boundary, not market research.

After the response and attachment are saved, replay the job read-only from the
checkout root:

```bash
python3 -m researcher.openbot_runner replay-native --job-id JOB_ID
```

A pass establishes only this host, provider, model and record version for one
paged Discovery boundary. It is not a two-stage or live-market pass.

## 6. Test 2 - archived two-stage research

Run only after Test 1 passes and the owner separately authorizes the exact
canonical message in `OPENCODE_TEST2_ARCHIVED_PROMPT.txt`, replacing
`@@APPROVED_COMMIT@@` with the published commit. This file is the single source
of truth for the owner message. It selects `AI_CORE_SMOKE`, using the shipped
retained market fixture and two native stages; it makes zero market-data
requests.

Replay with the same `replay-native --job-id JOB_ID` command. Require two
independently verified child receipts for `DISCOVERY` and `SHORTLIST`, exact
native arguments, complete provider-attested page delivery, accepted citations,
`AI_RESEARCH_COMPLETE` reconciliation, zero market requests, a verified archive
and `VERIFIED` delivery. An empty qualified shortlist can pass.

## 7. Test 3 - full live read-only research

Run only after Tests 1 and 2 pass and the owner separately authorizes the exact
canonical message in `OPENCODE_TEST3_LIVE_PROMPT.txt`, replacing
`@@APPROVED_COMMIT@@` with the published commit. This file is the single source
of truth for the owner message. It selects `SETUP_AND_ACCEPTANCE`, the existing
full read-only research mode, and is the only test that may read current market
data.

Replay with the same command. Do not claim a complete AI Researcher from a
partial run, a fixture, or a saved artifact path in prose.

## 8. Rollback

On failure, retain the job ID, provider/app records and artifact. Use the
bounded read-only replay to capture the first failure. For a runtime rollback,
use a separate clean worktree at the previously published commit and reinstall
that checkout's orchestration skill through the protected procedure. Keep the
feature branch, PR #24 and both job directories intact. Do not force push,
merge PR #24 or switch providers to manufacture a pass.
