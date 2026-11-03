# Profitability recovery — owner report

**Decision: NO-GO. Pause the final deployment-engineering session. No demonstrable trading advantage emerged.**

This completed investigation contains 114 official native Freqtrade result records (113 alternative portfolios plus 1 exact replay) and 7882 independently reconciled modeled trade records. Overlapping alternatives and the replay do not create independent market samples; returns are never additive. Raw sources, causal inputs, native ZIPs and simulated account state are privately backed up. No persistent paper, live, testnet or demo exchange operation was activated. PR #9 remains the parent; no merge/auto-merge is requested.

1. **Why did the existing system fail to demonstrate profitability?**

   The strongest confirmed causes are cost headroom, risk weighting and concentration. The frozen Session 4 reference earned 3.721900 USDT gross, paying 2.777714 in fees and 0.021045 funding: only 0.923141 remained. Extra-friction break-even was 2.49 bp per side; the structure variant tolerated 3.57 bp. These are below the mandated 10 bp/side robustness stress. Funding was not the dominant economic drag.

   The original structure's three largest winners supplied 43.66% of positive P&L; removing them changes +0.943062 to −3.624842 USDT. August lost 1.668367, September earned 2.309256, October earned 0.793589, and November's two fills lost 0.491417. This is unstable contribution, not a stable regime premium. Its summed net stop-R was −3.7313. Reweighting the SAME fills to constant modeled risk changes +0.943062 to −0.361018 before any lot/capacity/sequence changes; equal 25 USDT reweighting remains +1.221916. Native constant-risk portfolios lose too. The small dollar profit depends on how wider-stop winners are weighted.

   Predictability is **unestablished**, rather than proven universally absent. Among 61 matched-population reference continuation plans, only 24.6% reach 3 R before stop within 8 h; 55.7% stop first and 19.7% reach neither. Median MFE/MAE are 171.1/-113.1 bp. Net endpoint return after 35 bp assumed roundtrip cost averages -23.1 bp. Continuation timing lift versus matched times is 12.6 bp, week-block 95% [-103.9, +118.1], conditional matched-null p=0.405. Reversal has 22 matched plans, target-first 22.7%, timing-null p=0.335. These quantities do not establish monetizable signal timing. Actual native fills and all planned opportunities are separate populations.

   The frozen reference funnel has 2751 raw recipe records: 1157 fail stop/target/net-RR geometry, 914 fail suitability, 580 fail ranking/liquidity, and 100 produce approved plans; 82 become native fills. Plans-minus-fills also includes account/capacity/lot effects, not only execution nonfills. Barrier diagnostics condition on valid geometry, a complete outcome horizon and at least 8 matched control times; explicit exclusion counts are retained. Favorable-movement times denote 15 m bar starts, not observed tick times. Thus this analysis does not claim to reject every conceivable use of the raw candle patterns.

   The original structure continuation population has 56 matched plans; its shrunk target-first probability is 0.272, descriptive Jeffreys 95% [+0.166, +0.393]. Only five selected structure reversals enter the matched population. Their favorable conditional result is too sparse and selected during development to qualify a reversal edge. Reversing direction on identical observations is reported separately as a path diagnostic. Native entry timing, stop/target geometry, nonfills and thesis exits are tested independently below. Coarse execution remains uncertain; it cannot explain away the new hypotheses' negative gross/after-cost outcomes.

2. **What trading hypotheses did you test, and why?**

   **Context continuation:** broad directional participation plus asset-specific relative strength might distinguish durable pullbacks from isolated exhausted moves. Keep the original continuation setup/stop/3 R target/8 h management; require aligned BTC 4 h movement, aligned relative 24 h strength, majority 24 h breadth and ATR expansion versus its prior 24 h median. One predeclared SMC ablation tests the frozen structural suitability rule. Both variants are REJECTED.

   **Daily cross-sectional momentum:** persistent asset-specific demand might continue over a day and offer movement large enough to pay costs. At 00:00 UTC select the positive 24 h winner and negative 24 h loser; enter at native next-open market, 2 completed-hour ATR stop floored at 0.6%, abstain above 2.5%, 4 R objective and 24 h timeout. Compare with a credible liquidity-selected time-series momentum control using the same clock, sign, geometry and exits. No parameter search, retraining or winner substitution after a volatility rejection. Momentum is REJECTED.

   **Meaningful failure/reversal:** evaluate the existing external-boundary sweep, reacceptance, confirmed shift/displacement and opposite-direction paths. No new reversal recipe was promoted from five favorable selected examples. Existing confirmed swings, BOS/CHoCH, prior day/session boundaries, FVG formation/retests and range location are reused causally. They do not prove institutional activity. Historical genuine executed-flow/delta/CVD is UNKNOWN; historical volume profiles are OHLCV proxies. No unavailable flow feature receives claimed uplift.

   Definitions, feature availability, geometry and the evaluation protocol were sealed before new historical acquisition. Gate's documented response limits forced an availability amendment to real 1 h execution for the older daily-momentum test; the daily economic rule was already frozen. That amendment preceded evaluation. All tested variants, 31 nulls, sizing/fee/fill/management scenarios and failed attempts are registered and retained. This is continued development, not an uncorrected discovery from a strategy zoo.

3. **What actually improved?**

| Venue / period / policy | Fills | Native net USDT | Complete native +10 bp/side | Constant-risk net |
|---|---:|---:|---:|---:|
| Gate / development / reference | 76 | +1.108549 | -2.347494 | -0.415603 (64 fills) |
| Gate / development / structure | 62 | +1.195339 | -1.648672 | -0.021391 (54 fills) |
| Gate / development / context | 32 | -2.744429 | -4.222256 | -1.009929 (29 fills) |
| Gate / development / context-smc | 30 | -2.054756 | -3.446408 | -1.009929 (29 fills) |
| Gate / development / momentum | 29 | -6.274117 | -7.226318 | -1.277471 (19 fills) |
| Gate / development / liquid-momentum | 96 | -1.991700 | -5.820175 | -0.403595 (77 fills) |
| Gate / hourly-development / momentum | 29 | -5.781274 | -6.732182 | -1.082923 (19 fills) |
| Gate / hourly-independent / momentum | 21 | -1.679368 | -2.559024 | -1.307469 (16 fills) |
| Gate / hourly-independent / liquid-momentum | 62 | +2.542418 | -0.217951 | -0.108489 (50 fills) |

   Development means Aug 5–Nov 3, 2026, end exclusive. The separately reserved older Gate test is May 20–Jul 26, end exclusive, with May 10–20 warmup. It contains 67 calendar days. Hourly development is the same daily policy replayed at 1 h resolution; the older result does not independently validate 15 m continuation. All comparisons use 1000 USDT, 1 x, max 2 positions, 25 USDT fixed-notional ceiling; constant modeled-risk target 0.25 USDT uses the SAME 25 USDT ceiling. Native legal lots and unchanged account/cooldown constraints determine feasibility. Different exposures, turnover, risk deployment and fill counts are disclosed in economic-report.json.

   The small fresh structure-minus-reference improvement is +0.086790 USDT; both fail friction/constant-risk qualification. The context SMC ablation improves the losing context policy by +0.689673 USDT, paired block 95% [+0.000, +1.954]; it does not create a profitable policy. No trading improvement is promoted. The completed gains are stronger diagnosis, real minute execution coverage, older market evidence, more credible benchmarks and fully reconciled cost accounting.

   Native touch, 1 bp trade-through, immediate-open-only, market, deterministic 25% nonfill, half desired allocation, barrier-only management and full 1 m alternatives are in portfolio-table.md. Nonfill/half-allocation scenarios are hypothetical full portfolios, not inferred queue probabilities or observed partial exchange fills. Genuine 1 m data covers 14 markets×7200 rows=100800 candles during Oct 29–Nov 3. Minute feasibility population counts arecontext: 2/2 touch-range feasibility, 2/2 one-bp trade-through; context-smc: 2/2 touch-range feasibility, 2/2 one-bp trade-through; liquid-momentum: 8/9 touch-range feasibility, 8/9 one-bp trade-through; momentum: 3/3 touch-range feasibility, 2/3 one-bp trade-through; reference: 3/3 touch-range feasibility, 3/3 one-bp trade-through; structure: 2/2 touch-range feasibility, 2/2 one-bp trade-through. Queue priority and within-minute sequencing remain UNKNOWN; five recent days cannot qualify the full 90 day expiry model.

   Two predeclared structure sensitivities remain slightly positive under fixed-notional higher-cost execution:immediate-open-only +0.138026 USDT and the deterministic nonfill realization +0.325305 USDT. Twelve separately recorded post-result qualification checks evaluate the SAME frozen entry rules under constant risk and full native costs, with matching reference controls; no threshold is changed. The structure sensitivities become −1.086021 and −0.611086 USDT under constant risk plus 10 bp/side. A favorable arbitrary nonfill realization does not establish predictive information or empirical queue behavior. Neither sensitivity is promoted.

   The primary native fee is 7.5 bp per side with source funding. Full native 17.5 bp portfolios implement the additional 10 bp stress and may change trade sequence; posthoc ledger stress is separately labeled. A venue-specific market scenario uses public current 5 bp taker plus observed current half-spread and hypothetical 2 bp slippage; its full native conservative common fee rounds the worst observed cohort cost upward to 14.2 bp/side. Instantaneous spreads span 0.013–14.364 bp; they are not historical spread observations. Maker 2 bp is a source quote, not assumed guaranteed execution. The 0.0038 allowance is only admission/risk geometry and is never charged again as a fee.

4. **Is there now a demonstrable trading advantage?**

   **No.** 31 complete native matched-ranking nulls, seeds 61001–61031: mean null -4.002339 USDT; reference-minus-mean-null +5.110889 USDT, paired 7 day block 95% [-0.154, +10.793]; conditional empirical upper-tail p=0.06250, resolution 1/32. This tests conditional market ranking, not an omnibus proof of timing, direction, SMC or all research multiplicity. The 199 matched-time path replicates have resolution 1/200; they reuse the actual eligible control population and do not create 199 independent market histories. Paired day/week comparisons retain zero-return days and cross-market dependence.

   The ranking nulls average 132.0 fills and 5993.0 USDT turnover versus 76 fills/3456.0 USDT in the reference. Selection can change setup incidence and capacity even with the same eligible slots; this exposure difference is disclosed, not presented as leverage-free proof of setup alpha. Ranking shows conditional improvement over these nulls, but its empirical p-value, development reuse and negative cost-stressed reference do not establish an independently monetizable edge.

   Fresh reference mean net trade expectancy is +0.014586 USDT, +6.43 bp weighted by entry notional, block 95% total [-6.455, +8.736]; after 10 bp/side its ledger net is -2.347494 USDT. The independently reserved momentum result averages -0.079970 USDT per trade, block 95% total [-7.842, +3.697], with summed net stop-R -3.986. Its results do not support promotion.

   Power is calculated from observed weekly dispersion rather than a universal trade-count minimum. For the fresh reference, the approximate 80%-power/two-sided 5% detectable mean effect is 79.0 bp per trade-equivalent entry notional, far larger than its observed 6.43 bp. There are 13 weekly blocks. This normal approximation and circular 7 day bootstrap assume enough temporal stability; few blocks/nonstationarity limit precision. Target-before-stop shrinkage, conditional successful/unsuccessful payoffs and uncertainty are in opportunity-diagnosis.json; they are descriptive and not a fitted admission model.

5. **Which strategy should be retained?**

   Retain **PaperPolicyV4 / structure-execution-v4.0.0** unchanged as the existing guarded reference, with economic status **INSUFFICIENT / UNQUALIFIED**. Keep **PolicyFixedV3 / controlled-pullback-failure-v3.0.0** unchanged as its frozen rule benchmark. This is preservation, not a recommendation to activate trading. No new operational policy is selected. RecoveryPolicyR1/recovery-v1.0.0 and its hourly subclass remain executable historical research implementations; they explicitly refuse live and dry-run activation.

   Exact retained SHA 256 values:

   - research/session4/PaperPolicyV4.py: `a7b986d2f1e51c0ac2301ff6f6a3d712936fef8e65249f69db4c9706d645134b`
   - research/policy/PolicyV3.py: `750af82402a5dd8999caa54e87a27335447a48ff8327ecf0f03cee61551097a0`
   - research/policy/policy_features.py: `13f99f2c55a77b3c40764a64ba5d46f58f6b350b2f6c6fff8c54528ff921df95`
   - research/session4/session4_features.py: `380a9f24237630fc49331c9ab5ce7b7c3128172e710dea974edd77330749c65a`
   - configs/paper-policy-limit.json: `706ca7d14511a3a84bddc1d752f136e8cdbb6eaadc6ea27528dbc714b8c70981`
   - configs/paper-policy-market.json: `1082c4d09ca04c8dd7bdd5e5063c235da669d5230871494d86099163349bb737`

   Existing complete eligibility, regime/rank, entry/expiry, stop/invalidation, target/timeout, source-health and account constraints remain in the frozen source and Session 4 release/runbook. Wallet 1000 USDT, max 2 positions, 25 USDT ceiling, 1 x, 0.3–2.5% logical stops, continuation 8 h/reversal 4 h, 5 min entry expiry, and preinstalled 2.5% protective bound remain unchanged. Existing paper configuration files were not edited.

6. **What still prevents economic qualification?**

   Specified challengers lose under defensible costs, with no independently evaluated positive candidate. Ranking/timing uncertainty, concentration and risk-weighting effects remain. The 14-market current-survivor frame is not a complete historical universe; delisted membership and historical contract/tier changes are unknown. Only source-returned coverage and observed listing clocks support eligibility.

   Gate rejects 15 m history beyond 10000 recent points and funding beyond 180 days. The January–July 15 m acquisition failed; its partial 1 h sources and errors are retained. Binance archives were reachable, but official contract metadata returned 451; no Binance prices, costs or funding enter these Gate portfolios. The older 67 day 1 h experiment is therefore a separately labeled resolution test. Minute history for that period is unavailable under the same retention constraint.

   The approved Session 4 private archive was not attached. Its original manifest and all parent evidence are preserved; no restore of missing raw sources is claimed. All 56 corresponding reacquired files have separate manifests; raw row-level reconciliation remains UNCOMPUTABLE without originals. Complete reference/structure decision plans were restored from Git-tracked opportunities and BOTH hashes exactly match the private parent plan manifests. Full native replays separate frozen decisions from new source/feature recomputation; see source-reconciliation.json.

   Frozen-decision replays reproduce every 82 reference and 58 structure entry/exit price, time and quantity. Their only P&L differences are −0.003135 and −0.000669 USDT in funding under the source-clock model. Recomputed fresh selection produces 76/62 fills; that change is not attributed to a new strategy advantage. Exact trade reproduction does not establish byte identity of missing full source histories.

   All official trades reconcile quantity, fees, net P&L and every source-reported funding event. Second-offset events use the preceding hourly source mark OPEN. Exact settlement marks and venue priority at entry/exit boundaries are unknown. Initial equality-join and pre-exit snapshot failures, contract-volume normalization and matched-control availability corrections are quarantined; failed outputs never qualify a policy. Genuine tape, queue/partial fill probabilities, historical spread distributions and stop-gap tails remain unavailable. There is no historical order-flow uplift claim.

   The November 17–December 1, 2026 future holdout was neither acquired nor inspected. Positive independent after-cost expectancy with credible execution, risk robustness, favorable controls and tighter dependence-aware uncertainty would be needed to reconsider qualification. This session supplies no such candidate.

7. **Should the owner spend the final Codex session?**

   **NO-GO. Do not spend it on deployment engineering now.** Retain the working software and frozen references; pause persistent-operation work. Reconsider deployment only after a separately registered economic hypothesis earns positive independent after-cost evidence. Additional dashboards, agents or deployment polish cannot repair the measured strategy economics. This recommendation does not assume another paid research round.

Reproduce from the private source/input archive in an isolated checkout:

```bash
python scripts/recovery_archive.py restore /path/Recovery-Private-Backup.tar.gz work/owner-restore
python scripts/recovery_archive.py hydrate work/owner-restore .
./scripts/lab-recovery.sh tests
./scripts/lab-recovery.sh replay development reference --replay-id owner-check
./scripts/lab-recovery.sh replay hourly-independent momentum --replay-id owner-check
./scripts/lab-recovery.sh diagnose
./scripts/lab-recovery.sh report
```

Completed output directories refuse overwrite; use a new replay ID. `matrix primary|null|execution` reruns the finite registered matrix in a fresh checkout, or skips immutable completed jobs. Restore validation rejects unsafe paths, duplicates, oversized archives and overwrites. Raw sources/native ZIPs/simulated SQLite remain outside Git. The final backup's actual hash-verified restore is recorded in run -001/private-backup.json.

Evidence: [economic report](run-001/economic-report.json), [full portfolio table](run-001/portfolio-table.md), [opportunity paths](run-001/opportunity-paths.json), [diagnosis](run-001/opportunity-diagnosis.json), [source reconciliation](run-001/source-reconciliation.json), [decision](run-001/decision.json). All research outcomes are modeled historical results, not observed real-money or forward paper profits.

Validation: 5 recovery regressions, 5 confirmed-structure tests and 20 flow/profile/intelligence tests pass; all 14 new-feature prefixes match. Exact native replay matches all 76 complete trade objects. The private archive contains 1202 files(117341983 bytes); it was fully restored and hash-verified with 0 overwrites; SHA 256 `14e65f1cb2ba6dcf9a516ba32ed4d8aad781cf0b78bd1527f997a7d2f85c77aa`.
