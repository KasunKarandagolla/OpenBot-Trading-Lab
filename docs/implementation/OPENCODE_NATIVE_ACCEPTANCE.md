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

Require `NATIVE_ADAPTER_SUPPORTED`, provider schema `OPENCODE_V2_SESSION_PART`,
the installed skill hashes, and zero model and market requests. Stop on any
identity, provider, schema or skill failure.

## 5. Test 1 - synthetic compact paged Discovery

Run only after the owner sends this message. It proves the compact parent task
boundary, not market research.

```text
I authorize one OpenCode compact native paged Discovery test using the existing Trading Lab Market Researcher at commit @@APPROVED_COMMIT@@. Keep the currently configured OpenCode provider, model and reasoning effort. Use one synthetic research task. Make zero market-data requests and keep trade_authorization=false.

In this main chat, discover openbot.start_task and openbot.attach_files_to_response with openbot.tool_describe. Run the installed setup-only preflight and stop on any identity, skill, schema or provider failure. Start one job with the fixed runner command in the installed orchestration skill and one literal 32-character lowercase hexadecimal request ID. Reuse the exact status_command returned by the runner for every poll.

When ordinary status returns a complete OPENBOT_COMPACT_DISPATCH_V1 object with submission_permitted true, the exact start_task_arguments and end_frame END_OPENBOT_COMPACT_DISPATCH_V1, submit those exact arguments once through native openbot.tool_call to openbot.start_task. Preserve the brief newline. Do not reconstruct a command or path. If the frame is clipped or the submission is uncertain, stop and report it; never submit or request the task again.

Continue polling to completion and attach the returned ZIP with openbot.attach_files_to_response. Report the job ID, ZIP SHA-256, provider/task receipt, evidence page verification and zero market requests. This test contains no current-market analysis.
```

After the response and attachment are saved, replay the job read-only from the
checkout root:

```bash
python3 -m researcher.openbot_runner replay-native --job-id JOB_ID
```

A pass establishes only this host, provider, model and record version for one
paged Discovery boundary. It is not a two-stage or live-market pass.

## 6. Test 2 - archived two-stage research

Run only after Test 1 passes and the owner separately authorizes this message.
It uses the shipped retained market fixture and two native stages.

```text
I authorize one archived-only OpenCode AI-core acceptance run using the existing Trading Lab Market Researcher at commit @@APPROVED_COMMIT@@. Use the shipped retained market fixture and at most two same-agent native tasks for discovery and final interpretation. Keep the current OpenCode provider, model, reasoning effort and permissions. Make zero market-data requests and keep trade_authorization=false.

In this main chat, discover openbot.start_task and openbot.attach_files_to_response with openbot.tool_describe. Run the installed setup-only preflight and stop on failure. Start the job with the fixed runner command in the installed orchestration skill and one literal 32-character lowercase hexadecimal request ID. Poll the same job in this turn until an artifact or terminal failure appears, using the exact status_command returned by the runner.

For each REVIEW_READY, require the complete OPENBOT_COMPACT_DISPATCH_V1 frame with submission_permitted true, the exact start_task_arguments and END_OPENBOT_COMPACT_DISPATCH_V1. Submit those exact arguments once through native openbot.tool_call to openbot.start_task. Preserve the brief newline. If the frame is clipped or the submission is uncertain, stop and report it; never retry a granted or uncertain submission. Do not submit a second task for the same stage.

Report archived-only discovery and shortlist statuses, verified receipt count, reconciliation, zero market requests, the job ID and ZIP SHA-256. Attach the returned ZIP with openbot.attach_files_to_response and finish the main turn. The receipt observer verifies delivery after the final response is saved. Do not start a current-market run.
```

Replay with the same `replay-native --job-id JOB_ID` command. Require two
independently verified child receipts for `DISCOVERY` and `SHORTLIST`, exact
native arguments, complete provider-attested page delivery, accepted citations,
`AI_RESEARCH_COMPLETE` reconciliation, zero market requests, a verified archive
and `VERIFIED` delivery. An empty qualified shortlist can pass.

## 7. Test 3 - full live read-only research

Run only after Tests 1 and 2 pass and the owner separately authorizes this
message. It is the only test that may read current market data.

```text
I authorize one complete read-only OpenCode research run using the existing Trading Lab Market Researcher at commit @@APPROVED_COMMIT@@. Keep the current OpenCode provider, model, reasoning effort, agent, permissions and both installed skills. Make zero market-data requests before the run's normal read-only scan, place no orders, enable no scheduling and keep trade_authorization=false.

Use the checkout path in the installed openbot-market-research skill. Verify the repository is KasunKarandagolla/OpenBot-Trading-Lab, the branch is feature/external-first-market-researcher and the checkout is clean at the approved commit. Stop on divergence, local changes, a different remote or a missing authorization; do not reset, force, merge main or discard work.

Run configuration validation and the setup-only preflight from that checkout with the existing native command tool. Verify the configured agent, provider, model, effort, provider schema and installed orchestration and protected review skills. In this main chat, discover openbot.start_task and openbot.attach_files_to_response with openbot.tool_describe. These checks make zero model and market requests. Stop if they fail.

Start the job with the fixed runner command in the installed orchestration skill and one literal 32-character lowercase hexadecimal request ID. Keep this main turn active and poll with the exact status_command returned by the runner. For each REVIEW_READY, require the complete OPENBOT_COMPACT_DISPATCH_V1 frame with submission_permitted true, the exact start_task_arguments and END_OPENBOT_COMPACT_DISPATCH_V1. Submit those exact arguments once through native openbot.tool_call to openbot.start_task. Preserve the brief newline. If the frame is clipped or the submission is uncertain, stop and report it; never retry a granted or uncertain submission.

Complete the available-market scan, selective structural investigation, genuine native review and import, point refresh, deterministic reconciliation, persisted watches and candidates, and a verified ZIP. All viable finalists must be reviewed or explicitly marked unreviewed or stale. Keep unavailable specialist inputs and excluded histories visible. Zero conditional candidates and zero strict READY are valid outcomes. Do not require all eligible contracts to have full history or every method to find a setup.

Attach the exact returned artifact.attachment_path with openbot.attach_files_to_response. Report the UTC job ID, published commit, ZIP SHA-256, screening and structural coverage, active watch coins, conditional research candidates, strict READY count, native task states and verified model attempts, imported interpretation and reconciliation changes, resource metrics and precise omissions. Confirm trade_authorization=false. The runner's bounded receipt observer records the subsequent actual parent attachment and final proof; a completed worker or an attachment path in prose is insufficient. Claim full native acceptance only after the independent replay observes the owner, live scan, valid native interpretation and actual ZIP delivery.
```

Replay with the same command. Do not claim a complete AI Researcher from a
partial run, a fixture, or a saved artifact path in prose.

## 8. Rollback

On failure, retain the job ID, provider/app records and artifact. Use the
bounded read-only replay to capture the first failure. For a runtime rollback,
use a separate clean worktree at the previously published commit and reinstall
that checkout's orchestration skill through the protected procedure. Keep the
feature branch, PR #24 and both job directories intact. Do not force push,
merge PR #24 or switch providers to manufacture a pass.
