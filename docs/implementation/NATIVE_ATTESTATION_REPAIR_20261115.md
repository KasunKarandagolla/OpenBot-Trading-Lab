# Native-provider attestation repair — 15 November 2026

**Engineering validation only. Live status: NOT_RERUN_IN_CODEX. OpenBot acceptance
remains pending.** The owner reports orchestration skill v1 installed; this repair
requires no skill reinstall, model reassignment or app permission change.

## Confirmed root cause

The clean approved integration checkout and fetched remote both started at
`d4b2330370aceae62075ff80dceb9d5b3962d1b2`. PR24 is draft; main and older checkouts
were left alone. The saved failed job
`20261115T155254Z-3ad3e1865ecd4fb99a8de6ae65129913` contains only state.json,
process.json and worker.log. State is FAILED/NATIVE_PROVIDER_SCHEMA_UNSUPPORTED;
there is no start_proof, stage, scanner_started_at_utc, research ledger or report.
SCANNING was never entered. This failure supplies no analytics outcome.

Replaying the original read-only parser on the exact session selected through
that job's identity hashes reproduced **researcher/native_codex.py:65** at the
starting commit. Its prefix regex required `timestamp` immediately followed by
`type`. The authentic envelope is `timestamp` (string), `ordinal` (integer),
`type` (string), `payload` (object), with optional top-level `metadata` on response
items. The additional ordinal makes the original regex fail before session_meta
validation. Identity/workspace/backend matched; actual CLI version is 0.169.0,
OpenBot origin is openbot and backend is openai. Existing installation metadata
previously verified OpenBot 0.71.0. No version change was the cause.

A second confirmed incompatibility would have blocked the same start proof:
`recorded_launch_matches` allowed only PowerShell `-Command`, while the actual
successful receipt uses `-NoProfile -Command`. Its script argv exactly matches
the fixed WSL checkout/module/start/request ID invocation. Thread, turn, context
model/workspace and successful integer exit match. No command/output contents
are reproduced here. The repaired archived parser and matcher find exactly one
matching successful launch receipt. The old job was neither modified nor resumed.

Inherited fixtures passed because they serialized `timestamp,type,payload` with
no ordinal and exercised only the three-element PowerShell command vector.
They did not model these two authentic representations.

## Scoped repair

- `native_codex.py`: structurally locate envelope fields independently of JSON
  key order, preserving private historical/reasoning payload skipping; reject
  duplicate keys, malformed in-scope JSON, missing metadata, ordinal gaps and
  timestamp/semantic order failures. Verify session/backend against provider DB,
  model against DB/context, handoff thread and context workspace. Require actual
  complete brief bytes within a provider text part: inserting separators cannot
  repair a missing newline. Verify final response-item text when present as well
  as the required completed native item/app reply/task completion. Reject tools
  and orphan tool outputs. Export only allowlisted numeric usage counters.
- `openbot_runner.py`: recognize the two observed PowerShell flag vectors while
  retaining exact script argv matching; verify receipt thread and context.
  Attestation still precedes every scanner operation. Failed jobs remain final.
- `native_identity.py`, `native_host.py`, `agent_review.py` and runner: carry only
  allowlisted stage/check/schema-variant labels across the fixed reader, status
  and review fallback. Unsupported schema/version, incomplete evidence and
  inconsistent identity retain distinct error codes. No private values are
  inserted into diagnostics and no reader operation was added.
- Sanitized observed-layout fixture and 15 compatibility/security tests;
  this note, PROGRESS and the linked verification receipt.

Support remains explicit: Codex CLI **0.169.0**, backend **openai**, legacy and
observed ordinal envelopes. Unobserved versions/backends fail closed pending
real schema evidence. Model names are not pinned: trusted app/provider/context
must agree, and every input/reply/turn/security gate still applies. The existing
OpenCode review compatibility adapter remains; autonomous orchestration is still
Codex-only. A different configured model is not evidence of schema compatibility.

The analytical calculations, 27 measurements, F1–F9, 31 methods, data sources,
qualification/admission gates and trade_authorization=false are unchanged.
All SKILL.md bytes, blueprint, plan and source certificates remain unchanged.
No scanner HTTP run, model invocation, order, scheduler, trading DB operation,
Deep Analyst connection, new agent, credential inspection or Local Scripts use.

## Verification

The existing path-only audit configuration and query-only SQLite read path were
used. The sandbox's native Python probe fails with a WSL vsock bind error; the
same existing fixed Windows identity reader succeeds outside the sandbox and
identifies the expected existing Researcher. This required no app setting change.
No raw provider record, private path, prompt, reasoning or account value was
copied into a public artifact. Fixture values are replaced, not transcripts.

Focused compatibility: **15 passed, 0 failed, 0 skipped**. Initial inherited
native-runtime check: **13 passed**. Final full regression: **431 passed, 0 failed, 0 skipped** in 588.325s, recorded in the
[verification receipt](../../evidence/external-first/native-attestation-repair-20261115/verification.json).
Configuration is VALID; whitespace and protected-file checks pass. An optional
single-test faulthandler timeout probe exited139 in the interpreter trampoline;
it produced no assertion result. The same test passed in both complete
uninstrumented suites. No code/assertion change was made for that probe.

The first adversarial run exposed one failing negative: joining text parts could
restore a missing final newline. The proof now preserves part boundaries; the
original assertion remains and passes.

Adversarial coverage includes reordered keys versus reordered events, missing/
truncated/malformed/duplicate records, ordinal gaps, bad timestamps, unsupported
versions/backends, forged/inconsistent metadata, wrong identity/session/turn/
workspace/model, stale/replayed commands, text-only mentions, unsuccessful
commands, wrong argv/flags, another turn's result, missing/full-input mismatch,
forged finals, unauthorized tools and outputs, secret/metadata diagnostic leakage,
and terminal failure before scanner start. Existing native audit and analytical
regressions are retained. No assertions were relaxed or tests removed.

Publication SHA, local/remote equality and exact-head push/PR CI are verified in
the delivery report after committing; PR24 stays draft and unmerged. Passing
fixtures/CI cannot demonstrate live screening, a genuine new native reasoning
response, useful shortlisting, or completed OpenBot delivery.

## Owner next action

Refresh the approved OpenBot checkout to the published repair SHA, then send
**Run the complete market research now.** to the existing Researcher. Keep its
installed skills and configured model. OpenBot alone performs the next live run.
