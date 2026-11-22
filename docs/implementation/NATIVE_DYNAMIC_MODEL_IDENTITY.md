# Dynamic native model identity

| Revision | Commit |
|---|---|
| Approved tested baseline | `7282cf92ea7f185d38f87396f1ccfe3c51ec960e` |
| Tested implementation for owner-host readback | `c4e93d31f3dbc0074f6652f68b1cb4215c3382fe` |

The owner deliberately selected a different model after job
`20261121T155516Z-817636a12ff84a4797555d0d2887de42`. The earlier verifier
rejected that job with `NATIVE_MODEL_SWITCHED / IDENTITY / CONFIGURED_MODEL`
because the historical path compared its captured model with the current
Researcher configuration. The new regression reproduced that failure with a
complete simulated ten-page receipt.

## Identity rules

- **New job.** The existing runner reads the configured Researcher and its
  active provider session and captures the exact model, provider, adapter and
  session references. Before market work the existing command attestation
  checks the captured identity against the active configuration, app session,
  provider thread, rollout context and owner authorization. A new model must
  be supported by the existing provider and reader. Model identifiers are
  compared exactly as recorded.
- **Active native work.** Preparation, dispatch reservation, submission
  observation, collection and advice import still require the configured
  model to match the job's captured model. These operations verify the
  original parent while allowing OpenBot's active pointer to move to a
  child. The Windows reader receives the same active check.
- **Historical receipt.** Read-only submission observation, receipt collection
  and final-delivery proof use the original owner, session and model. They
  compare the captured identity to the exact parent app session, Codex thread
  and rollout, and check the child against the same historical model.
  The current model can differ. Current agent and workspace ownership,
  existing provider and adapter checks, packet hashes, page proof, one-shot
  dispatch and freshness remain enforced.

The changes are in `native_identity.py`, `native_runtime.py`, `native_app.py`,
`native_host.py`, `native_workflow.py`, `openbot_runner.py`,
`agent_review.py` and `native_codex.py`. Both paths share the existing exact
Codex rollout checks.

## Verification

The full offline suite passed **532 tests** in 529.223 seconds.
The focused identity and receipt suite passed **63 tests**. Configuration
validation, syntax checks and 25 protected paths passed.
The new fixtures cover a completed model-A job after a selection change,
a second authorized job with model B, rejection of changes during preflight
and native work, tampering and expiry.
Existing independent fixtures still reject discrepancies in the parent app
session, Codex thread and rollout, and child model. The Windows long-path
regressions also pass. The original Windows packet and ten saved pages were
verified by the owner. The readback below also verified a simulated ten-page
receipt after a configured model change. The original model receipt remains
pending host readback.

[Regression tests](../../tests/test_dynamic_model_identity.py) · [Draft PR and CI](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/pull/24/checks)

## Bounded owner-host readback

Use the same approved WSL checkout and configured Windows Python. Verify that
the remote is `KasunKarandagolla/OpenBot-Trading-Lab`. Fast-forward to the tested
implementation while the worktree is clean. Continue only if the block succeeds.

```bash
receipt_commit=c4e93d31f3dbc0074f6652f68b1cb4215c3382fe
test "$(git branch --show-current)" = feature/external-first-market-researcher &&
test -z "$(git status --porcelain)" &&
git fetch --no-tags origin refs/heads/feature/external-first-market-researcher &&
git merge-base --is-ancestor "$receipt_commit" FETCH_HEAD &&
git merge --ff-only "$receipt_commit" &&
git diff --exit-code "$receipt_commit" HEAD -- . \
  ':(exclude)docs/implementation/NATIVE_DYNAMIC_MODEL_IDENTITY.md' \
  ':(exclude)docs/implementation/NATIVE_RECEIPT_WINDOWS_RECOVERY.md' \
  ':(exclude)docs/implementation/PROGRESS.md'
```

Copy the Python block from the Windows readback procedure as
`work/native-receipt-check.py`, or reuse the existing copy of that block. Select
the 64-hex material from the original job's ten-page dispatch ticket and use
it as `RECEIPT_MATERIAL`. Keep the existing checkout path and recorded job files.
[Existing read-only verifier](NATIVE_RECEIPT_WINDOWS_RECOVERY.md#bounded-owner-host-readback)

```bash
read -r -p 'Original dispatch material (64 lowercase hex): ' RECEIPT_MATERIAL &&
[[ "$RECEIPT_MATERIAL" =~ ^[0-9a-f]{64}$ ]] &&
receipt_python=$(python3 -B -c 'from researcher.native_identity import load_private,local_path; print(local_path(load_private("work/openbot-integration/native-audit-local.json")["native_python"]))') &&
timeout 90s "$receipt_python" -B -X utf8 "$(wslpath -w "$PWD/work/native-receipt-check.py")" \
  "$(wslpath -w "$PWD")" "$RECEIPT_MATERIAL"
```

`CONFIGURED_RESEARCHER.model` is informational in this readback, so the owner's
subsequent choice can differ. Require the historical app, Codex thread and
attested rollout model to match exactly. Require the original packet hashes,
`PARENT_RECEIPT` with an acknowledged task, and `HISTORICAL_RECEIPT` with
`verified=true` and ten pages. Compare the reported request, arguments and
packet SHA-256 values with the original saved evidence where available. Keep the sanitized stage if verification fails.

The verifier opens the saved records read-only and holds the receipt in
memory. It checks the original recorded freshness window. Expired advice
stays outside current-market research. A later live acceptance requires
a successful owner-host receipt check and separate owner authorization for
a run using the then-current Researcher and installed skills.
