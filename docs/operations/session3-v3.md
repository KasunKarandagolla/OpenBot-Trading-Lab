# Session 3 — v3 intelligence and native historical research

The historical vertical slice is implemented. It uses authentic, locally checksum-reverified Binance USD-M archives. Economic qualification remains **UNQUALIFIED**; the breakout challenger is negative under the tested assumptions and the small positive reversal sum is cost-fragile. Native original-agent participation and live monitoring are not accepted. No trading or persistent paper process is activated.

## Exact tested command sequence

Run from this branch in WSL/Linux with Docker and the pinned chart-capable Python environment. The original owner-local environment used `/tmp/openbot-s3-venv/bin/python`; an isolated replacement needs `integrations/openbot/skills/v2/requirements.txt`. The engine image remains the unchanged Freqtrade 2026.10 digest below. Matplotlib runs in the separate chart environment.

```bash
export LAB_PY=/tmp/openbot-s3-venv/bin/python
bash scripts/lab-session3.sh skills check
# Fresh checkout only; supply the preserved local_recovery directory, not a credentials directory:
bash scripts/lab-session3.sh restore /path/to/preserved/local_recovery
bash scripts/lab-session3.sh prepare
bash scripts/lab-session3.sh test
bash scripts/lab-session3.sh experiments evidence/session3/owner-run-001
bash scripts/lab-session3.sh gate evidence/session3/owner-run-001/w1-retest/plans.json
bash scripts/lab-session3.sh native BreakoutAcceptanceRetest 2026-08-01 2026-08-08 /lab/evidence/session3/owner-breakout-001 /lab/evidence/session3/owner-run-001/w1-retest/plans.json through
bash scripts/lab-session3.sh native SweepReclaimReversal 2026-08-01 2026-08-08 /lab/evidence/session3/owner-reversal-001 /lab/evidence/session3/owner-run-001/w1-retest/plans.json through
bash scripts/lab-session3.sh verify evidence/session3/owner-breakout-001 evidence/session3/owner-reversal-001
```

For the complete 14-portfolio matrix with one fresh output root, the same tested components are joined by this owner command sequence:

```bash
bash scripts/lab-session3.sh experiments evidence/session3/owner-full-001/registered-final
bash scripts/lab-session3.sh matrix evidence/session3/owner-full-001
bash scripts/lab-session3.sh report evidence/session3/owner-full-001
```

`matrix --describe` prints the exact native command arrays without executing them. The matrix runs the unchanged engine with separate per-run scratch state, applies historical diagnostics, verifies all ledgers against source funding, and refuses existing result directories.

Skip `restore` and `prepare` when the verified native data are already present. Restore refuses an existing target. Use new output names for each research run; interrupted/completed backtests are preserved. The experiment command performs the broad scan, shortlist, immutable SQLite retention, chronological 5m monitoring, plan generation, backup/reopen checks and scanner/monitor equality check. It also registers the early-entry variants and second weekly window. Read its `monitor-receipt.json` for the dedicated Linux runtime directory. Native ZIP timestamps can differ on reproduction; compare frozen decisions, fill/exit records and economics rather than expecting a timestamped ZIP to be byte-identical.

For the full recorded comparison, use the two retest plan files with both mandatory strategies, the first week's `w1-immediate` with `BreakoutImmediate`, and `w1-early` with `SweepReclaimEarly`. Run the first retest cohort again with native mode `touch` for fill sensitivity. Controls are `TrendPullbackBaselineV1`, `VWAPTrendContinuationV1` and `LiquiditySweepReversalV1`, with no plan file argument. Each native command creates its own scratch directory. All runs use 1x, <=25 USDT initial notional, two slots and the same fee scenario. Each portfolio resets to a 1000-USDT virtual wallet.

## Inspect and reconcile a watch

```bash
export LAB_PY=/tmp/openbot-s3-venv/bin/python
export S3_STATE_ROOT=/tmp/openbot-v3-owner-watch
bash scripts/lab-session3.sh scan --at 2026-08-01T12:00Z --out work/owner-scan.json
bash scripts/lab-session3.sh watch --at 2026-08-01T12:00Z --out work/owner-watch.json
bash scripts/lab-session3.sh tick --at 2026-08-01T15:00Z
bash scripts/lab-session3.sh list
# Copy a setup_id from list:
bash scripts/lab-session3.sh history SETUP_ID
bash scripts/lab-session3.sh backup /tmp/owner-watch-backup.sqlite3
```

These are historical clocks. `tick` reconciles expiry without requiring a newer candle, validates previously observed bar hashes, and refuses a changed source/feature version, gap or backward clock. SQLite WAL uses a local Linux path; `/mnt` and symlink paths are rejected. The existing schema migrates to v3 without rewriting old setup/event rows. Legacy arbitrary raw-bar/hash observations remain blocked. `DISCOVERED`/`WATCH` correspond to developing hypotheses; `TRIGGER_CANDIDATE` is separate from a complete `RESEARCH_PROPOSAL`. Risk diagnostics remain a separate `RISK_QUALIFICATION` stage with `NO_ACTION` when native Risk/account evidence is absent.

## Source and time contract

- `panel-pins.json` binds all 600 archive coordinates, original public checksum receipts and source-inventory identity across 24 preselected symbols, May–September 2026. This is a credible convenience panel, not a historical listing census or fresh exchange authentication. All ZIP checksums were reverified locally; no new Binance HTTPS authentication is claimed.
- `native-data-pins.json` binds the 240 converted native/research Feather files; `native-metadata-pin.json` binds the later public exchange snapshot. Historical execution filters and account fee tiers remain unqualified. `legacy-test-fixture-pins.json` preserves two existing development fixtures needed by the inherited real-data tests; these are not new trading evidence.
- The registered windows are August 1–8 and August 8–15 UTC, end exclusive. They are previously studied development data. All four variants use the same June 22 feature origin and 40-day warmup before the first window. Complete raw source archives are still verified. The final 16 hours are purged from new setup arming to keep expiry/holding inside the window; frozen controls retain their native end-of-window behavior.
- Candle dates are opens. Decisions use completed 5m closes; native execution starts on the following executable row at that close time. HTF joins use completed-hour/4h availability. Strict 2L/2R pivots become known at the second right-hand bar's close, never at the pivot extreme.
- Source receipt time is the later archive acquisition time. Historical theoretical candle availability is not a claim of contemporaneous human or HTTP receipt. Future price paths are not fed back into frozen decisions.

## Executable policy and interpretation

`playbooks.py` is the shared causal state/plan kernel; the scanner, persistent monitor and native plan adapters use it. The existing historical Binance `cheap_frame`, archive converter, strict structure implementation, chart renderer and Freqtrade lifecycle are reused. There is one watchlist store and no new exchange simulator or daemon.

The screen separates 4h/1h direction and structure, balance/transition, volatility, published quote activity, participation, BTC context, proximity and obstacles. It retains developing long/short hypotheses without requiring a current trigger. All 24 population rows remain available; attention is focused on four markets by declared proximity/activity rules. The population audit records holds outside that budget and genuine `NO_QUALIFIED_SETUP` location reasons. Unselected geometry-admissible candidates are potential missed research proposals; their outcomes were not natively executed or called missed winners.

`BreakoutAcceptanceRetest` requires a pre-known boundary, two later completed closes accepting outside, then a later retest/defense with participation. `BreakoutImmediate` compares execution after acceptance. `SweepReclaimReversal` requires a known boundary, bounded excursion and completed reclaim, then a later confirmation away from the boundary; `SweepReclaimEarly` compares entry after the reclaim. Fresh opposing HTF impulse is a contradiction, not a wick-based story. HTF support/resistance reactions route context and hypotheses; no separate native HTF-reaction strategy is claimed.

Stops sit outside structural invalidation with a 0.15 ATR1h buffer; stop fractions must stay between .0025 and .025. The first still-active relevant-side 1h/4h pivot or declared range obstacle caps the objective, with a .05 ATR1h buffer. A completed close consumes a pivot's old role; role flips require a new hypothesis. Targets farther than 6 ATR1h are rejected. After-cost R:R must be >=1.25 using the registered .0033 admission allowance. No structural stop is pulled into noise to force admission.

Orders expire after five minutes, with .0015 maximum deviation from the signal reference. The native full-exit model holds at most eight hours for breakout and four for reversal, with declared no-progress and two-close thesis-invalidity exits. Protective stops are separate. Partials, breakeven and trailing are off. Native candle touch/one-tick-through assumptions do not prove queue position, real spread, impact or partial fills. Kline participation is not trade-print CVD, footprint or genuine volume-at-price.

## Skills, native agents and live limitations

Load the exact owner pack with `bash scripts/lab-session3.sh skills bootstrap --agent trading-lab-market-researcher`. There are 27 separate assignments, nine skill IDs, 55 restored original members, both complete 15-member Vision packages, and 54 added owner-owned current-contract/reasoning references. The section-level concept matrix maps 441 original spans and explains operational corrections. All v3 references and hashes resolve; all 27 frontmatter validators pass.

The bootstrap prints checked load paths; it does not install or inject into OpenBot. Independent Codex source-only reviews cover the old sealed cases plus four new developing/trigger cases; B04 is explicitly excluded from baseline-blind counts after accidental baseline exposure. Four new proposals were independently derived without opening plans or outcomes. Local Codex inspected genuine cutoff chart pixels. None of these are original OpenBot messages, Vision receipts or independent native Risk votes.

The installed documented CLI requires Local scripts URL/token markers; both remain absent. Token contents were never read, no native task was sent and no native attachment receipt exists. No separate supported OpenBot connector was available. Owner unblockers are a supported original-role native listener/attachment route and a properly contained read-only research export. Profile/model/permission changes and persistent skill installation were not performed.

`refresh` invokes the existing public Binance scanner and clock checks. The observed attempt failed on DNS/TLS networking. Live watchlist admission remains fail-closed; fresh capture and incremental live reconciliation have not been accepted. No current market, 24/7 monitoring or live operational claim is made.

## Evidence, safety and Session 4

See [results](../../evidence/session3/README.md), [native economics](../../evidence/session3/ECONOMICS.md), [four review perspectives](../../evidence/session3/REVIEWS.md), and [frozen protocol](../../research/session3_v3/protocol.json).

The engine is `freqtradeorg/freqtrade@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7`, run with no network, no published ports, no host secrets or Docker socket, a read-only checkout and writable clone-local data/evidence. New strategies refuse every mode except offline BACKTEST with `dry_run=true`. Original strategies/configs are byte-identical to the verified base. No signed exchange request, order, admin API, permanent skill install or paper service was started. Original OpenBot host permissions are not asserted to be isolated merely by role labels.

The old Gate/synthetic-first/one-challenger/five-session design wording is historical and superseded by the owner's Binance multi-playbook mandate; causality, risk, privacy and independent-veto protections remain. Existing source rights/terms continue to apply; no commercial data rights or subscriptions are claimed.

Rollback selects the verified base commit `6225d925851e3373002d7b5a06a6949d80cbda12` and its load cards. Preserve runtime backups separately; no installed v3 state needs rollback. Session 4 starts with runnable, source-frozen multi-playbook experiments and untouched controls. Its work is expanded economic qualification and operator/native-access acceptance, including live incremental validation after networking is restored. Do not promote the small positive weekly reversal result into paper activation.
