# Final native orchestration engineering proof — 16 November 2026

Engineering evidence is offline. **LIVE ACCEPTANCE: NOT_RUN_IN_CODEX_CLOUD.**
Every model reply in the new harness is a fixture, never a genuine model call.
The uploaded owner's live-run ZIP is immutable failure evidence, not a new run.

## Reproduced defect and restored contract

Baseline `7c72c817f87c829db1042d9b009e11117bb23fe4` delegated the entire
`native_app.wait_for_reply` process before `prepare` published the review task.
A controlled reader-process failure reproduced **no usable review-task file**.
`exchange` also attempted collection before publication, status inferred readiness
from a transient file, and the ordinary runner explicitly passed one card.
These are proven code paths. The supplied ZIP does **not** retain the original
reader exception; its specific Windows/process/database cause remains unknown.
The earlier ordinal / `-NoProfile` attestation repair is preserved.

`native_workflow.review_batches` now builds bounded groups using both complete
request bytes and the actual 100,000-character OpenBot brief limit. It exports
every viable finalist hypothesis plus current protected rivals. Whole cards
that individually exceed transport limits have explicit omissions and prevent
complete native qualification. It never truncates either canonical skill.

`exchange(prepare_only=True)` publishes the hash-bound request without collecting.
After the current identity is independently checked, local `prepare` verifies the
request hash and installed skill and atomically publishes the exact immutable
`{title, brief}`. It does so before receipt collection; WSL delegates only scoped
reads to the fixed Windows `native_host` reader. Reader outages after authorized
publication cannot suppress REVIEW_READY. No code submits a model task.

The worker persists REVIEW_READY before waiting. Main-chat `status --include-review`
returns full unchanged arguments once and atomically reserves a dispatch ticket.
Subsequent polls show REVIEW_DISPATCH_RESERVED until app storage shows the task,
then REVIEW_RUNNING. A lost dispatcher is allowed to time out; no automatic
resubmission occurs. Each next distinct material/batch returns to REVIEW_READY.
The existing skill's no-redispatch rule continues to apply to the same material.
A caller bypassing this protocol and creating duplicate tasks is rejected by the
independent receipt reader. No global idempotency feature of OpenBot is assumed.

The monotonic bounded wait is per batch, up to the configured 600 seconds; each
native-host read also has its existing 30-second subprocess bound. Request
creation, publication, dispatch latency, provider execution and collection latency
are recorded separately. Transient storage faults retain their first sanitized
stage/code, even if collection later succeeds. Integrity/config/identity errors
are terminal; failed tasks have NATIVE_TASK_FAILED. Missing final/provider proof
cannot be counted as completed reasoning. Actual audited attempts survive reply
rejection and receipt-file persistence errors.

## Full ordinary offline chain

`tests/test_workflow_e2e.py` starts from an actual fixture owner delivery. A
simulated process launcher starts an asynchronous worker thread. The production
`attest_start`, scanner, PartitionEngine, family/method reducers, admission,
native receipt validators, reconciliation, ledger and ZIP exporter execute.
Only external source adapters, process launch and app/provider storage are faked.
The Codex provider fixture uses the independently verified 0.169 ordinal envelope,
exact parent command and start_task receipt, isolated same-agent turn, full inline
skill/request, usage record, exact app/provider final and completion events.

Positive scenario 1 computes five distinct final research coins on 1h/15m, in
F2/F8 with both directions including BEARUSDT. Six viable finalist hypotheses
and one current rival travel in three bounded tasks: seven distinct cards,
three fixture provider attempts, zero genuine model calls. All finalist IDs
are reviewed; no one-card shortcut or omitted finalist. The pending task takes
at least 1.1 seconds in the app fixture; the worker remains alive and no ZIP exists
while pending. INVESTIGATE advice changes research ordering without changing
source facts, strict admission or trading authority.

The observable durable chain is:

```
OWNER_AUTHORIZED -> COMMAND_ATTESTED -> SCANNING
-> REVIEW_REQUEST_PREPARED -> REVIEW_READY -> REVIEW_RUNNING -> REVIEW_VERIFIED
-> [next distinct bounded batches repeat those four review states]
-> RECONCILED -> EXPORTED -> COMPLETED
-> FINAL_DELIVERED [only on separate parent attachment + final-answer proof]
```

The ZIP contains reconciliation and its original awaited-delivery status. It
cannot contain evidence of its own subsequent delivery. A later scoped status
read verifies the actual parent attachment tool receipt and matching provider/app
final containing the job ID and ZIP SHA, then records FINAL_DELIVERED separately.
The harness exercises this proof and confirms the original ZIP remains unchanged.
Neither worker completion nor a filename mentioned in text proves delivery.

Positive scenario 2 advances the evidence clock by 61 seconds per completed
batch and moves AAAUSDT beyond its first obstacle. Current quote/spread and depth
are refreshed, economics/room are reevaluated, and AAAUSDT is removed. No expired
point observation is relabeled current and no closed history is fabricated.

Positive breadth/cache scenario uses 519 eligible fixture contracts, real scalar
response normalization and selective history. More than the former twenty alts
are investigated within the physical I/O/freshness allowance. A warm run fetches
no additional selected history or remote scalar packs and preserves ledger
reference/event/watch identities. Current job ID replaces cached job metadata.
The final resource reservation includes both depth/quote phases before allocating
history. Fake adapters count inventory, aggregates and histories as well as depth,
and assert the complete run stays within80 official-call slots.
The normal runner now shares `work/openbot-integration/research.sqlite` across
jobs instead of discarding watch/cache continuity with a per-job database.

## Controlled faults and inherited adversarial evidence

| Fault | Exercised outcome / tests |
|---|---|
| Inaccessible process, incompatible reader/schema, locked/busy/I/O database | Task stays visible after authorization; bounded wait or precise terminal code; test_native_workflow, test_native_codex_compat |
| Publication/skill/input/hash failure before readiness | TASK_PUBLICATION / exact sanitized code; no usable unauthorized handoff; test_native_workflow |
| Pending/missing/late task or provider receipt | Explicit timeout/stale/incomplete; zero unaudited attempt claims; test_native_workflow, test_native_runtime |
| Failed native task | NATIVE_TASK_FAILED / RECEIPT_COLLECTION; no completed-reasoning claim |
| Changed private config, active agent/model/session/backend | Reject without new task; test_native_workflow, test_native_runtime |
| Wrong title/material, duplicate task/reply, forged text final | Reject provenance/contract; test_native_runtime, test_native_codex_compat, test_agent_review |
| Truncated skill/input, bad citation, forbidden tool | Exact byte/citation/tool rejection; test_native_runtime, test_native_codex_compat, test_agent_review |
| Interrupted worker / repeated start / double poll | Durable worker claim and dispatch reservation; no automatic scan or task replay; test_openbot_runner |
| 350 returned / 400 requested / 519 eligible | One missing-only recovery after healthy partitions; otherwise 50 absent and 119 never requested remain explicit; test_recovery_coverage |
| Stale/future/missing bars, Unicode, zero quote baseline, unknown fees/depth/sectors/rights | Existing source/numerical/specialist guards and new coverage/E2E tests; no forced positive/READY |

Focused native/orchestration/coverage files contain **62 tests**, including two
complete asynchronous scanner-to-delivery/reconciliation scenarios. Full-suite,
config, checksum and protected-file receipts are in
`evidence/external-first/final-recovery-20261116/verification.json`.
The untouched baseline passed 431 tests. Intermediate red publication/wait tests
and a warm-cache assertion during ongoing source edits are disclosed in the
verification record; no cache assertion was relaxed or hidden skip added.

All skills, blueprint, plan, source certificates and trading boundaries retain
their original bytes/gates. Genuine OpenBot execution, permitted host market I/O,
provider availability, actual cognitive usefulness and prospective discovery
quality still require the owner's separate live acceptance.
