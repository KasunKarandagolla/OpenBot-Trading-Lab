# Session 3 owner report

**Working native policy and account/position mechanics delivered; profitable edge and persistent paper qualification remain unproven.** Three additional sessions completed including this milestone; **two remain**.

## A. What now works

One deterministic controlled-pullback/failed-breakout policy family runs through the existing public scanner, signed shortlist, closed setup interpretation, frozen executable plan, cost/account admission, official Freqtrade lifecycle, independent report and sanitized OpenBot export. The final scan was **586 eligible →46 native candidates →18 shortlisted →five deep markets**. Genuine current flow captured **3,000 REST + 334 WebSocket prints**; historical flow remains UNKNOWN and historical profiles remain OHLCV_PROXY.

Native features include absolute leveraged stops, frozen entry/invalidation/targets, five-minute expiry, 8h continuation/4h reversal maximum holds, thesis exits, partial fills/reductions, cost breakeven, monotone structural/2ATR tightening, pending-order cancellation/replacement, duplicate protection and SQLite recovery. Native funding uses persisted event ownership and actual first-fill chronology. Source gaps inhibit entries while protective exits continue. No DCA, averaging down, agent administrative access or new exchange execution engine was introduced.

Equity-based sizing distinguishes cash, unrealized/realized net, collateral, margin and notional. It reserves pending entries and unresolved exits, caps aggregate/correlated exposure, checks current contract maintenance/liquidation clearance, and persists UTC MTM loss, peak drawdown and loss-streak state.

## B. What improved—and what did not

Five predeclared Gate survivors, August 5–November 2 UTC end exclusive, 1,000 USDT wallet, initial notional ≤25 USDT, max two positions, 0.075%/side native fees and actual source funding. These are **alternative portfolios, never additive returns**.

| Full chronological portfolio | Trades | Win rate | Native net USDT | +10 bp/side friction |
|---|---:|---:|---:|---:|
| TrendPullbackBaselineV1 | 453 | 30.02% | -12.41602122 | -33.32364095 |
| IntelligenceRegimeV2 | 8 | 50.00% | +0.58494245 | +0.20730497 |
| PolicyFixedV3 | 68 | 29.41% | +0.19192444 | -2.94951754 |
| PolicyManagedV3 | 68 | 29.41% | -0.35922343 | -3.50051591 |
| PolicyRetraceV3 | 68 | 19.12% | -1.40713072 | -4.56111766 |
| PolicyObjectiveV3 | 68 | 29.41% | +0.12197694 | -3.01939504 |

The old router admitted nine plans and filled eight; the new fixed reference admitted **78 plans and filled 68**, including **29 continuation fills (+1.88441790 native USDT)** and **39 reversal fills (−1.69249346)**. Continuation is now economically executable in the modeled funnel, whereas the earlier router admitted none. These recipe contributions belong to the combined portfolio; they are not separate continuation-only backtests.

Accuracy did not improve: fixed win rate **29.41%**, versus **30.02%** baseline and **50% on only eight** router fills. Fixed expectancy is **+0.00282242 native USDT/trade**, profit factor **1.0252**, and total netR **−1.6166**. Mean win/loss are **+0.38999063 /−0.15849767 USDT**. It does not beat the sparse router's net expectancy. Lower baseline losses also reflect lower exposure; they do not establish a superior scalable edge.

The 20 bp round-trip friction allowance corresponds to the +10 bp/side column. Native net already includes fees and source funding; the 38 bp admission allowance is not double-deducted. Even +1.5 bp/side turns the fixed portfolio negative (**−0.27929186 USDT**). Economic promotion is blocked.

The exact same68 native entries, partial/final orders and **−0.35922343 USDT** management result reproduce at 1x, 10x, 20x. Initial notional and risk remain constant; margin scales by leverage. Minimum modeled 20x stop/liquidation clearance is **2.3148% of entry price**, above the 1% policy floor, using current captured Gate tiers. This is a current-spec historical-price scenario, not proof of historical tiers, real liquidation safety or future fills.

## C. What failed and what the next experiment should resolve

The managed package reduced full-portfolio native net by **0.55114787 USDT**, with identical 68 entry keys and ten partial exits. Its apparent protection cut winners; automatic partial/BE/trailing is not selected. Objective-aware targets also worsened net. Retracement increased admitted plans but worsened expectancy and missed both filled fixed-reference opportunities in the one-minute cohort: fixed2 fills/+0.75844207 native USDT, retracement0. A touched coarse candle is not proof of a timely queued fill.

October remains negative: fixed 24/−0.56648621 versus router 3/−0.23436884. The target ceiling excludes the old XRP winner; meaningful-boundary qualification excludes both October 29 losing reversals. All three examples remain visible. The ceiling and boundary conditions are not universal winners. November 1 has zero new-policy fills. It was registered before the first Session 3 attempt, then replayed after engineering repairs; it is now inspected development, not untouched prospective evidence.

A concrete next hypothesis is continuation-versus-reversal suitability on newly registered dates, while retaining the mixed fixed reference and all exclusions. Reversal reacceptance and premature winner exits need evidence. Do not simply remove losing development cases or tune a new partial fraction against these same outcomes.

Engineering failures are retained: inherited baseline stop/ROI overrides, one-lot leverage conversion differences, the out-of-retention one-minute request, Docker VFS exhaustion, a native deferred import and a partial all-market leverage-tier response. Corrected comparisons use run 002 only. A five-market pre-outcome public tier snapshot supplies missing native tiers through the native parser with contract identity checks; nothing is invented. Original results and datasets are not overwritten.

## D. Best available integration reference

**PolicyFixedV3, controlled-pullback-failure-v3.0.0**, exact release/config/source fingerprints in `research/policy/release.json`. This is a transparent post-development reference selection, not an independent promotion. Native dry-run mechanics are validated by controlled fixtures and stopped startup; **economic status UNQUALIFIED, persistent_paper_allowed=false**. Default leverage 1x;10x/20x remain conditional supported scenarios. The generic equity-risk contract permits a 250 USDT ceiling, while all economic comparisons deliberately use 25 USDT.

The fixed reference combines signed selection, completed-hour trend/pullback or contextual boundary failure, bounded entry, logical stops, bounded3R/objective alternatives, deterministic exits and portfolio constraints. Qualified genuine flow and proxy profiles remain research context wherever historical execution control is unsupported.

## E. Remaining operational gaps

Session 4: actual isolated Director/Researcher/Risk Reviewer coordination using the final read-only files, fresh mark/source readiness on the owner host, and registration of further economic evidence. Session 5: owner-host operational/recovery acceptance and separately authorized prospective paper evidence. No persistent paper service, live/testnet/demo order or credential was used. No actual forward paper fill was observed. A stopped process cannot manage positions during an outage.

Historical membership, news, genuine flow, queue/depth, original receipt clocks and historical maintenance tiers remain unknown. Historical account marks use hourly open proxies; the finer replay resolves minutes, not intra-minute order/queue priority. **November 17–December 1 remains unacquired and unobserved.**

## F. Evidence and reproducibility

- **26 final native portfolios / 1,166 modeled trade records**; every Decimal order/fee/net calculation and independent source-funding bound reconciles. Funding has no positive-quantity event before actual entry.
- **176 tests: 174 pass, two original-private-backup identity checks explicitly skipped.** New source identities and mechanics are tested. The absent historical bundles are not replaced with fabricated originals.
- Native lookahead: eight qualifying signals, no detected bias, limit orders explicitly allowed. Recursive numeric differences round to0%; unsupported/dash cells are not passing evidence.
- Calendar analysis includes 47 zero-realization days in 89 days. Seven-day block95% native-net interval: **[−4.7543,+5.8346] USDT**, with development dependence remaining. Candidate trades occur on 41 entry days. Maximum filled hold480min; closed/hourly-proxy MTM drawdown3.19509235 USDT. Average entry-notional exposure is only 0.1686% of model equity.
- All **882 original evidence files** and all original strategy freezes are unchanged. Three backward-compatible wrappers changed among1,039 inspected parent files. Five of20 old source slices match byte-for-byte; other sources were honestly reacquired. The corrected baseline's161 October fills differ from the original 162; exact original-source replay is not claimed.
- Final reader: `policy-session3-002/openbot-release/`, schema-v1, bounded, hashed, with joined decision/trade/outcome IDs. The preregistered/pre-normalization readers are retained for audit and are not the integration target.

```bash
./scripts/lab-foundation.sh run policy-owner-001
# Verified recovery of an existing interrupted run:
./scripts/lab-foundation.sh resume policy-session3-002
# On this session's already-running disposable pinned runner:
LAB_FOUNDATION_CONTAINER=openbot-policy-session3 ./scripts/lab-foundation.sh resume policy-session3-002
```

The complete command includes all 26 portfolios, calculator scenarios, native fixtures, independent reporting and reader publication. Sources and native ZIPs are private, excluded from Git and delivered in the owner backup. See the runbook for restoration and rollback to parent913eec3. No merge is performed.

## G. Session budget

**Three of five additional sessions completed; two remain.**
