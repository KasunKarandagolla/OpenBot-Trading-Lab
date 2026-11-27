# Engineering checkpoint — OpenBot orchestration, 15 November 2026

Status: **PARTIAL. No fresh owner-initiated live acceptance has been run.**
This session's verification is offline. Historical scanner/native runs are not
combined into evidence of current autonomous operation.

## Starting truth and scope

Fetched clean integration HEAD `54f6e39e994224a56d6459823bd8e32697b7ae11`;
origin is `KasunKarandagolla/OpenBot-Trading-Lab`; PR24 remains draft. Work uses a
new isolated checkout. Older agent/recovery/Codex checkouts and main are intact.
The immutable blueprint and plan retain respectively
`cf7a58fd9ed5f5d1010673406c26a405c8112b907216a47f88a9ebee1bd3d45c` and
`245591eea0f92cd185c51db3420043031c11c1d941f91ecdb31fd64a34e0c232`.
The deployed and repository review skill retain
`96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb`.

Scoped installed metadata inspection found OpenBot0.71.0, Codex CLI0.169.0,
existing Researcher `agent-ddb6c6ee-1d0d-4ed7-92a5-f97ae670d2a7`, configured
`codex / gpt-6-luna`, high effort, existing full access, Computer Use off.
The matching prior provider session's backend metadata is `openai`. Current
active identity is re-read at request creation; this inspection is not a new
native reasoning invocation. No profile or permission was changed.

Allowed implementation impact:

- `researcher/agent_review.py`: trusted identity in requests; live imports
  independently re-audit native storage instead of trusting dropped audit files.
- `researcher/native_identity.py`, `native_host.py`, `native_codex.py`,
  `native_runtime.py`, `native_app.py`: fixed read-only identity/receipt adapters.
- `researcher/openbot_runner.py`, `diagnostic_export.py`: fixed scanner lifecycle,
  owner/provider authorization, private job state and sanitized exact-file export.
- `researcher/discovery.py`: pass private audit configuration into its existing
  pre-admission exchange. No market/source/method/admission predicate changes.
- New separate orchestration skill source, focused tests, this note and PROGRESS.

No edits to existing skills, source certificates, approved design references,
other agents, Freqtrade, trading components, orders or schedules. No global MCP
server or Local Scripts is added.

## Identity and provider proof

An owner-managed ignored path-only JSON retains `openbot_db`,
`agent_workspace`, optional `native_python`, and either the legacy single
`provider_db` or `provider_databases` with exactly `codex` and `opencode` paths.
The two-entry mapping selects storage from the trusted existing agent/provider
identity. Before a query, a read-only schema check rejects a mismatched or
ambiguous database with `SESSION / STORAGE_PROVIDER`; no fallback is guessed.
The mapping keeps both providers' historical stores available without changing
paths when the Researcher switches providers. There are no credentials in this
file; it is ignored, is not committed, and is excluded from diagnostics.

The live request binds agent ID, configured provider/model, actual provider
backend and hashes of the current main thread/session/turn. Agent-generated
identity text is never accepted as proof. Identity changes reject advice while
retaining the market snapshot and deterministic results.

The Codex adapter uses the inspected ordinal rollout format: app turns and
provider sessions; state `threads` metadata; `session_meta`, `turn_context`,
completed items, complete input, exact final answer, task completion and unique
provider usage response IDs. It independently verifies OpenBot origin, current
backend/model, exact session/turn, full inline skill/request, zero review tools,
reply provenance, citations, bounds, cutoff and freshness. Prior payloads are
skipped using timestamp/type envelopes; raw reasoning is not returned/exported.
The CLI version is validated as version metadata and retained in the receipt;
structural envelope and execution checks determine compatibility across
releases. Unsupported record shapes still fail closed. This is
provider-persisted local audit, not cryptographic host isolation or proof of
hidden cognition.

The previous OpenCode session_message/read-tool collector remains a compatibility
adapter and regression fixture. ProviderID/modelID are compared to the actual
requested/configured identity, without a DeepSeek-only acceptance rule. The old
MODEL value remains solely for historical/unbound offline fixture compatibility;
ordinary live scanner exchanges require trusted identity. Codex fixtures exercise
gpt-6-luna and a second schema-compatible test model; OpenCode fixtures exercise
the historical model and a second backend/model. These are fixture results, not
fresh empirical model compatibility or a universal support claim.

The autonomous runner currently supports the inspected Codex handoff only.
Other orchestration backends fail with
`RUNNER_AUTONOMOUS_HANDOFF_UNSUPPORTED_FOR_PROVIDER`; unknown receipt providers
fail `NATIVE_PROVIDER_UNSUPPORTED`. A model must also actually return conforming
structured reviews. A plausible model name alone supplies no support.

## Existing tools and asynchronous handoff

The installed Researcher already has native command tools. Windows→WSL launches
use one fixed command and checkout. A detached worker returns a UTC job ID;
status exposes scanning, review-ready/running, reconciliation and final states.
Only a current user delivery matching the documented natural-language run
command, plus its genuine provider command-execution receipt, can start scanning.
Retries in that owner turn are idempotent. Interrupted processes never silently
replay a live scan; a new owner request starts a separately timestamped run.

The supported app `openbot.start_task` creates a separate context of the same
existing agent. The bounded review receives the entire unchanged skill/request
inline and returns only JSON with zero tools. The main agent remains active,
polls, and attaches the actual resulting ZIP through
`openbot.attach_files_to_response`. No replacement model, agent, owner prompt
copy or Local Scripts callback is used.

OpenBot's general start_task guidance is for independent work. Installation must
therefore include explicit owner authorization for this narrowly dependent
same-agent review handoff. Skill text is not authorization. The prepared setup
message requests that exact scope. No setup/live message is submitted by Codex.

Fresh Windows→WSL offline preflight initially reproduced `disk I/O error` against
OpenBot's active Windows WAL. A fixed Windows reader now handles identity,
authorization and receipt reads. Its operation set excludes SQL/code/shell,
network and model invocation. Repeating the real offline launcher then returned
OFFLINE_PREFLIGHT_ONLY, correct configured identity, exit0 and zero live calls.

## Installation dependency and next owner action

The Windows computer-use bridge fails before JavaScript with
`sandboxCwd is not a local file URI`. The installed OpenBot CLI requires Local
Scripts; that route is intentionally unused. Codex has not installed the new
orchestration skill. A prepared private skill ZIP substitutes the verified
isolated checkout into the separate source template; it contains no audit
configuration, native database, credentials or provider trace. Its local path
is owner-only setup information and is not published to GitHub.

The owner installs that package into this existing Researcher using OpenBot's
supported skill interface, explicitly authorizing the bounded same-agent review
handoff. Setup may run only offline preflight. Once installed, the owner sends
one normal message: **Run the complete market research now.** Only that app
message may initiate the first live examination of these changes.

First exact acceptance blocker: **new orchestration skill is not installed and
its bounded task handoff has not received the required explicit owner setup
approval.** After that, fresh OpenBot-originated live acceptance remains pending.
Codex cannot replace either action with an engineering test.

## Validation and remaining research limits

Untouched baseline:390 tests passed. First integrated full suite:414 passed,
before the final Windows-reader repair. Final local regression:416 passed in385.333s; the final exact owner-command guard
also passed its12 focused tests in8.034s. Exact published-head CI is observed
separately in the final handoff. Sanitized receipts are in
`evidence/external-first/openbot-integration-20261115/engineering-verification.json`. Offline
fixtures cover identity/model/session/agent failures, full read and final
provenance, tool denial, invalid citations, stale/future input, private config,
wrong cwd, genuine owner command, idempotency, interruption, state transitions,
fixed bridge operations, path/symlink/export bounds and no synthetic FULL label.
Configuration/reference hashes are rechecked. No live scanner or native review
was initiated by Codex; fresh funnel, native decisions, HTTP/bytes/time and live
ZIP are **NOT_RUN**, not historical numbers or invented zeros.

Specialist feeds, true profile/footprint/executed absorption/liquidation,
dated sectors/catalysts, M14/M15 primary definitions, quota/cadence, actual future
execution costs and prospective performance remain unqualified. Trading
authority stays false. Functional orchestration itself remains unverified until
the required owner-originated run and actual delivery are observed.
