# November 27 OpenCode session-part structural compatibility correction

Status: **CODE IMPLEMENTED / FOCUSED REGRESSIONS PASSING / NATIVE ACCEPTANCE NOT CLAIMED**.
No Researcher task, market request, order, or provider/model change was made.

- Root cause: the compact `parent_binding()` path passed the fixed `2.4.1`
  version into `session_record()`, which rejected the retained fresh OpenCode
  `2.4.2` session before reading its turn. A newly-created session on this host
  was also `2.4.2`, so starting fresh was not a no-code remedy.
- The session-part adapter now uses required record identity and turn evidence
  to establish compatibility. The actual provider version is returned as
  `provider_session_version` diagnostic metadata; a version change alone does
  not reject structurally compatible records.
- The legacy `OPENCODE_V2_SESSION_MESSAGE` path retains its observed
  `2.2.5`/`2.2.6`/`2.3.0` boundary. Codex dispatch and output are unchanged.
- Read-only inspection of the two retained Researcher turns confirmed version
  `2.4.2` and matching app/provider/model/effort identity. The completed turn
  passes structural parsing (10 messages, 14 parts); the interrupted turn is
  rejected at `EVIDENCE/COMPLETION_MISMATCH`, not at `SESSION/VERSION`.
- Additive database columns and the observed inert `time.ran` field are
  tolerated. Required model identity, part order/completion, truncation state,
  exact commands/pages/final output, and explicit assistant errors remain
  validated. The retained interrupted turn's `finish=error` is not accepted.
- Focused suites: OpenCode adapter 47 tests and acceptance/preflight 21 tests
  passed. Config validation returned `VALID`; provider status reports
  `NATIVE_ADAPTER_SUPPORTED` / `OPENCODE_V2_SESSION_PART`, with zero model or
  market requests and `trade_authorization=false`. The full offline suite passed
  675 tests in 1175.930 seconds; commit/push and CI are pending.
- Existing Researcher readback remains OpenCode `opencode/deepseek-v4.1-flash-free`
  at high effort with its permissions unchanged. Orchestration skill v5.1.0 is
  registered at revision 10; both workspace mirrors match SHA-256
  `5b927e5bbbe64322749c74e8cc5983160e226ead97f558181dd90bf6d4e806d4`. The
  protected review skill is unchanged at
  `96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb`.
  The private audit config points to the OpenCode database and Windows Python
  reader. Current-turn preflight was not run outside the Researcher's active
  owner turn.

The current Researcher-turn native preflight and all three native acceptance
tests remain owner-host gates; none was initiated here.

---

# November 26 OpenCode authorization and active-turn correction

Status: **IMPLEMENTED / FOCUSED REGRESSION VERIFIED / CONFIG VALID**.
No native acceptance, market request, order, provider switch or installation
change was made.

- `_owner_proof()` now accepts the three exact OpenCode acceptance prompts,
  only when OpenCode is the configured provider, commit-bound and delivered by
  the current owner. Their canonical text is in
  `OPENCODE_TEST1_COMPACT_PROMPT.txt`, `OPENCODE_TEST2_ARCHIVED_PROMPT.txt`, and
  `OPENCODE_TEST3_LIVE_PROMPT.txt`; the acceptance guide refers to those files
  instead of duplicating prompt bodies.
- Run modes map to the existing compact synthetic poll test, archived AI-core
  smoke path, and full read-only research path. No verifier or identity check
  was weakened.
- The orchestration skill now documents the exact JSON-literal OpenCode Code
  Mode wrappers consumed by `parse_execute()` and is version 5.1.0.
- Active OpenCode parent turns may contain incomplete assistant rows or partial
  text parts. Preflight and command/submission polling now ignore only those
  unfinished suffixes while still requiring completed tool records for proof.
  Complete child/historical turns retain the strict completion requirement.
- The compact reader remains pinned to session version 2.4.1. Legacy parent
  binding explicitly permits only previously observed 2.2.5, 2.2.6 and 2.3.0
  versions, preserving message-reader historical replay.
- Shell page output permits the exact page bytes with at most one LF or CRLF
  terminator; extra whitespace, repeated terminators and changed bytes remain
  rejected.

Focused OpenCode and acceptance/preflight suites passed: 64 tests.
`python3 -m researcher config validate` returned `VALID` (9 families, 31
methods). Commit, push and CI are pending. Native acceptance remains unrun and
must be separately authorized.

---

# November 26 OpenCode session-part adapter - implemented, offline verified, native acceptance pending

Status: **CODE_IMPLEMENTED / OFFLINE_VERIFIED / HISTORICAL_EVIDENCE_VERIFIED /
READY_FOR_NATIVE_ACCEPTANCE / NATIVE_ACCEPTANCE_NOT_CLAIMED**. No native task,
market request, order, scheduling change or provider switch was made.

## What changed

- Added `researcher/native_opencode.py` implementing
  `OPENCODE_V2_SESSION_PART` for the observed OpenCode `2.4.1` records. Session
  identity is `(session_id, message_id, ordinal)`; assistant
  `session_message.content` is never a content source. Text, reasoning and tool
  parts come from `session_part`. Reasoning is structurally checked but never
  returned or published.
- Exact session version, provider/model, variant/effort, turn window, part
  ordering, completion, final text and output completeness are attested.
  Unknown or ambiguous schemas, duplicate calls, reordered or modified parts and
  duplicate submissions fail closed.
- The nested Code Mode `execute` form is parsed narrowly for literal
  `tools.openbot.tool_describe` and `tools.openbot.tool_call`. Recorded code is
  never executed, substring matching is not used, and only the exact
  `openbot.start_task` submission is accepted once.
- Compact evidence pages are verified byte-for-byte: CRLF handling, byte
  length, SHA-256, page order, and missing, duplicate or truncated pages.
  Unauthorized child tools are rejected.
- Registered OpenCode as compact-capable and wired provider dispatch through
  preflight, parent identity, owner authorization, start-command attestation,
  discovery, compact dispatch, submission, child identity and evidence, both AI
  stages, artifacts, delivery proof and historical replay. The legacy
  `OPENCODE_V2_SESSION_MESSAGE` reader remains for its historical scope. Codex
  compact bytes and historical replay are unchanged.
- Provider and model remain dynamic: no provider model ID is hardcoded, identity
  is frozen per run, mid-run changes are rejected, and between-run changes
  remain possible. The OpenCode compact brief names `shell`; the Codex brief is
  byte-identical. `collect` returns `trade_authorization=false`.

## Verification

- `tests/test_native_opencode.py`: 38 adversarial offline tests pass, including
  record integrity, session identity, effort changes, discovery duplicates and
  failed nested wrappers, submission timing and acknowledgments, child pages and
  final text, inline and compact collect, ticket mismatches, start command,
  preflight and delivery proof.
- Focused compatibility suites pass: compact native 11, native handoff 25,
  native runtime 13, native app 6, dynamic model identity 10, dispatch
  confirmation 16.
- Full WSL suite: `Ran 664 tests in 1121.173s ... OK`.
- `python3 -m researcher config validate`: `VALID`, 9 families, 31 methods.
- The Phase C parent/child record shapes and hashes were re-read from the
  retained diagnostic evidence. No archived OpenCode compact job exists, so no
  historical two-stage compact replay is claimed.

## Not verified

- Native acceptance remains pending separate owner authorization.
  `READY_FOR_NATIVE_ACCEPTANCE` is not a receipt. The live OpenCode parent/child
  boundary, the actual `review-page` stdout terminator and Windows/OpenCode
  shell normalization remain `UNVERIFIED_OR_BLOCKED`.
- The private audit config holds one `provider_db`; an OpenCode run needs it
  pointed at the retained OpenCode database, with WSL delegating WAL reads
  through `native_python`. The exact procedure is in
  `OPENCODE_NATIVE_ACCEPTANCE.md`; private config is not published.

## Next

Three separately authorized tests are prepared in
`OPENCODE_NATIVE_ACCEPTANCE.md`: synthetic compact paged Discovery, archived
two-stage research, and full live read-only research. Keep PR #24 draft and
open. Do not force push or merge it.

---

# November 25 Phase C OpenCode boundary diagnostic — run complete, adapter not implemented

The owner ran the single authorized synthetic diagnostic on 2026-11-24 on the
existing Researcher, configured as `opencode/deepseek-v4.1-flash-free` at
reasoning effort `high`. The fixed page is `233` bytes, SHA-256
`e529506e6b3cff6881a02616138a50b68eba9e7ec17ed801f2f8f82ed271d798`.
Read-only `mode=ro` inspection of `openbot.db` and `opencode.db` confirms one
parent turn, one submitted task, one child turn and one final answer. No market
request, trade, production-runner call or second task was made.

Both sessions are OpenCode record version `2.4.1`. The parent turn contains four
completed native tool calls: one `shell` read of the exact page (exit `0`,
`235` output bytes, SHA-256
`ea011a591e8bd4d7c1cd64dc8fa25b36c9c74ac8e33d131230b19c8ef414461c`); one
`execute` attempt that the bridge rejected because `tool_call` cannot run
`tool_describe`; one direct `tools.openbot.tool_describe` that returned both
schemas (`2,341` bytes, SHA-256
`aa370892476f450c33c99e0ed9dc3e8b14831f5481bc07df0bb9000229f7312a`); and one
`openbot.start_task` call with the exact title and brief (`487` bytes, SHA-256
`3f6f33c8f9d2f2087a1e59e71171e9eb820b99d9698b1d81791c7487fba270e6`). The child
session contains exactly one `shell` call with the same command, exit `0` and
the same `235`-byte output hash; its `220`-byte final answer
(SHA-256 `45d26b165b7bd746e4feebe2a360741c47ba8b617acf0c5e6af328fd1bcafbb5`)
reports the page ID, nonce, marker and `9 × 7 = 63`.

The record-format gap is now exact: every assistant `session_message` row in
these turns has `content: []`; all tool calls are in the normalized
`session_part` table (`type=tool`, `name`, `call_id`, `state.input`,
`state.content`, `state.metadata.exit`). The existing `native_app` reader
consumes `session_message` only, so it would see no tool calls and cannot attest
this boundary. The OpenCode compact adapter remains unimplemented and OpenCode
is still excluded from `COMPACT_ADAPTERS`. Status: `HOST_EVIDENCE_OBSERVED`;
`NATIVE_ACCEPTANCE_NOT_CLAIMED`. The next gate is a narrowly scoped
`OPENCODE_V2_SESSION_PART` reader/attester with adversarial offline tests, then
a separately authorized acceptance run. Docs-only CI for `37f626e` concluded
`success`; this entry records no code change.

---

# November 24 Phase C OpenCode boundary diagnostic — prepared, not run

Approved commit `2349ba78f96a4367ca9c2392481cd3bdbab87f27` is clean and in
sync on `feature/external-first-market-researcher`. Both CI runs for that commit
concluded `success`: push run 45397257999 and pull-request run 45397270079.

The installed orchestration skill was republished as local revision 9 and
installed on the existing Researcher. Both workspace mirrors are 3,766 bytes
with SHA-256 `324979430bb1c9d6c9af98ed7c78ced049563900861aa9d6b39ab474fda795be`;
the registered revision and same-turn rule were read back. The protected
`market-research-review` skill remains
`96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb`.

Host inventory: OpenBot `0.76.1`; OpenCode provider records in `opencode.db`
with session record versions `2.2.5`, `2.2.6` and `2.3.0`, legacy
`session_message` JSON parts and a newer normalized `session_part` table. The
native command tool is `shell` (PowerShell dialect); observed native tools are
`execute`, `shell`, `write`, `edit`, `grep`, `subagent`, `read`, `webfetch`,
`websearch`, `glob`, `question` and `skill`. The existing compatibility reader
consumes `session_message` only.

A fixed 233-byte synthetic page (SHA-256
`e529506e6b3cff6881a02616138a50b68eba9e7ec17ed801f2f8f82ed271d798`) and the
exact one-run owner diagnostic are recorded in
`PHASE_C_OPENCODE_BOUNDARY_DIAGNOSTIC.md`. No provider switch, native task,
market request or trade was made. Status: `CODE_IMPLEMENTED` and
`OFFLINE_VERIFIED` for the installation sync; the OpenCode adapter remains
`UNVERIFIED_OR_BLOCKED` pending the owner diagnostic and real host records.

---

# November 24 native tool-discovery attribution fix — implemented and offline verified

Retained-evidence diagnosis of the failed archived smoke job
`20261124T031654Z-5bc2e449d49d495e822bfff23c113d91`. The job reached
`OWNER_AUTHORIZED`, `COMMAND_ATTESTED` and `PREFLIGHT_REJECTED` with zero model
attempts and zero market requests. Its diagnostic ZIP SHA-256 is
`916045b5b0d54aa5d178c0f99ec5f9619916f84b38ca9df1baecfdb615820764`.

The rejected parent turn `7b489ba28469` (started 2026-11-24T03:09:21Z) contains
no `tool_describe` call. Discovery had succeeded at 03:06:55Z in the preceding
setup turn `d3c9e268a53e`, which the same verifier accepts when replayed
read-only against the retained records. The verifier was therefore correct:
discovery must occur in the same parent turn as the start command. No check was
weakened or bypassed, and no unbounded earlier-turn scan was added.

`attest_smoke_discovery` now raises `NATIVE_TOOL_DISCOVERY_UNVERIFIED` with a
sanitized diagnostic naming the first missing pipeline step: `NO_CALL`,
`INVALID_CALL`, `NO_COMPLETION`, `COMPLETION_MISMATCH`, `CONTENT_MISMATCH`,
`SCHEMA_MISMATCH`, `NO_OUTPUT` or `OUTPUT_MISMATCH` at stage `TOOL_DISCOVERY`.
The orchestration skill now states that discovery must be repeated in the same
main-chat turn as the start command, including after a host continuation, owner
steer or retry. Acceptance behavior for valid same-turn records is unchanged.

Focused native preflight suite: 19 passed. Full
`python3 -m unittest discover -s tests -v`: 626 passed in 1500.081 seconds.
`python3 -m researcher config validate`: VALID, nine families, 31 methods, zero
production detectors/full-core packs. `trade_authorization=false`; no market
requests, model calls, provider changes or native-task submissions were made.
Status: `CODE_IMPLEMENTED`, `OFFLINE_VERIFIED` and
`HISTORICAL_EVIDENCE_VERIFIED`. Native re-acceptance remains
`UNVERIFIED_OR_BLOCKED` until a separate owner authorization repeats discovery
and the start command in one main-chat turn. Remote CI is reported in the
session handoff after observation.

---

# November 24 provider identity continuation — partial, native gate open

Starting clean remote HEAD `04e214f5e26a33f4a92601c159ad501407bc0d50` was
fetched from the feature branch. The same Researcher, compact child workflow,
source and analytical engines, historical ticketed pages and research-only
permissions are retained. No market requests, native model calls or provider
settings changes were made in this environment.

`native_identity` now distinguishes the current selection from compact reader
support through a read-only `provider-status` command. OpenCode's legacy file
reader remains unsupported for compact pages; unknown providers are reported
as unsupported, not switched. The shared gateway, runner and preflight use the
same compact-adapter registry. The existing Codex verifier and historical
receipt formats are unchanged. A reader in the registry is not proof of current
provider availability or verified execution.

Historical Codex replay previously compared the original provider/adapter with
the current configured selection. It now verifies the original provider and
adapter against the captured identity and original app/provider records,
while preserving agent/workspace checks and all active-run provider/model
checks. Fixture regressions cover a later OpenCode or unknown selection,
forged adapter and mid-run provider change. Replay requires the retained
original Codex database and rollout files, including an appropriate private
read-only path. A new model under the same supported provider remains covered
by existing tests. Neither direction of a two-provider native run is claimed.

Focused provider, compact, native preflight, Codex receipt and AI-core suite:
60 passed. Full `python -m unittest discover -s tests -v`: 624 passed in
518.738 seconds. The fixed native-reader capability operation also passed a
separate fixture check. `python -m researcher config validate`: VALID, nine
families, 31 original registry methods, zero production detectors/full-core
packs; M32/M33 remain separately registered SHADOW trials. Exact remote CI
outcome is reported in the session handoff after observation.
OpenCode compact attestation and genuine two-stage acceptance remain blocked
on the actual sanitized host records described in
`OPENCODE_DEEPSEEK_BOUNDARY.md`. `trade_authorization=false` is unchanged.

---

# November 23 final code-first continuation — partial, native gate open

Started from clean `5c9499abadf5a434ec719dba18c2640da95976a6` on the existing
feature branch. The complete mandatory documents and historical consultation
were read before a Context Acceptance Receipt and application edits. No model,
market, native-task or paid-provider calls were made in this Cloud continuation.
The original blueprint, historical evidence, plan and current provider/agent
configuration were not edited. `trade_authorization=false` remains mandatory.

## Completed and blocked

* **P0, OpenCode/DeepSeek compact integration: BLOCKED / NOT NATIVE VERIFIED.**
  The real older OpenCode evidence in `SESSION_06C_NATIVE_REVIEW.md` does not
  establish the installed compact task/page/turn/reply boundary. Upstream ACP
  source alone is not installed-host evidence. The runner and preflight retain
  their non-Codex rejection. `native_runtime.collect` additionally prevents
  compact requests from being misrepresented as verified by the legacy OpenCode
  session reader. No provider receipt or native capability was invented.
  `OPENCODE_DEEPSEEK_BOUNDARY.md` records the smallest owner-host diagnostic and
  the subsequent acceptance gates; the existing orchestration skill still needs
  owner-approved installation/readback when a supported adapter exists.
* `ai_core` permits a different family only through a separate transmitted,
  independently qualified same-symbol/timeframe/reference card, citing that
  card's own formation evidence, and re-applies current admission gates. This
  is offline-tested; it does not qualify an untested model or source. Existing
  discovery, selective inquiry and shortlist stages remain distinct.
* **M32 and M33: SHADOW/TRIAL, selected history only, not qualified.**
  `shadow_methods.py` freezes a first 32-bar balance and evaluates later
  Spring/UTAD, response, retest and LPS/LPSY candidates with explicit volume
  unknowns. M33 requires a preselected completed 4H parent and explicit bounded
  aligned 5M history, a later outside body close and separate later inside
  close; source gaps, delayed availability and expiry are explicit. Shared bar
  IDs retain common observation roots. M33 supplied inputs are accepted only
  for synthetic/authentic replay; no live 5M adapter, warehouse, universe
  scanner or source qualification was added. Optional invalid input cannot
  disable the baseline selected engine. Offline shadow observations can appear
  as unqualified shortlist context; no live ranking or admission is changed.
  The fixed-window trials are not full prospective range nomination, full
  lifecycle/source qualification, independent event-counting qualification,
  or evidence of profitability. Room/friction and broader multi-timeframe
  context remain unimplemented. M01–M31, M05 and M12 remain intact.
* Local implementation increments: `ae00b5f` (OpenCode fail-closed guard) and
  `6b2eb33` (bounded shadow trials and qualified alternative handling).

## Verification and release status

Focused compact/native regression: 17 passed. Focused AI/shadow regression:
20 passed. Existing session 6A analytical regression: 58 passed. Config
validation: VALID, 31 configured methods, nine families, zero production
 detectors and zero full-core packs. These are offline checks, not native or
source certification. Full-suite and remote CI results are recorded in the
final session handoff after actual execution; this document cannot contain its
own final commit SHA. First native action and required evidence are specified in
`OPENCODE_DEEPSEEK_BOUNDARY.md`. Do not declare the workflow released or PR #24
ready while that gate remains open.

---

# November 23 compact native-child implementation

The owner selected Option A and reported a real owner-host compact **inline**
child task: an 870-byte brief matched provider input, a 619-byte reply matched
the provider and app final, the existing attester succeeded with no unauthorized
operations, and the observed Codex CLI record format was 0.171.0. That is
owner-supplied evidence for the inline boundary; its records were not available
in this Cloud session. It does not establish paged delivery or two stages.
Cloud started from clean feature commit `54ec29f454813adbcf3ed8dec146b9dabdc83134`
and issued a Context Acceptance Receipt before editing.

## In-place changes and security boundary

* `ai_core.py` emits the versioned `COMPACT_AI_CORE_PAGES_V1` request for both
  stages. Existing broad Discovery, selective inquiry, Shortlist, citations,
  source/economic gates and reconciliation remain in place. `native_handoff.py`
  reuses the bounded immutable, material-hash-bound pages and the literal first
  and next commands; old ticketed formats remain separately readable.
* `openbot_runner.py` issues one small native `title`/`brief` object under the
  existing job lock. A deterministic internal dispatch record binds the exact
  arguments, material and page hash before publication. No Base64 round trip,
  model-operated grant command, 90-second submission countdown or 180-second
  publication countdown is required. The request's existing freshness and
  overall run limits still apply. A second poll does not reissue permission;
  an uncertain or clipped output must not be submitted or automatically
  retried. This deliberately favors duplicate prevention over recovering an
  unobserved clipped first status response. A local synthetic fixture measured
  a 1,298-byte frame and 843-byte brief; this is not a host clipping guarantee.
* `native_app.py` and `native_runtime.py` retain independent owner/parent,
  selected provider/model, exact call arguments, native acknowledgment/task ID,
  ordered complete provider-visible pages, final response and no-forbidden-tool
  checks. The compact acknowledgment is bound to the actual provider record;
  it is not an echoed authorization token. Provider formats outside the
  existing qualified Codex adapter fail closed; no model is selected or changed
  by this implementation. Historical child receipt and replay formats remain.
* Updated the existing orchestration skill template and added an exact
  commit-bound synthetic paged Discovery owner instruction and
  `COMPACT_NATIVE_ACCEPTANCE.md`. Neither installs a host skill. Registered
  skill revision/readback and the actual host preflight remain owner-host gates.
  The isolated acceptance run uses one real task, cited synthetic evidence and
  no market request; it does not accept a two-stage or live workflow.

No new agent, provider gateway, database, scheduler, market scan, live model
call or trading action was created in Cloud. M32/M33 remain trial specifications;
the original blueprint and implementation plan are unchanged. Source coverage
and `trade_authorization=false` remain as before. The owner's reported inline
test and offline simulated records do not make the compact paged workflow
`NATIVE_VERIFIED`.

## Verification

* `python -m unittest discover -s tests -v`: **607 tests passed** in 707.055
  seconds. This includes the compact one-stage fixture, both AI stages with
  simulated provider records, historical ticketed verification and read-only
  replay. It is not an actual OpenBot model invocation.
* Focused compact and synthetic Discovery regressions: **11 tests passed**;
  focused legacy confirmation and AI-core regressions: **24 tests passed**.
  They cover clipped/missing/modified/reordered/duplicate page outputs, wrong
  child model and task acknowledgment, citations, forbidden tools, concurrent
  one-shot issuance, uncertain submission, expiry and unsupported providers.
* `python -m researcher config validate`: **VALID**; nine families, 31 methods,
  zero production detectors and zero full-core packs enabled. No market,
  model or native task calls were made in Cloud. See the session handoff for
  final commit and observed CI status.

---

# November 23 compact native-child investigation

The owner requested investigation of Design 1+ §H4 and authorized a minimal
in-place implementation only where the indispensable interfaces are verified.
Cloud fetched `feature/external-first-market-researcher` at
`b3fa9e5ea4c2551cd55798336203d1a15543fdaa`, verified a clean checkout and
issued a Context Acceptance Receipt. No application code was changed.

## Decision and evidence

**Recommend Option A, the compact native-child path, conditionally.** It reuses
the existing Researcher and needs no new submission service. Option B, a typed
host interface, is not justified unless the child path fails a measurable gate.

* `AIResearch.discover` precedes selective investigation in
  `scan_market_research`; `AIResearch.shortlist` follows it and reconciliation
  enforces citations and research gates. The current gateway uses two distinct
  native tasks, at most 12 observed provider responses and a 600-second overall
  budget. Offline fixtures exercise this order, not real native completion.
* The historical owner-host readback in `NATIVE_DYNAMIC_MODEL_IDENTITY.md`
  verified one actual child task, its exact parent submission, matching
  provider/model, ten complete provider-visible pages and final reply. It
  demonstrates the earlier ticketed protocol, not two AI-core stages or a
  compact no-ticket protocol. Its elapsed time and response count do not prove
  that two stages fit current budgets.
* The pinned OpenBot upstream `agent-tasks.ts` accepts only trimmed `title` and
  `brief`, reports the created task ID, and deduplicates retries by agent, turn
  and **call ID**. A fresh tool call has a different call ID: content equality
  alone does not prevent a second task. The pinned provider descriptor supports
  concurrent turns for Codex and OpenCode, but this is source-version evidence,
  not proof of the current installed host or another provider's behavior.
* `native_handoff.load_dispatch`, `openbot_runner.review_page`,
  `native_app.observe_handoff` and `native_runtime.collect` require the saved
  ticket and bind its timing to the exact parent call, task and page access.
  `native_codex.observe_submission` only extracts the acknowledged task ID on
  the reserved path. Removing the ticket is therefore a protocol and verifier
  change, not a safe deletion of an encoded string. The current AI gateway and
  runner reject non-Codex providers; OpenCode's older compatibility reader is
  not proof of a paged AI-core adapter. Owner-selected provider/model identity
  must remain per-run and unsupported formats must fail closed.

The shortest candidate is a new **versioned** compact title/brief containing
one immutable manifest reference, fixed bounded page commands and no Base64
round trip. Retain owner-turn and exact provider/model binding; independently
observe the exact call and task ID, every page output and model-visible byte,
and the generated reply; reject missing pages, altered briefs, duplicates and
unexpected tools. Preserve the old ticketed protocol for historical replay.
An atomic local stage state can protect publication and acceptance, but cannot
make separate native tool calls idempotent: an uncertain submission must not be
retried until independently resolved. Continue to enforce an explicit owner/run
expiry and live source freshness rather than an arbitrary short publication
race. This remains a proposed design, not installed capability.

**STOP:** the installed host has not demonstrated the new no-reservation
submission/receipt boundary, and the current scoped verifier requires a ticket.
Thus no new protocol, attester or model/provider support was implemented. The
old clipping, wrong-path, deadline and argument-mismatch failures could be
avoided by the candidate design, but the benefit and exact receipt shape remain
unverified. The first Incident III differing byte remains unknown.

## Smallest owner-host test

In the existing Researcher's owner-authorized main chat, start exactly one
synthetic task through the existing `openbot.start_task`, with a short literal
title and brief and no reservation or encoded confirmation. Have the child
read one fixed, bounded synthetic evidence page through its existing command
tool, then return a short JSON hypothesis with a citation and a rival; make no
market request or trade. Preserve the task and, using only a separately
authorized scoped read-only host audit, establish whether the records contain
the owner/parent turn and configured provider/model, exact task-call arguments
and acknowledgment/task ID, exact child page output as seen by the model,
and the child's final bytes and tool list. Report only sanitized hashes,
lengths, timestamps and pass/fail fields. The checked-in verifier requires a
ticket, so it must not be claimed to validate this unreserved test; if the
available authorized reader cannot expose the required records, report that
precise missing capability. No automatic retry or second task is authorized.

## Verification

* `PYTHONPATH=tests python -m unittest test_dynamic_model_identity
  test_native_codex_compat test_native_dispatch_confirmation test_ai_core -v`:
  **47 tests passed** in 14.261 seconds; these exercise the existing protocol
  with fixtures, not a new native acceptance.
* `python -m researcher config validate`: **VALID**, nine families, 31 methods,
  zero production detectors and full-core packs. No market/model calls or
  OpenBot tasks were made in Cloud. M32/M33 remain trial specifications.
* The earlier full offline suite on the same application code passed 596 tests
  in 686.872 seconds. Both PR #24 checks for the investigated HEAD passed;
  PR #24 remained draft.

---

# November 23 Design 1+ Cloud capability gate — STOP

The owner requested the in-place Design 1+ refactor and M32/M33 shadow work,
subject to the hard native-boundary stop in
[the single-session brief](CODEX_CLOUD_SINGLE_SESSION_DESIGN1_PLUS.md).
This session fetched the feature branch at
`97188ca169df8cb840dd58dc23f94e81e06d884c`, verified a clean worktree and
issued the Context Acceptance Receipt before editing. The original blueprint
and implementation plan still match their recorded SHA-256 values
`cf7a58fd9ed5f5d1010673406c26a405c8112b907216a47f88a9ebee1bd3d45c`
and `245591eea0f92cd185c51db3420043031c11c1d941f91ecdb31fd64a34e0c232`.

## Evidence and decision

* The checked-in runner exposes `start`, `status`, `review-page`,
  `reserve-review`, `replay-native` and `preflight`. The repository skill
  describes the existing timed, confirmed child-task flow. The pinned upstream
  `start_task` schema accepts `title` and `brief`; it does not establish a
  parent-stage JSON submission channel. These are source observations, not
  evidence of the version or capabilities currently installed on the owner host.
* This Cloud checkout does not contain the owner's installed OpenBot, its
  main-chat command-tool schema, active agent/session, or original Incident III
  parent command and event records. The available Codex receipt code observes
  historical child-task formats; it does not establish that actual parent page
  outputs and dynamically submitted response bytes can be independently bound
  to one owner-authorized main turn. An OpenCode entry in the identity map and
  a compatibility branch are not certification of a Design 1+ parent adapter.
  No current provider or model was observed or changed in this session.
* The first Incident III mismatch remains **UNCLASSIFIED**: without its original
  command there is no defensible first-byte offset, length/hash comparison or
  proof-versus-end-marker attribution. No historical job was retried.
* **STOP / NATIVE_INTERFACE_UNQUALIFIED:** no supported main-turn submission
  mechanism or independent parent-turn attestation was demonstrated. In
  accordance with Step 1, no speculative transport, adapter, new protocol,
  stage wiring or method implementation was added. Existing AI-core code and
  fixtures are not a native Design 1+ acceptance. In particular, the existing
  `ai_core.validate` requires a HANDOFF interpretation to equal the card's
  primary family; a qualified-rival change remains unimplemented.

## Reuse and remaining work

| Existing surface | This session | Dependency / future minimal delta |
|---|---|---|
| `discovery.py`, screening and source adapters, query planner, causal ledger, F1–F9 and M01–M31 | REUSED_UNCHANGED | Preserve partial source status, identity, clocks and historical evidence. |
| `ai_core.py` | REUSED_UNCHANGED | After the gate, reuse the two stages and citation/economic validators; independently prove any alternate-family formation before relaxing the primary-family restriction. |
| `openbot_runner.py`, `native_handoff.py` | REUSED_UNCHANGED | Only after a supported submit path is demonstrated, add one versioned parent flow in place while retaining old child replay. |
| `native_identity.py`, `native_runtime.py`, `native_codex.py`, `native_app.py` | REUSED_UNCHANGED | Verify selected provider/model and actual parent page/submit records through a qualified adapter; fail closed on unsupported formats. Historical Codex child receipts do not prove this new boundary. |
| Existing skills and configuration | REUSED_UNCHANGED | A future repository skill change does not install or register a host revision; confirm approved revision and permissions separately on the host. |
| M32/M33 | DEFERRED | Only after stable core: append trial-only shadow variants and temporal/source oracles, with M12/M05 unchanged and shared-event roots. No live method or economic qualification is claimed. |

No new source file, agent, provider, market call, model call, native task,
subscription, trading permission or Local Scripts controller was introduced.
Source coverage remains partial; the previous Cloud Binance 451 remains a
stop, and no denied route was retried. `trade_authorization=false` remains the
research contract. M32 and M33 remain published **TRIAL_SPEC**, not registered
or implemented; their source qualification, prospective utility and economic
edge are unproven.

## Smallest owner-host gate

In the existing Researcher's owner-authorized main chat, inspect the actual
installed command-tool schema and its permitted input/output and record format.
If it documents a bounded way to pass model-authored structured bytes to a
fixed, scoped validator without shell-quoting a long JSON body or changing
permissions, demonstrate that one channel with a tiny synthetic non-market
payload and capture only sanitized lengths, hashes, tool/turn references and
whether the provider record independently exposes the exact submitted bytes and
model-facing output. Also establish whether the same turn can continue after
the tool result. Stop if any capability is missing; do not assume stdin or
write to private provider records. This is a **capability probe**, not an
acceptance of a Design 1+ implementation. After a supported path is implemented,
the first native certification is one no-market, no-trade model-authored
discovery with complete evidence-page observation, a cited rival/falsifier,
independent owner/provider/model and reply verification, and negative checks
for a missing page and invalid citation plus an identical-submit retry. Two
authentic stages and delivery require later separate evidence.

## Cloud verification

* `python -m unittest discover -s tests -v`: **596 tests passed** in
  686.872 seconds. These are offline tests; simulated provider-shaped records
  do not certify native model execution or the proposed parent transport.
* `python -m researcher config validate`: **VALID**; nine families, 31 methods,
  zero production detectors and zero full-core packs enabled. Manifest SHA-256:
  `fe6826b1df739c3e859abadeb44cead3057bc853e7d4da62efa9c79e9c6f8272`.
* `git diff --check`: passed. The two immutable design files retained the
  SHA-256 values listed above. No Cloud market, model or native task calls
  were made. The pinned upstream OpenBot task schema was read over HTTPS.

---

# November 23 parent polling correction

Owner-supplied forensic timeline reports job
`20261123T102245Z-5c1c1d4fc00c4c219bd8c63ff600f491` missed its publication
window after a wrong checkout path and a 60.985-second gap. The gap remains
unexplained. The supplied timeline records no native submissions and no
market requests. The 3,673-byte preview was reconstructed separately, and
the old late status stdout was complete. Those host records are not present
in Cloud.

Confirmed AI-core ordinary status now delivers the complete bounded preview
from the locked READY snapshot. Start returns the exact canonical status
command, and the preview retains its canonical grant command. New confirmed
materials allow 180 seconds from publication, bounded by monotonic time and
the existing 600-second request freshness limit. The subsequent one-time
submission deadline remains 90 seconds from grant. Historical materials keep
their original windows and packet protocol.

The initial CI run exposed two historical workflow fixtures that needed to
request their unchanged legacy `--include-review` transport explicitly.
The fixture harness now follows the transport indicated by each READY state.

A separate owner-authorized polling integration test uses a single synthetic
empty-discovery native task, the existing verified receipt path, and zero
market sources. Its exact owner message and installation instructions are in
[Native polling test](NATIVE_POLL_TEST.md). Cloud runs fixtures only.

---

# November 23 AI-core dispatch truncation recovery

The owner brief reports that Local job
`20261123T084728Z-df41c5be1afc410796a1097cce9326d7` at
`7cadbf9edc8d1e3e8df7add520191de4e2390276` clipped a 39,263-byte
discovery brief after creating a one-time ticket. The stated diagnostic ZIP
SHA-256 is `778ab36e05c20b042a6176aacbb863b7fb00cce170392eeb231a06a83cca3f02`.
Its bytes and the original clipped result were unavailable in Cloud.
An 8 KiB synthetic parent cap reproduced the stranded ticket in a detached
checkout of the failing commit. The same-size corrected fixture used a
3,402-byte preview and four exact evidence pages. The cap is a fixture input.
[Hashed reproduction](../../evidence/external-first/ai-core-dispatch/transport-regression.json)

Both mandatory stages now confirm every compact native argument byte before
a one-time grant. Missing tails and altered confirmations leave the preview
recoverable within its window. Receipt collection waits locally before the
grant. Provider-shaped tests exercise truncation, delayed projections,
Windows timeouts, duplicate polling, invalid receipts, exact child page
receipts, archived replay, and genuine zero-handoff semantics using fixtures.
Two native tasks remain the limit. The observation budget covers up to twelve
provider responses to account for the bounded reads.
[Dispatch protocol and diagnostic](AI_CORE_DISPATCH_RECOVERY.md)

A concurrent local full run surfaced a race between separate status and
preview snapshots. One poll kept an earlier REVIEW_READY label after the
worker advanced and could no longer provide its preview. The confirmed
preview now uses the same locked snapshot as status. A focused regression
checks that the lock remains held while rendering the preview.

The next dependency is one owner-authorized archived smoke on the existing
installation with the newly pinned orchestration skill. This Cloud work
started no native tasks and made zero market requests. PR #24 stays draft.
[Canonical installation and acceptance](AI_CORE_LOCAL_ACCEPTANCE.md)

---

# November 23 AI-core implementation

Continued draft PR #24 from `7fd0865c062889b228b9d0a1a336173f104ee8a1`.
The owner-approved [AI-core decision](AI_CORE_DECISION.md) makes independently
verified discovery and comparison required. Scoped model questions precede
alt history allocation. The final model stage determines membership and rank
within current deterministic admission gates.

The inline path keeps historical page verification. The first fixture attempts
exposed a missing digest import and an oversized final packet. Import and
projection were corrected. The end-to-end synthetic workflow verified both
stage receipts, investigated M05, reconciled a clipped shortlist and observed
a fixture ZIP delivery. The retained-input archival workflow verified two
fixture receipts and read-only replay, with zero market calls. The 571-test
discovery run passed, and the eight additional AI-core tests passed separately.
Configuration validation passed. These results use simulated provider events.

Native acceptance remains owner-host only. Run the exact
[archived smoke instruction](AI_CORE_LOCAL_ACCEPTANCE.md) once after the
published checkout and installed orchestration skill match. No live market or
model requests were made in Cloud.

---

# November 23 native review reliability recovery

Job `20261123T014656Z-ef68145ab7cc4cda8cf5432111ef76d0` ran at
`f95bf125451fab99109a384b0371d0b49b7e9530`. The recovered ZIP SHA-256 is
`1e2b200be2ab93b672e246b53df27a4d0dcd6d5f72b22df1191a7884231355cc`.
Its report and internal hashes match. Delivery was not observed. The parent
turn completed at 02:06:08 UTC, while the worker exported at 02:09:17 UTC.

- The first rejection was ordinal 18 at 01:54:46.792 UTC, a permitted page 1
  `custom_tool_call` whose JavaScript omitted the optional final semicolon.
  The parser incorrectly required that semicolon. Pages 1–4 each reached the
  model as exact canonical bytes. Page 5's fixed command was started at
  01:55:45.903 UTC and exited 0 at 01:55:56.751 UTC with the exact page in its
  execution record. The tool response at 01:55:55.950 UTC contained an empty
  output because the command was still running. The child stopped and returned
  prose. No pages 6–9 or valid advisory JSON were delivered.
- The reader accepts the observed equivalent semicolon-free wrapper and
  classifies empty or prematurely returned output as `NATIVE_READ_INCOMPLETE`.
  New packets require a 30-second command wait and still stop on empty output.
  A legacy packet's bytes and ticket remain unchanged. Exact commands, bound
  execution events, page order and byte equality remain mandatory.
- `replay-native --job-id JOB_ID` reaudits a saved terminal job with the
  existing production receipt verifier and checks the archived report and ZIP.
  Replaying this job produces `NATIVE_READ_INCOMPLETE`, with zero market or
  model requests and no imported advice.
- The separately authorized native smoke mode uses the exact committed
  `OPENBOT_NATIVE_SMOKE_PROMPT.txt`, the normal parent identity and one-shot
  dispatch, attests successful discovery of the task and attachment schemas in
  that parent turn, and uses one saved live packet labeled as archived. It runs no scanner.
  The artifact reports the verified review and an archived-only reconciliation
  against the hash-verified original report when its candidate is available.
  Provider delivery remains a separately observed receipt. An incomplete
  smoke still exports a partial diagnostic report. The main status now says
  when an artifact remains pending after a review failure.

Focused offline runs passed the historical wrapper and early-output tests,
bounded-wait page validation, invalid citation and unauthorized-command
checks, interrupted-child handling, archived reconciliation, saved-report
replay, tool discovery and its negative cases, and the paged smoke fixture.
The complete offline suite and the feature-branch CI runs are tracked in the
session handoff.

Keep PR #24 draft and `trade_authorization=false`. This work does not prove
live native review or make the historical market evidence current.

---

# November 22 native page 7 recovery

Job `20261122T145844Z-859c591ced8d42b4b644ef6991d56083` ran at
`07e9d1e7e4d152be09f54c125235fb1fd74b66da`. The retained ZIP SHA-256 is
`402a0bd1ffc1a324fba0fd1e646ec870ba9b3cde66f37f6ab92739a12bebbbeb`.

- The parent's only child submission was acknowledged at `15:06:40.995Z`.
  The Codex 0.171.0 child delivered pages 1–6 byte for byte. Its page 7
  `response_item.custom_tool_call` at ordinal 60, `15:07:47.124Z`, omitted
  `c3` from the literal `--packet-sha256`. The exact command allowlist
  rejected that record. The actual command completion at ordinal 62 exited 1,
  and ordinal 63 delivered `NATIVE_HANDOFF_UNATTESTED` to the model. The job
  was still `REVIEW_RUNNING`. With the original request and ticket and the
  historical open state reconstructed in memory, the same arguments failed
  and the canonical arguments served page 7. Pages 8–10 were never requested.
  The persisted final was prose and failed `AGENT_REPLY_JSON`. The unchanged
  historic collector rejection was reproduced and no advice was imported.
- New materials use literal commands bound to the immutable ticket by job
  and material. The exact parent brief and every page still contain the full
  canonical packet digest. The page reader recomputes and checks the saved
  ticket, and the verifier matches the exact authorized command and both
  persisted outputs for each ordered page. Legacy packets retain their
  original commands and exact digests. The saved failure fixture preserves
  the offending script and output with the local checkout path redacted.

All 558 offline tests passed across the discovery groups and workflow reruns.
Four cases initially hit the harness deadline under local contention. The
baseline reproduced the deadline failure during simulated scanning. All seven
workflow cases passed after increasing only the test harness limit from 90 to
180 seconds. The receipt, citation, and reconciliation tests cover complete
ordered delivery, altered commands and outputs, incorrect turn identity, and
finalist coverage without duplicate processing. The Windows receipt collector
still rejects the unchanged historical trace.

Configuration validated and 25 protected files matched the baseline.
Registered orchestration revision 4 and both
workspace mirrors matched the rendered source. Both review mirrors matched
the protected review skill. The owner-host job remains partial. No market
requests, native task submissions or model calls were performed. Fresh
acceptance remains a separate owner action. Keep PR #24 draft and
`trade_authorization=false`.

---

# November 22 priority recovery

Recovered from `a81d3ebff60b8468b0c63961d2febe274cf49b7a` using job
`20261122T121818Z-af613474da394f86a0850b7f3dd3788f`. The original ZIP SHA-256 is
`241dd4ebd74fc2bcf95a7bc2ce3504cefdea6b1f9efa9d2c16b73c96cac94206`.

- The first rejected provider record was `response_item.custom_tool_call`,
  ordinal 18 at `12:25:00.376Z`. All eleven wrappers supplied an unauthorized
  `shell` argument. Page 5 also used a misspelled path on its first attempt
  (ordinal 46), and WSL exited 1. The second attempt (ordinal 53) used the
  correct path and delivered page 5 once, with the same unauthorized argument.
  Independent byte comparison found all ten pages in model-facing output.
  The first child turn completed with 12 distinct provider response records
  and three citation-valid JSON rows. Receipt verification still rejects the
  original turn and none of those rows was imported. A later prose follow-up
  is outside the brief-bearing turn, which now anchors completion selection.
  New packets provide literal commands in sequence and explicitly forbid extra
  arguments and retries. Legacy packets retain their exact bytes and checks.
- Sequential local HTTP receipts moved backward, and the 38 reported clock
  samples came from eight held high-water marks. A current read-only comparison
  found a multi-second Windows/WSL UTC difference. Historical System records
  did not identify the clock adjustment mechanism. The reader now uses raw UTC
  for native checks, preserves the research watermark, and records local
  request brackets and grouped clock diagnostics. The `NO_READY` gate and the
  original evidence times are preserved.
- The retained phase order covered 519/519 broad 15m, 350 causal 1h, and 150
  broad 1h contracts. The fourth broad 1h partition encountered cooldown. With
  21.736 seconds left, the 60-second pause could not fit despite physical cap
  headroom. Interleaving at the same observed dispatch limit exchanged 50
  causal rows for 50 broader rows in the sensitivity check. Three selected
  1h gaps had bounded local fallback. The schedule and source scope are kept.
- The 652 nominations represented 480 unique symbols, including the benchmark
  context. The trace had 47 investigated nominations, 605 deferred, and 22
  investigated non-context symbols with no duplicate selected history keys.
  The priority heuristic was combining distance from one timeframe with
  pressure from another. Retained-input replay found 23 order-sensitive
  scores before the fix and zero after. Reversing inputs changed three of 22
  selected symbols before the fix and none after when both comparisons omitted
  unavailable turnover tiebreaks. Fair lanes and history caps remain.
- Attachment output used the Windows spelling of the same checked WSL ZIP
  path. The patched reader verified the original attachment and final response
  read-only while retaining exact artifact identity and checksum controls.
  Unattested model-request totals are now unknown instead of conflated with zero
  verified requests. Existing oversized-card, citation, and planning diagnostics
  passed the native workflow fixtures.

The end-to-end fixture validated seven advisory rows covering all six finalists
across three simulated provider responses, reconciled them against deterministic
controls, and independently verified the ZIP and final delivery.
Fourteen focused tests and all 555 offline tests passed. Configuration validated,
installed skill revision 4 and both review mirrors matched, and all 28 protected
paths and six original artifact and evidence hashes matched their baselines.

No expired advice was imported and no live market request, model call or task
was made. The original job remains PARTIAL, with its artifact and evidence
unchanged. Keep PR #24 draft and `trade_authorization=false`.

---

# November 22 second live acceptance recovery

Job `20261122T104452Z-dff48ef326cb419aaccf56dc101916b9` ran at
`b98f73841209650465a7b016473d95b05c0b6e5a`. Its ZIP SHA-256 is
`5c205b425ebf3c1ae2b14a67e49da3203d971bd7b3b8671419ba4c4d1465fd44`.

- Batch 1 delivered all ten pages and attested 11 provider responses. The
  first ATUSDT support ID (`a1157d76…386f`) appears nowhere in the immutable
  request. The other cited event and the two ZROUSDT citations are present.
  The original reply remains rejected. New packets give an exact card-local
  copy-and-check rule, while the validator retains strict ID membership.
- Replaying the collection snapshot at `10:52:19.284Z` returned
  `AGENT_EVIDENCE_FUTURE`. The recorded child completion was `10:52:23.358Z`.
  At the stored audit time, `10:52:24.100Z`, receipt collection reached the
  citation check. The timestamp rule remains enforced.
- Batch 2 was reserved at `10:53:28.757Z`. The sole exact start call at
  `10:54:29.280Z` was 31.120 seconds beyond the old publication deadline.
  OpenBot acknowledged and created a child after the runner's missing-task
  decision. All nine page commands returned `NATIVE_DISPATCH_WINDOW_CLOSED`.
  New request-bound tickets retain the 90-second reservation phase, then
  allow a single submission within 90 seconds of reservation. Old tickets
  retain their original cutoff. Response and overall freshness limits stay
  in force, and the one-shot reply exposes `submit_before_utc`.
- The retained PARTIUSDT graph lists 92 card support IDs and 135 distinct
  potential IDs across the card, reference and events. Each of its two events
  repeats all 42 reference source IDs in the same order. The old single-card
  packet was never published, so its exact wire size is unknown. New packets
  factor identical provenance and the exact repeated reference suffix, and
  use compact JSON when needed. The retained topology with synthetic 48-byte
  fact values fit in 95,501 characters. The same topology with synthetic
  100-byte values still exceeded the 100,000-character limit. The projection
  preserves IDs, source order, eligible values, causal times and the full
  skill. Irreducible cards still report explicit omissions. Planning omissions
  have their own field and cannot mask a failed native batch.
- Basis made 21 physical requests against 40 allowed. The seventh causal
  screen returned a tool-level cooldown after 300 successful evaluations.
  All 519 broad 15m contracts were evaluated and zero broad 1h requests were
  dispatched. The remaining broad budget was 38.889 seconds against the
  60-second cooldown. A fixed-dispatch-count sensitivity check trades one
  50-contract causal partition for one broad partition in both saved traces.
  The provider's busy threshold under a different order is unestablished.
  The existing schedule and scope remain in place.

Nine focused regressions and all 548 offline tests passed. Configuration
validated, the registered revision 4 and both skill mirrors matched, and
all 28 protected paths matched the baseline. Read-only Windows replay
reproduced the original future timestamp, citation and dispatch rejections.

The original job remains PARTIAL. Its running delivery watcher recorded
`FINAL_DELIVERY_NOT_OBSERVED_WITHIN_BOUND` during the investigation. That
changed the mutable job state. The report, ZIP, requests, tickets, reply and
audit matched their initial hashes. Historical inspection did not import
advice, rerun market requests, or submit native tasks. Fresh acceptance and
delivery must be verified independently. Keep PR #24 draft and
`trade_authorization=false`.

---

# November 22 live acceptance recovery

Job `20261122T090259Z-8d6f07e2d94347a5b159951b28b6ef26` ran at
`bf8a40596cbc6f0adf6cf42c7ed38ce67982a1f5`. The original child rollout's
record 19 (ordinal 18) was the authorized page-1 read at `09:08:18.757Z`.
The verifier expected a single-line Code Mode wrapper and rejected the
observed indentation and line breaks. The reader now allows ASCII formatting
whitespace around the same fixed tokens and still binds the exact literal
command, execution, output bytes, turn, and page order.

The regular WSL-to-Windows reader verified one parent acknowledgment, ten
distinct successful page reads and their exact model-facing output, and an
attested final reply with two valid rows and 11 provider model responses.
This was historical verification within the job's original time bounds,
including a pass with the live configured-model checks enabled. The
original terminal rejection halted eight planned later batches (14 cards).
The first error was a separate Windows subprocess timeout during the parent
handoff observation at `09:07:56.659Z`. The collector recovered and verified
the acknowledgment at `09:08:00.428Z`. Retained logs do not identify where
the process stalled or which timeout bound expired. New allowlisted
diagnostics identify the read operation and binding timeout; bounds and
retry behavior are preserved.

The report's 19 physical Basis requests comprise three setup requests,
eleven successful 15m screens, and five causal 1h screens. Causal 1h returned
200 valid rows before its fifth partition hit the tool-level 60-second
cooldown. The shared stop deferred all 519 broad 1h contracts before any
broad 1h dispatch despite 11 reserved partitions. An offline regression
reproduces those denominators and the zero-dispatch result. Phase order stays
in place pending evidence that a bounded interleave can improve coverage
while preserving causal reads, freshness and fair allocation.

Saved report SHA-256 `6a71cb66c417207f26967dffda22d9253c451ca3fe30831f7ab30103370e9d45`.
Canonical packet SHA-256 `cf4b976a1582fc83b5d3e66d51065ac2c1e35b9930d12791860635d7b1dfac63`.
Five focused tests and all 542 offline tests passed. Configuration validated,
28 protected paths matched the baseline and the saved job hashes matched
their initial readbacks.
The saved job remains PARTIAL. The replay made no market or model calls and
imported no advice. Fresh end-to-end acceptance requires separate owner
authorization, current native review and reconciliation, and verified final
delivery. PR #24 stays draft and `trade_authorization=false`.

---

# Setup-only native preflight compatibility

From `fb6f8e3bb880e510929a737a744bedb5aeb995b5`, the reader now allows exact
Codex CLI `0.171.0` ordinal envelopes alongside the two supported `0.169.0`
formats. Windows Python verified the retained setup scope through its
original preflight command. Its later compaction remains unsupported. The
documented command returned `NATIVE_NOT_INVOKED` while the Researcher was idle.
All 539 offline tests, 58 focused tests, configuration validation and 28
protected-path comparisons passed.

Overall setup is not ready. The local registered orchestration revision
still supplies older inline instructions despite matching workspace
mirrors. The Full access and auto-approval profile also requires an owner
decision. No skill, profile, configured model or private record was changed.
There were zero market requests, model requests or task submissions.
[Evidence and separate owner gates](NATIVE_PREFLIGHT_COMPATIBILITY.md)

---

# Historical native receipt compatibility

The approved code baseline was `c4e93d31f3dbc0074f6652f68b1cb4215c3382fe`.
The integration branch advanced through the documentation-only upstream
revision `e606f9e6f3f603c0084e8a3e537b83c7a8b06c83` before publication.
Historical Codex model checks now use the exact bound parent and child turns.
The active path still verifies the configured model and session projections.
The paged reader validates the observed Code Mode envelope and its paired
literal command, successful execution and model-facing page bytes.

Windows readback of `20261121T155516Z-817636a12ff84a4797555d0d2887de42` passed
inside its original freshness envelope. It verified one acknowledged parent
submission, the child execution, ten pages and the final reply. The saved job
is `PARTIAL`, and the historical advice has expired for current use. All 536
offline tests, configuration validation and 28 protected-path comparisons
passed. A future live acceptance requires separate owner authorization and a
passing preflight for the active runtime and installed skills.
[Verification details and evidence hashes](NATIVE_DYNAMIC_MODEL_IDENTITY.md#receipt-compatibility-verification)

---

# Dynamic native model identity

From tested baseline `7282cf92ea7f185d38f87396f1ccfe3c51ec960e`, the owner-confirmed
`CONFIGURED_MODEL` failure was reproduced after a legitimate selection change.
The implementation at `c4e93d31f3dbc0074f6652f68b1cb4215c3382fe` verifies historical receipts against
the captured parent, child and model. Active native work still checks the
configured model against the captured job. The next authorized job captures
its own model from the live configuration and attested session.

The full offline suite passed **532** tests in 529.223 seconds.
Configuration and 25 protected path checks passed. The configuration manifest
SHA-256 is `9afd9d38838c2f767db5bb995633928380db3ac8b09c8f5014f3a15c805623e3`.
The owner reported successful Windows packet and ten-page readback.
The original job's historical model receipt remains pending bounded host
verification. [Recovery and readback procedure](NATIVE_DYNAMIC_MODEL_IDENTITY.md)

---

# Windows native receipt recovery

The recovery uses tested baseline `27addd0a0ea3d39799aad7f8ac0ba602c103fe42`.
The Windows reader validated ordinary drive paths before reopening them through
the same extended path for file metadata and bytes, preserving the link and
scope checks. A 272-character regression fails against the baseline and passes
against `7282cf92ea7f185d38f87396f1ccfe3c51ec960e`. The full offline suite passed **527** tests.

The historical `NATIVE_MODEL_SWITCHED` comparison remains unresolved on the
intended host. The scoped reader now reports the failing comparison and keeps
exact model, provider and adapter equality. Protected skill sources and the
source configuration were verified against the baseline. The original job's
Windows packet, identity and receipt still require a read-only host readback.
[Recovery report and readback procedure](NATIVE_RECEIPT_WINDOWS_RECOVERY.md)

---

# Consolidated Market Researcher recovery

The recovery starts from the approved `62395f3ff3057c096724498dca5648e06f5da6bb` on
`feature/external-first-market-researcher`. The tested implementation is
`27addd0a0ea3d39799aad7f8ac0ba602c103fe42`. Draft PR #24 carries the implementation and its verification.

The scan protects 15M breadth, runs the qualified causal 1H pack before optional
work and reports actual dispatch, validation and deferred coverage. Selected
audit draws require completed price-structure assessment on both timeframes.
F4 recognizes a later qualifying move after weak opposing progress. The native
runner closes submission observation on deadline, preserves a reserved packet
within its original freshness during a reader outage, and serializes terminal
state and final delivery.

The full offline suite passed **517** tests. Configuration, 320
independent ATR comparisons and 25 protected paths passed. No market or native
task/model calls were made. The eight independent audit files were unavailable.
Current Basis 1H breadth, Windows receipt access, genuine native execution and
final ZIP delivery remain pending one controlled owner-host acceptance.
[Recovery report and acceptance procedure](CONSOLIDATED_RECOVERY_IMPLEMENTATION.md)

---

# Native handoff recovery — 20 November 2026

The approved baseline `d07b450c28121da778c17888f45eb657f4c24b20` was fetched
on `feature/external-first-market-researcher`. The owner-supplied post-mortem
for job `20261119T022832Z-e3e2d1562cbb43f5ab602d179a391930` identified a
reserved ticket with no `openbot.start_task` call. The full console output,
Windows-side path read and isolated tool discovery each blocked dispatch.
Modern Standby subsequently exhausted freshness.

The v2 orchestration skill uses the main chat's OpenBot catalog and sends the
runner's compact, exact argument object to the native task tool. The existing
same-agent task receives the full canonical skill and evidence in numbered,
SHA-256-bound WSL reads. The parent call, native acknowledgment and task row are
audited separately. Submission and response have 90- and 30-second observation
bounds respectively. App creation, provider execution, review validation and
delivery require their own evidence. No automatic redispatch occurs. Freshness
still expires after 600 seconds and clock discontinuities have a separate
diagnostic.

Offline checks against the pinned OpenBot 0.71.0 catalog, Zod schema and mailbox
gate accepted the exact 1,067-byte argument object. They exercised a
95,759-character fixture that produced 99,937 bytes as inline task arguments.
Ten pages reproduced the full packet, with a maximum page of 11,247 bytes.
The schema/mailbox rejected the respective oversize cases and the schema
rejected a file argument. Fixture receipts proved one submission, matching app
creation, complete provider input, validated advice and reconciliation. Fault
injections covered missing attempts and responses, task acknowledgment without
a task row, rejections, duplicate dispatch, truncation, Windows/WSL path
translation, hash substitution and stale requests.

The initial full offline suite passed 495 tests and the broad focused suite
passed 91. The final targeted integrity suite passed 40 tests, including the
additional duplicate-attempt, truncated-page and oversized-status-history
assertions. Configuration validation and the 24 unchanged protected hashes
passed. The orchestration skill is the single versioned exception in the prior
protected manifest. Its source SHA-256 is
`1170500f182592cf6fe89f7aae04fb74fe68b7a0de96ae68b2bb2d601f318a27`.
An intermediate push check exposed a poll between file publication and the
durable ready state. Selecting v2 at command attestation closes the legacy
ticket path during that window, with a regression that polls immediately
after file publication. An intermediate local run that overlapped source edits
also failed the warm-cache assertion. The cache keys include source hashes,
so release checks use frozen source. No tests or cache gates were relaxed.
The full release checks run against the published commit. Cloud preflight
returned `NATIVE_AUDIT_CONFIG_MISSING`. Live acceptance requires the existing
owner runtime using the v2 installation, checksum and acceptance procedure.
[Native handoff v2](NATIVE_HANDOFF_V2.md)

---

# Workflow lifecycle recovery — CODEX_CLOUD, 16 November 2026

**ENGINEERING_READY_FOR_LIVE_ACCEPTANCE — live OpenBot NOT_RUN_IN_CODEX_CLOUD.**
One writer on the existing integration branch, fetched clean at
`95d509617f52e6fe8911930b8360faf1d5230c5d`. PR24 stays draft; main stays
`2343053ce68f6fff4525c5b67771ea445deb3779`.

The latest failure facts supplied by the owner are retained as observations;
the ZIP named `0721464f2085b14f953c617c9ff56f5f785d78a9d9d574f87901dc2acdfac3db`
was not supplied, so its checksum/offending native row was not independently
verified. No exact cause of that individual live exception is manufactured.
Controlled regressions prove the active-pointer contract can reject valid
persisted parent/child work and expose additional lifecycle faults.

Native collection/import now binds the captured parent across legitimate active
pointer changes, checks child task/turn/session relationships and exact provider
input/output, rejects duplicate/pre-request handoffs and persisted task
substitution, and keeps actual creation states separate from verified model
attempts. One-shot tickets remain one-shot; missing tasks and terminal causes
are explicit. Mixed validated batches survive rejected independent batches;
per-card expiry and unreviewed finalists prevent false completion. All viable
finalists remain covered; optional watch review has a visible four-card budget.
The model gets the complete registry states/definitions and source/dependency
labels under the existing whole-card transport limits.

Startup reservations are atomic/recoverable. The approved WSL/POSIX runner uses
an OS-released guard, publishes its worker process, detects PID reuse/missing
publication and preserves terminal states. Dead whole scans are not replayed;
receipt-only resume re-audits the same task. A bounded read-only delivery observer
checks exact attachment/final proof and unchanged ZIP bytes after export.

The exact SHA-rendered setup-and-acceptance message is now an explicit owner
command alongside the unchanged ordinary sentence. Preflight checks actual
provider records and both installed skills. A separately labeled archived
packet may prove genuine native transport before the one current scan; a failed
transport preflight exports diagnostics without starting market access. No
archived interpretation is imported as a current-market finding.

Untouched baseline:447 passed645.733s. Intermediate full:478 passed892.649s,
plus the exact acceptance-chain fixture. Final release: **485 passed960.099s,
zero failures/errors/skips**, exact79-file source hashes. Expanded targeted set:
92 passed. Initial red fault injection, a corrected lazy-iterator diagnostic,
and the deliberately interrupted preliminary full run remain disclosed.
Config VALID; all25 protected files unchanged, including both canonical skills,
blueprint/plan and source configuration. F1–F9/27 measurements/31 methods and all
source/admission/trading gates remain intact. No actual new market/model request,
Cloud Binance retry, order, scheduler, app/model/permission/Local Scripts change.
Actual Cloud native preflight stops at NATIVE_AUDIT_CONFIG_MISSING.

[Root causes, complete workflow and acceptance checklist](WORKFLOW_RECOVERY_AUDIT_20261116.md)
· [Exact acceptance prompt template](OPENBOT_RECOVERY_ACCEPTANCE_PROMPT.txt)
· [Verification](../../evidence/external-first/workflow-recovery-20261116/verification.json).
Publication SHA, remote equality, draft status and exact-head CI are observed in
the final delivery. Full live acceptance remains NO-GO until the existing owner
OpenBot runtime independently supplies the genuine receipts and ZIP/final proof.

---

# Final engineering recovery — CODEX_CLOUD, 16 November 2026

**END-TO-END ENGINEERING: COMPLETE_OFFLINE_VERIFIED.**
**LIVE ACCEPTANCE: NOT_RUN_IN_CODEX_CLOUD.** User-authorized recovery of the
existing external-first Researcher; one integration writer, PR24 remains draft.
Started from fetched clean `7c72c817f87c829db1042d9b009e11117bb23fe4`.

The supplied failed live ZIP verifies SHA256
`249438aaebe657a3fa8849f86bcdcb7a54c8f0dbdd11ae35af3393c1090460ae`
and all internal checksums. It remains immutable historical evidence. The
original reader exception was not retained, so no speculative Windows root cause
is claimed. A controlled process failure independently reproduced publication
being skipped by the old whole-wait delegation.

Task publication is now separate from scoped native receipt reads. Durable
review states and a real monotonic per-batch wait expose READY before blocking,
retain the first sanitized fault, and handle pending, failed, invalid and timed-out
tasks. Exact one-shot dispatch tickets survive double polls; worker claims and
persistent shared metadata prevent scan/task replay and lost watch continuity.
Provider attestation/model flexibility remains strict and the prior ordinal /
-NoProfile repair is intact. Separate attachment/final provider proof records
FINAL_DELIVERED without changing the already exported ZIP.

All viable finalist hypotheses plus protected current rivals enter whole-card
batches under actual request/brief limits. The full asynchronous fixture computes
five coins on two TFs/two families including a bearish case: six finalist
hypotheses plus one rival, seven reviewed cards, three fixture tasks/attempts,
zero genuine LLM calls. Valid advice changes research priority. A second E2E
scenario ages quotes/depth and invalidates a consumed-obstacle candidate after
refresh. Strict READY stays zero and trading authority false.

History allocation now derives from physical I/O, measured source latency and
freshness instead of18+2 coins; current in-radius references and decisive questions
are no longer cut at4–12/six. The519 fixture investigates beyond20 selectively,
warms without new histories/remote screens and preserves reference/event/watch
identities. Requested-but-absent rows get one missing-only recovery while accepted
partitions and frozen cutoff survive.27 actual component measurement states,
9 families and31 method states are exported with source/definition exceptions.
No source certificate, fee/room/admission gate or production-method flag changed.

Untouched baseline431 tests passed299.374s. Final frozen-source full suite:
**447 passed454.566s, zero failures/skips**. Focused receipt covers62 native/
runner/provider/coverage tests. Config VALID; protected hashes and whitespace
pass. Red publication/wait tests and an intermediate warm-cache assertion during
ongoing source edits remain disclosed in the verification record; no assertion
was relaxed and no hidden skip added. Genuine OpenBot/market/model performance
is unclaimed. No Cloud Binance probe, live model substitute, trading/admin/DB
change, schedule, Local Scripts, new agent or model reassignment.

[Feature/source matrix](FINAL_RECOVERY_ENGINEERING_MATRIX.md) ·
[Native E2E trace](FINAL_NATIVE_ORCHESTRATION_E2E_TRACE.md) ·
[One-message live acceptance](FINAL_OPENBOT_LIVE_ACCEPTANCE.md) ·
[Verification](../../evidence/external-first/final-recovery-20261116/verification.json).
Publication SHA/remote equality/exact-head CI are observed in the delivery handoff.
After the approved checkout update, the owner's next action is one message to
that same Researcher: **Run the complete market research now.**

---

# Native attestation compatibility repair — CODEX_LOCAL, 15 November 2026

**Engineering validation only. NOT_RERUN_IN_CODEX; OpenBot live acceptance pending.**
Started clean and fetched the approved integration branch at `d4b2330`; older
checkouts/main preserved, PR24 stays draft. The saved failed job confirms FAILED
before start_proof/SCANNING, with no ledger/report. Read-only authentic-session
inspection reproduced native_codex.py:65: the regex assumes timestamp,type,
but the real envelope is timestamp,ordinal,type,payload. Actual CLI0.169.0,
OpenBot origin, session/workspace/backend/model match. The successful actual
launch also has PowerShell -NoProfile,-Command; the old matcher allowed only
-Command. Inherited fixtures represented neither difference.

Scoped parsing/receipt repair now reads that authentic archived session and
matches exactly one successful launch receipt. It preserves full identity,
owner/turn/session/workspace/model, exact command, successful exit, input/reply
provenance and zero review tools. Ordinal/semantic order, duplicate keys and
metadata checks fail closed. Full-input bytes cannot be reconstructed by joining
parts after a missing newline. Only allowlisted diagnostic labels and numeric
usage counters leave the reader. Known Codex backend/version remain openai/
0.169.0; models are not name-pinned and unverified providers fail closed.

Both installed discovery skill files and both repository SKILL.md files retain
their hashes; blueprint/plan, source certificates, 27 measurements, nine families,
31 methods, source/admission gates and trade_authorization=false are unchanged.
Existing fixed Windows read-only identity reader passes outside the WSL sandbox;
no app permissions, credentials or Local Scripts changed. No live scanner/model
or OpenBot acceptance was initiated. Focused compatibility15/15 and initial
native-runtime13/13 pass; full-suite/config/protected-file results are in the
[sanitized receipt](../../evidence/external-first/native-attestation-repair-20261115/verification.json).
See [repair report](NATIVE_ATTESTATION_REPAIR_20261115.md) for exact guards,
observed layouts, adversarial coverage and provider limits. Publication and
exact-head CI are verified in the delivery handoff. Owner next action: refresh
the approved checkout to the published SHA and send **Run the complete market
research now.** to the existing Researcher. No skill reinstall is required.

---

# Model-flexible OpenBot integration — CODEX_LOCAL, 15 November 2026

**PARTIAL: new orchestration skill is not installed; explicit owner approval for
the dependent same-agent task handoff and owner-originated live acceptance are
pending.** No live market scan or native review was initiated by Codex. See
[engineering checkpoint](OPENBOT_MODEL_FLEXIBLE_INTEGRATION.md) and
[sanitized verification](../../evidence/external-first/openbot-integration-20261115/engineering-verification.json).

Started from freshly fetched clean54f6e39 on the sole integration branch in a
new isolated clone; existing checkouts/main unchanged. Existing native Researcher
configuration is codex/gpt-6-luna on OpenBot0.71.0/CLI0.169.0. Trusted runtime
identity replaces the live static-model assumption. The inspected Codex receipt
schema verifies backend/model, current parent and isolated review turns, exact
full inline skill/request, zero review tools and exact provider/app final reply.
Live import re-reads native storage rather than trusting an audit file. The
historical OpenCode collector is retained; unsupported schemas fail closed.

A fixed asynchronous runner requires the exact current owner run message and a
genuine provider-recorded command before market access. It exposes durable UTC
job/progress/review/final states, prevents duplicate runs, imports verified advice
into the existing scan and exports a sanitized hash-verified ZIP. Its separate
orchestration skill does not alter the evidence-only review skill. No global MCP,
Local Scripts, model/profile/permission change, trading or scheduling operation.

Actual Windows→WSL offline preflight exposed cross-OS active-WAL disk I/O errors.
Extending the existing fixed Windows reader to identity/authorization/receipt
reads repaired the real offline launcher: exit0, correct configured identity,
zero live calls. The Windows UI bridge instead fails before JavaScript due to
its WSL sandboxCwd metadata; the Local Scripts CLI is intentionally unused.
A private path-only setup was reconstructed locally; it is ignored, not public.

Untouched390-test baseline passed643.037s; initial414-test integration passed
679.385s; final416-test local regression passed385.333s. The exact owner-command
guard additionally passed12 focused tests8.034s. Config VALID; immutable
blueprint/plan/review-skill hashes and all source certificates unchanged. Fixture
compatibility is not empirical live compatibility. Fresh funnel/advice/resources/
live diagnostic ZIP are NOT_RUN. True specialist feeds, M14/M15 definitions,
quota/cadence/execution costs and prospective performance remain unqualified.
Publishing/remote-head/CI results are reported in the final handoff; PR24 stays
draft and is not merged. Next: supported in-app skill setup, then the owner alone
initiates the first live examination from the Researcher's normal main chat.

---

# Final functional acceptance — CODEX_LOCAL, 15 November 2026

Started from fetched clean `6af2e8db8016688e78878baf4950c7d2c5b710cc` on the same
integration branch; PR24 remains draft. See
[final acceptance](FINAL_FUNCTIONAL_ACCEPTANCE_20261115.md) and
[sanitized receipts](../../evidence/external-first/final-acceptance-20261115/README.md).

The ordinary operator path now freezes its first valid closed remote snapshot,
preserves valid partitions, shares source time across TFs and turnover quartiles,
adapts the separate operational-alt capacity to measured costs, preserves old
nearest obstacles as explicit source gaps, and invalidates caches on code changes.
F5 requires an observed failed-reversal rebreak for conditional admission; F9
adverse recovery/recycled stabilization no longer supplies the old directional
case. Actual measured F6 balance feeds M16; F7 selects the current episode.
Fresh quotes follow slow depth retrieval. Immutable exports survive report
updates and real warm decoding. Readable show/results/watch/coverage and UTF-8
saved Decimal rendering are exercised on actual production-facing outputs.

Distinct live cutoffs: D09:00 accepted200/150 remote15m/1h rows and investigated
2 alts under poor connectivity; E09:15 accepted450/400 and investigated20; final
G09:45 accepted519/519 and investigated20. Final G produced5 conditional research
coins GUN/F8, ATOM/F8, HUMA/F8, MMT/F5, KAT/F8;21 active watch coins and0 strict
READY. G311.856s/93HTTP/6,536,742B; H25.065s/9publicHTTP/0Basis/0histories preserves
21 active coins and revalidates the five candidates. No forced positive count.

One owner-submitted native task used the unchanged Researcher/model/skill:
2 valid ACE F8/F9 cards,3 observed provider attempts, complete reads and0
unauthorized operations. ACE F8 was the final conditional candidate in that same
D run; F9 remained deferred despite model INVESTIGATE advice. Matched-source
membership unchanged; source-gap/first-obstacle questions linked to dispositions.
No performance improvement or native review of the separate later G cohort is
claimed. Original Recovery UNI/AAVE arithmetic survives; premature MET/F5 and
adverse ESPORTS/WIF shock interpretations are independently checked negatives.
Original snapshots remain unchanged, including their disclosed export hash fault.

All9 families/31 methods and27 measurements retained, with actual selected
execution and independent price/alternative examples. True profile/footprint,
executed absorption/liquidation, dated sectors/catalysts and canonical M14/M15
remain precise source/definition limits. No production certificate promotion,
orders, scheduling, Freqtrade DB/config, other subagents or Deep Analyst changes.
Full/focused test receipts, immutable hashes and exact final GitHub delivery/CI
are recorded in acceptance evidence and the final handoff.

Final delivery cross-check corrected a stale MMT audit sentence: its recorded
09:45 closed-bar outside acceptance was observed; renewed retention remains a
question. Original snapshots and calculations are unchanged. Initial exact-head
CI exposed two tests assuming ignored work/ already existed; the new test class
now creates its own scratch parent before any temporary directories.

---

# Historical one-session recovery — CODEX_LOCAL, 15 November 2026

Fetched clean feature HEAD `722fe0a6f5232fad23f39f387b475e7476e47be5` before
implementation; PR24 draft/main untouched. Independently supplied diagnostic ZIP
hash `7d9333ebad157cac66fafc27cba0b6d5f0a1894743dc5fde8ce4f62cc231289d`
verified. Immutable blueprint/plan and historical source certificates unchanged.
The owner explicitly approved CONDITIONAL_RESEARCH_ONLY handoffs with verified
current structure/price/spread and named room/fee/depth questions; strict READY,
production method/source qualification and trading authority are unchanged.

**Actually functional:** separate2-symbol protected allocation plus18 operational
capacity;20 genuine non-context coins investigated in successful ordinary runs;
selected current causal episodes, explicit reference/nominee dispositions and
ranked coin watches. Sourceable significance/proximity, quote participation,
whole-bar Q/V, targeted displayed-depth M25 and declared horizon/cost scenarios
execute. Missing balance/specialists remain precise gaps. Current candidate
selection no longer depends on terminal trade authorization. No forced count.

Source integrity uses exact frozen bar cutoffs; no historical Basis as_of claim.
One advised60s same-session busy resumption, pending202/transient receipts,
physical dispatch accounting and bounded calls/bytes/time preserve good data.
Selected official endTime histories recover justified candidates; no wide local
warehouse. One real run accepted35015M price rows with1H price deferred while
its separate causal1H pack evaluated519. The next real restart accepted519/519
price rows on both TFs. Final newer remote rows were all rejected, yet20 selected
alts still produced useful research. This is not a provider ceiling or a claim
about opportunities among unobserved symbols.

Final normal run `827bfd3d6bb548e873c4754b76f6b34d2ab0803427b7b0ae9685c8438b67de1e`:
**five conditional research coins** UNI/F8, MET/F5, AAVE/F8, ESPORTS/F9, WIF/F9;
three measured research-room cases/two named room questions, zero strict
handoffs.22 active watch coins include BTC/ETH;197 historical references on33
names remain separate.750 archived contradictory hypothesis records are not
trades/losses. All common watch first-seen times survive real restarts
(103/103,167/167,167/167). Two benchmark1H freshness checks became stale when the
run crossed the hour; frozen selected histories remain available, context
unknown/non-veto. Final98 market HTTP/6,802,540B/1,140.198s including native wait.

**Actual native acceptance:** existing Trading Lab Market Researcher and
unchanged `opencode/deepseek-v4.1-flash-free`, skill hash
`96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb`.
Request `8baf49cd472d2c57d3113927706898fded04a3ea5acea22f407f175d1a06e33d`
created07:07:58Z; actual turn07:11:44.564–07:14:26.414Z, five provider assistant
attempts, two ICNT/APR cards independently audited/imported before07:14:30.633Z:
VALIDATED_ADVISORY_ONLY in the pre-admission phase. Complete skill/request bytes,
exact citations and read-only tools verified; Local Scripts/model/permissions
unchanged. WATCH/INVESTIGATE priorities and questions added; no facts or
eligibility changed, usefulness unmeasured. A prior genuine turn/five attempts
was rejected for prose in an enum; actual invocation counts are now retained
independently of reply validity. No hand repair or copied-chat escape conversion.

Real testing exposed/fixed multi-coin obstacle scope on restart and prevented
its old post-error native fallback. Other fixes: direct membership rather than
repeated full fact-map copies, recent/relevant references, distance-aware stage,
expiry/contradiction identity, route units, publication/model counters, exact
quote/1H denominators, F9 code/source state, portable CPU and UTF-8 manifest.
All27 measurements/F1–F9/31 methods remain. Eight selected current-depth method
observations on each selected TF in the final run do not qualify persistent
walls. Full methods/production/source rights/sustained quota remain PARTIAL;
M14/M15 definitions and actual profile/footprint/flow/liquidation/sector/catalyst
feeds remain unsourced. No Deep Analyst integration or trade/scheduling change.

Baseline357 tests passed678.857s; final372 passed1,211.303s, zero failures/skips;
19 critical source/native/restart regressions passed27.749s. Config, immutable
hashes and diff checks pass. Initial pacing-test regression, expired preliminary
request/interrupted transaction, scoped-room failure and rejected native reply
remain explicit in receipts. Four completed live scans total367 market HTTP /
25,056,841B; interrupted-probe cost not fully retained. Two native turns/10
assistant attempts report estimated$0 in app records; billing/entitlement and
charged/sustainable source quota unknown. No future outcome/recall/P&L claim;
ten diagnostic cases stay pending until after2026-11-15T18:46:28Z.

See ONE_SESSION_RECOVERY_RUNBOOK.md and
`evidence/external-first/recovery-20261115/` for exact source/method/native/test
receipts, before/after scopes and hashes. Full reports/private receipts stay
ignored under work/recovery. Publication SHA/remote equality and exact CI are
verified after commit/push and recorded in the owner handoff; PR24 stays draft.

---

# Session 6C — final combined acceptance under approved source gates

CODEX_LOCAL / SOL, completed2026-11-15. A `8a7e61b` and B `4c3b88f` were
pushed/verified; intermediate implementation `119ae13` also passed both CI runs.
Final ordinary `scan now` now imports real existing-agent advice while current:
**VALIDATED_ADVISORY_ONLY**, complete skill/request byte proof,1 reviewed card,
3 actual provider assistant attempts,0 unauthorized operations/0 read retries.
Import461.217s after request creation, native111.169s; persisted0 research handoffs,
0 orders. Same Trading Lab Market Researcher/model; Local Scripts remained off.

Current market denominator519:15M price519/519;1H150/519 with369 failed/unevaluated
(including50 missing rows); full registered CORE519/519 on both TFs remains the
separate Phase A qualification receipt, not a broad current production claim.
38 market HTTP/4,041,060B/657.409s including interactive wait;1164 watches,
79 near misses,777 invalidations,953 gaps. DB176541696B at9 snapshots.
Subsequent changed-cutoff run34 HTTP/0 model attempts/0 handoffs. Actual earlier
warm4 official/0 Basis, stable watch timestamps, clock, numerical/formation,
quiet/footer/Unicode/multiplier/young and real SQLite interruption receipts stand.

Fixed file-local grep compatibility without directory-search permission; all
request bytes and current skill still required. Optional per-run native budget
1–4 cards, default4; final test1. Manual-only normal application interface and
fixed Windows read-only receipt helper; no automatic message route or app
permission/model/key/new-agent change. All182 preexisting native skill files
unchanged. Native skill6c-native-review.2 SHA256
`96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb`.

Six known native turns/30 provider assistant attempts; five valid whole replies,
19 validated source-cited rows;1 original malformed whole reply rejected.
Late/closed replies remain excluded from current state.0 numeric claims, so
numeric hallucination rate not measurable; counterargument richness/recall/P&L
benefit unproved. App reports1773319 aggregate tokens and estimated$0 on its
API-equivalent basis; quota/future entitlement/failed usage remain unknown.

All27/F1–F9/31 rows retained:18 offline-oracle,11 source-dependent,M14/M15 pending.
Source/prospective/rights qualification remains PARTIAL as explicitly approved;
no new production certificates. Optional Deep Analyst NOT_INTEGRATED; one-way
read-only export preserved and tested, no unearned downstream activation.
Full suite357 pass, all331 inherited retained; current native/exchange tests pass;
final exact-source CI, SHA equality, clean worktree and immutable hashes are
verified before final handoff. PR24 remains draft; main/trading/Freqtrade intact.
See SESSION_06C_COMBINED_ACCEPTANCE.md, SESSION_06C_OPERATOR.md and final-acceptance
receipts. Earlier entries below are historical checkpoints, not current pending
work. Final publication SHA/CI are linked in PR24 and the owner deliverable.

---

# Session 6C — combined implementation checkpoint (Phase C acceptance pending)

A `8a7e61b` and B `4c3b88f` pushed/verified; both push/PR CI success for each.
Owner approved strict source gates. Actual existing Researcher/model ran3 native
turns/10 provider assistant attempts;14 rows validate across frozen/live-partial
cases,1 malformed whole reply rejected,0 current handoffs. The live model reply
completed within600s, but manual auditing/import passed the deadline; stale
fallback preserved actual time. No source-limited final is published.

Added optional exact-task read-only receipt collection to the ordinary scan,
with complete skill/request/tool/model proof, immediate import and final-time
admission recheck. No automatic model submission, new agent, model/key or
permission change. Native skill version2 hash
`96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb`.
All182 preexisting native specialist skill files unchanged. Fixed context budget/
tuple overflow, explicit nested-value transport omissions, strict numeric claim
validation, excessive JSON depth/exponents/audit roots and cached input reuse.

Actual WSL wait observed591 Windows WAL read failures and safely persisted
fallback. Existing Windows Python subsequently passed20 native DB probes and
five complete reader passes, all0 failures. Only the fixed data-only reader uses
that runtime; no Windows UI helper, app restart, native DB mutation or model call.
Latest16 focused tests pass; clean snapshots357 pass/no failures/skips; latest
exact-source clean full suite/CI publication are recorded separately.

Final corrected ordinary native collection requires one coordinated owner app
submission. Old timed prompt expired; owner readiness requested before another
window. Do not claim C completion from fixtures or native metadata reads alone.
Source/27/9/31 flags unchanged, downstream NOT_INTEGRATED, PR24 draft/main intact.
Read [combined acceptance](SESSION_06C_COMBINED_ACCEPTANCE.md) and
[operator steps](SESSION_06C_OPERATOR.md). Preserve this safe implementation
checkpoint while awaiting the final external acceptance action.

---

# Session 6C — existing native Researcher checkpoint (Phase B)

A `8a7e61b43abe4f0add5cf5c164f92cfa25ff29e2` pushed/verified, both CI success;
owner approved strict-bound Phase B. Existing **Trading Lab Market Researcher**,
`opencode/deepseek-v4.1-flash-free`, actually ran through the native application.
Scoped skill version `6c-native-review.1`, SHA256
`c2b50794113ea9561c0f38f3d99e9ad063e5f1e6517e1e9f5ca716b551b3ced9`; complete
skill-tool content and all2139 input lines independently verified in scoped
read-only app/provider records. All182 preexisting native skill files unchanged.
No profile/model/key/permission/trading edit or replacement agent.

Two native turns/six provider assistant attempts, two transport failures; one
skill load/two evidence reads, no other tools. Initial malformed whole JSON
rejected; explicit owner format correction5009 bytes validates12/12 rows/citations.
Four authentic frozen episodes/eight synthetic controls; both matched arms0
external requests/0 current handoffs. Added4 WATCH/8 DECLINE priorities and narrow
questions; injection detected, gaps retained. All contradicting-ID arrays empty;
0 numeric claims, so richer challenge and numeric accuracy remain unproved.
Genuine complete profile/witnessed-liquidation source positives NOT_RUN.
Original fixture rival-direction inconsistencies are explicitly disclosed.

Native wall778.943s +61.015s; app reports188781 total tokens and estimated$0 on
API-equivalent basis; quota/future cost/timely live response remain unqualified.
Optional ordinary scan exchange deduplicates changed inputs, consumes only
matching separately audited advice, and falls back on invalid/missing/stale
responses. No automatic invocation/retry; native application submission is the
owner's supported mechanism. Default scanner model calls remain0; hard source/
clock/economic gates unchanged. Frozen review cannot create live admission.

Isolated B snapshot353 passed552.658s; final fingerprint fixes12 focused pass;
config VALID. Exact pushed CI and final clean-checkout acceptance follow. See
[native review](SESSION_06C_NATIVE_REVIEW.md), impact list and compact public
native receipts. Phase C pending, downstream unconnected, source scope PARTIAL;
no source-limited final published.

---

# Session 6C — standalone Local checkpoint (Phase A; programme continues)

CODEX_LOCAL / SOL, 2026-11-14. Fetched/fast-forwarded to actual feature remote
`0034faec6a15690c67a3526eafdf94cd46490b62`; one writer, PR24 draft, main unchanged.
**PARTIAL standalone scope; no Phase B/C activation or final completion claimed.**

Actual public Binance/Basis qualification: fresh519 eligible of946 native records.
Registered full CORE15M519/519; CORE1H200 initial +319 serial same-cutoff recovery
=519/519. Independent quiet50, medium50 and footer7 pass with fillers excluded.
Selected BTC1H/ETH15M/1000PEPE1H/FRAX15M each33 fields/660 aligned comparisons on
recorded revisions. Corrected zero-amplitude correction was rechecked on FRAX.
Ten independently labeled authentic F2/F4/F5 historical positive/prefix-negative
cases preserve later availability; not complete family certification or live READY.
Unicode screen/official klines work; Basis targeted market_candles remains a
source-specific tool failure. No eligible listing under30 days; multiplier fields
absent, never inferred. All27/9/31 remain present;18 offline,11 source-dependent,
M14/M15 pending; no new production source flags manually enabled.

Repaired genuine nesting-limit/scaled-let/reserved-variable/zero-division failures,
explicit300-bar oracle validation, independent per-column isolation and provenance,
versioned scale decoding, minute-rounded shorter official ticker windows and
HTTP200/isError busy cooldown stopping. Original failed receipts retained and hashed.
Owner Windows time sync settled: three Windows and three later WSL server-time
request brackets contain Binance time; no restart or rewritten timestamps.

Clean final-code ordinary live cold:519 inventory,15M519/519,1H300/519 then provider
busy;0 admissions/385 watches/96 near misses/731 invalidations;41 HTTP,4,353,867 bytes,
117.310s. Warm4 official/0 Basis/0 history calls,6.100s, unchanged watch first-seen.
Later actual14:45 restart: both precursor TFs519/519;0 admissions,451 watches,
210 GAP_UNOBSERVED;361 common watch identities/times unchanged;47 HTTP,150.728s.
Actual abrupt SQLite process exit on copied real research DB rolled back its
uncommitted cache deletion; later restart records1 interrupted attempt. No trades.
Historical404 watches are404 reference IDs/396 exact directed levels/588 rival
interpretations on four watched names of five eligible.321 references are over15h
old. No calibrated false-alert evidence warrants fitting new thresholds.

Inherited331 baseline passed544.180s. Final standalone341 passed572.722s with zero
failures/skips, config valid; focused new10 regressions preserve all inherited tests.
Actual source responses/selected histories/SQLite remain ignored; compact public
receipts, failed artifacts hashes, full27/9/31 matrix and operator steps are in
`evidence/external-first/session6c/`, SESSION_06C_MATRIX.md and
SESSION_06C_FINAL_LOCAL_RUNBOOK.md. Only six Researcher files + focused tests/docs
and evidence change. No subagent/skill/trading edits,0 LLM calls.

Next: push/verify standalone checkpoint and both CI triggers; obtain explicit owner
approval of residual formation/specialist/quota limitations before Phase B. Then
inspect the actual existing OpenBot subagent/backend, produce tiny impact list,
and request secure model setup immediately if truly missing. No source-limited
final has been published. Phase B/C remain pending; no unsafe gate crossing.

---

# Session 6B — deterministic research completion (CODEX_CLOUD / SOL)

Owner completion Session 2 of 3. Started from fetched feature remote
`9b8128abc0868ff9e086c85b07c79367c27bd5af`; same integration branch, one writer,
PR #24 draft. **Ordinary on-demand research now works offline; production remains
PARTIAL pending the authorized Local source/clock/economics/coverage gates.**

The ordinary `scan_market_research` now consumes all F1–F9 timelines into causal
cards, simultaneous rivals/NULL, applicable method roles, bounded equivalent
questions, first-obstacle/cushion/economics, family fronts/Pareto comparison and
0–5 research output. A/B/C initiators union before advisory context; independent
strict specialist envelopes and rotating protected review are exercised. All31
method/TF rows remain explicit (18 offline-oracle, 11 source-dependent, M14/M15
definition-pending). Source receipts can qualify exact packs/families/methods
without changing interpretation; no new live certificate is shipped.

Added a versioned exact-partition resource plan (historical519: CORE22,
participation+22, approach+22; 26 cap cannot run66), explicit partial fallback,
remaining-transport cap for causal work, BTC/ETH multi-label context/breadth/IQR,
source-aware equivalent fact/absence caching, normal CLI replay injection,
read-only saved views and hashed serialized report. Original watches reopen;
late historical reconstruction preserves later availability and earlier reports;
incomplete gaps remain unobserved. Existing ledger/one-current-cache/atomic
recovery is preserved, with compact nested warm deltas. An actual retained pivot
before ATR warm-up exposed and fixed an early-history exception.
Later warm runs refresh point quotes/depth against the frozen export without
replaying history. Witnessed obstacle consumption persists across reconstruction;
changed independent envelopes invalidate the cache. Extended ordinary-runtime
tests verify later-UTC admission and a current crossing becoming LATE.

Ordinary CLI SYNTHETIC_TEST: **two conditional F4 hypotheses for one native
control contract**, 8 watches, 4 near misses, 2 invalidations; all cited exports
replay. Cold/warm offline scan wall1.816s/0.071s; DB405,504→413,696 bytes with
8/28/30/8 references/events/hypotheses/watch revisions unchanged; no market HTTP.
AUTHENTIC_RETAINED_REPLAY: dated five-name source subset, price5/5 on both TFs,
8 selected histories, **zero admissions**, 404 watches, 89 near misses, 713
invalidated hypothesis records, 2 symbol/TF budget omissions. Forty distinct
source-gap audits are reused across4,239 hypothesis links (81 planner records).
No4H/quote/depth/fee fabrication, current-universe claim or prospective recall.
All14 genuine Session5.5 histories separately traverse interpretation in tests.

Verification preserves the inherited295 tests and adds36 substantive tests;
final complete/clean-checkout receipts, immutable hashes, config and publication
readback are retained in [Session6B evidence](../../evidence/external-first/session6b/README.md).
The [runbook](SESSION_06B_RUNBOOK.md) contains the actual code path, limitations,
exact registered Local probes and single dependency-ready Session3 checklist;
the [27/9/31 matrix](SESSION_06B_MATRIX.md) reuses unchanged6A definitions.
Runtime source gating is not qualification, and offline positives are not live
opportunities. Sustainable source rights/quota/p95, full new CORE/method live
scope, optional specialist feeds, canonical definitions and the retained ~6s
clock problem remain explicit. LLM calls0, Cloud Binance0, market-provider HTTP0;
no paid dependency, bulk candle store, scheduler, order, trading DB/config change
or Deep Analyst connection. Final SHA/CI are verified in the publication handoff.

---

# Session 6A — analytical engine implementation (CODEX_CLOUD / SOL)

**Production release remains PARTIAL; offline implementation checkpoint.** Started
from fetched remote `ed0f63e8610ba2b34d734ff449d2de6156cfad2c` on the same integration
branch; PR #24 stays draft. Main and the immutable blueprint/plan are unchanged.

Implemented shared measurement gaps, strict executed-tape/profile/footprint/
aggression/specialist adapters, all F1–F9 selected formation reducers, actual
named price-method lifecycles and all 31 explicit method contracts. M14 canonical
rules and M15 Keepssy remain definition dependencies; no invented signals.
Added two finite 12-column CORE contracts, isolated participation and registered
pre-break approach/pressure, quiet-location and controlled-correction packs:
33 distinct column definitions / 10 compiled TF packs plus 3 typed source-adapter
contracts. No new live source gate was promoted. Legacy 16 scalars and 3 narrow
masks retain their narrower prior qualifications.

The ordinary scan now calls the capability-registered analytical engine on its
existing bounded selected histories; every family/method's independent code,
source, formation, coverage and empirical flags are visible. Source-gated Route A
remains disabled pending real qualification. Quote-RVOL is isolated from price
packs; both price TFs run first under the unchanged 26-call ceiling, with explicit
optional omissions. Frozen IDs are memoized without changing hashes. No extra
broad local history, feature warehouse, order, scheduler or downstream connection.
The source-gated F6 true-profile, F7 event-anchor, F9 witnessed-liquidation and
M21 executed-tape branches are wired into the same analyzer. Tape/profile IDs
bind content across retrievals; OI native/base/notional conversions remain distinct.

**Verification:** inherited 237 tests passed before edits; final **295 passed,
0 failed, 0 skipped** (58 new), 147.46 seconds on this Cloud run. All 14 genuine
Session 5.5 selected histories execute through the new analyzer with recorded
ticks and original availability; this is retrospective reconstruction, not a
prospective shortlist. Added arithmetic/event positives and negatives, strict tape,
MSS/OB/breaker/iFVG traps, F5-without-reclaim, zero/no-event/short history,
append-future invariance across all families and methods, TF/identity/clock and
runtime optional-failure isolation. Native ATR/precision/pressure/Unicode/provider
failure regressions and all original fixtures remain intact. Config, immutable
hashes and diff checks pass. **Zero market-provider HTTP and zero Cloud Binance
requests**; only Git/GitHub publication uses live network.

See [Session 6A runbook](SESSION_06A_RUNBOOK.md), [complete 27/9/31 matrix](SESSION_06A_MATRIX.md)
and [compact evidence](../../evidence/external-first/session6a/README.md).
Source qualification/rights, exact funding/multiplier metadata, complete specialist
tape, witnessed liquidation sampling, dated sectors, original publishers and
canonical M14/M15 definitions remain open. The owner was asked for Keepssy's
primary rules; no key or purchase is requested for the enabled public subset.

Next Cloud Session 2 can use these algorithms for professional interpretation,
multi-route questions, specialist orchestration, economics and intelligent
shortlisting. The exact Local-only registered oracle CLI is in the runbook;
Session 3 retains live source/clock/semantic proof and conditional integration.
No claim of new live all-coin coverage, useful forecast, profitable performance
or real new handoff. Final pushed SHA/remote equality and CI are in the publication
handoff; this commit cannot contain its own SHA.

---

# Session 5.5 — source-qualified causal nominations and defect closure

**CODEX_LOCAL; integration branch; start remote b330b20c4f7ff5d1558ed98fe0aa5b8cd36fa836. Release remains PARTIAL.**

Implemented a finite registered remote compiler for confirmed-pivot fixed-age F2/F4/F5 nomination subclasses, independently qualified on actual selected Binance data. Broad 1H causal work reuses the existing PartitionEngine and scan path, with separate sparse/event coverage and explicit disabled F2-upper positive gate. Added bounded deferred recovery across distinct failed partitions, protected same-budget causal/watch/quiet/contrary/audit allocation, genuine selected native depth/OI, first-obstacle consumption checks, declared economic scenarios with a separate conditional disposition, and a hashed replayable one-way export. Optional consultant stays disabled and cannot invent evidence. The public provider schema is pinned and checked before enabling causal work.

**Critical remaining gates:** full always-finite/sparse-isolated CORE, complete family/method semantics beyond the narrow templates, authentic positive admission under prospective availability, full representative young/multiplier cohorts, and sustained quota/recall qualification remain incomplete. This is substantive Sol work, not Luna housekeeping. No downstream integration or GO claim.

The concise [Session 5.5 acceptance matrix/runbook](SESSION_05_5_RUNBOOK.md) and [evidence](../../evidence/external-first/session55/README.md) record before/after states, exact failures and source limits. Owner assistance: **NONE** for the enabled public subset; no model provider is approved. Final clean code ebf7176948c78cf12b76d631cf14651eca439a5a passed 237 tests; price 1H/15M and narrow 1H causal templates each returned/evaluated 519/519, zero final failures. Two genuine remote nominations, positive CTK native verification; 47 watches, two invalidations, zero handoffs and 903 question omissions (507 symbols). Real SIGKILL after two retained GETs recovered without changing reference/event/hypothesis counts or watch IDs/first-seen. Warm/later each four fresh public GETs, zero Basis/history/LLM. Cold 56 HTTP / 5,401,481 response bytes / 176.373s scan, warm 4 / 1,808,941 / 5.127s; SQLite 5,189,632→5,246,976 bytes. A genuine 6.081851s clock regression blocked READY without altering source times. All 31 full-method gates/full CORE remain incomplete; limited Luna usability PARTIAL, later integration NO_GO. Exact per-method/tf coverage, advertised-versus-unknown quota, prospective audit and final publication receipts are linked in the runbook/evidence.

---

# Session 5 — durable on-demand remote research (2026-11-14)

**Environment: CODEX_LOCAL. Release gate: PARTIAL.** Explicit owner authorization
covers this Local session. Starting actual fetched remote feature head:
`38437c031a007634161edf03f5dde07afd7b9dd0`; local was `5c65978` and was
fast-forwarded only. Clean baseline, one Local writer, no agents/concurrent Cloud
writer launched. PR #24 remains draft. No main edits, resets or force operations.
Immutable blueprint/plan hashes remain unchanged. Delivery SHAs and CI are in the
final handoff; a commit cannot contain its own SHA.

## What now functions

- One `scan_market_research` path behind ordinary `python3 -m researcher scan now`:
  automatic official inventory/pulse, frozen source cutoffs, registered remote
  partitions, independent research questions, BTC/ETH context, bounded causal
  investigation, current selected economics, source-cited review, watches and
  atomic metadata. No owner inventory JSON, account key or LLM is required.
- Reused existing Basis/public Binance clients, PartitionEngine, Decimal numerics,
  frozen references/events, hypothesis/review/planner and SQLite ledger. No
  competing scanner, full-market local candle engine, feature history, bot/admin
  interface, paid/trial service, order route or scheduler was added.
- SQLite v5 composes savepoints with an outer transaction; immutable reference
  identity/ATR/availability, idempotent event/hypothesis writes, watch first-seen,
  scoped last **verified** observations, crash recovery and identity quarantine.
  Historical snapshots retain coverage/receipts/output hashes and causal metadata;
  only one current remote scalar export is cached. Repeats store compact deltas.
- Bounded selected F1/F3/F6/F7/F8/F9 facts now join the existing F2/F4/F5 and
  FVG/iFVG machinery. Added an executable selected EQH/EQL trial (M04): two
  confirmed separated pivots, first-pivot frozen ATR/tick tolerance, actual
  intervening retreat, birth only at second confirmation. Inferred price
  sensitivity is never witnessed stops. All 31 method statuses remain explicit.
- Source-backed BTC/ETH 4H/1H ContextCards and synchronized 16-bar remote-return
  breadth/median/MAD. Context orders questions without direction eligibility;
  watch/exception/structural budgets and every omitted question remain visible.
  Sector mapping stays UNKNOWN. No discovery-lift or profitability claim.
- Fresh selected top-of-book/premium facts may inform review; actual depth, fee
  tier, slippage/funding bounds, horizon and complete production causal source
  qualification remain missing. No fictitious READY/FAST or executable entries,
  stops, targets or probabilities are produced.

## Exact inherited repairs and limits

1. **ATR sampled remedy qualified:** explicit `rma(TR,14)` passes eight identical
   long starts and eight short starts for BTC/ETH/1000PEPE/quiet FRAX × 1H/15M.
   Short captures retain initial NULLs, 14-valid-TR seed and next five recurrences.
   The native `atr(14)` four/80 failures and Session 4 exact-start failures remain
   rejected regressions. No infinite-history or all-contract seed promise.
2. **New precision defect fixed:** Basis screen exports round to four decimals.
   The unscaled trial passes only 35/140 scalar comparisons. Registered ×1e8
   export/decode and a scaled close preserve small ATRs/prices. Final selected
   multi-column checks pass **160/160**, including Unicode screen membership and
   independent official oracle values. Actual source warm-up/window/ties/units
   are declared. A later positive-event check exposed the zero-offset pressure defect missed by
   zero-only samples. Both failed trials are retained; explicit current fields now
   pass 16 tail evaluations / 320 values, including 45 positives. Pressure remains
   a fixed-window visit proxy, not a complete method predicate.
3. **Real broad price pass:** fresh inventory **519 eligible / 427 excluded /
   946 total**; on both 1H and 15M, all 15 columns requested/evaluated/returned
   **519/519/519**, zero missing/failed in a complete development run. This is
   historical protocol coverage; its pressure qualification was revoked/repaired
   after the positive-event check. The final 16-column clean pass is recorded
   separately. **Full CORE = 0** and
   **production remote method predicates = 0**. Method/tf denominators and missing
   specialist/source reasons remain explicit for all 31 methods.
4. **Failures retained:** first broad run 1H 517/519 (rounded small prices rejected),
   15M 0/519 (source advanced beyond frozen cutoff plus tool failures); a later
   run accepted 300/519 and 319/519 amid transient MCP errors. A subsequent full
   pass accepted both 519/519. No failed response becomes a no-setup observation.
   One restart crashed on a missing `utc` import; fixed here, transaction recovered;
   its four earlier successful GETs have no retained byte/latency receipts and
   are explicitly excluded from measured totals, not hidden.
5. **Unicode remains operation-specific:** `我踏马来了USDT` screen formulas match
   independent Binance values, while Basis targeted `market_candles` fails on
   both tf with HTTP 200/MCP_TOOL_ERROR. Preserve exact native spelling.
6. **Quote RVOL repaired:** camel-case quoteVolume still fails; the supported
   quote_volume field matches native quote-volume RVOL in the final oracle. Zero
   baseline is separately UNKNOWN and cannot veto price families. One unqualified
   exploratory alias call used a provider-default 999-bar remote window; final
   client requires bounded references, and qualifying data is <=300 bars.
   **Still unavailable:** complete CORE, remote ordered method packs, true profile/nodes/footprint,
   absorption/OI direction/complete liquidations, unspecified primary definitions,
   dated sectors and sustained quota/rights remain unqualified/unsupported.
   Young and official multiplier cohorts are not fabricated from symbol names.

## Verification and measured operation

Baseline **184/184** passed before edits. Full suite **213 passed / 0 failed /
0 skipped**, plus the final 29 Session 5 tests after source/cache refinements.
Config, immutable hashes and whitespace checks pass. Tests include authentic
same-start seeds/initial samples, original failures, scaled columns, stale clocks
and filler exclusion, source/identity/gap safety, first run/repeat/restart,
crash rollback, corrupt/foreign/future DB rejection, bounded scalar retention,
zero ATR/volume, new listings, EQH known-at and no fake readiness. Existing tests
and source fixtures were not weakened. Required clean-pushed-checkout live and
CI evidence is appended after that execution; development results are not
relabeled as a clean-checkout test.

Development full pass: **39 HTTP / 4,471,412 response bytes / 109.810 seconds**,
p50/p95 **3,458/4,901 ms**. Separate-process warm repeat: **4 public GETs / zero
Basis/history calls / 1,808,644 bytes / 6.342 seconds**; references/events and
first-seen watches reused. That development ledger reached 9,154,560 bytes before
final bounded-cache compaction; it is an ignored runtime artifact, not a release
storage claim. Final fresh-ledger measurements are recorded separately.

Price-return coverage and causal/admission coverage are separate. The measured
development review retained **44 watches, 0 handoffs, 0 near misses**; zero does
**not** establish no opportunities. Hundreds of questions remain budget omissions.
Real request/source hashes and failures are in the
[Session 5 evidence](../../evidence/external-first/session5/README.md); operation
and resource scenarios are in the [runbook](SESSION_05_RUNBOOK.md). Gap/outage
multi-day tests are explicitly **SIMULATED**, not measured live downtime.
Charged units, daily quota, sustained rights and sustainable cadence are UNKNOWN;
no automatic schedule was enabled. No orders, account/admin/trading DB access,
credentials, whole-market candle store or external messages outside the authorized
GitHub workflow.

**Publication interruption during implementation (resolved):** WSL HTTPS and
Windows Git initially lacked usable non-interactive credentials; the owner
completed normal Git Credential Manager sign-in. No exchange/provider key was
needed. The first local checkpoint
`747da48c1cb9af859fe8096ae010ecc24bbf836c` was committed; remote publication/CI
must not be claimed until verified. A clean checkout of it passed 212 tests but
its live metadata write found receipt/host UTC skew. The repaired run preserves
all original timestamps, uses a disclosed conservative known-by bound and blocks
READY under clock uncertainty. It accepted all **16 columns × 519 contracts ×
2 timeframes = 16,608** scalar readings: 41 HTTP, 189,558 request-body bytes,
4,918,993 response bytes, 115.149 seconds; p50/p95 2,692/4,784 ms. It saved
48 references, 44 watches and four causal invalidations in **1,961,984 SQLite
bytes**; zero handoffs/near misses, 776 budget omissions. BTC/ETH 4H/1H and
519/519 synchronized breadth are source-backed; sectors UNKNOWN. Clock skew
up to 6.589 seconds is explicit; it is not used to assert historical timeliness.
A later invocation after cache expiry was correctly refreshed and partially
failed (15M 519/519; 1H 319/519), not mislabeled an immediate repeat. Final clean
clock-repaired cold/warm evidence is recorded separately.

 Session 5 is a useful
PARTIAL read-only checkpoint, not the complete six-session source/structural exit
gate. Full CORE/ordered method compiler and source-backed admission/specialist
qualification remain Sol work; do not move those blockers to Luna. Session 6
Luna may do bounded operator help/status/report presentation and housekeeping
while preserving the exact capability gates. Keep PR #24 draft and do not merge.

## Final clean-checkout verification

Clean detached checkout `1985543a59aab066120f00b5e26669b07c433579`, initially
unmodified, Python 3.12.3, no manual market input: both actual CLI processes exited
0 with PARTIAL reports. **213 tests / 0 failures / 0 skips** also pass in that
checkout. Blueprint/plan and evidence checksums/config/whitespace pass.

| Final cold source | Eligible | Requested | Evaluated | Returned | Missing | Failed | Unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|
| 15M, each of all 16 columns | 519 | 519 | 519 | 519 | 0 | 0 | 0 |
| 1H, each of all 16 columns | 519 | 519 | 450 | 450 | 69 | 69 | 0 |

All failed partitions/recoveries remain in receipts; this is not a no-setup
result. Quote RVOL has the same evaluable counts and zero unavailable baselines
in this run. Low historical width questions: 82 on 15M, 52 on the accepted 1H
subset. Those counts are not full method detections. All 31 full remote method
predicates remain requested/evaluated/returned 0, missing 0, failed 0 and
unsupported/unqualified 519 on each 1H/15M/4H; selected trial sources are reported
separately. BTC/ETH 4H/1H are source-backed; synchronized breadth is 450/519;
sectors UNKNOWN. Outcome: **44 watches, 4 causal invalidations, 0 handoffs,
0 near misses, 727 budget omissions**. Source/economic/causal qualification limits
explain zero; no claim of no opportunities or predictive accuracy.

Cold: **43 HTTP**, 206,258 request-body bytes, 2,214 URL bytes (headers unmeasured),
4,747,359 response bytes, **116.653 seconds**, p50/p95 **2,031/4,529 ms**;
SQLite **1,982,464 bytes**. Immediate separate process: **4 HTTP**, zero Basis,
zero history, 1,808,957 response bytes, **5.516 seconds**, p50/p95 **1,015/1,789 ms**;
SQLite **2,035,712 bytes**. Same 48 reference IDs, 106 events, 240 hypotheses,
44 watch revisions and original first-seen values; no duplicate watch/event writes.
The repeated snapshot stores a delta and the database retains one current scalar
cache. Partial coverage is retained explicitly during reuse. Charged units,
permitted daily quota and sustainable cadence remain UNKNOWN.

The earlier clock-order failure and import failure have unretained source receipts;
measured totals explicitly exclude their unknown requests/bytes/latencies. A
complete 16-column 519/519 pass on both tf is separately recorded from the repaired
run; it does not overwrite this final clean run's 69 failed 1H names.

**Publication verified after owner sign-in (2026-11-14):** fetched remote feature
head and local HEAD both equal `af3f08a99cf7a65f6e913e8635bff6502749ef78`.
PR #24 remains draft. Both [push CI](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/actions/runs/43540413638)
and [PR CI](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/actions/runs/43540417127)
completed successfully for that commit. The earlier publication interruption is
resolved; no ref was reset/forced and main was not merged. This documentation
follow-up preserves the tested runtime; its final pushed SHA/CI are verified in
the delivery handoff and PR description.

**Owner assistance now: NONE. Release gate remains PARTIAL.** No provider or
exchange key is requested for the supported subset. Full CORE/ordered method/
specialist/admission source gates remain Sol work; Session 6 Luna gets only bounded
operator usability and housekeeping, not those unresolved release blockers.

---

# OpenBot external-first Market Researcher — progress

## Session 4 — context, evidence investigation and research admission (2026-11-13)

**Environment: CODEX_CLOUD. Coherent implemented increment; full source/production
exit gate PARTIAL. Session 4 of the accepted six-session plan.** Verified the
actual remote feature head was exactly
`5c659786b66f36d186e1740417a4703e958b1213` before edits. Clean generated checkout
initially fetched only main; explicitly fetched/tracked the approved integration
branch and fast-forwarded only. No user changes, reset, force operation, main
edit, Local launch or parallel writer. Immutable blueprint/plan preserved.
PR #24 remains draft. Final pushed SHA and observed CI belong in the handoff;
a commit cannot record its own hash.

### Supported implementation and reuse

- Typed source/units/time/fidelity-aware research facts and ContextCard slots for
  BTC/ETH 4H/1H; selected causal benchmark producer; synchronized breadth,
  median/MAD and outperform-BTC fraction with exact evaluable denominators.
  Qualified missing/stale HTF and dated sector mappings remain UNKNOWN. Context
  reorders questions without altering nomination eligibility or side.
- Deterministic necessary-fact/contradiction query planning with allowlisted
  read-only operations, exact scope/windows/units, authorization/history checks,
  separate discovery/targeted/exception/watch budgets, cheaper equivalent
  sources, validated cache, unchanged-WATCH suppression and explicit stop/UNKNOWN/
  NOT_REVIEWED_BUDGET dispositions. No invented agent-tool Python entitlement.
- Typed structure/hypothesis cards reuse the Session 3 frozen references, causal
  F2/F4/F5 events and metadata-ledger contracts. NULL and opposing rivals remain;
  same-reference chronology is enforced. Deduplication preserves all initiators.
  All nine families/31 methods retain honest original states/roles/dependencies.
- Every research stage has declared requirements. Admission needs qualified
  current causal facts, fresh verified identity, significance, first pre-known
  opposing obstacle, actual source-fresh price/spread/depth, fees and declared
  slippage/funding bounds plus relevance within 15h. Unknown room/economics is
  distinct from exhaustion/unfavorable friction. A consumed first obstacle cannot
  be replaced with a farther one. Pairwise/Pareto comparisons and exposure
  diversity preserve incomparable cases and audit records; maximum five handoffs.
- Actual operator interfaces: `review replay-session3` is hash-checked, offline
  AUTHENTIC_REPLAY; `review probe-precursors` makes real bounded Basis calls.
  Existing automatic `scan now`, provider clients, partition normalizer, Decimal
  library, method registry and SQLite metadata ledger remain reused. Added 4H
  clock/selected-public-kline support without increasing sample-symbol/call caps.
  Managed-host inherited transport/trust settings are preserved; no route override.
- Reviewed pinned PR #23 OpenBot v3 structure/research-contract/flow skills and
  current-contract. Added one original compact
  `.agents/skills/market-research-review/SKILL.md`; reused contradiction/causality/
  fidelity concepts, imported no old code or conflicting funnels/recipe/trading
  assumptions. No third-party skill collection/license dependency installed.
  LLM calls zero; optional model integration remains unimplemented.

### Real source evidence and exact qualification limits

- One Cloud Binance access check: **HTTP 451**, 224 bytes, 722 ms. Stopped the
  route; no alternate host, location, VPN, bypass or second Binance request.
- Twelve registered remote precursor expressions executed for BTC × 1H/15M:
  width16; past-only quiet median ratio and percentile; prior bounds; rolling
  distances; efficiency/progress; base RVOL; TR fraction; explicit TR/rma ATR.
  Two more ETH ATR experiments were executed. **98/98 comparisons match** exact
  retained independent Local timestamps across **22 evaluations**; four other
  evaluations (base RVOL and quiet median ratio, both tf) have no adequate retained
  independent inputs. These are live Basis vs authentic historical independent
  facts, never a falsely live Cloud Binance oracle.
- The four new long-warm-up ATR matches are convergence evidence with changed
  starts, **not exact seed repair**. Recomputed all **four original evaluations /
  80 failed scalar pairs** from authentic receipts. First-bar H-L alternative and
  conditional recurrence evidence remains; raw initial seed bars were not
  retained. `ATR_REMOTE_UNQUALIFIED` and full CORE gates remain disabled.
- A bounded additional experiment starts remote history at the first of the 20
  retained independent BTC HLC rows. **Explicit TR/rma passes the exact seed plus
  five recurrences on each timeframe: 12/12**. Native atr(14) fails all 12 and
  matches its first-bar H-L alternative. This supplies a real sampled remote
  remedy; global/all-contract/ETH production qualification remains absent.
  The original four/80 failures are retained, not overwritten.
- New explicit independent cohort screens on each timeframe: quiet percentile
  **50/50 requested/evaluated**, progress16 **50/50**, upper distance **7/7**;
  returned/matched sets equal requests, zero failed/missing/truncated names;
  **13 footer fillers excluded per timeframe**. Distinct scope **107 per tf**;
  each formula covers only its stated partition. Historical source census is
  **946 / 519 eligible / 427 excluded**; current live eligible denominator null.
  Historical not-requested counts by formula: **469 / 469 / 512**. Full CORE and
  production method evaluations **0**. No current all-universe or pressure/
  swing-lifecycle certification follows from scalar outputs.
- Original Unicode market_candles failure on both tf preserved. The one bounded
  supported formula-by-symbol alternative for `我踏马来了USDT` on 1H also returned
  **HTTP 200 / MCP_TOOL_ERROR**. Successful screens do not establish targeted
  history. The coin remains in scope and fault records.
- **24** low-width research questions (4 on 1H, 20 on 15M) preserve both directions
  and NULL; all PREMATURE, formation unsupported, UNKNOWN due to absent qualified
  frozen-reference/current-eligibility facts. They are not READY nominations.
- Three routes are implemented as independent contracts. A currently blocked by
  remote causal predicate/history qualification; B has no qualified runtime
  specialist; C preserves genuine quiet questions and recorded watch/reference
  audits. No denied specialist route was retried; no paid/trial dependency, key
  request, true-profile/footprint/absorption/OI-intent/liquidation claim invented.
- Authentic historical review: **40 references → 37 watches, 3 invalidations,
  zero research handoffs**. Qualified HTF/breadth/sector context UNKNOWN; neutral
  agenda. Planner retains missing necessary facts rather than querying today's
  API as if it supported historical as-of. Empty shortlist is incomplete coverage,
  not a statement that the market offers no opportunities.

### Verification, resources and delivery gates

- **184 tests passed / 0 failed / 0 skipped**, preserving all 135 original tests
  and adding 49 source/contract/causal/fairness/planner/admission tests. Real 98
  matches and four/80 ATR failures are regressions; synthetic READY/FAST cases
  validate safety contracts without promoting live capabilities. Tests include
  bullish BTC/bearish alt, falling BTC/bullish alt, mixed/unknown context, shock
  retaining a range question, equal budgets, specialist-only/quiet routes, source
  mismatch, stale clocks/quotes, cache/quota, room/exhaustion, citations, 0–5 and
  no executable trade output. No existing tests weakened or skipped.
- **53 actual HTTP requests** (52 Basis, one Binance), **373,822 response bytes**,
  **52,346 ms summed durations**, p50/p95 **774/3,260 ms**; one HTTP 451 and one
  HTTP-200 tool error. Actual charged quota and sustainable cadence unknown;
  separate probe wall time was not instrumented. No fabricated throughput claim.
- Configuration/immutable reference validation and whitespace checks pass;
  standard library only, no credentials, orders/accounts, Freqtrade/trading DB
  mutation, full candle store, runtime SQLite artifact, scheduler or LLM calls.
  Curated evidence and hashes: [Session 4](../../evidence/external-first/session4/README.md).
  Commands, stages and source limits: [runbook](SESSION_04_RUNBOOK.md).
- P0/P1/P3 and G1/G2/G8 remain **PARTIAL**, with host access, exact ATR seed,
  full remote causal CORE/history, true specialists/current coverage/quota gates
  explicit. G3/G4/G5/G7 have deterministic and stated source-scope verification.
  G6 durability is Session 5. G9 delivery additionally requires remote SHA and
  both push/PR CI observation, recorded in the final handoff.

**Owner help: NONE for the implementation.** Live qualification requires a
separately authorized, independently lawful runtime for a bounded same-start/
same-cutoff BTC/ETH × 1H/15M oracle, retaining the first 15 selected seed bars and
final comparisons, plus two selected 4H benchmark samples. Maximum 300 bars,
within the existing five-symbol/ten-kline-call cap; exact GitHub-synced handoff
in the runbook. No Local execution or location change was initiated here.

**Session 5 readiness: PARTIAL.** Proceed with dependency-ready read-only
orchestration, watch persistence/resumption/gap recovery and end-to-end failure
handling using these capability gates. Production source qualification remains
blocked until real evidence clears it; no diagnosis-only extra session and no
premature Session 6 merge.

---

## Session 3 — Local live APIs and causal intelligence (2026-11-13)

**Environment: CODEX_LOCAL_EXCEPTION. Delivered functional increment; full remote
CORE/production structural qualification and Session 4 readiness remain PARTIAL.**
The owner explicitly authorized Local execution and Session 3 implementation.
Started from the latest verified remote
`35f459e42b17a05ec041db71614f82624acf3eb8`, still the last reported successful
commit. Fresh checkout was clean; fetched all remote branches and confirmed
fast-forward. No existing user changes were overwritten, reset or force-pulled.
One writer / same integration branch / PR #24 remains draft. Immutable blueprint
and plan hashes remain unchanged. The exact final SHA/CI are in the delivery
handoff; no commit can contain its own hash.

### Implemented and independently source-verified

- Official normal-host Binance public access succeeded directly with HTTP 200;
  no proxy/VPN, alternate market-data host, geographic switching, API credential,
  paid service, order/account mutation, scheduler or trading DB access.
- `python3 -m researcher scan now` automatically fetches current exchangeInfo,
  market-wide 24h ticker, bookTicker and premiumIndex, using the existing
  inventory/market/runtime contracts. `scan live` is an alias. Manual JSON is no
  longer required for ordinary runs; the explicitly supplied owner-snapshot
  compatibility path remains available. `scan qualify` is a separately bounded
  explicit probe, not implicit production promotion.
- Verified universe: **946 inventory rows, 519 eligible COIN USDT perpetuals,
  427 exclusions, zero provisional rows**. Fixed exact native Unicode symbols,
  official INDEX/PREMARKET class exclusion and ticker minute-boundary window
  handling. Preserve full exchange filters/listing metadata, exact status,
  settlement/tick/quantity rules and optional facts; never infer multipliers.
- Two genuine disjoint lower/medium 50-symbol partitions plus a seven-name
  footer: **107/107 requested/returned/scalar-evaluated on each timeframe**, no
  missing/failed IDs or truncation. **13 fillers excluded per footer**. Full
  exchange denominator stays 519; 107 observations do not certify full-market
  structure or complete per-row remote history.
- Five selected symbols × 1H/15M, 300 closed official klines each; 10 small
  samples, no market-wide candle store. **46 remote formula evaluations / 920
  numeric comparisons; 42 evaluations / 840 values match** independent Binance
  references. Close/high/low, base volume, width, previous extrema, lag, median,
  odd q=.5 and BTC taker-buy/delta evidence improve on the unchanged prior
  **167 same-Basis-input arithmetic comparisons**.
- Request/time/byte/query/source hashes, original source time, actual bar-open
  and inclusive/exclusive close semantics, native base/USDT units, missingness,
  quota headers, 25-second timeouts, response/request/sample budgets and short
  memory caching are explicit. Source/API data never becomes operational config.

### Implemented but awaiting remote/provider qualification

- Shared Decimal verification library: TR/Wilder ATR with explicit seed,
  normalized width, excluded-current-window historical percentile, efficiency,
  overlap/displacement, confirmed swings/ladder, frozen level/first obstacle
  distance, independent touches, quote RVOL, bar aggressor delta, whole-bar Q/V
  and anchored CVD, aligned relative return and lag-trained beta/residual.
- Frozen references and trial chronological **F2/F4/F5** rivals; same-reference
  pressure/excursion/reclaim/opposing attempt/rebreak/two-later-hold semantics.
  **F5 never comes from no-reclaim F2**. NULL and rival explanations remain.
- Confirmed swing BOS / CHoCH candidates and FVG birth/mitigation/accepted
  failure/iFVG opposite-side retest and later invalidation. No institutional,
  stop-execution, tick-path, predictive or readiness claim is inferred.
- Compact immutable SQLite metadata/event ledger; stable origin IDs, first
  recorded availability/scale reuse, chronological/identity enforcement,
  lifecycle and hypothesis snapshots, atomic rollback and idempotent reopening.
  Final persistent replay of captured actual selected metadata: **40 references,
  59 events, 200 hypothesis snapshots, 425,984 bytes**. The capture originally
  used memory; final persistence replay is labeled retrospective and distinguishes
  the fixed stable-ID scheme. No candle table or runtime DB is committed.
- All **F1–F9 and 31 exact blueprint methodologies** remain in one registry,
  each with role, necessary evidence, calculation dependencies, sequence,
  interpretation, traps/rivals, invalidation, provider/fidelity and honest state.
  F1/F3/F6 are **partial formation/primitives**; F7/F8 **primitives only**;
  F9 **not implemented**. All production detector/CORE flags remain false.

### Actual failures, partial coverage and unsupported methods

- **Four ATR evaluations / 80 values fail blueprint seed equivalence.** Basis
  matches a first-bar H−L seed; all four alternative-seed and conditional Wilder
  recurrence checks pass. This remains a production gate, not a rounded-away
  discrepancy. The passing test suite asserts these actual live failures.
- `我踏马来了USDT` screen rows succeeded, but targeted Basis `market_candles`
  failed with HTTP 200 tool errors on both timeframes. Independent Binance
  samples succeeded. Exact provider support is operation-specific.
- Qualification current pulse: ticker/premium 519, valid book 516 (three rejected
  rows). Final normal pulse: ticker 518 (YGGUSDT rejected), book/premium 519.
  Rejected rows remain visible; no failed row becomes no-opportunity evidence.
- No eligible contract younger than 30 days existed (youngest onboard date
  CTUSDT, 2026-10-01). No explicit multiplier metadata was returned. Those
  real-world qualification classes remain unexercised/unsupported.
- Full remote CORE, remote causal method packs, all-symbol production history,
  quota sustainability and arbitrary historical provider replay remain
  unqualified. **No full-market structural-success claim is made.**
- True profile/nodes/footprint/absorption/exhaustion/OI/observed forced orders/news
  remain **blocked by source requirements**. Keepssy stays **DEFINITION_PENDING**;
  Silver Bullet lacks a qualified primary-source window. Full OB/breaker/EQH,
  CRT/AMD/OTE and statistical-reversion detectors are **not implemented**.
- Context interpretation/specialist query planning, room/ranking/shortlist,
  watch recovery and complete Deep Analyst handoff stay in later packages.
  BTC/ETH remains non-veto guidance and cannot suppress contrary nominations.

### Measurements and verification

- Qualification: **79 HTTP requests / 2,449,132 response bytes / 96,725 ms summed
  request time / 188,303 ms wall**, p50/p95 **929/3,413 ms**; 14 Binance / 65 Basis
  calls, six screens, zero HTTP failures, two HTTP-200 tool errors, no recovery.
- Final normal automatic run: **9 requests / 1,898,702 bytes / 15,801 ms summed /
  16,053 ms wall**, p50/p95 **1,574/3,525 ms**, zero HTTP/tool errors, one rejected
  ticker row. Earlier diagnostics used 14 more requests; **102 explicitly issued
  provider requests total**. Early unavailable byte/latency observations stay
  NULL in the diagnostic accounting. No unknown quota is estimated.
- Actual Binance used-weight headers are retained; Basis charged units absent,
  cache hits zero. Continuous/hourly/15M sustainable cadence remains unqualified.
- **135 offline tests passed / 0 failed / 0 skipped**, including the original 80
  and 55 new numeric/causal/API/integration/recorded-source tests. Append-future,
  shifted time, pivot timing, missing bars, volume units, warm-up, independent
  touches, F2/F4/F5 distinctions, FVG/iFVG, F1 false-pullback, shock-without-base,
  BOS/CHoCH, metadata persistence and contradiction/non-veto cases pass.
- Config validation passes with 9 families / 31 methods / zero production
  detectors or full CORE packs enabled. Diff whitespace, immutable reference
  hashes and outgoing credential/database/personal-data checks pass. No added
  package dependencies. Evidence/hashes: [Session 3](../../evidence/external-first/session3/README.md).

**Owner assistance required: none for the delivered increment.** Provider limits
are documented; no paid service, credentials or manual snapshots are requested.
**Session 4 readiness: PARTIAL.** Proceed with interpretation/query planning only
within the verified source scope, while resolving remote ATR/CORE semantics and
operation-specific coverage gates. The next Cloud session must fetch the exact
pushed Local commit and recheck its own lawful access; Local 200 does not clear
Cloud's historical 451. Keep PR #24 in draft.

---

## Session 2 — external discovery implementation (2026-11-13)

**State: working R0 partial-coverage implementation; full-market source
qualification remains incomplete. Session 3 readiness: PARTIAL; not started.**
The owner explicitly instructed Session 2 to proceed while resolving or carrying
Session 1 dependencies. That instruction supersedes the historical NO-GO/stop
wording below and the former AGENTS gate; the immutable blueprint/plan bytes
remain unchanged. Provider production gates were not waived.

### Repository and delivery scope

- Repository `KasunKarandagolla/OpenBot-Trading-Lab`; approved branch
  `feature/external-first-market-researcher`.
- Latest remote verified before edits: expected
  `1c47940657339aa7fa058966ccca9528f3609a1c`. Checkout clean; the prepared
  container initially held documentation-only `work` at `2343053`, so the
  explicitly fetched feature head was checked out safely. No reset, overwrite,
  automatic merge, force push, main edit, Local switch or parallel writer.
- Reused the existing standard-library Basis runtime MCP client, transport,
  immutable contracts, manifest, clock validator and 167-comparison arithmetic
  oracle. No alternate client, dependencies, candle store, trading service,
  ledger database, LLM call or scheduler.
- PR [#24](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/pull/24)
  remains draft. Final pushed SHA and observed CI are supplied in the exact
  session handoff; a commit cannot include its own hash.

### Implemented

- Typed official/live, owner-official snapshot and future reviewed inventory
  source interface; strict provenance/hash/schema/UTC/TTL validation. Exact
  native identity, contract type, quote/settle, trading status, tick/quantity,
  classification, source/capture, listing and explicit multiplier facts retained.
  Missing fields stay unsupported; no multiplier-prefix inference. Source
  completeness and eligibility completeness are distinct. Stale or unresolved
  rows preserve `PARTIAL_INVENTORY`; eligible denominator stays null when unknown.
- Fixed read-only aggregate ticker/book/premium adapters and current timestamp,
  spread, rolling-window and unit contracts; disabled on this recorded-denied
  Cloud route. Current observations do not certify historical structure.
- One capability registry and finite remote compiler; explicit maximum-50
  partitions, smaller footer support, serial bounded pacing and HTTP/screen/
  recovery/byte budgets. Separate `CORE_1H` / `CORE_15M` contracts expose every
  required unavailable output and isolate the registered width3 observation.
  Full CORE, optional/sparse formulas and all strategy detectors remain disabled.
- Strict response scope/formula/count/numeric/clock normalization, filler
  exclusion, missing/failed identities, hidden truncation detection, bounded
  bisection and HTTP 200 tool-error isolation. Denials/quota end the route;
  each original/recovery attempt stays visible. Effective recovery leaves avoid
  double-counting. Invalid temporal joins and stale/after-cutoff values fail.
- Per-calculation/timeframe coverage and provenance: planned/not-requested,
  requested/recognized/evaluated/returned/matched/missing/failed, fillers,
  truncation, cutoffs, source/schema/formula hashes, version, fidelity, history
  uncertainty, quota and measured resource use. Raw scalar execution never
  becomes qualified CORE or zero-opportunity evidence.
- Independent nomination contracts for boundary/pressure, compression,
  trend/pullback, breakout/sweep, relative anomalies, shock, previous watch,
  quiet tail, new listings, specialists and value. Exact source evidence IDs,
  fidelity, frozen reference times, stages and rivals validated; BTC/ETH context
  cannot veto routing. All F1-F9 and 31 methodologies remain represented.
  No actual strategy predicate or readiness promotion was invented.
- Independent lower/medium/young/multiplier cohort planner, gated on fresh
  verified inventory and complete independent turnover data. Its synthetic
  50+7 tests are not an authentic tail qualification.
- `python -m researcher scan now` end-to-end read-only partial observation;
  optional owner inventory/provenance arguments. Existing smoke/probes retained.
  [Session 2 runbook](SESSION_02_RUNBOOK.md) documents usage and source contracts.

### Actual source qualification and live denominators

Final run began `2026-11-13T06:57:27.785971+00:00` (machine UTC).
[Curated source evidence](../../evidence/external-first/session2/README.md).

| Capability | Actual result / state |
|---|---|
| Binance official inventory / current pulse | Existing HTTP 451 honored; zero new Binance requests. No authorized snapshot supplied; no qualified alternate inventory. `PARTIAL_INVENTORY`, eligible denominator null; 5 provisional names only. |
| Finite width3 on 1H | Requested 5 / recognized 5 / scalar-evaluated 5 / returned 5 / matched 5 / missing 0 / failed 0; 15 fillers excluded; no truncation; closed output end 06:00 UTC. |
| Finite width3 on 15M | Requested 5 / recognized 5 / scalar-evaluated 5 / returned 5 / matched 5 / missing 0 / failed 0; 15 fillers excluded; no truncation; closed output end 06:45 UTC. |
| Genuine independent quiet tail | Zero partitions sent; inventory plus independent liquidity cohort unavailable. Young/multiplier eligibility remains unverified; exact 1000PEPE spelling is not multiplier proof. |
| Independent numerical source | Unverified; no lawful timestamp-aligned independent sample available. Existing 167/167 same-source arithmetic passes; no ATR seed, source authenticity, exact volume-unit or historical event claims promoted. |
| Full CORE / F1-F9 / 31 methods / true specialists | Zero qualified evaluations; all unavailable outputs explicitly retained. No shortlist, room, causal structure or specialist signal generated. |
| Free access / cadence | Credential-free public Basis calls succeeded. Actual charged units absent; fixed small run budgets applied. Sustainable cadence and production broad scope remain unqualified; scheduling disabled. |

The exact cohort is BTCUSDT, ETHUSDT, SOLUSDT, FILUSDT, 1000PEPEUSDT. It comes
from prior targeted provider observations, not authoritative eligibility or an
independent tail source. `complete=false` records absent per-row input-history
attestation. Four-decimal screen readings cannot establish tick-exact levels.

Final demonstration: **5 HTTP requests / 2 screens / 90,208 response bytes**,
6,212 ms summed request durations, **6,239 ms wall**, p50 713 ms / nearest-rank
p95 2,272 ms; **0 HTTP/tool failures**, 0 retries. These include MCP startup.
All three bounded implementation demonstrations combined: **15 HTTP requests / 6
screens / 270,621 bytes / 17,505 ms summed durations**. No endurance, cache or
throughput guarantee inferred. No credentials/session headers committed.

### Verification, limits and owner assistance

- `python -m unittest discover -s tests -v`: **80 passed / 0 failed / 0 skipped**.
- `python -m researcher config validate`: **VALID**, 9 families / 31 methods,
  zero strategy/full-CORE packs enabled, frozen reference hashes unchanged.
- `python -m researcher provider status`: recorded source capabilities, public
  keyless observations only; no optional key used.
- `git diff --check`: passed. Source/evidence hashes are recorded in
  `evidence/external-first/session2/SHA256SUMS.json`. CI must be observed after
  pushing; local test success is not a claim of remote CI success.
- Unimplemented/degraded: complete inventory and cheap current pulse, genuine
  broad-tail and young/multiplier qualification, full CORE calculations,
  independent source accuracy/ATR seed/volume definitions, sustainable quota,
  causal F1-F9 detector/event ledger, real specialist feeds, watch persistence,
  context interpretation, remaining room and Deep Analysis shortlisting.
  The latter responsibilities remain in their planned later sessions.
- **OWNER ASSISTANCE REQUIRED:** provide a fresh full lawful official Binance
  USD-M `exchangeInfo` JSON file plus capture UTC, exact raw-file SHA-256, source
  URL, completeness attestation and authorization/source statement in the
  [runbook's provenance format](SESSION_02_RUNBOOK.md). For genuine tail tests,
  also provide a contemporaneous official `/fapi/v1/ticker/24hr` snapshot with
  the same provenance facts. For independent numerics, provide a licensed tiny
  source-aligned sample (about 65 closed bars per 1H/15M for at most five
  representative symbols, with venue, time/unit definitions, capture/hash and
  retention rights). No secret value, new API key or Local geographic workaround
  is requested. The prior CoinGecko review shows its key alone does not solve
  this gap; no speculative new provider search was repeated.
- **Session 3 readiness: PARTIAL.** Reusable contracts, partitions, coverage and
  on-demand partial observation are ready. Full production universe/core
  qualification remains blocked on the stated source evidence. Next authorized
  work should import/validate that evidence, run real tail/independent checks
  under bounded budgets and preserve these capability gates while implementing
  later causal intelligence only when separately requested. Session 3 was not
  started during this session.

---

# OpenBot external-first Market Researcher — Session 1

## Session 1.5 — External provider qualification repair (2026-11-13)

**State:** bounded investigation complete; provider qualification remains
**PARTIAL / BLOCKED** and **Session 2 remains NO-GO**. The latest remote branch
was fetched before work and matched starting SHA
`aba986518fda656a5ae3c3d5f78cced594dc4b96`; the checkout was clean. No reset,
rebase, alternate network location, Local Codex, paid service, trading route,
or Session 2 implementation was used. No external market-data or trading
credential was used.

### Qualification repair findings

- **Official eligible Binance inventory remains BLOCKED.** The recorded
  `fapi.binance.com/fapi/v1/exchangeInfo` HTTP 451 was not retried or bypassed.
  Binance's official Public Data repository documents USD-M klines in daily or
  monthly archives. Its current-symbol helper directly calls the same blocked
  futures `exchangeInfo` URL and reduces the response to symbol strings; it is
  not a separate metadata source or a route around the 451. A single HEAD for
  the documented BTCUSDT 1H daily archive for 2026-11-12 returned HTTP 404 from
  CloudFront at 2026-11-13 06:03:50 UTC. No file was downloaded and the reason
  for the missing file is not established. The archive's terms specify
  noncommercial CC BY-NC-SA 4.0 use; no dataset or derived fixture was retained.
- **CoinGecko is only a documented candidate.** Its derivatives ticker endpoint
  offers exchange/contract labels and live ticker fields, but the free Demo API
  requires an owner-created key. The documented response does not supply the
  complete authoritative exchange status, settlement, listing-age, tick-size,
  lot-size, or multiplier facts needed here. No key was present and no request
  was sent; it cannot clear the inventory gate by itself.
- **Genuine Basis quiet-tail support remains BLOCKED.** The prior live footer
  probe evaluated the two requested popular symbols and exposed 18 provider
  fillers. No independently selected eligible 50-member quiet-tail cohort was
  available, so zero tail partitions were submitted. The prior live evidence
  demonstrates narrow remote formula execution and explicit-symbol input, not
  coverage of the lower-ranked, young, or multiplier contract tail.
- **Independent numerical verification remains PARTIAL.** Session 1's
  167/167 comparisons are same-Basis-input arithmetic only. The independent
  Binance archive file probe returned 404, so no source-aligned formula
  comparison was possible in this repair. No external-source accuracy,
  volume-unit, ATR-seed, or cross-source timestamp claim is added.
- **Free-service suitability remains PARTIAL.** Session 1's credential-free
  Basis observations and terms remain the bounded evidence: 33 HTTP requests,
  251,961 response bytes, p50 696 ms / p95 1,671 ms, no observed 429, no
  returned charged units, and no measured sustainable cadence. Its documented
  1,000 keyless daily calls and 10,000 free-key daily calls do not establish a
  per-minute limit or production automation suitability.

The exact source checks, limits, and owner dependency are recorded in
[`Session 1.5 evidence`](../../evidence/external-first/session1_5/README.md).
There was no provider code defect justified by the evidence; existing
capability gates and disabled methods were preserved. No historical market
data, credentials, caches, or generated runtime output were added.

### Session 1.5 verification and handoff

- `python -m unittest discover -s tests -v`: **43 passed, 0 failed, 0 skipped**.
- `python -m researcher config validate`: **VALID**, 9 families / 31 methods,
  0 detectors enabled.
- `python -m researcher provider status`: Basis remains
  `LIVE_TESTED_NARROW`; formula/screener production enablement remains false;
  Binance remains blocked at HTTP 451.
- **Owner assistance needed to clear the inventory and tail gates:** provide a
  current, provenance-bound Binance USD-M USDT-perpetual inventory captured
  through a lawful authorized source, including native symbol, contract type,
  quote/settlement, status, listing time where available, price/quantity rules,
  and multiplier metadata. A plain symbol list or CoinGecko key alone is not
  sufficient. No credential is requested for this checkpoint. Do not use Local
  Codex to change location or work around the 451.
- **Session 2: NO-GO** until exact inventory, real independent quiet-tail
  partitions, and a source-aligned numerical oracle pass the blueprint gates.
  Next task is to obtain that authorized inventory and a bounded independent
  Binance-futures historical sample; then resume the 50-member Basis tail
  qualification. PR #24 must remain draft.

**Environment:** CODEX_CLOUD. **State:** Session 1 scaffold and bounded proof sprint
implemented; provider qualification **PARTIAL / BLOCKED**. **Session 2: NO-GO**
until the narrower qualification repairs below pass. No Local exception used.

## Verified branch and source authority

- Repository: `KasunKarandagolla/OpenBot-Trading-Lab`.
- Single integration branch: `feature/external-first-market-researcher`, draft
  [PR #24](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/pull/24) to main.
- Starting fetched remote SHA: `694dfdfa9d7700d7ced0a79f4502423b38ff9681`.
- Default main: `2343053ce68f6fff4525c5b67771ea445deb3779`; unchanged.
- Latest relevant unmerged implementation: PR #23 at
  `2f9ebc7b86a99c4519278ced2287a449ed4b2822`; not silently imported. All 24 PRs
  inspected were open/unmerged. [Repo truth/reuse inventory](REPO_TRUTH.md).
- Initial checkout clean. Switched to the supplied branch; fast-forward only.
  No reset/rebase/force push/main mutation. No existing AGENTS instructions were
  overwritten. Branch protection is not configured upstream; no rules bypassed.

All three authoritative files were read completely before implementation. Their
original bytes are preserved; the runtime validates the first two hashes.

| Reference | Git blob | SHA-256 |
|---|---|---|
| [Blueprint](OpenBot_Final_External_First_Market_Discovery_Blueprint.md) | `5a73d9fcbed66b29e3c0151b99b5b0d5e8966fdd` | `cf7a58fd9ed5f5d1010673406c26a405c8112b907216a47f88a9ebee1bd3d45c` |
| [Implementation plan](OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md) | `fdccc3890bb9842653495d98dd81adc55df1802b` | `245591eea0f92cd185c51db3420043031c11c1d941f91ecdb31fd64a34e0c232` |
| [Session 1 prompt](CODEX_SESSION_01_PROMPT.md) | Recorded in starting commit | `4043051af7c1cec13314a08cf6e798cd269360158b5f4f366069eece2b09421b` |

## Implemented increment

- Standard-library Python 3.11+ `researcher` package, frozen typed instrument,
  capability, evidence and batch contracts; typed minimal report skeleton.
- Strict Decimal parsing, bar-open/end/known-by/received chronology, exact native
  symbol preservation, missing-value reasons, fidelity/scope and resource fields.
  Earliest provider availability remains null when unknown.
- Real runtime Streamable HTTP MCP initialize/notification/tools-list/call,
  JSON/SSE parsing, session reuse without logged session IDs. Five read tools
  allowlisted; chart/alert/publishing/trading/admin tools rejected. Unqualified
  screens/formulas require an explicit probe and registered expressions.
- One versioned `researcher/config/discovery_specs.json`: **F1–F9 and all 31
  blueprint method rows**, SMC/ICT grouping, roles, observable definitions,
  caveats and honest status. All detectors/packs/formulas disabled; Keepssy is
  DEFINITION_PENDING. No fake detector, compiler, ranking or scheduler added.
- `config validate`, recorded `provider status`, safe `scan smoke`; four optional
  small probe profiles. New report files only in ignored work/, no overwrite or
  traversal/symlink output. Keys are unnecessary and never loaded/sent.
- Concise AGENTS guidance, runbook, source/reuse inventory, bounded fixtures,
  evidence receipts/hashes and an offline CI workflow. Existing paper controls,
  frozen strategies, configs and trading databases were not changed or opened.

The normal smoke makes one targeted provider call after the MCP handshake and
returns no shortlist. No core or specialist evaluation is certified. No native
Deep Analyst service, original agent installation/injection or deployed Freqtrade
integration was verified or activated. Source ideas were reused; no conflicting
historical engine or skill funnel was copied into the feature branch.

## Actual provider qualification

Machine times below are UTC, 13 November 2026. Requests are credential-free.
Full requests/bytes/timing/hash receipts are in the [evidence index](../../evidence/external-first/session1/README.md).

| Operation | Actual scope and result | Capability status |
|---|---|---|
| Binance official exchangeInfo | `https://fapi.binance.com/fapi/v1/exchangeInfo`: **HTTP 451**, 224 bytes. Route stopped; no alternate hostname/location or signed route attempted. Current inventory, listing age, crypto classification, multiplier and tick/lot metadata unverified. | BLOCKED |
| Basis initialization / tools/list | Runtime MCP protocol `2025-03-26`, server `basis` 1.0.0, 43 tools observed; read schemas, variables, formula signatures and orderflow schema inspected. | LIVE_TESTED_NARROW |
| Basis market_candles + width | BTCUSDT, ETHUSDT, SOLUSDT, FILUSDT, 1000PEPEUSDT × 15M/1H: 10 requested symbol/timeframe operations, 10 returned; corresponding 10 remote width calculations executed. Every exact exchange eligibility/multiplier remains UNVERIFIED. | LIVE_TESTED_NARROW; TARGETED_ONLY |
| Finite explicit footer | BTCUSDT + ETHUSDT, 1H, 300-bar load, minimum vendor universe=20: 2 requested / 2 scalar-evaluated / 2 requested returned / 0 missing-failed, **18 fillers excluded**; provider total 20 evaluated. First/repeat executed. Not a tail cohort. | LIVE_TESTED_NARROW, broad capability UNVERIFIED |
| Sparse-column poison | Add `quantile(close[1],1000,0.2)` under `logic:any`: HTTP 200 + `isError=true`, all 20 vendor instruments unevaluable. Requested 2: zero valid / 2 faulted, no negative-setup conclusion. Separate finite recovery succeeds. | LIVE_TESTED_NARROW failure isolation |
| BTC sampled formulas | 65 requested bars, 64 reported closed, 20-point reduced tails; lag, prior extrema, width, median, q=.5 quantile, ATR recurrence, comparison, bar-delta identity and no-event behavior checked. No native pivot entries from current catalogue query; arbitrary historical as_of not exposed/proven. | PARTIAL semantics, not discovery-qualified |
| Genuine independent quiet tail | **0 partitions sent**: current eligible inventory/rank/age source blocked. No actual eligible 50-member cohort can honestly be selected here; no provider top board substituted. Young-contract coverage unknown. | BLOCKED_CURRENT_INVENTORY |
| True VP / footprint / derivatives | Schemas/docs only; no actual flow/history/units/source reconciliation. No optional adapter/key purchased or enabled. | UNVERIFIED |

Normal observation cutoff: 1H bar open **04:00**, source window end **05:00**;
last final smoke received **05:40:40.123268**. LoadedAt is a conservative known-by
time, not claimed earliest publication. Sample 15M/1H clocks are separately
retained. Source contract is provider-reported Binance futures; official
quote/settle/type/multiplier verification is not inferred from its symbol.

Price unit is reported USDT per native contract price unit. Base/quote/taker
volume units are **not independently reconciled**. Bar delta is not footprint;
OHLC value is not true profile; OI does not identify new longs; raw return is not
beta residual. Four-decimal screener rounding cannot support tick-exact levels.
Formula response informational links incorrectly said spot while data objects
said futures; links are ignored, discrepancy retained.

## Numerics, rights, quotas and performance

- **167/167 arithmetic comparisons pass**, over the same provider's bounded BTC
  tails. Width max absolute error `1.6152573441763e-16`; prior extrema, lag,
  3-value median/q=.5 comparisons exact at reported precision. ATR recurrence
  error ≤`6.357142857143e-13`; initial seed not independently tested. Delta
  identity residual ≤`1.8189894035458565e-12` in source base-volume scale.
- This is **independent arithmetic, not independent source data**. Exchange
  authenticity, young/quiet/multiplier oracle cohorts, full ATR seed/warm-up,
  quantile interpolation/ties/general baseline, chronological multi-event
  value_when/pivots and arbitrary historical replay remain unqualified.
- No-event functions returned `defined=0`, omitted tails; never coerced to 0.
  No fake F2/F4/F5 historical sequence or family accuracy claimed.
- Basis MCP page and terms accessed successfully; terms permit lawful research
  and prohibit bypass/abusive automation. Public documentation: 1,000 keyless
  calls/day, optional free key 10,000/day, unknown exact per-minute limit.
  Actual charged quota units absent. No key or paid entitlement used.
- Instrumented final runtime samples + footer + smoke: **33 HTTP requests,
  251,961 response bytes, sum of request durations 25,104 ms**, request p50
  696 ms / nearest-rank p95 1,671 ms. These include three handshakes, are a small
  measured subset of session traffic, and prove no SLA or sustainable cadence.
  Original finite first/repeat: 2,561/1,858 ms; actual server cache temperature
  unknown. No live 429 observed; backoff/denial tested offline.
- All source/fixture hashes are in `evidence/external-first/session1/SHA256SUMS.json`.
  Small public schema/market-fact extracts only; no bulk history, session headers,
  credentials, operational DBs or user data committed.

## Verification and stop/go

Executed from this Cloud checkout:

```bash
python -m unittest discover -s tests -v
python -m researcher config validate
python -m researcher provider status
python -m researcher.qualify samples --output work/runtime-samples-001
python -m researcher.qualify footer --output work/runtime-footer-001
python -m researcher scan smoke --output work/runtime-smoke-release.json
```

Offline suite: **43 passed / 0 failed / 0 skipped**. Includes actual-provider
shape/error fixtures, 167 arithmetic comparisons, wrong contract/venue, clocks,
future bars, missing/truncated/duplicate rows, tool-level errors, denied routes,
quota budget/Retry-After, read-only allowlist, secret/session redaction, output
boundary and complete registry preservation. No inherited implementation suite
exists on the approved documentation base; unmerged native engine tests were
not falsely claimed executed. Live probes are excluded from CI.

Repaired during the session: initial local tracking/refspec setup; initial probe
scratch-directory creation; output traversal caught by tests; a synthetic 15M
test's inconsistent receive/load clock. Final recorded test output is clean.
No unhandled failure is presented as a passed acceptance check.

Session 1's documented-failure path is satisfied: working pushed scaffold,
successful permitted remote observations, precise blocked gates and reproducible
qualification follow-up. G1/G2 production feasibility and all later detector,
nomination/context fairness, watch-resumption and deployment gates are **not**
passed. The fixed advisory/non-veto policy is preserved; real family nomination
invariance tests await actual detectors. No Session 2 implementation began.

Git publication: final pushed SHA and observed CI/check-run status are provided
in the session's exact GitHub handoff; a commit cannot contain its own hash.
CI was not claimed passed before its run was observed. Keep PR #24 draft; no merge.

## Next dependency-ready task — narrower qualification repair

1. Obtain a **lawful, current, provenance-bound official eligible inventory and
   ticker snapshot** with classification, age, status, settlement, tick/lot and
   exact multiplier metadata where supplied. Do not evade the Cloud 451 or use
   Local merely to change IP/location. No user credentials are currently needed.
2. Independently select and freeze actual quiet-tail/medium/young/multiplier
   strata; run an explicit 50-name screen and a smaller footer, audit recognized,
   returned, evaluated, filler, missing and faulted IDs. Production qualification
   requires the blueprint's second independent tail partition too.
3. Reconcile a tiny timestamp-aligned BTC/ETH/several-alt oracle from an
   independently permitted source, including volume units, closed 15M/1H,
   ATR seed/warm-up, no-event and sparse-column semantics. Keep methods disabled
   when proof is absent. Qualify quotas/cadence before any scheduling.
4. Only then decide whether Session 2's full-universe external adapter work is
   dependency-ready. If a specific Cloud-only operation is demonstrably blocked
   while a compliant Local operation exists, hand off **only that operation**
   from the exact verified remote SHA. No parallel implementation track.
