# Codex Cloud — OpenBot External-First Market Researcher — Session 1

**Model:** GPT Sol / strongest available coding workhorse for architecture, integration and API qualification.  
**Environment:** Codex Cloud **first**. Codex Local is a narrowly scoped exception for a specifically blocked Cloud operation, never a parallel implementation track.  
**Repository:** `KasunKarandagolla/OpenBot-Trading-Lab`  
**Target workstream:** read-only, external-first Market Researcher for Binance USDⓈ-M USDT-settled perpetual futures; ≤15-hour prospective trading horizon.  
**Scope:** **Session 1 only** of the six-session plan. Do not implement Sessions 2–6 speculatively.

## 0. Authoritative references — read before implementing

Read these exact repository files **in full** and treat them as the frozen project reference for this workstream:

1. [`docs/implementation/OpenBot_Final_External_First_Market_Discovery_Blueprint.md`](./OpenBot_Final_External_First_Market_Discovery_Blueprint.md) — authoritative detection and system specification, especially Sections 0–4, 6–7, 9, 12–14, 16–17, Appendix B. All other sections remain in scope and must be understood.
2. [`docs/implementation/OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md`](./OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md) — authoritative sequencing, six-session scope, Git sync discipline, Cloud/Local handoff, and acceptance gates; especially Sections 2–4, 6–7, 9.
3. The current checkout's `AGENTS.md`, any relevant actual `SKILL.md`, project README, architectural documents, existing tests and `docs/implementation/PROGRESS.md` if present.

If the approved files are absent from your checkout, **fetch the published reference branch/commit**; do not create a guessed alternate design. Check that you are reading the exact source, not a different similarly named historical draft. Do not alter the two finalized reference documents unless the owner explicitly authorizes a revision; document implementation-dependent clarifications in `PROGRESS.md` instead.

## 1. Mandatory start-of-session Git and repository reality check

1. Confirm the repository URL, authenticated remote, permissions, current branch, `git status --short`, `git rev-parse HEAD`, `git remote -v` and `git fetch origin`.
2. Locate the **published reference branch** and verify the expected previous remote commit SHA supplied by the handoff. Only fast-forward to an approved remote branch; **never** reset, force-pull, force-push, overwrite unrelated work, or make direct unreviewed changes to `main`.
3. Inspect actual repository branches, older PRs/commits and deployed code if accessible. The previously audited `main` at `2343053ce68f6fff4525c5b67771ea445deb3779` mainly described a smaller Freqtrade paper lab. **Do not presume** older Market Researcher, Deep Analyst, 27 skills, causal feature code or PR #11/#23 artifacts are merged into current `main`.
4. Determine the *latest relevant implementation base*, not merely the newest timestamp. Document reusable code/functions and their proven versions; distinguish active code from old experimental/unmerged research.
5. Keep a **single integration branch and one active writer** after base selection. If the published reference branch was created from documentation-only `main` but the real approved implementation base differs, **stop and reconcile safely** (e.g. user-approved branch/cherry-pick strategy). Do not silently rewrite history or lose the reference documents. Ensure Session 2 has exactly one verified remote branch SHA to start from.
6. Read the actual paper-trading/execution boundary; no order permissions may be introduced by this workstream.

Deliver a concise **repo truth/reuse inventory**: current heads and relevant PR status; which modules and skills really exist; what can be reused; what is unmerged; what the Deep Analyst interface actually looks like, if present; any mismatches requiring owner decision.

## 2. Fixed project invariants — do not reopen these decisions

- **External-services-first is settled for this implementation experiment.** No compulsory universe-wide local OHLCV history downloads, continuously maintained all-symbol 15M/1H stores or universal local structure engine. Small targeted oracle data, provider normalization, tests and a minimal metadata/watch SQLite database are allowed.
- Entire eligible Binance USDT-settled USDⓈ-M **crypto perpetual** universe is the inventory; record genuine per-method/source coverage, including lower-ranked quiet alts, young symbols and multiplier contracts. Never claim complete structural coverage from 24h ticker presence or the provider's top-50/top-200.
- **BTC/ETH, breadth and sectors guide research attention and trap questions but never veto contrary, independent or idiosyncratic altcoin nominations**.
- All **nine F1–F9 families** and selected specialist methodologies (SMC/ICT, BOS/CHoCH, S/R, EQH/EQL, OB/breaker, FVG/iFVG, CRT, PO3/AMD, OTE, auction/profile, VWAP, real flow, derivatives and relative strength) remain in the registry with honest `NATIVE_REMOTE`, `REMOTE_RECONSTRUCTED`, `PROXY_ONLY`, `TARGETED_ONLY`, `UNSUPPORTED`, `UNVERIFIED` or `DEFINITION_PENDING` statuses. Do not invent Keepssy Reversal Model rules.
- Closed bars; exact contract/venue; `window_end`, `known_at`, `available_at`, `received_at`; source history/cutoff and event order are nonnegotiable. An indicator combination is not a causal historical sequence.
- Provenance, scope and units matter: bar-aggregate taker delta ≠ price-bin footprint; OHLC-derived value proxy ≠ true Volume Profile; OI increase ≠ new long positions; historical percentage change ≠ beta-adjusted residual.
- The researcher produces **0–5 read-only Deep Analysis hypotheses**, watches and honest coverage reports; it **never places orders, changes Freqtrade configurations or databases, supplies unauthorized final executable entries/SL/TP, or enables live trading**.
- Optional LLM reasoning is over validated compact evidence; no per-coin prompt flood, hallucinated data or made-up predictive confidence.
- Do not purchase services, circumvent geographic restrictions/403/451, scrape behind access gates, repurpose credentials or silently change the data architecture.

## 3. Session 1 work package — build a truthful, reproducible foundation

### A. Establish branch, layout and read-only contracts

- Follow the **approved** reference/integration branch procedure in Section 1. Preserve unexpected dirty changes and protected workflows. Create/reuse the smallest logical scaffold appropriate to the **actual repository**; avoid a second duplicate application if useful researcher code exists.
- Add or refine **concise** `AGENTS.md` guidance for repo/session boundaries **after reading any existing instructions**; do not overwrite an existing user's `AGENTS.md`. Establish/update `docs/implementation/PROGRESS.md` with: base commit, branch, verified items, blocked items, tests, capability status, architecture invariants, next dependency-ready tasks, and source reference hashes.
- Define minimal, typed, **read-only** interfaces for: `Instrument`, provider capability/entitlement, evidence with data fidelity and time provenance, `ScanBatchReceipt`, coverage denominator and a final report skeleton. Avoid creating fake working family detectors in Session 1.
- Centralize provider feature/parameter configuration in one small, versioned manifest (`discovery_specs.yaml` or existing equivalent), with all unproven formula/method entries **disabled/unverified** by default.
- Add `.env.example` with **names and guidance only**, ignore real `.env`, caches, provider responses containing tokens, generated SQLite stores. Provide a straightforward `provider status` / `config validate` / `scan smoke` command using existing CLI conventions where possible. If optional `setup-keys` can be implemented safely now, use one centralized interface; otherwise document the exact simple future interface. **Never** echo key values or commit credentials.
- Provider transports matter: a tool callable by the ChatGPT agent **is not automatically a Python/runtime MCP integration**. Implement/test the actual runtime client/handshake as needed.

### B. Qualification sprint: live, permitted external provider evidence

This is the **first hard dependency gate**. Check the actual host's network permissions and free automation terms before bulk calls.

1. **Binance reference/identity**: from the actual permitted host, query official `exchangeInfo` and verify instrument type, quote and settlement, trading status, listing age, price tick, quantity rules and unusual/multiplier products. Use cheap all-symbol ticker/book for separate market observation where lawful. If the host gets HTTP **451**, stop that route and record the location/access restriction; **do not circumvent it**.
2. **Basis MCP** (`https://www.basischarts.com/api/mcp`): establish correct current supported MCP session; inspect `tools/list`, `screener_run`, `formula_evaluate`, `market_candles`, `orderflow_read`, applicable formula/column schemas, output fields and documented entitlements. The archived Consultation 1 test demonstrated a **50-name server-side scan from a provider top-60 pool** and short formula-function probes; that is **not** proof of full-universe quiet-tail coverage or historical oracle accuracy.
3. **Real quiet-tail cohort**: select at least one 50-member explicit partition of **independently sampled actual Binance eligible contracts** outside provider top-ranked cohorts; include low-ranked but tradable, medium, young and multiplier contracts where present. Verify exactly which requested names were **recognized, evaluated, returned, filled in, truncated, missing and faulted**. Test a final partition smaller than 50 to detect vendor-added filler rows.
4. **Time and units**: test closed 15M/1H source as-of versus bar-open, bar-end and provider availability times, quote/base volume/taker-buy field units, prior closed level vs rolling 24h high, history warm-up and missing bars. Qualify no source by marketing names alone.
5. **Remote formula proof**: test at least an always-finite scalar core (range/normalized width, lagged high/low, ATR or permitted equivalent, volume, a simple prior-bar comparison). Probe `highest/lowest`, `lag`, `median`, `quantile`, `bars_since`, `value_when`, delayed pivot and no-event/NaN semantics **only if tool schema provides them**. The previous 1,000-bar quantile with 300 loaded bars reportedly poisoned an entire 20-symbol screen despite OR fallback. Explicitly reproduce/isolate that sort of failure if permitted; place sparse/optional methods in separate packs.
6. **Independent oracle**: collect tiny, bounded permitted historic references for BTC, ETH and several representative alts; independently compare provider numeric outputs and shifted timestamps against expected calculations. **Passing syntax is not passing semantics.** Historical arbitrary `as_of` remote replay is **UNVERIFIED** until demonstrated; do not claim it from current-batch scans.
7. **Quota, rights, performance**: record free entitlement, allowed automation/cadence, response bytes, actual evaluated denominator, cold/warm wall time, 429/Retry-After, HTTP 200 with `isError=true`, 403/451 and cancellation/backoff. Use conservative serial or bounded parallel probes; don't burn free quotas with premature 24/7 testing.
8. **Alternatives only if useful**: inspect CoinBeacon, TraderSpy, Coinfuty, Coinalyze, MarketTrace, Depth Radar or other documented free sources *only where they solve a specific failed or missing core test*. Do not implement every optional adapter in Session 1. A failed provider is a **capability record**, not authorization to swap in mass local downloads.

For each operation, record `LIVE_TESTED_NARROW`, `DOC_CONFIRMED`, `VENDOR_ADVERTISED`, `UNVERIFIED`, `PARTIAL`, or `BLOCKED` as appropriate. Store **sanitized** JSON/schema fixtures and reproducible small probe scripts only where rights and repository privacy permit. Preserve source hash, provider cutoff, requested/evaluated/returned/failed IDs, exact units and quota costs.

### C. End-to-end **Session 1** read-only smoke demonstration

- Provide one safe command that loads provider config, emits current capability/health, invokes **one reproducible qualified remote operation if available**, verifies response schema/scope and writes a **truthful machine-readable** minimal observation + coverage report. It is fine to return **no shortlist** and `UNVERIFIED` methods.
- If every host/provider access route is blocked, produce a **specific, reproducible failure report**, testable offline fixtures, and a clean scaffold; do not label it a successful external broad scanner.
- Include tests for exact symbol mapping, clock/fidelity/units schema, missing/truncated rows, tool-level errors, secrets redaction, deterministic no-order boundary and incomplete capability status.
- No full F1–F9 detector/structure engine, no complete ranking/LLM system, no routine full-market historical klines, no automation scheduler in Session 1. These belong to later gated sessions.

## 4. Mandatory tests and stop/go gate

**Session 1 passes only when**:

- [ ] Current real repo branch/history/current active code reuse is documented accurately.
- [ ] Reference documents and working branch are verified, no unrelated changes lost.
- [ ] Minimal read-only skeleton, config/keys status and safe smoke interface exist where practical.
- [ ] At least one **lawful reproducible** external provider call succeeded **or** a specific documented provider/host failure remains with explicit next qualification path.
- [ ] Exact contract/venue/time fields are validated where source is available; any unknown remains labeled UNKNOWN.
- [ ] Real quiet-tail external capability has been probed or is specifically blocked; **no full-universe claim** without it.
- [ ] Core formula tests and independent sampled oracle fixtures are versioned as available; untested semantics cannot become certified.
- [ ] Relevant unit, provider-contract, clock/fault and safety tests run; failures clearly reported.
- [ ] Work is committed, pushed to the approved integration or clearly labeled WIP checkpoint branch, and the **remote SHA verified**; CI status observed, not guessed.

If the provider qualification gate remains unresolved, **do not preemptively begin Session 2's all-universe implementation**. Clarify the exact blocked function and propose the narrowest qualified external alternative or follow-up probe. When a particular Cloud development operation cannot be completed due to tooling/network/runtime limitations, document the exact reason and hand **only that operation** to Codex Local from the latest pushed SHA. Do not use Local merely to evade service restrictions.

## 5. Mandatory GitHub handoff (no silent local completion)

Before ending:

1. Inspect `git diff` and stage **only** project-relevant files, without caches, credentials or large sample market data.
2. Run and report exact tests (`passed / failed / skipped`), including reproduction commands and known limitations.
3. Update `docs/implementation/PROGRESS.md` with repository base/branch, source revisions, provider capability table, sampled quiet-tail coverage, exact fixture/commit hashes, unresolved gates and next task.
4. Commit meaningful changes and push to the same approved branch; **verify remote branch head equals local HEAD**. If protected workflow/auth blocks push, report the blocker and **do not claim publication**.
5. State CI/check-run status precisely; no claim of green CI when not run or pending.
6. Provide this final handoff format:

```text
OpenBot Market Researcher — Session 1
Environment: CODEX_CLOUD (or CODEX_LOCAL_EXCEPTION for exact isolated operation)
Repository and target integration branch: ...
Starting remote SHA: ...
Final pushed remote SHA / checkpoint SHA: ...
Reference blueprint/implementation-plan hashes: ...
Actual branch/code/skills/deployment reuse inventory: ...
Code and guidance added/changed: ...
Provider qualification: operation / exact contract cohort / auth / timestamp /
  units / requested / evaluated / returned / failed / source cutoff / quota / result
Numerical/oracle results: passed / failed / not tested, exact rationale
Read-only and no-order security result: ...
Tests/CI: ...
Blocked or unqualified capabilities: ...
User action needed (if any): ...
Next dependency-ready task (Session 2, or narrower repair): ...
GitHub branch / commit / PR links: ...
```

**Success means a trustworthy source-proven, GitHub-pushed foundation, not claiming an entire Market Researcher was built in one session.** The next Codex session begins from the **exact verified remote SHA** and reads these same two immutable reference documents plus `PROGRESS.md`.
