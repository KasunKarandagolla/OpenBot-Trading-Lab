# OpenBot Trading Lab — Cloud-First, GitHub-Synced Implementation Plan

**Version:** 1.0 · **Date:** 13 November 2026  
**Primary design authority:** `OpenBot_Final_External_First_Market_Discovery_Blueprint.md` (13 November 2026)  
**Scope:** Implement and test the external-first **Market Researcher** for Binance USDⓈ-M USDT perpetuals, for a separate ≤15-hour-trade-horizon research workflow.  
**Development venue:** Codex Cloud first; **Codex Local only for a specifically blocked Cloud task**, with every handoff synchronized through GitHub.  
**Status:** Engineering plan, not authorization to place orders, purchase services, or claim that untested providers/methods work.

## 1. Revised session estimate and rationale

**Target: six focused sessions (five Sol + one Luna), not nine mandatory sessions.** This is a scheduling target, not a guarantee that the entire research methodology can be empirically validated in six prompts.

- **Five sessions are plausible** when useful prior OpenBot code is recovered, the external provider tests pass promptly, and documentation/usability can be finished in Session 5.
- **Six is the recommended target**: five substantial Sol sessions and one narrowly scoped Luna completion session.
- **Seven to nine sessions may be justified** if Session 3's structural methodology implementation needs splitting, if provider authentication/interfaces require redesign, or if integration evidence reveals substantive defects.
- **Additional weeks of point-in-time/forward observation** may be needed to judge screening quality, missed opportunities and downstream trading usefulness; more coding sessions cannot replace elapsed observation time.

**Why six rather than nine:** Keep one end-to-end increment per session, combine closely related modules, run test-and-repair loops in the same session, and use reusable repository guidance and progress records. **Do not cut independent source qualification, semantic or causal tests, full-universe accounting, gap handling, or end-to-end acceptance to hit a session number.**

The word **implemented** must not be confused with **externally supported** or **empirically proven**. Every F1–F9 family and selected methodology is included in the registry, but claims requiring unavailable profile/footprint/remote historical sequences must remain explicitly `UNSUPPORTED`, `UNVERIFIED`, `PROXY_ONLY`, or `TARGETED_ONLY` until independently qualified.

## 2. Rules fixed across all implementation sessions

1. **External-services-first is the agreed experimental architecture.** Do not reopen this choice or implement a compulsory universe-wide local-candle engine. Small selected-symbol reference/oracle tests and lightweight local storage are permitted.
2. The researcher's responsibility is **market-wide discovery, evidence interpretation, EARLY/DEVELOPING/READY/FAST/LATE status, watches, and a 0–5 candidate research handoff**. It does not place trades or write final entry/stop/TP instructions.
3. Coverage is measured by **exact requested / evaluated / returned / failed instruments, method, timeframe, source, and exclusion reason**. Quiet-tail and BTC-contrary nominations cannot disappear through a top-movers-only gate.
4. BTC/ETH/breadth/sector context changes **priority of questions**, never eligibility or the right to apply any methodology.
5. Historical references, events and hypotheses must preserve **window end, known-at, available-at, venue/contract identity, and actual event order**. No future leakage or fabricated structural sequences.
6. Use tested, deterministic computation for observable facts. Use an optional concise skill-driven LLM pass for ambiguous interpretation, evidence comparison and rival hypotheses—not for inventing numeric data.
7. Every provider and specialist operation is **capability-gated**. Failed access, unknown quota, partial market scope or unvalidated units create visible degraded modes, not fake coverage.
8. Inspect actual code, branches and older PRs first. The previously reviewed `main` snapshot at `2343053ce68f6fff4525c5b67771ea445deb3779` predominantly contained a smaller Freqtrade paper-lab design; **do not presume historical Market Researcher/Deep Analyst implementations are merged**.
9. All work goes through a **reviewable GitHub feature branch**. No force pushes, no bypass of branch protection, no unapproved direct change to `main`.
10. A completed change is not handed off until **tested, committed, pushed, and verified on the remote branch**. If GitHub push/authorization is blocked, report the blocker and do not claim it was delivered.

## 3. The exact Cloud → GitHub → Cloud/Local operating protocol

### 3.1 One-time branch selection

- In Session 1, inspect the repository's default branch, older research branches and relevant PRs; identify the **latest relevant upstream code**, not just the most recently timestamped branch.
- Create or reuse a single integration branch such as `feature/external-first-market-researcher` from the reviewed base. Maintain a PR against the approved target branch.
- **One active writer at a time** to this branch: do not let Cloud and Local make concurrent unsynchronized edits.
- Place the final blueprint, this implementation plan, and a compact `docs/implementation/PROGRESS.md` in the repository if licensing/access allows. Record source file IDs, design hash, and implementation assumptions; do not duplicate 170 KB into prompts on every session.

### 3.2 Mandatory beginning of **every** Cloud or Local session

1. Confirm the correct GitHub repository and intended integration branch.
2. `git fetch origin` and `git status --short`; inspect rather than overwrite any unexpected existing changes.
3. Switch to the approved branch and **fast-forward only** to `origin/<branch>`; if it is not a fast-forward, **stop to reconcile**, never reset or force-pull.
4. Compare local `HEAD` with the expected previous **remote commit SHA**. Confirm remote HEAD changed only through authorized work.
5. Read `AGENTS.md`, relevant `SKILL.md` instructions, the selected sections of the blueprint and `PROGRESS.md`.
6. Read prior-session test failures and unresolved capability gates; select only the next dependency-ready task.

### 3.3 Mandatory end of **every** change/session

1. Run task-relevant unit, contract, oracle and integration tests. Run the full verified test suite at each major vertical-slice boundary.
2. Inspect exact diff; avoid unrelated files, credentials, generated SQLite databases and runtime caches.
3. Update `PROGRESS.md`: **verified, partially verified, blocked, unimplemented, next actions, tests, operational assumptions**.
4. Commit the exact completed changes with a meaningful message; push to the same integration branch.
5. Verify the remote branch SHA matches local `HEAD` and CI status is observed; if CI fails, repair and push before declaring the stage done. If CI remains pending, mark it pending instead of passed.
6. Provide a concise handoff: repository URL/branch, commit SHA, implemented behavior, evidence/test results, incomplete capabilities and next-session prompt.

If the task cannot reach its pass gate, push an **explicitly named work-in-progress checkpoint branch** with truthful test status only when appropriate and authorized; do not label it a completed integration increment. The next session resumes from that exact relevant pushed checkpoint.

### 3.4 The Local Codex exception rule

Local Codex is **not a second development track**. Use it only if a concrete Cloud operation is blocked by Cloud environment tooling, approved host reachability, required desktop access, or unsupported local dependencies.

1. Cloud attempts the task and captures a minimal reproducible failure plus why the block is environmental rather than a code bug.
2. Request or use the necessary approved local setup. Do **not** use a local IP/location merely to evade an external provider's legal, geographic or account restriction.
3. Local fetches the latest pushed integration/checkpoint branch and confirms the expected commit SHA.
4. Local performs **only the blocked subtask**; runs the same tests, writes machine-readable evidence/fixtures, and pushes the relevant commit.
5. Cloud's next operation fetches that local push and verifies the new SHA before proceeding. Never manually copy competing edited folders or assume local work has appeared in Cloud.
6. If provider access is blocked on **both** environments, record a provider capability failure, try qualified alternative external services if available, or emit a degraded/partial research result. Do not silently substitute a full local market scanner.

Cloud-hosted development environments are not assumed to provide permanent runtime database storage or 24/7 scheduling. Those are separate deployment decisions after the on-demand build works.

## 4. Six session work packages and objective pass gates

### Session 1 — Sol: Repo reality, provider qualification and a working skeleton

**Do together:** audit the actual repo + relevant history, establish the branch and build conventions, define read-only interfaces, implement centralized configuration, and run a first **real external-provider proof sprint**.

- Locate/reuse existing Market Researcher skills, numerical tools, structure/event code, adapters and persistence where genuinely present. Identify incompatible duplicate architectures.
- Inspect repo protections: preserve Freqtrade paper-lab boundary, no writable trading API, paper/live separation.
- Create minimal scaffold and contracts, one smoke-test runner, `AGENTS.md`, `PROGRESS.md`, source capability manifest, `.env.example` and an ergonomic key setup/status command.
- Reproduce Basis MCP `tools/list`, explicit symbol partition scan and formula function output. Critically test **genuine eligible quiet-tail contracts**, not only the top-60-derived 50-symbol historical probe.
- Check actual Cloud access, API entitlements/terms, symbol identity, data units, closed 15M/1H semantics, historical availability and preliminary latency/quota.
- Store sanitized provider request/response fixtures; mark all untested operations `UNVERIFIED`.

**Exit gate:** a pushed, testable read-only scaffold; a trustworthy code-reuse inventory; at least one reproducible permitted provider call or a documented, specific provider failure; an exact provider-qualification next step. If broad provider capability fails, do not launch giant downstream code work assuming it exists.

### Session 2 — Sol: Full-market external discovery and coverage accounting

- Implement exact Binance USDⓈ-M eligible perpetual inventory/metadata and cheap whole-market current observations.
- Implement provider adapters with one shared interface for read-only remote formula execution, quotas/timeouts, response normalization, pagination/partitioning and error isolation.
- Compile and run **only qualified** shared 1H/15M remote precursor packs over explicit supported-symbol partitions; select and verify independent numeric samples against small reference/oracle data.
- Preserve quiet-tail, new-listing, abnormal-return/volume, historical-watch, relative-strength and provider-specialist nomination entry points without arbitrary top-mover exclusion.
- Output auditable `ScanBatchReceipt` files, exact requested/evaluated/failed denominators, source freshness and **partial/degraded coverage** reports.
- Demonstrate one genuine end-to-end **on-demand read-only scan** producing normalized observations and a truthful coverage summary (the shortlist can still be empty).

**Exit gate:** a real batch scan operates on the provider-qualified universe, does not silently omit failed names, respects request budgets, and passes instrument-identity, cut-off, units, no-hidden-truncation and fault-injection tests.

### Session 3 — Sol: Causal structure intelligence and methodology coverage

- Implement frozen reference objects, chronological event transitions, rival hypotheses and a tiny SQLite metadata ledger (not a market-wide candle archive).
- Build the shared numerical measurement library with explicit timeframe/window, price-tick precision, stale data and reference invalidation behaviour.
- Implement the **full F1–F9 and selected analytical-methodology registry** with exact necessary conditions and explicit capability/fidelity labels. Construct the most feasible causal detector pathways first (for example F2/F4/F5 rival events, FVG and F1 controlled pullback), then other methods using shared primitives.
- Do not label approximate value-area proxies as true Volume Profile; do not label candle-derived delta as footprint; do not infer order intent from OI alone.
- Create small independent historical-oracle fixtures, counterexamples, time-shifted tests, no-lookahead tests and invalidation tests.

**Exit gate:** each method has an implemented, honest status; supported methods have numeric and causal verification; transitions/invalidations are reproducible; every incomplete specialist remains surfaced, not removed. **This is the most likely session to split into two Sol sessions** if implementation/testing cannot be completed with reasonable focus.

### Session 4 — Sol: Trader-style interpretation, specialist checks and shortlisting

- Build BTC/ETH 4H/1H structure, breadth, dispersion and sector **ContextCard** from qualified synchronized sources.
- Make market context a **non-veto research agenda**; verify counter-BTC, bearish-under-bullish-BTC, specialist-led and new-listing pathways remain eligible.
- Add only the one or two **highest-value accessible** specialist sources (e.g. selected derivatives history and supported real profile/order-flow), with source-specific coverage and truthful missingness.
- Implement an evidence-aware query planner: ask only targeted questions that could change stage, interpretation or inclusion; enforce quotas.
- Implement structural room, exhaustion, tradeability, evidence dependency, rival hypotheses, 0–5 research handoffs, EARLY/DEVELOPING/READY/FAST/LATE watches and near-miss reasons.
- Add concise `.agents/skills/.../SKILL.md` instructions for market interpretation and research verification; reuse older OpenBot skills where proven. Add an optional batch LLM consultant **only if it improves decisions** over deterministic evidence.

**Exit gate:** independent family nominations feed a source-cited shortlist; all methods remain visible; context never silently vetoes opposing cases; a Deep Analyst can accept or reject each hypothesis without trusting an opaque score.

### Session 5 — Sol: Robust on-demand operation, resumption and integration verification

- Connect scanner, event ledger, context, specialists, reasoning and shortlist behind one `scan_market_research` read-only entry point.
- Finish user-invoked scanning with **SQLite watch persistence and interrupted-run recovery**: store last verified cutoff, reopen watches, identify time gaps, use qualified remote historical repair where possible, otherwise report `GAP_UNOBSERVED`.
- Provide one clear run command and outputs: shortlist (0–5), watches, near misses, coverage, source health, stale/unavailable methods, data/resource costs, reasoned uncertainties.
- Run contract, oracle, replay/synthetic, sampled-live, provider-failure, quota-exhaustion, causal-order and no-order side-effect integration tests; measure latency and network payload on the actual provider-qualified scope.
- Verify handoff/read-only isolation from current Freqtrade admin, bot config and DB; validate paper-lab boundaries.
- Begin timestamped prospective observation/benchmarking, comparing neutral and context-prioritized discovery at equal budgets.

**Exit gate:** a first complete, on-demand **read-only research release** works from a clean checkout with documented, honest capability limits; functional gaps and failed tests are not concealed. If a major quality gate fails, fix it with Sol before assigning cosmetic cleanup to Luna.

### Session 6 — Luna: Nontechnical usability, documented setup and final housekeeping

- Clean up only well-scoped CLI/config screens, docs, duplicate code, error messages, status commands and straightforward tests; do not re-architect provider semantics.
- Deliver a quick-start user procedure: **set/update keys → check provider status → run scan → view shortlist → resume later**.
- Add `config validate`, `provider status`, `scan now`, `show last results`, `show watches` commands or equivalent existing interface if available.
- Confirm `.env` and secrets are excluded from GitHub; no secrets in logs; runtime provider keys configurable under stable names regardless of whether running on Cloud, local Windows or an eventual hosting service.
- Confirm CI and documentation agree with actual behavior. Escalate unresolved source correctness, causal reasoning or architecture defects back to Sol.
- Push and verify final feature branch; open/update PR for user-approved review/merge.

**Exit gate:** a nontechnical operator can follow a small number of documented steps; the project is reproducible from its GitHub branch; all capability/quality limitations remain explicit. **Merge this into Session 5** if time and quality allow; do not create a Luna session solely to polish wording.

## 5. API-key management (minimum effort for the user)

- **One key configuration interface**, not provider-specific code edits. Use an optional command like `openbot setup-keys` that accepts a provider name and securely updates a local ignored `.env` file. Provide `.env.example` with **names only**, e.g. `OPENBOT_BASIS_TOKEN`, `OPENBOT_COINBEACON_KEY`, `OPENBOT_COINALYZE_KEY` as examples—not claims that every provider actually requires keys.
- For Codex Cloud tests, use the environment's supported credential/secret configuration and verify whether it is visible to the actual test runtime. Do not assume product-specific Cloud and Agents API secret behaviour are interchangeable.
- For services offering login/OAuth/MCP with no developer key, use their supported authentication flow instead of inventing API tokens.
- Public Binance research endpoints may not require API keys; only ask for credentials that are demonstrably required by an enabled capability.
- A key replacement must be **one settings edit/command, no code edit or GitHub commit**. Provider health/status must never print key values.
- Defer optional third-party key onboarding until its capability passes a cost/access/coverage review; avoid collecting credentials for services the product never uses.

## 6. Proposed minimal repository impact

**Inspect and reuse existing modules before adding files.** The following is a logical layout, not a forced rewrite:

```text
AGENTS.md                              # Short repo-wide development and research boundaries
.agents/skills/                       # Small, reusable research/review SKILL.md packages
researcher/                            # External-first Market Researcher (or reuse existing equivalent)
  discovery.py                         # One on-demand orchestrator
  adapters/                            # Binance, Basis, qualified specialist clients
  core/                                # Coverage, math, event ledger, context, hypotheses, ranking
  config/discovery_specs.yaml          # Method/family/measurement registry and trial parameters
  storage/                              # SQLite research state, ignored from GitHub
tests/                                 # Unit, provider contracts, oracle, integration, prospective
docs/implementation/PROGRESS.md        # Verified state and next tasks across sessions
.env.example                           # Placeholder names only; real .env ignored
```

**Functional separation:**

- **Provider adapters** make actual permitted remote calls (some via direct HTTP, some via qualified MCP); agent-accessible MCP tools **do not automatically become runtime Python tools**.
- **Deterministic code** handles calculations returned, timestamps, causal transitions, evidence reliability, coverage, quotas, persistence and shortlist rules.
- **`SKILL.md`** instructs Codex/compatible research agents in how to reason about the verified evidence; it is **not executable detector code**.
- **Optional reasoning agent** examines a small set of ambiguous candidates only when shown to add value; no swarm or per-coin LLM flood.
- **Deep Analyst** receives a read-only, traceable handoff, when actually available, with no implicit order permission.

## 7. Cross-session acceptance matrix (must not be sacrificed to compress sessions)

| Gate | Must demonstrate before claiming success |
|---|---|
| G0 Repo truth and Git | Correct real code base; relevant old PR reuse checked; branch and remote SHA proven; pushed changes tracked. |
| G1 External feasibility | At least one real permitted remote-computed core path; authentic quiet-tail test; formulas sampled against oracle; real quota/access evidence. |
| G2 Universe coverage | Exact eligible contracts; requested vs returned/evaluated failures; no invisible top-board bias or mystery truncation. |
| G3 Causal correctness | No future reference leakage; closed-bar and `known_at` integrity; event order, invalidation and stale/gap handling. |
| G4 Analytical honesty | All F1–F9/methods represented; actual remote/proxy/unsupported distinction; source units/venue correct. |
| G5 Market-context fairness | BTC/ETH influences research order but cannot veto an otherwise supported contrary alt case. |
| G6 Operational durability | Manual start/stop and later restart preserve watches; missed periods identified; provider outages degrade clearly. |
| G7 Safety boundary | No new orders, no execution/write API capability; limited handoff to separate Deep Analysis. |
| G8 Resource realism | Observed requests, bytes, quota consumption, latency and source cost recorded; no invented free-limit assumptions. |
| G9 Reproducibility | Clean checkout, documented key setup, automatic tests, pushed remote commit and expected outputs verified. |

### When to stop or split a session

- Split only when an unresolved dependency would make the remaining scope misleading or the task has grown beyond a reliable implementation-and-verification loop.
- A test failure is **work still to do in the same session** when feasible, not an automatic new-session request.
- A provider block is a **specific capability problem**: record the exact failing endpoint/operation, environment, status and effect; test an eligible external alternative; use Local Codex **only for the blocked development operation** when compliant.
- A source-specific limitation must not be relabeled as `complete`. A working lower-coverage release is valid only if coverage omissions are explicit and not mistaken for certified whole-market discovery.

## 8. Actual owner's workflow after implementation

**First time:** connect the approved runtime, set any needed provider keys once, run `provider status`, then invoke `scan now`.

**Whenever desired:** run the same command. The researcher checks the last scan, updates its stored watchlist, examines missed periods via supported remote history, flags unverifiable gaps, scans the current supported universe, and produces a new research shortlist. **No requirement to run continuously** for the initial on-demand release.

**Later optional:** enable approved scheduling only after confirmed API quotas, rights, state persistence and host availability. Running Codex Cloud development tasks is **not** the same as maintaining a production 24/7 trading-data process.

## 9. Required format of every session's final handoff

```text
OpenBot Market Researcher — Session [N]
Environment: CODEX_CLOUD | CODEX_LOCAL_EXCEPTION
Repo / target integration branch: ...
Started from remote SHA: ...
Final pushed remote SHA: ...
Changed / added: ...
Reused from old OpenBot: ...
Tests: passed / failed / not-run (exact reasons)
Provider capabilities: qualified / partial / blocked / untested
Coverage denominators: requested / evaluated / failed by timeframe and method
Known limitations and unchanged user boundaries: ...
Next dependency-ready task: ...
GitHub URL / PR / CI status: ...
```

## 10. The session-one instruction to use next

> **Implement Session 1 of `OpenBot_Cloud_First_GitHub_Synced_Implementation_Plan.md`, using `OpenBot_Final_External_First_Market_Discovery_Blueprint.md` as the design authority. Work in Codex Cloud with Sol. Start by fetching and verifying the latest relevant GitHub branch and older OpenBot implementations; do not assume the design-only default branch is the deployed Researcher. Reuse proven code/skills where applicable. Create a single protected feature-branch integration path, concise repository guidance and progress document, user-friendly central key configuration, a minimal read-only scaffold, and reproducible actual external provider/capability tests including authentic eligible quiet-tail contracts. Preserve external-first, BTC/ETH non-veto, all family/method registry obligations and no-trading-authority boundaries. Run tests, fix within this session, commit and push every completed increment, verify the remote SHA, and produce the exact handoff specified in Section 9. If a task is specifically blocked by the Cloud environment, record the failure and hand **only that operation** to Codex Local from the current pushed SHA; do not silently change the market-wide calculation architecture. Do not claim unverified providers or method semantics are functional.**

## 11. Source and policy references

- `OpenBot_Final_External_First_Market_Discovery_Blueprint.md` (13 Nov 2026), especially Sections 0, 2–4, 7–14, 16–17.
- `OpenBot_Two_Consultations_Independent_Comparison_and_Evidence_Audit.md` (13 Nov 2026) and the two source consultation archives.
- Official OpenAI guidance on repo-local skills / `AGENTS.md`: https://developers.openai.com/blog/skills-agents-sdk
- Official OpenAI guidance on compact skills and contextual repo instructions: https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
- Official OpenAI guidance on remote Codex worktrees and intended branch selection: https://developers.openai.com/blog/mastering-codex-remote-for-engineering

**Final decision:** Aim for **six sessions, compress to five only when quality gates are truly met, extend selectively when evidence requires it.** Every Cloud/Local transition passes through a verified GitHub push; no unverified code or unsupported research claim is silently promoted.
