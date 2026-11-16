# Market Researcher workflow recovery — 16 November 2026

Engineering recovery of `feature/external-first-market-researcher` from remote
`95d509617f52e6fe8911930b8360faf1d5230c5d`. PR #24 remains draft. Main remains
`2343053ce68f6fff4525c5b67771ea445deb3779`. This report supersedes the earlier
recovery's engineering conclusions where the implementation changed.

**Live OpenBot acceptance: NOT_RUN_IN_CODEX_CLOUD.** All new provider replies
and market responses used in tests are fixtures. No genuine new model or market
request was made here. Passing tests do not establish live operational success.
The exact publication SHA, CI and verdict are recorded in the delivery receipt;
this document cannot contain its own commit SHA.

## Evidence and causal limits

The owner's supplied account of job
`20261116T025218Z-1a702b306b3b45f58540e422893543e3` is the evidence for the latest
live failure: 519 eligible contracts, 101 public requests, about 6.29 MB, 24 active
watch coins, 11 unranked alternatives, zero strict/conditional candidates at
export, 33 prepared cards on 22 symbols, 12 planned batches, a three-card first
batch, REVIEW_READY, a reserved dispatch ticket, and eventual
NATIVE_SESSION_MISMATCH during RECEIPT_COLLECTION after about 446 seconds.
Zero validated cards and zero verified model attempts were reported. These are
**owner-supplied observations**, not a ZIP independently inspected this session.

The ZIP identified by the owner as SHA-256
`0721464f2085b14f953c617c9ff56f5f785d78a9d9d574f87901dc2acdfac3db`
was not supplied. No checksum verification or exact offending live row is claimed.
A ticket does not prove task creation, provider execution or a model response.
The precise cause of that particular live exception therefore remains unconfirmed.

The repository contains verified defects compatible with the symptom. Controlled
counterexamples and full scanner fixtures establish those defects independently.
They do not retroactively establish what happened in the missing native records.

Cloud has the repository and GitHub connection, but no installed OpenBot native
storage, approved path-only audit configuration, or OpenBot start_task tool.
The actual Cloud preflight returns `NATIVE_AUDIT_CONFIG_MISSING`. That is the exact
external dependency preventing a genuine OpenBot run here. No agent, provider,
account, model, permission, Local Scripts setting or trading credential was
created or changed to bypass it. The recorded Cloud Binance denial was not retried.

## Verified root causes and coherent repairs

| Defect | Evidence in starting implementation | Repair and boundary |
|---|---|---|
| Temporary active pointers treated as immutable identity | `native_identity.assert_current` compares captured turn/session hashes to a newly queried active turn; `native_runtime.collect` calls it twice. A stored authentic-shaped parent becomes uncollectable after a legitimate active-pointer transition. | `assert_parent` resolves the original agent/thread/turn/provider-session relation independently of active pointers. Configured agent/model/backend/workspace, exact hashes and captured parent start time remain checked. `assert_current` remains strict for initial owner/command authorization. |
| Identity recaptured at each batch/import | `agent_review.exchange` calls active_identity even for a cached request; `review_batches` independently captures identity before separate exchange captures. | The runner's original parent binding is passed through scanner, planner, every batch and cached import. Cached reads use the request's immutable identity and revalidate it against storage. |
| Unrelated later parent contexts contaminate old proof | Handoff and launch readers inspect every context in a reused session time window and compare each to the original turn. | Provider records are selected by their turn context/task boundary. A later different turn is outside the proof; a different model or workspace in the selected turn still fails. Envelope/schema/order validation remains strict. |
| Child app rows can be cross-linked | Final lookup joins on turn/session IDs but does not check their thread equals the selected task thread. | Check task, message, turn and provider-session thread relationships; require isolated child turn/session distinct from parent; preserve agent/model/backend/input/output proof. |
| Duplicate or pre-request handoff accepted | `attest_handoff` uses a Boolean match, without counting matching successful submissions or rejecting a receipt before the request existed. | Require exactly one successful exact parent handoff after request creation. Child startup may precede the parent's tool-completion timestamp; no unjustified ordering constraint was added there. |
| Dead worker can still issue a dispatch capability | Status reads/reserves/returns task arguments, then checks process liveness. | Check liveness first; an observed dead worker becomes INTERRUPTED before issuing a ticket or arguments. No automatic scan restart or task resubmission. |
| Startup reservation can become permanently orphaned | The active lock is written before job state/process publication; a crash leaves later starts calling status on a missing file. An abandoned replacement-lock file or reused PID can also falsely keep work active. | Atomically publish a recoverable start snapshot, use an OS-released start guard on the approved WSL/POSIX runner, let the worker record itself before attestation, bound absent process publication to 30 seconds, and check process birth tokens where available. Same-owner retries return INTERRUPTED; only a new actual owner delivery authorizes a fresh job. Stale progress/liveness reads cannot overwrite terminal results. |
| Creation, pending work and provider reasoning conflated | review_count is only a thread count, and running notification alone carries no actual execution proof. | Independently expose MISSING/PENDING/RUNNING/COMPLETED/FAILED/UNKNOWN task observations. Persist the first task reference/creation timestamp and reject substitution on later collection or receipt resume. Counts remain zero until provider proof is audited. |
| Missing task after ticket has a generic timeout | Reservation can exist without a task; repeated polls never establish submission. | Retain the one-shot reservation; return `NATIVE_DISPATCH_RESERVED_TASK_MISSING` as the terminal cause. Never renew the ticket automatically. Halt remaining sequence after terminal transport/integrity failure, listing all omitted cards. |
| First read fault masks a later terminal fault | First error is reused as batch reason even when a later failure is the actual terminal state. | Preserve first_error and terminal_error separately, including publication/persistence. Halting uses the terminal cause. A recovered transient remains an incident, not a false model failure. |
| Mixed batches discard good advice | `apply_native_research_advice` requires aggregate VALIDATED status before using any row. | Individually validated current rows retain per-card material/provenance/status and can inform eligible research while the aggregate remains INCOMPLETE. Rejected/unreviewed rows cannot influence decisions. |
| Old advice can be counted as current review | Reviewed ID membership ignores per-card expiry; runner completion checks aggregate accepted count. | Export current/stale/unreviewed coverage for every viable finalist. Reconciliation uses only current validated advice. Any unreviewed/stale required finalist prevents complete qualification; admission gates are unchanged. |
| Low-value review queue grows with all watches | Selection appends all active primary watches after viable finalists, creating many optional tasks. | Preserve every viable conditional and strict finalist, while optional watch interpretation has a visible four-card default budget. Deferred watch IDs/reason are exported; deterministic watches are retained. All selected whole cards still obey actual request/brief limits. |
| Zero-tool model lacks the registry it is told to consult | Brief contains the skill and cards, but no complete method definitions/states; fact transport drops source/dependency labels. | Include all nine family names/states and 31 method definitions, necessary evidence, sequence/caveats and actual qualification states. Include source_id, cluster and freshness metadata per fact. Account for these bytes before packing. No registry/skill/blueprint semantics were changed. |
| Model transport is first discovered after costly scan | Old preflight checks configuration but not actual provider envelope or both installed skills. | Read current supported provider records and compare installed analytical/orchestration skills before market I/O. This is explicitly zero model calls. The exact acceptance message additionally authorizes one separately labeled archived-packet native transport check when a suitable capture exists. |
| Combined setup/run message cannot pass owner guard | Only one exact ordinary sentence is accepted, despite the owner needing a complete setup-and-run instruction. | Retain that sentence and add exact equality to a versioned complete acceptance prompt rendered with the checkout SHA. Wrong commit, extra instructions, negation, quotation and delegated senders are rejected. No substring-based authorization was introduced. |
| Final delivery proof is usually never observed | Worker returns after export; later attachment/final are not automatically read. | The fixed worker subsequently observes delivery read-only for at most 600 seconds. Require the original parent relation, exact successful attachment arguments, matching app/provider final, job/hash in final, and unchanged ZIP bytes/checksums. Observation timeout does not launch a new task. |

The Windows data bridge adds only named read operations for parent validation
and integration preflight. No arbitrary SQL, executable, shell, model, network,
account or write endpoint was added. Native receipt databases remain query-only.
Hash references are provenance, not cryptographic protection against a malicious
local storage administrator. Full input bytes do not establish hidden cognition.

## Identity and timestamp contract

| Object | Immutable binding / permitted transition |
|---|---|
| Owner | Actual app mailbox sender `user`, recipient agent, delivered parent turn, exact accepted message bytes/hash. |
| Configured Researcher | Existing agent ID/name, provider adapter, configured model and workspace. A midflight switch fails. A new independently compatible model may be configured outside this work, then independently verified for a new run. |
| Original parent | App thread/turn/provider-session/external-session references, captured start UTC, provider backend/model/workspace. Active or closed state may change; relation substitution may not. Legacy stored requests without the new start field retain the old known reference format; new captures include it. |
| Review task | One exact title/brief, same existing agent, agent origin and app creation UTC. First observed task reference/creation time is persisted and cannot be replaced on receipt resume. |
| Review execution | Exact child app turn and provider session bound to task thread, provider metadata/context, request time through completion, exact complete skill/request and exact app/provider final. Parent and child sessions are distinct. |
| Active pointer | May move to the isolated task or a later turn/session. It is used to authorize the initial start, not to identify historical review receipts. |
| Provider attempt | Unique response IDs with model/turn/session proof. A ticket or app task row contributes zero verified attempts. Invalid JSON/citations still retain actual audited attempt counts. |
| Cutoffs and availability | Original market timestamps, source hashes, reference identities and qualification stay unchanged. Receipt request freshness remains 600 seconds; preparation/startup consumes that envelope. Reconciliation refreshes point evidence without backdating it. |

A completion record can be flushed after a read's as_of snapshot. The collector
may retry that future-to-snapshot observation; it never accepts it before the
snapshot permits it. Unknown versions/backends/record schemas remain closed.

## Blueprint and complete workflow reconciliation

The immutable blueprint's external-first, selective investigation, non-veto
context, source-specific missingness and 0–5 handoff rules remain authoritative.
No market-wide historical reconstruction, new specialist feed, forced shortlist,
trade execution or source/admission promotion was added.

| Transition | Initiator → completion evidence | Failure/resumption/duplication policy |
|---|---|---|
| 1. Ordinary or exact acceptance owner message | Existing main agent receives actual owner delivery. | Quoted/provider/delegated/negated authority is rejected. |
| 2. Approved runner invocation | Main native command tool → exact successful provider command receipt. | No market operation before command attestation; same-owner retries return the existing job. |
| 3. Owner/identity authorization | Runner + fixed reader → owner hash and current configured identity. | Wrong agent/model/session fails; no replacement agent or model. |
| 4. Integration preflight for acceptance | Fixed reader → known current schema/context and both installed skill hashes. | No market/model calls. Unsupported/missing installation is a precise blocker. |
| 5. Optional archived transport check | Existing main agent submits one exact archived replay task → independent provider/app audit and import. | Clearly separate from current market evidence and attempts; failure stops acceptance before market I/O and exports diagnostics. Missing archive defers proof to actual current review. |
| 6. Live scan/pulse | Existing scanner/API adapters → actual request receipts, inventory and cutoffs. | Denied routes stop; unsupported sources do not poison independent valid evidence. |
| 7. Broad screening | PartitionEngine → exact requested/evaluated/returned/missing/faulted identities. | Valid partitions remain; bounded missing-only repair; no all-history requirement. |
| 8. Selective structure | Existing family/method engines → frozen references, causal events, hypotheses and source scope. | Actual history gaps/exclusions remain visible; F1–F9, 27 measurements and 31 methods retained. |
| 9. Review selection and packing | Candidate review + native_workflow → all viable finalist IDs, whole-card batches and explicit optional omissions. | No viable finalist silently dropped; an oversized card is an explicit incomplete review. |
| 10. REVIEW_READY publication | Worker → immutable request and full exact task arguments before waiting. | A receipt-reader outage cannot suppress publication; bad installed skill/input fails closed. |
| 11. Dispatch instruction | Main status include-review → one atomic dispatch ticket and exact arguments. | Repeated polls do not return another ticket. Dead-worker detection precedes reservation. |
| 12. Task creation | Main existing OpenBot start_task → app task row/creation reference. | MISSING/PENDING is distinct from model execution. Creation is durably observed; no automatic resubmission. |
| 13. Native model execution | Existing configured model → provider input/context/response/usage/completion records. | Zero review tools, correct backend/version/model, complete bounded input, strict output. No fixture is a genuine invocation. |
| 14. Locate and attest | Fixed reader → persisted parent/child app relations, selected provider turns and exact bytes. | Active pointer changes allowed; substituted relations, duplicate handoffs, changed inputs/finals and unauthorized tools rejected. |
| 15. Import | Exchange re-reads scoped native storage → validated cited rows and provenance. | A dropped audit/reply JSON cannot forge import. Completed receipts can be re-read without redispatch. |
| 16. Reconcile | Scanner refreshes point evidence; deterministic/native comparison is exported. | Current valid advice can reorder/defer already eligible research; rejected/stale advice cannot admit evidence or change hard gates. |
| 17. Dispositions/watches | Existing admission + ledger → conditional/strict candidates, alternatives, watches and omission reasons. | Zero candidates is valid; current reviewed status is separate from historical validation. |
| 18. Persist | Existing atomic metadata ledger → report/cutoff/watch snapshot and hashes. | Interrupted transaction rolls back; prior committed watches survive. No partial transaction becomes a completed run. |
| 19. Export | Existing exporter → fixed sanitized entries, verified internal hashes and immutable ZIP SHA-256. | Private native DBs/config/reasoning are excluded; repeat immutable publication cannot overwrite different bytes. |
| 20. Owner delivery | Main attaches exact ZIP and saves final; bounded fixed observer → FINAL_DELIVERED receipt. | Attachment path in prose/worker completion is insufficient. Missing or modified attachment/final remains unverified. |

Source gaps are qualification states for the affected operation. True Volume
Profile/footprint/absorption/liquidation, sector/catalyst data and M14/M15 remain
source/definition limited. Full CORE and production family/method flags remain
disabled. Conditional research stays distinct from strict READY and trading.

### Crash and retry limits

- Normal pending/delayed reads are bounded by monotonic waits and request expiry;
  they do not create a second native task.
- The request, ticket and first task observation survive receipt-reader interruption.
  Re-entering the scoped receipt collector re-audits the same completed task;
  a replaced task or modified provider final is rejected.
- A detached whole scanner worker that dies is marked INTERRUPTED. This release
  does **not** serialize and automatically resume an arbitrary Python scanner stack.
  Re-running _worker does not replay the scan; the durable claim prevents it.
  A new actual owner command can authorize a fresh scan using the last committed
  shared ledger. No ticket is recycled and no completed model task is auto-submitted.
- A crash before job state publication is recovered from the complete atomic
  reservation as INTERRUPTED, without spawning a worker. Missing process records
  expire after the startup bound; the worker publishes its own process record
  before any attestation or market operation. Corrupt legacy authorization/state
  files remain a fail-closed operator dependency; they are not guessed or deleted.
- A lost dispatch response can leave a reserved ticket without an app task. The
  system reports that exact omission and ends the affected sequence. Renewed
  submission needs renewed authorization; there is no timeout-based lease renewal.
- Final-delivery observation is bounded and read-only. If it expires, a later
  legitimate status read can still verify already persisted attachment/final proof.

## Verification and independent assertions

The untouched starting implementation passed **447 tests in 645.733 seconds**.
The red regressions reproduced active-pointer rejection and lost mixed-batch
advice before repair. They additionally exposed missing child-thread checks,
duplicate parent handoffs and dead-worker ticket issuance. Test construction
errors in two initial selection cases were corrected by making valid distinct
cards; production assertions were not weakened.

The first focused repair run passed 73/74 tests: one wrong-session case received
a wrong-model diagnostic because the new turn iterator evaluated lazily. Eagerly
validating the bounded provider records restored the precise wrong-session error.
Subsequent 74-test focused runs passed; the expanded focused set passed **86/86**.
A preliminary full run was deliberately interrupted during audit to preserve a
publication failure's terminal cause and halt subsequent batches correctly.
Only the final frozen-source regression/CI receipts count as release verification.

An intermediate full suite passed **478 tests in 892.649 seconds**, and the exact
setup/archive/current-scan positive fixture passed separately. Startup fault
injection then reproduced orphan reservations, absent process publication and
reused-PID states. The repaired startup and terminal-transition checks bring the
focused set to **92 passing tests**. The final release suite covers all changes.

The original two full orchestration fixtures passed: actual production scanner,
PartitionEngine, analytical reducers, native validators, reconciliation, ledger,
ZIP, and parent attachment/final verification run against fake source/storage
adapters. Additional full-workflow fixtures passed active task-pointer changes,
mixed accepted/rejected batches and zero candidates with zero invented calls.
A further positive exact-setup/archive-preflight/current-scan chain is included
in final verification. The model output itself is synthetic in every new test.

The final release suite passed **485 tests in 960.099 seconds**, with zero
failures/errors/skips. The exact 79-file release source manifest, 25 protected
file hashes, configuration and test-log hashes are in the
[verification receipt](../../evidence/external-first/workflow-recovery-20261116/verification.json).

Final test counts/durations, frozen source hashes, protected hashes, configuration,
publication and exact-head CI are in the linked machine-readable verification
receipt and final GitHub delivery. No passing local/native fixture is described
as successful live OpenBot execution.

| Required scenario | Executed assertion source |
|---|---|
| 1. Authentic-shaped parent/child records | `test_native_codex_compat`, `test_native_runtime`; sanitized observed 0.169 envelope fixture, no raw private transcript. |
| 2. Legitimate active turn/session changes | `test_native_lifecycle_recovery`, full `test_workflow_lifecycle_recovery`. |
| 3. Valid same-agent native review | Runtime audit and complete ordinary/acceptance workflow fixtures. |
| 4. Wrong agent | Runtime/config/start ownership rejection; no accepted row. |
| 5. Wrong model | App/provider/context/model-switch negative tests, dynamic second compatible fixture model. |
| 6. Wrong session | Parent binding, cross-linked child rows, substituted task anchor and provider metadata negatives. |
| 7. Wrong backend/schema | Observed compatibility and actual-reader preflight negatives. |
| 8. Modified input | Complete inline bytes, request hash, archival hash and split-text newline negatives. |
| 9. Invalid/incomplete replies | Enum/citation/JSON validators, mixed-batch whole-run test, explicit not_reviewed aggregation. |
| 10. Unauthorized review tool use | Shell, dynamic tool, file write and orphan output negatives. |
| 11. Reservation without task | Exact missing-task terminal cause and unchanged single reservation. |
| 12. Poll/duplicate prevention | Start idempotency, exclusive worker claim, one-shot ticket, duplicate app/parent rejection. |
| 13. Delayed completion | Monotonic collector and asynchronous model/storage fixtures. |
| 14. Interruption/resume | Existing ledger rollback, dead worker/no replay, receipt-only re-audit, persisted task substitution guard, startup crash/new-owner recovery, PID reuse and terminal-state monotonicity. |
| 15. Reader failure | Locks, process errors/timeouts, first versus terminal cause and publication-before-read assertions. |
| 16. Multi-batch completion | Ordinary and active-pointer full workflow fixtures cover every finalist. |
| 17. Mixed accepted/rejected | Whole scanner result remains PARTIAL; independent valid current advice survives. |
| 18. Deterministic reconciliation | Native priority/defer versus identical-source control; stale quote/depth and consumed obstacle remain blocking. |
| 19. Zero candidates | Full scanner with no alt finalists exports explicit partial native coverage and zero calls; archive fallback stays a separate scope. |
| 20. Partial source coverage | Existing source-gap, quote-RVOL, missing rows, history exclusion and independent-method regressions. |
| 21. Watches/candidate accounting | Active coins versus historical references, all viable finalist/alternative records and current review statuses. |
| 22. Verified ZIP | Full export/reopen/internal hashes, immutable bytes and tampered attachment rejection. |
| 23. Parent delivery | Exact attachment tool arguments plus matching saved app/provider final; bounded observer. |
| 24. Read-only authority | All scenarios retain false trading/order authority; source/config/protected checks. |

## Operational PASS/FAIL checklist

This is the live gate; unchecked items are **not** passed by the Cloud tests.

- [ ] Actual clean approved local checkout equals published commit, correct remote
  and integration branch; canonical blueprint/plan/skills and source gates match.
- [ ] Bounded actual reader preflight accepts installed app/provider schema, current
  configured agent/model, parent relation and both installed skills.
- [ ] Actual owner message and exact provider command prove one authorized job.
- [ ] Where an archived capture exists, one exact same-agent archived transport
  task executes and imports before the market scan; its counters/scope are separate.
- [ ] Actual available-market inventory, broad screening and selective structures
  have truthful cutoffs, source receipts, counts and exclusions.
- [ ] Every current required finalist has validated current interpretation or an
  explicit omission/stale state that prevents a complete qualification claim.
- [ ] Every accepted review has correct parent/task/child/session/backend/model,
  exact full input, zero tools, provider usage/completion and exact app/provider reply.
- [ ] Current evidence is refreshed/reconciled and persists with watches/candidates;
  no missing specialist source becomes a positive fact or global family veto.
- [ ] Zero candidates/READY is accepted when justified. A no-card current scan
  uses the separate genuine archived transport proof; if neither packet exists,
  live native acceptance remains blocked rather than fabricated.
- [ ] The complete sanitized ZIP verifies; the actual attachment and parent final
  are independently observed and FINAL_DELIVERED is persisted.
- [ ] Trading/order authority is false; no scheduler/model/agent/permission changes.

Any wrong identity/input/output, duplicate native task, unauthorized review tool,
hidden required finalist, stale admission, false complete-source claim or missing
actual delivery is FAIL. Unavailable evidence and a properly justified empty list
are not failures. A functioning scan with missing required native reasoning is
PARTIAL, not full end-to-end success. Model/source/reader incompatibility is a
NO-GO for complete live acceptance until the exact dependency is resolved.

## Deployment and remaining scope

Use the delivered `OPENBOT_SETUP_AND_ACCEPTANCE.txt` **verbatim** in the existing
Researcher's main chat. It is the versioned template
[OPENBOT_RECOVERY_ACCEPTANCE_PROMPT.txt](OPENBOT_RECOVERY_ACCEPTANCE_PROMPT.txt)
rendered with the exact published SHA. The existing agent handles the path,
checkout update, preflight, one run, exact bounded task dispatch, reconciliation
and ZIP attachment. There are no manual terminal commands or temporary prompt
copies for the owner. The two installed skills remain unchanged.

After successful setup, the ordinary command remains:
**Run the complete market research now.**

Empirical usefulness, prospective recall/performance, sustainable source quota,
new provider versions/backends, unknown specialist feeds and execution economics
remain separate evidence questions. No universal provider compatibility or
positive-candidate guarantee is claimed. The operational runtime remains the
owner's existing approved OpenBot installation, not this Cloud workspace.
