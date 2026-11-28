Historical acceptance record. The later owner-originated native handoff failure
and its engineering recovery are documented in
[FINAL_NATIVE_ORCHESTRATION_E2E_TRACE.md](FINAL_NATIVE_ORCHESTRATION_E2E_TRACE.md).
Current recovery live acceptance is NOT_RUN_IN_CODEX_CLOUD; use the
[one-message acceptance procedure](FINAL_OPENBOT_LIVE_ACCEPTANCE.md).
The original observations below remain unchanged.

---

# Final functional acceptance — 15 November 2026

Verdict: **USABLE_RESEARCH_SHORTLISTING**, with disclosed source/method and latency limits. Read-only on demand; every conditional candidate has `trade_authorization=false`. Strict READY, source certificates and trading permissions are unchanged. This is neither all-method production qualification nor a profitability result.

The starting fetched/verified integration head was `6af2e8db8016688e78878baf4950c7d2c5b710cc`; PR #24 remains draft and main is unchanged. Final SHA equality and exact-head CI are verified in the delivery handoff. No unrelated local changes existed at start.

## Ordinary operator flow

Run from this repository checkout. No Python/config edits or keys are required for its enabled public sources. Each output name must be new.

```bash
python3 -m researcher config validate
python3 -m researcher scan now --output work/my-research-001.json
python3 -m researcher show results
python3 -m researcher show watches
python3 -m researcher show coverage
```

`show` defaults to a short readable view; append `--json` for exact per-coin/timeframe evidence, omissions and method coverage. `--db work/example.sqlite` selects an isolated research ledger for both scan and show. The report states its as-of time. Reference expiry is separate from point-price freshness: prices/spreads require a new scan after their 30-second source window. Closed evidence, source ages, next discriminators and unchanged structure caches remain separately timestamped.

For optional native reasoning, use the existing Local path-only audit setup already verified in this checkout:

```bash
python3 -m researcher scan now --native-review-dir work/my-native-001 \
  --native-audit-config work/session6c/native-audit-local.json \
  --native-max-cards 2 --native-wait-seconds 600 \
  --output work/my-native-001.json
```

When the console prints the generated `.prompt.txt`, paste its exact text once into a fresh chat under the existing **Trading Lab Market Researcher**. Keep its configured `opencode/deepseek-v4.1-flash-free`, skill and permissions; Local Scripts remains off. The scanner never invokes a replacement model/agent. It waits visibly, audits the matching app/provider turn read-only and imports only a timely valid reply. The private path-only audit config/native receipts are intentionally absent from Git; an installation move requires its existing operator setup, not credentials or code edits.

Missing, expired, invalid, wrong-model or unaudited advice retains deterministic results. Advice may change a research question/order or defer an eligible thesis, while source, chronology, economics, strict admission and trading gates retain authority. Repeating an unchanged material does not cause a hidden model call.

## Operating defects and changes

| Area | Before | Final behavior |
|---|---|---|
| Source as-of | Frozen start cutoffs could reject every later precomputed bar | First valid closed remote partition freezes the snapshot once after setup; later/future rows cannot advance it. Restart anchor cannot regress behind a prior snapshot. No unsupported historical Basis query is invented. |
| Broad allocation | First timeframe and optional work could consume all useful budget | Per-pack source slices and rotating turnover-quartile order preserve both timeframes and quiet tails; every skipped coin remains deferred. Valid partitions survive busy/empty202/transport faults. |
| Investigation | Two protected audit slots could be mistaken for the whole capacity | Up to 18 extra operational alts; actual capacity responds to observed history cost. Context delays reserve independent-alt capacity. No BTC-side veto or compulsory positive count. |
| Method execution | Duplicate reducers; F7 could select an old episode; M16 could use an unrelated empty balance | Reuse immutable validation/time/ID and shared break/zone calculations. Current F7 episodes and the actual measured F6 balance feed sourceable M16/M20 work. Specialist and canonical gaps remain explicit. |
| Candidate quality | MET/F5 had only a reclaim; ESPORTS/WIF retained the old shock direction through recovery | F5 conditional research needs an observed failed-reversal rebreak. Adverse F9 recovery cannot support the old direction; unchanged stabilization cannot recycle an old event into fresh evidence. |
| Native relevance | Watch-stage/hash sorting could select convenient non-finalists | Same-source provisional finalists precede protected exception/rival cards. Real ACE F8 review linked directly to that run’s final conditional candidate; F9 remained deferred despite model INVESTIGATE advice. |
| Watches | References and active coins could be conflated; warm decode could shrink to exported finalists | Unique current coin attention, deduplicated cross-timeframe zones and separate archive. Warm reprice retains all active coins. Recovery against a shock stays nondirectional observation. |
| Room/economics | Mutable export aliases invalidated hashes; a missing nearest old source could favor a farther level | Exports deep-freeze nested values. Retain known eligible obstacle metadata, preserve identity quarantine and mark nearest-source loss ROOM_UNKNOWN. Fees/future depth/slippage remain scenarios/gaps. |
| Latency/usability | 19-minute combined run, giant JSON views and hidden waiting | Timed stages and explicit owner/native wait; readable actual candidates/watches/coverage; UTF-8 output, valid saved Decimal formatting and code-hash cache invalidation. |

## Genuine live runs — UTC

Counts below are unique coins unless a timeframe is explicit. D/E/G are separate live source snapshots. F/H are real warm repeats; their retained structural analysis is reused, not recomputed live. Exploratory A/B and failed inventory C remain separately recorded.

| Run | 15m / 1h cutoffs | Accepted/requested 15m; 1h | Investigated alts | Active coins | Conditional / READY | HTTP / bytes | Market seconds; native wait/import |
|---|---|---|---:|---:|---|---|---|
| live-d-native | 09:00 / 09:00 | 200/200; 150/150 | 2 | 4 | 1 / 0 | 35 / 3,746,514 | 615.1; 362.5 |
| live-e-restart | 09:15 / 09:00 | 450/450; 400/400 | 20 | 21 | 5 / 0 | 90 / 6,356,284 | 349.4; 0.0 |
| live-f-warm | 09:15 / 09:00 | 450/450; 400/400 | 20 reused | 21 | 5 / 0 | 9 / 1,831,930 | 49.1; 0.0 |
| live-g-delivery | 09:45 / 09:00 | 519/519; 519/519 | 20 | 21 | 5 / 0 | 93 / 6,536,742 | 311.9; 0.0 |
| live-h-warm | 09:45 / 09:00 | 519/519; 519/519 | 20 reused | 21 | 5 / 0 | 9 / 1,831,474 | 25.1; 0.0 |

Final G: 519/519 source rows on each timeframe, 20 investigated alts, 21 active coins, five conditional names and zero READY. It crosses no promise of complete methods or source sustainability. Earlier D had valid 200/519 15m and 150/519 1h rows; E had 450/519 and 400/519. Their other coins were deferred, not false negatives or request failures. Accepted partitions continued into complete bounded investigation despite those gaps.

G’s source/analysis time was **311.856 seconds (5.2 minutes)**; H was **25.065 seconds**, nine public HTTP requests, zero Basis/history/model requests and all 21 active coins preserved. The approximately-five-minute target is approached, not a guaranteed SLA. D’s poor connection required 615.1 market seconds plus 362.5 owner/native wait/import seconds. Windows and WSL both observed transient official-route timeouts; no route/location restriction was bypassed.

G breakdown: inventory/context 23.658s; Basis handshake/plan 2.208s; broad/causal batches 183.880s; nomination/context/selected history 36.101s; structures/methods/questions/current-source refresh 62.979s; final review/export/report 3.028s. Persistence is measured in each run receipt. The final five-name report renders in 0.00032s and writes 5,594 UTF-8 bytes in 0.0062s; operator watch/coverage render receipts are separate. These are measured file-render costs, not a UI network benchmark. D native request preparation was 0.075s; request-to-native-start owner delay 215.116s; actual native trace 147.105s. Combined wait includes polling/import; its small residual is not mislabeled as market calculation. Peak RSS, charged quota and sustainable cadence remain unknown.

G implementation fingerprint: `319c489fdc428e695219c2bd114b117fb0442abf3c7d4f92bc7c9155486c907c`. It matches the final researcher source files; docs/tests do not alter that fingerprint. A changed analyzer revision invalidates a same-cutoff cache.

### Complete final coin funnel

| Stage | Count |
|---|---:|
| active_watch_unique_coins | 21 |
| cheap_source_observed_unique | 519 |
| closed_remote_observed_unique | 519 |
| conditional_unique_coins | 5 |
| eligible_considered | 519 |
| inventory_seen | 946 |
| investigated_unique_alts | 20 |
| native_review_cards | 0 |
| native_review_unique_coins | 0 |
| nominated_unique_alts | 488 |
| strict_ready | 0 |

Nominee coin dispositions: `{'DEFERRED_BUDGET': 468, 'INVESTIGATED': 22}`. Per-timeframe dispositions are separately stored and never summed into a coin total. Full requested/returned/accepted/absent/deferred/rejected/unsupported membership is available via `show coverage --json` and the saved report. Retained deferred nominees can be reconsidered on the next on-demand run.

All five final G candidates are bullish while the same-source BTC/ETH 1h and 4h context is TREND_DOWN. This is an actual contrary-context path, not a simulated exception or a BTC veto. Turnover quartiles are interleaved before source time limits; zero coins are excluded for liquidity rank.

## Independently checked candidate quality

Every final G candidate has matching raw venue bar IDs, causal timestamps, independent method arithmetic and the nearest same-coin obstacle checked across selected 15m/1h metadata. See `delivery-five-audit.json` for exact card IDs, quotes, levels, numerical checks and source hashes. These are later retrievals at the original frozen endTime, never replay presented as live.

| Coin / family | Observed case and remaining discriminator |
|---|---|
| #1 GUNUSDT / F8 | PERSISTENT_RESIDUAL_AT_LOCAL_DECISION; source price 0.0015275; first obstacle 0.0015800 (343.7 bps gross research room). Common beta/sector noise; residual persistence has no demonstrated statistical significance or profitability. |
| #2 ATOMUSDT / F8 | PERSISTENT_RESIDUAL_AT_LOCAL_DECISION; source price 1.2995; first obstacle 1.304 (34.6 bps gross research room). Common beta/sector noise; residual persistence has no demonstrated statistical significance or profitability. |
| #3 HUMAUSDT / F8 | PERSISTENT_RESIDUAL_AT_LOCAL_DECISION; source price 0.0067430; first obstacle 0.0069900 (366.3 bps gross research room). Common beta/sector noise; residual persistence has no demonstrated statistical significance or profitability. |
| #4 MMTUSDT / F5 | OPPOSING_REVERSAL_ATTEMPT → REVERSAL_FAILED_REBREAK_SAME_REFERENCE → LATER_OUTSIDE_ACCEPTANCE; source price 0.1024500; first obstacle 0.1046000 (209.9 bps gross research room). F4 can revive on a new reclaim; failed-reversal rebreak and later closed-bar outside acceptance are observed, while renewed retention and execution economics remain questions. |
| #5 KATUSDT / F8 | PERSISTENT_RESIDUAL_AT_LOCAL_DECISION; source price 0.0029685; first obstacle 0.0030760 (362.1 bps gross research room). Common beta/sector noise; residual persistence has no demonstrated statistical significance or profitability. |

Ranking is an explicit research heuristic: observed room, current decision proximity and source age, with valid native question priority when available. It is not a calibrated success probability. The source IDs, real price/zone distances, rival, falsifier and next fact are retained. Account fee tier, future relevant-price liquidity, fills/slippage/funding and future price arrival remain unresolved; no conditional name becomes an executable trade.

The E-run cohort KITE/F4, GUN/F8, HEMI/F8, USELESS/F5 and OP/F3 is also fully audited in `fresh-five-audit.json`. KITE had same-bar wick/reclaim, with later initiative still missing; OP had quiet-before-displacement, with later retention missing; USELESS had an actual reclaim → opposing attempt → same-reference rebreak, while later acceptance and a renewed F4 reclaim remained questions. Current price reentry is observable risk, not proof of an unobserved completed candle.

The original Recovery five were checked without changing their snapshots. UNI/AAVE residual arithmetic matches independent regression and supports only conditional relative research with beta/sector-noise rivals. MET/F5 had no opposing reversal attempt or failed-reversal rebreak and should remain a reclaim watch. ESPORTS/WIF shock ratios match, but their frozen closes show adverse midpoint recovery: the old directional conditional rank was not justified. The original retained export’s internal hash mismatch is disclosed; forensic reading is not a repaired operational import. New export hashes and warm decoding pass.

Additional authentic as-of examples cover F1/BROCCOLI continuation maturity, F2/EGLD early approach, F6/EGLD measured balance, and F7/EGLD repricing invalidation plus BROCCOLI prior-value-reached lateness. Their raw IDs and Q/V/geometry match; late/invalid states remain excluded. No future diagnostic outcomes, wins, recall or profitability were adjudicated.

## Native reasoning receipt and control

Exactly one owner submission in the unchanged existing Researcher produced one audited app turn and **three provider assistant attempts**, 09:14:22.122–09:16:49.227Z. Complete current skill/request reads were independently verified; two cards/citations validated; zero unauthorized operations. Request material `3589ff785010fc0df3c31bc6505cefe319a3ebc56c873dfce8036360f7ad52f8`, skill `96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb`. Full private native receipts remain ignored.

ACE F8 was the actual final conditional candidate in that same D run. The model returned WATCH, COMMON_BETA and SOURCE_GAP; the current final card received that discriminator. Its same-coin F9 rival received INVESTIGATE / RECOVERY / FIRST_OBSTACLE, but deterministic `NO_RECENT_STRUCTURAL_EVENT` still deferred it. Matched-source control and native-assisted membership were identical. The review challenged source completeness, common-beta and recovery/first-obstacle interpretation; no ranking or performance improvement is claimed. Later E/G cohorts are different live snapshots and were not falsely labeled native-reviewed.

## F1–F9 / M01–M31 execution and residual matrix

The numbers below count selected symbol/timeframe algorithm evaluations, including BTC/ETH, in G. They do not certify full formations, the entire eligible universe or empirical usefulness. All inherited production/source gates remain closed where previously unqualified. Independent numerical/chronology checks are separated in the linked evidence.

| ID | Selected 15m / 1h | Executable path / qualification boundary |
|---|---|---|
| F1 | 22 / 22 | researcher.family_engine.continuation; selected price hypotheses, with pre-known balance/anchor requirements and actual no-event/source-unknown states retained. |
| F2 | 22 / 22 | researcher.family_engine.boundary_family; selected price hypotheses, with pre-known balance/anchor requirements and actual no-event/source-unknown states retained. |
| F3 | 22 / 22 | researcher.family_engine.compression_family; selected price hypotheses, with pre-known balance/anchor requirements and actual no-event/source-unknown states retained. |
| F4 | 22 / 22 | researcher.family_engine.boundary_family; selected price hypotheses, with pre-known balance/anchor requirements and actual no-event/source-unknown states retained. |
| F5 | 22 / 22 | researcher.family_engine.boundary_family; selected price hypotheses, with pre-known balance/anchor requirements and actual no-event/source-unknown states retained. |
| F6 | 1 / 1 | researcher.family_engine.boundary_family/balance_references; selected price hypotheses, with pre-known balance/anchor requirements and actual no-event/source-unknown states retained. |
| F7 | 1 / 1 | researcher.family_engine.value_reversion; selected price hypotheses, with pre-known balance/anchor requirements and actual no-event/source-unknown states retained. |
| F8 | 22 / 22 | researcher.family_engine.relative_family; selected price hypotheses, with pre-known balance/anchor requirements and actual no-event/source-unknown states retained. |
| F9 | 22 / 22 | researcher.family_engine.shock_family; selected price hypotheses, with pre-known balance/anchor requirements and actual no-event/source-unknown states retained. |
| M01 | 22 / 22 | numerics.confirmed_swings/swing_ladder; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M02 | 22 / 22 | method_engine.evaluate_methods/swing_breaks; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M03 | 22 / 22 | method_engine.evaluate_methods/order_blocks; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M04 | 22 / 22 | structures.equal_level_references; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M05 | 22 / 22 | family_engine.boundary_family; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M06 | 22 / 22 | method_engine.order_blocks; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M07 | 22 / 22 | method_engine.zone_lifecycle; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M08 | 22 / 22 | structures.gap_lifecycle; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M09 | 22 / 22 | structures.gap_lifecycle; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M10 | 22 / 22 | method_engine.zone_lifecycle; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M11 | 22 / 22 | method_engine.ote; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M12 | 22 / 22 | method_engine.crt; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M13 | 22 / 0 | method_engine.amd; Declared 00:00-08:00 UTC experimental 15m variant; no canonical all-timeframe AMD claim |
| M14 | 0 / 0 | method_engine.timed_subclass; Canonical primary definitions absent |
| M15 | 0 / 0 | None; Canonical primary definitions absent |
| M16 | 22 / 22 | method_engine.auction; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M17 | 0 / 0 | specialists.true_profile; Complete executed price-bin profile/nodes and revisit coverage absent |
| M18 | 0 / 0 | specialists.profile_nodes/first_profile_revisit; Complete executed price-bin profile/nodes and revisit coverage absent |
| M19 | 22 / 22 | numerics.anchored_value; Complete-session whole-bar Q/V; no executed weighted variance |
| M20 | 22 / 0 | measurements.value_extension/family_engine.value_reversion; Declared >=17 session bars; current 1h UTC session too short, 15m executes |
| M21 | 22 / 22 | measurements.flow_divergence/specialists.trade_delta; Actual kline aggressor volumes; bar delta/CVD, not footprint |
| M22 | 0 / 0 | specialists.footprint; Complete executed footprint/comparable attempts unavailable |
| M23 | 0 / 0 | specialists.aggression_attempts; Complete executed footprint/comparable attempts unavailable |
| M24 | 0 / 0 | specialists.aggression_attempts; Complete executed footprint/comparable attempts unavailable |
| M25 | 8 / 8 | method_engine.depth_walls; Current displayed snapshots only; no persistent walls or executed absorption |
| M26 | 0 / 0 | measurements.oi_decomposition; Aggregate OI observed; aligned multiplier/mark decomposition and position direction not qualified |
| M27 | 0 / 0 | measurements.funding_basis; Premium observations do not qualify actual funding kind/interval/settled carry |
| M28 | 0 / 0 | specialists.liquidations; No witnessed complete forced-execution feed |
| M29 | 22 / 22 | measurements.persistent_residual/sector_strength; Aligned price branch executes; dated exact-perp sectors absent |
| M30 | 22 / 22 | numerics.compression/context.build_context; Selected closed OHLCQV price path; source-backed trial, full-method production qualification and empirical usefulness remain unproved. |
| M31 | 0 / 0 | measurements.catalyst; No verified original-publisher catalyst feed |

## Reliability, tests and integrity

Inherited tests are retained; the JSON CLI test now requests its explicit `--json` contract and also checks the readable default. Focused regressions cover first-response freeze and later boundary rejection, future source bars, stale-provider restart regression, per-pack fairness, missing eligible IDs, partial busy/empty202/transport, changed analyzer cache revision, nearest missing obstacle versus farther target, quote expiry through slow depth, absent current prices, premature F5, adverse/recycled F9, cross-timeframe deduplication, distant watches, missing fee/depth/room, native invalid/timeout/late handling, immutable export nesting and saved UTF-8/Decimal views. Observational-gap tests are labeled simulations; real D→E→G restarts are distinct live observations.

The final local full suite passed **390 tests in 782.427s**; earlier full runs of 381 and 386 also passed. Exact-head GitHub CI is observed before final delivery. All 372 inherited tests remain; eighteen new focused operating regressions pass on final code, as do the scoped native collector checks and configuration/reference hash validation. Final counts/durations and log hashes are in the verification receipt and delivery handoff. The earlier 372-test in-session run exposed the intentionally changed show-default contract; the test was updated to preserve JSON parsing under `--json`, not removed or weakened.

Immutable blueprint SHA256 `cf7a58fd9ed5f5d1010673406c26a405c8112b907216a47f88a9ebee1bd3d45c`; plan `245591eea0f92cd185c51db3420043031c11c1d941f91ecdb31fd64a34e0c232`. All 27 measurements, nine families and 31 methods remain. No orders, scheduling, trading credentials, Freqtrade config/database access, other subagents or Deep Analyst implementation. No profile/model/permission changes.

Evidence: [final acceptance receipts](../../evidence/external-first/final-acceptance-20261115/README.md). Missing true profile/footprint/executed absorption/liquidation, dated sectors, catalysts and canonical M14/M15 definitions remain precise source/definition limits. No owner action remains for this completed acceptance; future optional native calls require the documented one-prompt app handoff.
