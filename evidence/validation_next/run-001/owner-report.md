# Fresh-history trading validation — no promotion

Research date: November4,2026 UTC. Parent: PR14 `ccb2f4adb8d11605d8d33156f86acc769ba68e39`; parent PR13 `ade410ec625be51f8dbcb7194b98965d8286daf7`. Branch: `codex/fresh-market-validation`. **Personal, non-production historical research only.**

## Executive summary

We obtained four months of real Binance USD-M history for BTC,ETH,XRP,DOGE and ran **27 corrected native Freqtrade portfolios**, independently reconciling **579 overlapping trade records**. These are alternative portfolios and repeated execution sensitivities, not579 independent trades. One predeclared target hypothesis changed four plans across development/validation and **no filled-trade outcomes**. It provides no measured economic improvement.

The transferred V4 logic lost **1.720899USDT** in development and **0.440407USDT** in validation. April's single-use holdout made **0.279531USDT on seven fills**, but falls to **−0.066347USDT** with an extra10bp per side on the same fills. Its descriptive weekly-block interval includes zero. This does **not** establish a reliable positive edge or realistic income.

**Verdict: PARTIAL_COST_MODEL / INSUFFICIENT_ECONOMIC_VALIDATION for every method.** Binance's metadata API returned451, so the offline experiment uses a clearly identified public CCXT test fixture for Binance contract steps/minimums and generic fees. That fixture is not verified historical exchange metadata. Exact settlement marks, queue priority and spreads remain unknown. Gate's old profits are separately source-sealed; they are not compared as equivalent Binance dollars.

Engineering outcomes are useful: genuine5m execution detail, exact archived funding-clock preservation, auditable trade contracts, corrected net-RR diagnostics, native cancellation observations, all-opportunity economics and one-use chronological evaluation. All **4,210 prior files remain unchanged**. Eleven new tests pass; the broader153-check suite is **136 passes,15 errors,2 skips**, with no assertion failures. Errors are two inherited safety registrations and13 missing prior private-input prerequisites; no old seal was weakened.

## Native results at base cost

All times below are UTC and window ends are exclusive. Each cell is `fills / net USDT`. Wallet1,000USDT,1x,25USDT initial notional cap, maximum two positions, no DCA or widening, base5bp/side plus actual archive funding valued with preceding hourly mark OPEN. All listed results use identical15m decisions with genuine5m execution detail.

| Frozen method | Jan11–Mar1 development | Mar2–Apr1 validation | Apr2–May1 final holdout |
|---|---:|---:|---:|
| v4-transfer | 32 fills / -1.720899 | 15 fills / -0.440407 | 7 fills / +0.279531 |
| passive-transfer | 27 fills / -1.945252 | 14 fills / -0.188263 | 6 fills / -0.220324 |
| structural-transfer | 32 fills / -1.670818 | 15 fills / -0.440407 | 7 fills / +0.279531 |
| thesis-compatible-transfer | 32 fills / -1.489468 | 15 fills / -0.440407 | 7 fills / +0.279531 |
| continuation-only-diagnostic | 22 fills / -2.382481 | 12 fills / -0.015394 | 6 fills / -0.066516 |
| parent-target | 32 fills / -1.720899 | 15 fills / -0.440407 | 7 fills / +0.279531 |

No-trade earns zero in all three blocks. These small positive/negative amounts reflect intentionally limited exposure; they do not establish low risk at larger sizes.

## 1. What new market history was obtained?

Official Binance Vision USD-M monthly archives, **Jan1–May1,2026**, four preselected long-existing perpetual contracts. **80 ZIPs**, each verified against its official checksum, total **9,210,638 compressed bytes**. Actual candles: **46,08015m / 11,5201h / 138,2405m**, plus hourly mark candles and source funding events. Source URLs, contract IDs, millisecond clocks, close conventions, SHA256s, gaps, duplicates and bad-tick checks are in [data-manifest.json](data-manifest.json). All candle series are complete. Candle taker-buy fields exist in the source but were not tested as a predictive signal; no executed-volume profile or L2 claim is made.

The earlier Gate15m request was already documented as unavailable beyond10,000 candles; it was not repeated. A bounded Gate1h probe succeeded, but prior work had already inspected a different hourly momentum model, so it was not substituted for the requested15m V4 experiment. Binance archives, funding and mark data succeeded. Binance exchangeInfo returned451; no bypass or account access was attempted. [Feasibility evidence](data-feasibility.json).

Partitions were registered before strategy outcomes: development Jan11–Mar1(49days), validation Mar2–Apr1(30days), final Apr2–May1(29days). Indicator warmup precedes scoring. Shared24h gaps exceed the8h maximum hold plus order lifetime; plans whose full horizon exceeds a block end are purged. The final block's features/plans were not generated until the code/input freeze and exclusive one-use opening. This was untouched **within the checked repository/session**; unseen research outside this repository cannot be established. The reserved future Gate Nov17–Dec1 period was not accessed.

## 2. What defects were fixed?

- **Native funding clock:** the pinned data handler floors funding timestamps to seconds. Independent archive-event comparison caught the mismatch. The isolated adapter restores actual source millisecond clocks before backtesting; all rates remain real and each event is charged once. Twenty earlier result records without `-exactclock` remain preserved and excluded from final economics. Some initial development console filenames were reused during repair; those overwritten stdout streams are not claimed retained. All original invalid native ZIP/config/result/order/state artifacts and the exact pre-repair runner source remain preserved in the invalid-run index.
- **Trade-contract diagnostics:** passive repricing leaves the inherited stored `after_cost_rr` stale in47/19/15 plans. The new audit recomputes risk, reward and net RR from actual plan prices, distinguishes a barrier from a target, deduplicates price levels and checks clocks, sides, horizon and expiry. The38bp allowance is an admission reserve, never an extra cash fee. Existing native admission already recomputed geometry; this diagnostic correction alone cannot create profit.
- **Input integration:** funding filename convention and the native end-boundary dataframe row were corrected before successful portfolios. No future signal or price path was invented.

The single new causal rule reuses a preknown previous UTC day/8h-session opposing objective between2R and3R, with unchanged net-RR and6ATR guards; otherwise it retains3R. It preserves entry, stop, rank and exit authority. It changed two development plans and two validation plans, none in holdout, and changed no realized exit. **Logical audit capability is delivered; target superiority is not demonstrated.** See [trade-contract audit](trade-contract-audit.json), [compact contracts](compact-trade-contracts.json), [protocol](../../../research/validation_next/protocol.json) and [technical corrections](technical-corrections.json).

## 3. Which original methods were evaluated?

V4, passive0.15ATR, original structural exit and PR14 compatibility guard were transferred unchanged in rule meaning to the separate Binance fixture scenario. Continuation-only remains an explicitly post-hoc **diagnostic** inherited from Gate research. The new parent-target rule is isolated, not combined with a new entry/selection rule. Genuine5m here changes execution resolution only.

PR12, relaxed EMA/context, qualified-only ranking, integrated first-obstacle admission and genuine5m entry rules retain their original source-sealed Gate evidence. They were **not** newly economically validated on Binance. Reimplementing every strategy or relaxing admission to force fills was outside this prioritized experiment. No new selector or entry classifier had sufficient causal evidence to justify another hypothesis; the failed body/RVOL switch was not recycled.

Original sealed Gate development benchmarks remain: V4 45/+3.473272; passive36/+1.257884; structural45/+2.668069; relaxed61/−0.730953; integrated0/0; conditional42/+1.953465; corrected30m expiry38/+1.661944; compatibility45/+3.100606; qualified-only rank129/−0.866186; continuation-only40/+4.094245. PR12's14/−0.246954 is also preserved. They are **development figures, not independent validation**. The old native engine source SHA matches the installed engine, and all22 source seals/578 evidence seals verify: [control verification](frozen-control-verification.json). Old private Gate input bundles were absent, so no new reproduction of those original portfolios is claimed.

## 4. What happened to entries?

Development passive has26 shared V4 fills, whose net improves **+0.600062USDT**. It misses6 V4 fills that had earned **+1.145539USDT**, while also changing portfolio access/capacity for extra fills. On holdout it has5 shared fills, improves those by **+0.078709**, misses2 V4 fills worth **+0.433140**, and has1 extra fill(s). Its full holdout result loses0.220324. Missed V4 profit is a descriptive counterfactual; passive did not earn that money. No-fill realizes zero cash and is never labeled a losing fill.

Every original candidate—including geometry rejection, ranking rejection, legal/capacity non-submission and native expiry—remains in the [lifecycle ledger](opportunity-lifecycle-ledger.json.gz). Original counts are265/104/121 raw strict candidates; selected V4 plans47/19/15. All policy comparisons use those same raw IDs within each block. Native entry orders are33/16/7 for V4 and34/16/8 for passive. The exact order/fill/cancellation clocks and reasons are in each native order audit. Detail runs remove pending entries at5minutes; main15m runs have15m cancellation resolution. A tick-through replay is a conservative scenario, not a queue model. Fees use the fixture taker rate for both sides, so maker improvement is not assumed.

## 5. What happened to stops and exits?

No stop was widened and no quantity/risk increase disguised the effect. Structural-only and compatibility share V4 entries. Development structural changes net by+0.050082 versus V4; compatibility by+0.231431, but all remain negative. Both later blocks match V4 exactly. The compatibility guard remains a logical safeguard: a structural failure beyond the protective stop cannot be an earlier exit. A custom exit never replaces the native protective stop. The cash ledger distinguishes native `stop_loss`/tightened-stop labels, ROI, thesis exits and maximum hold. A `trailing_stop_loss` label can describe tightening from the emergency bound to the fixed planned stop; it does not prove an adaptive trail.

## 6. What happened to target quality?

Four changed plans supplied a bounded target experiment, with no measured changed exit. Most raw rejects are the inherited6ATR horizon or net-payoff guards; those were not removed to manufacture activity. The integrated Gate model's187 first-obstacle reward rejects, four geometry passes, three ranking exclusions and one liquidity exclusion remain preserved. Its41 local15m/13 parent-session/two consumed nearest barriers are evidence about that implementation, not a universal judgment on local structure. First barriers are cautions here; parent objectives are separate authority. Neither a subsequent break nor post-exit MFE is admissible pre-entry evidence.

## 7. What happened to selection quality?

Frozen EMA eligibility and original cross-pair ranking remain. Market qualification, setup geometry and rank/capacity reasons are separately recorded. BTC fixture minimums preclude a25USDT order; this is not a bad setup classification. The two other threshold/selector slots were intentionally unused. Feature AUCs are descriptive filled-cohort comparisons only, recorded separately by chronological block in [separability results](chronological-feature-separability.json); small cohorts and changing discrimination do not support a stable selector. Rejected candidates have unknown counterfactual fills/outcomes.

The old Gate cases remain inspectable by exact IDs and source hashes: nine passive misses; six structural changes, including DOGE's sacrificed gain and SOL's favorable delay; relaxed EMA additions/displacements; four integrated geometry passes; both genuine early5m responses rejected by shortlist; largest winners versus comparable losers. [Prior case lineage](prior-case-lineage.json) links the frozen ledgers. Old/new IDs cannot be matched across venues as if they were the same tradable opportunity.

## 8–9. Economics and independent validation

The full mandatory comparison table follows below. Original-candidate expectancy includes zero cash for rejected/nonfilled candidates. R_price divides net cash by actual quantity times distance from actual entry to original stop. R_cost adds entry fee and hypothetical stop-exit fee to that denominator; actual funding stays in net cash. Per-pair/playbook/state and chronological week breakdowns, winning/losing streaks, holding times, exposure, fees/funding, turnover and largest1/3/5 winner arithmetic are in [portfolio-economics.json](portfolio-economics.json). [Trade ledger](trade-cash-ledger.json.gz) gives reconciliation and strictly timed descriptive MFE/MAE. Removing winners arithmetically is not a new capacity-aware replay.

V4 holdout net/original candidate is **+0.002310USDT**, median netR_cost **0.141250**, win rate **57.14%**, PF **1.676**, worst losing streak **2**, native drawdown **0.303578USDT**. Its7day all-pair cluster interval for total net is **[-0.083172,+0.753655]USDT**. This is descriptive bootstrap uncertainty from very few blocks, not a reliable significance claim. Extra10bp/side on fixed holdout turnover gives **-0.066347USDT**; this holdout stress is arithmetic, not an extra native replay. Development also includes true native extra10bp and tick-through replays and identical15m versus5m execution comparisons.

Peak reserved notional stays below50USDT, about5% of the modeled wallet, with at most two positions. All filled entry/exit prices satisfy the **fixture** ticks and quantities obey its lot steps. Legal fixture sizing is not proof of authentic historical exchange acceptance.

**Did any method establish better reliable economics on new history? NO. Did independent validation establish durable profitability? NO / INSUFFICIENT.** The April block was opened once after [evaluation freeze](evaluation-freeze.json). A VFS storage failure interrupted one evidence export; frozen inputs/code were reverified, completed portfolios retained and only remaining commands resumed. The failed structural ZIP and recovery ZIP have identical complete seven-trade objects. [Recovery receipt](holdout-recovery.json), [equivalence proof](holdout-recovery-equivalence.json). No threshold or selection changed, and seven repeated trades are counted once. This is a documented operational interruption of a single opening, not a second holdout.

## 10. What remains unknown?

Authenticated historical contract specs, price-filter changes, account-specific historical fees and market membership; exact settlement marks/publication semantics; historical spread, queue and partial/nonfill probability; intrabar ordering inside5m; authentic executed-price volume-profile/flow incremental value; and recurrence of valuable opportunities across future regimes. The short sample cannot turn generic market-state labels into an institutional-intent claim.

The professional references motivate these tests: [Freqtrade backtest assumptions](https://www.freqtrade.io/en/latest/backtesting/), [callback semantics](https://www.freqtrade.io/en/latest/strategy-callbacks/), [lookahead limits](https://www.freqtrade.io/en/stable/lookahead-analysis/), [Bailey et al. on repeated backtest selection](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf), and [official Binance archive provenance](https://github.com/binance/binance-public-data). Practitioner discussion is explicitly anecdotal and supplies no measured advantage. The installed pinned source controls engine behavior; generic lookahead slicing of cached schedules alone cannot verify their construction. Eight raw-source all-feature prefix recomputations and eight cross-pair ranking comparisons pass.

## 11. Variant verdicts

| Variant | Verdict | Reason |
|---|---|---|
| V4 | PRESERVE_FOR_RESEARCH; UNQUALIFIED | Negative development/validation; seven-fill holdout fails cost stress |
| Passive | REJECT_SPECIFIC_RULE for promotion | Shared-fill improvement loses opportunity access; no stable net advantage |
| Structural-only | REJECT_SPECIFIC_RULE as an earlier-failure replacement | Can require failure beyond hard stop; no durable economic gain |
| Compatibility guard | PRESERVE_FOR_RESEARCH | Logical correction retained; no qualified after-cost edge |
| Parent-target hypothesis | NEEDS_MORE_EVIDENCE; no promotion | Four changed plans, no changed realized outcomes; holdout changes zero targets |
| Continuation-only | NEEDS_MORE_EVIDENCE | Post-hoc diagnostic, negative development and final block |
| Relaxed EMA / qualified rank | REJECT_SPECIFIC_RULE for promotion | Old negative Gate evidence retained; no new Binance validation |
| Integrated | UNQUALIFIED | Preserved zero fills; obstacle significance not independently established |
| Genuine5m entry signal | UNQUALIFIED | Execution detail tested; new timing-signal economics not tested |
| PR12 | PRESERVE_FOR_RESEARCH | Original Gate control source-sealed; not reimplemented here |

These verdicts reject promotion of specific implementations, not EMA/VWAP, SMC/ICT, passive participation or volume-profile concepts as a whole.

## 12. Owner action, code and reproducibility

**Next owner action: review this draft's negative comparison and metadata limitation before authorizing further research; do not activate paper.** Obtain independently verifiable historical Binance contract metadata/fee evidence before treating this scenario as venue-qualified. Further strategy development needs a newly untouched evaluation block; this April block is consumed. The future Gate reserved block remains untouched and cannot be evaluated until fully elapsed.

Runnable entry points, exact image/version, restore/replay and rollback are in [the runbook](../../../docs/operations/validation-next.md). Keep the delivered private bundle and its SHA256 receipt. `scripts/lab-validation-next.sh tests` runs the11 focused tests. Broad regression's actual exit code is1; details and all15 errors/two skips are preserved in [regression-and-validation.json](regression-and-validation.json). No safety registration was bypassed. Code/config/data hashes and native argv are retained, and all original sources/evidence remain unchanged. No paid data, new cloud task, real/testnet order, key, leverage increase, recurring service, merge or deployment was used.

## Mandatory full comparison

"Missed" is submitted unfilled entry orders; it does not include non-submission. Original candidates are raw strict IDs, while Plans records policy-qualified selected plans. Extra-cost results below are fixed-fill turnover sensitivities; native development stresses are separate records. All method economics remain partial/unqualified.

| Method | Venue | Window | Original candidates | Plans | Orders | Fills | Missed | Net USDT | Net/original candidate | Median net R | Win % | PF | Largest-winner dependence | Worst losing streak | Drawdown | Extra-cost result | Validation status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| continuation-only-diagnostic | Binance scenario | development 2026-01-11/2026-03-01 | 265 | 32 | 23 | 22 | 1 | -2.382481 | -0.008990 | -0.880969 | 13.636364 | 0.374579 | net ex top3 -3.809406 | 11 | 2.839941 | extra10bp -3.462719 | PARTIAL / INSUFFICIENT |
| parent-target | Binance scenario | development 2026-01-11/2026-03-01 | 265 | 47 | 33 | 32 | 1 | -1.720899 | -0.006494 | -0.780689 | 25.000000 | 0.652792 | net ex top3 -3.214156 | 6 | 2.178359 | extra10bp -3.286531 | PARTIAL / INSUFFICIENT |
| passive-transfer | Binance scenario | development 2026-01-11/2026-03-01 | 265 | 47 | 34 | 27 | 7 | -1.945252 | -0.007341 | -0.803979 | 18.518519 | 0.538458 | net ex top3 -3.482056 | 8 | 2.461351 | extra10bp -3.266947 | PARTIAL / INSUFFICIENT |
| structural-transfer | Binance scenario | development 2026-01-11/2026-03-01 | 265 | 47 | 33 | 32 | 1 | -1.670818 | -0.006305 | -0.963183 | 28.125000 | 0.680267 | net ex top3 -3.164074 | 6 | 2.076477 | extra10bp -3.235779 | PARTIAL / INSUFFICIENT |
| thesis-compatible-transfer | Binance scenario | development 2026-01-11/2026-03-01 | 265 | 47 | 33 | 32 | 1 | -1.489468 | -0.005621 | -0.880969 | 28.125000 | 0.704723 | net ex top3 -2.982724 | 6 | 1.895128 | extra10bp -3.054611 | PARTIAL / INSUFFICIENT |
| v4-transfer | Binance scenario | development 2026-01-11/2026-03-01 | 265 | 47 | 33 | 32 | 1 | -1.720899 | -0.006494 | -0.780689 | 25.000000 | 0.652792 | net ex top3 -3.214156 | 6 | 2.178359 | extra10bp -3.286531 | PARTIAL / INSUFFICIENT |
| continuation-only-diagnostic | Binance scenario | holdout 2026-04-02/2026-05-01 | 121 | 12 | 6 | 6 | 0 | -0.066516 | -0.000550 | -0.003323 | 50.000000 | 0.839103 | net ex top3 -0.413410 | 2 | 0.303578 | extra10bp -0.362130 | PARTIAL / INSUFFICIENT |
| parent-target | Binance scenario | holdout 2026-04-02/2026-05-01 | 121 | 15 | 7 | 7 | 0 | 0.279531 | 0.002310 | 0.141250 | 57.142857 | 1.676161 | net ex top3 -0.390671 | 2 | 0.303578 | extra10bp -0.066347 | PARTIAL / INSUFFICIENT |
| passive-transfer | Binance scenario | holdout 2026-04-02/2026-05-01 | 121 | 15 | 8 | 6 | 2 | -0.220324 | -0.001821 | -0.538079 | 33.333333 | 0.567499 | net ex top3 -0.509420 | 3 | 0.471793 | extra10bp -0.515395 | PARTIAL / INSUFFICIENT |
| structural-transfer | Binance scenario | holdout 2026-04-02/2026-05-01 | 121 | 15 | 7 | 7 | 0 | 0.279531 | 0.002310 | 0.141250 | 57.142857 | 1.676161 | net ex top3 -0.390671 | 2 | 0.303578 | extra10bp -0.066347 | PARTIAL / INSUFFICIENT |
| thesis-compatible-transfer | Binance scenario | holdout 2026-04-02/2026-05-01 | 121 | 15 | 7 | 7 | 0 | 0.279531 | 0.002310 | 0.141250 | 57.142857 | 1.676161 | net ex top3 -0.390671 | 2 | 0.303578 | extra10bp -0.066347 | PARTIAL / INSUFFICIENT |
| v4-transfer | Binance scenario | holdout 2026-04-02/2026-05-01 | 121 | 15 | 7 | 7 | 0 | 0.279531 | 0.002310 | 0.141250 | 57.142857 | 1.676161 | net ex top3 -0.390671 | 2 | 0.303578 | extra10bp -0.066347 | PARTIAL / INSUFFICIENT |
| continuation-only-diagnostic | Binance scenario | validation 2026-03-02/2026-04-01 | 104 | 16 | 13 | 12 | 1 | -0.015394 | -0.000148 | -0.974401 | 25.000000 | 0.991603 | net ex top3 -1.833271 | 5 | 1.005658 | extra10bp -0.612081 | PARTIAL / INSUFFICIENT |
| parent-target | Binance scenario | validation 2026-03-02/2026-04-01 | 104 | 19 | 16 | 15 | 1 | -0.440407 | -0.004235 | -0.984060 | 20.000000 | 0.804982 | net ex top3 -2.258285 | 7 | 1.252627 | extra10bp -1.183622 | PARTIAL / INSUFFICIENT |
| passive-transfer | Binance scenario | validation 2026-03-02/2026-04-01 | 104 | 19 | 16 | 14 | 2 | -0.188263 | -0.001810 | -0.986790 | 21.428571 | 0.908482 | net ex top3 -2.057115 | 6 | 1.126962 | extra10bp -0.885328 | PARTIAL / INSUFFICIENT |
| structural-transfer | Binance scenario | validation 2026-03-02/2026-04-01 | 104 | 19 | 16 | 15 | 1 | -0.440407 | -0.004235 | -0.984060 | 20.000000 | 0.804982 | net ex top3 -2.258285 | 7 | 1.252627 | extra10bp -1.183622 | PARTIAL / INSUFFICIENT |
| thesis-compatible-transfer | Binance scenario | validation 2026-03-02/2026-04-01 | 104 | 19 | 16 | 15 | 1 | -0.440407 | -0.004235 | -0.984060 | 20.000000 | 0.804982 | net ex top3 -2.258285 | 7 | 1.252627 | extra10bp -1.183622 | PARTIAL / INSUFFICIENT |
| v4-transfer | Binance scenario | validation 2026-03-02/2026-04-01 | 104 | 19 | 16 | 15 | 1 | -0.440407 | -0.004235 | -0.984060 | 20.000000 | 0.804982 | net ex top3 -2.258285 | 7 | 1.252627 | extra10bp -1.183622 | PARTIAL / INSUFFICIENT |
| No trade | Binance scenario | development | 265 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | NO_EXPOSURE_CONTROL |
| No trade | Binance scenario | validation | 104 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | NO_EXPOSURE_CONTROL |
| No trade | Binance scenario | holdout | 121 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | NO_EXPOSURE_CONTROL |


Data-derived artifacts: attribution **Binance Vision**, CC BY-NC-SA4.0, personal noncommercial research; historical results are not an endorsement or future-income estimate.
