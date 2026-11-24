# Dynamic native model identity and receipt compatibility

## Provider changes and capability inspection (24 November 2026)

`python -m researcher.openbot_runner provider-status` reads the selected
Researcher provider and exact model from the existing agent projection. It
does not start a run or contact a model. `MODEL_SELECTED` describes that
configuration; `provider_available: UNKNOWN_NOT_PROBED` does not assert an
available provider. `NATIVE_ADAPTER_SUPPORTED` means the compact reader is
implemented, not that this host or a particular run is verified. OpenCode's
older session-message reader is not a compact adapter; it reports
`PROVIDER_ATTESTATION_UNSUPPORTED` and the missing compact task, page and turn
attestation. Unknown providers report a missing native adapter. No receipt is
verified by this command (`native_receipt: NOT_CHECKED`). Actual collected
receipts retain their existing `native_invocation_verified` evidence fields.

Compact adapter selection is centralized in `native_identity`; the shared AI
gateway, runner and preflight check it without selecting a model. The only
implemented compact verifier remains Codex. A new provider still needs actual
provider-specific identity, task, page, response and tool-operation readers and
the corresponding dispatch integration; adding a registry entry alone is not
qualification or a complete adapter. Unsupported providers fail before the
AI stage, without a fallback.

Historical Codex readback now checks the original agent and workspace, then
verifies the captured provider, adapter, backend, session, turn and model from
the retained records. It does not compare the captured provider or model with
today's agent selection. Active work continues to compare both. Readback still
requires access to the original Codex provider database and rollout files: if
the private `provider_db` path was changed for a later provider, the correct
original read-only provider store must be supplied for replay. No alternate
store is guessed, and historical OpenCode's older reader retains its existing
constraints. These changes do not establish compact OpenCode replay or an
OpenCode-to-Codex two-run acceptance.

The recovery for job `20261121T155516Z-817636a12ff84a4797555d0d2887de42`
uses the exact parent and child Codex turn contexts for historical model
verification. OpenBot's event log records later model selections on the same
provider session. Both parent projections now
record `gpt-6.1-sol`. The original parent and child contexts record
`gpt-6-luna`. These are distinct model selections.

The child ran the ten page reads through the Codex 0.169 ordinal Code Mode
wrapper. The receipt reader matches one complete literal page-read script
to the successful command event and the paired model-facing output. It checks
the order, turn, call IDs, exit status and canonical bytes for each page. The
reader never evaluates persisted code. The existing flat receipt format
remains supported. Unknown wrappers or mixed transports fail closed.

| Revision | Commit |
|---|---|
| Prior Windows long-path baseline | `7282cf92ea7f185d38f87396f1ccfe3c51ec960e` |
| Approved receipt compatibility baseline | `c4e93d31f3dbc0074f6652f68b1cb4215c3382fe` |

The owner deliberately selected a different model after job
`20261121T155516Z-817636a12ff84a4797555d0d2887de42`. The earlier verifier
rejected that job with `NATIVE_MODEL_SWITCHED / IDENTITY / CONFIGURED_MODEL`
because the historical path compared its captured model with the current
Researcher configuration. The earlier regression reproduced that failure with a
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
  and final-delivery proof bind the original owner, workspace, provider,
  backend, session and turn. For Codex, the original turn's one recorded
  model context must exactly match the captured model. Relevant settings
  records must agree. App and provider model projections can advance after
  session reuse. The child gets the same per-turn check in its own distinct
  session. Packet hashes, page proof, one-shot dispatch and freshness remain
  enforced.

The changes are in `native_identity.py`, `native_runtime.py`, `native_app.py`,
`native_host.py`, `native_workflow.py`, `openbot_runner.py`,
`agent_review.py` and `native_codex.py`. Both paths share the existing exact
Codex rollout checks.

## Earlier verification at the approved baseline

The full offline suite passed **532 tests** in 529.223 seconds.
The focused identity and receipt suite passed **63 tests**. Configuration
validation, syntax checks and 25 protected paths passed.
The new fixtures cover a completed model-A job after a selection change,
a second authorized job with model B, rejection of changes during preflight
and native work, tampering and expiry.
The earlier tests treated parent session and Codex thread model drift as
errors. They kept both models synchronized for historical fixtures and emitted
the flat child tool format. The Windows long-path regression and simulated
ten-page receipt passed at that checkpoint. The actual host evidence exposed
the two compatibility gaps described above.

[Regression tests](../../tests/test_dynamic_model_identity.py) · [Draft PR and CI](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/pull/24/checks)

## Receipt compatibility verification

The same-session parent regression, historical child projection regression and
ten-page Code Mode regression all failed on the approved baseline. They pass
with the compatibility changes. The complete offline suite passed all 536
tests in 1249.342 seconds. Configuration validation and byte comparisons
against the baseline for 28 protected paths passed. The tests cover later
model selection on the same session, genuine same-turn contradictions,
missing and duplicate contexts, ownership and task binding, both page-read
formats, command and output tampering, expiry and Windows long paths.

The existing read-only helper ran under Windows Python 3.12.10 against the
original saved job and returned exit 0. The original request was timestamped
`2026-11-21T15:58:19.798240Z`. The observation cutoff was
`2026-11-21T16:08:19.798239Z`, one microsecond before its original expiry.

| Historical check | Status | Evidence |
|---|---|---|
| Request and material | PASS | Request SHA-256 `72e3bae7c8182d3848f0890fa579447f05b5c452f5b41c133e666280bcf3c22b` and matching material. |
| Ticket and saved arguments | PASS | Arguments SHA-256 `40dd586bb62538bb9592b50e824001714574b81a02c514533e7a1c78c87dc181`. |
| Exact parent identity and submission | PASS | Exact turn model `gpt-6-luna`. One submission at `15:58:51.960Z`, acknowledged at `15:58:51.996Z` with the matching child task. |
| Child execution | PASS | Distinct child turn, model `gpt-6-luna`, with 11 provider response IDs. Completed at `16:00:21.710Z` within the original envelope. |
| Code Mode page proof | PASS | 10 of 10 pages. Canonical packet SHA-256 `e1d6cfe133b7dab615698d3a9d7c46cb4b9b30f30d1b119dcb0e72ea6e627728`. |
| Final reply | PASS | Exact app and provider final, reply validation `VALIDATED`. |
| Saved evidence | PASS | State, request, arguments and dispatch file hashes agree before and after readback. |

The saved job status is `PARTIAL`. The historical reply is expired for
current research. The readback used saved evidence only.

## Bounded owner-host readback

Use the same approved WSL checkout and configured Windows Python. Verify that
the remote is `KasunKarandagolla/OpenBot-Trading-Lab`. Fast-forward to the tested
implementation while the worktree is clean. Continue only if the block succeeds.

```bash
receipt_commit=${RECEIPT_COMMIT:?Set the verified receipt compatibility commit}
test "$(git branch --show-current)" = feature/external-first-market-researcher &&
test -z "$(git status --porcelain)" &&
git fetch --no-tags origin refs/heads/feature/external-first-market-researcher &&
git merge-base --is-ancestor "$receipt_commit" FETCH_HEAD &&
git merge --ff-only "$receipt_commit" &&
test "$(git rev-parse HEAD)" = "$receipt_commit"
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

The configured, app-session and Codex-thread model comparisons are
informational on historical readback. Require the exact captured model in both
original provider turns, the original packet hashes, `PARENT_RECEIPT` with an
acknowledged matching task, and `HISTORICAL_RECEIPT` with `verified=true` and
ten pages. Keep the sanitized stage if verification fails.

The verifier opens the saved records read-only and holds the receipt in
memory. It checks the original recorded freshness window. Expired advice
stays outside current-market research. A future live acceptance requires a
clean checkout at the approved revision, a passing read-only preflight for the
then-current provider schema and installed skill hashes, and separate owner
authorization in the existing Researcher's main chat. Capture the active model
from that new turn and verify its own submission, child reply and delivery.
