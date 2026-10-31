# Bonus acceptance and owner review

**Profitability is not demonstrated. Overall acceptance is PARTIAL: 9 PASS, 8 PARTIAL, 0 FAIL.** The engineering delivers a working native research pipeline. The strict integrated and ICT policies abstained on every tested opportunity; this is insufficient economic evidence, not a profitable result. M1 has an independently identified native funding defect and remains research-only.

## A. Reused components

Official pinned Freqtrade 2026.10 / CCXT 4.5.90; existing Gate public adapter, native scanner/eligibility exporter, both frozen recipes and PlaybookRiskV1; unchanged Session3 right-confirmed structure; native informative merges, fills, ROI/stop conversions and position-adjustment callbacks; native footprint aggregation. NumPy/Pandas implement only bounded profile/value-area calculations. No dependency upgrades, alternative execution engine, backtest simulator, model service, dashboard or paid source. See [component compatibility](source-compatibility.md).

All **329 prior tracked files are byte-identical** to verified Session3 `48f34bcd51d080204c3e4bf90ec4b014a3319dd5`, including every earlier strategy, protocol, evidence file and entrypoint. PRs #1–#3 were open at their recorded heads; main was design-only. See [starting point](starting-point.json) and [preservation](prior-preservation.json).

## B. Actual opportunity pipeline

Observed scanner snapshot: **583 eligible contracts → 20 shortlisted → 5 deeply analyzed → 5 REJECT**, because essential ticker source clocks were unknown. It uses the existing scanner. No current trade or order is claimed. The market and receipt clocks are retained in [scanner snapshot](scanner-snapshot.json) and [assessments](current-assessments.json).

Historical acquisition: 20 validated source files / 2,005,504 bytes, five predeclared surviving markets, July 26–October 30 UTC. Full acquisition/warm-up ranking ledger: 46,080 market-time rows, 32,950 cheap-screen passes, 27,363 selected market-time rows, 95 empty-screen timestamps. These are repeated observations, not distinct markets. The evaluation window is August 5–October 30 UTC, end-exclusive, after 240 hourly warm-up bars.

Every completed 15m decision ranks available sample coins using absolute 4h relative return versus BTC and trailing quote-volume activity, retaining up to three. It supports strength and weakness. Hourly ADX routes VWAP continuation at >=25 and failed breakout below 25; the frozen entry recipes still determine whether a setup exists. The native vectorized historical calculation precomputes features over the five-market dataset; current serious analysis is capped at five after broad screening.

In the evaluation window there are **92 route-ready parent candidates** across 8,256 decision timestamps. The router has no new TRADE plan at 8,246 of those timestamps; the strict integrated policy abstains throughout. Router-only: 50 rank/screen exclusions, 32 cost/target exclusions, 10 TRADE plans, 9 native fills. The full integrated policy: 50 rank exclusions, 26 ICT exclusions, 3 SMC exclusions, 13 target/cost exclusions, **0 TRADE**. No minimum trade count is forced. Rejected ledger direction is available where matched to native frozen-parent records; full pre-admission rejected direction export is incomplete. The full ledger includes every variant; 24 exported plan examples are variant examples, not 24 unique opportunities.

Historical eligibility/spreads are conditional assumptions within five known survivors. Today’s 583-contract membership is never backdated. This is a real limit on broad historical dynamic-selection claims. See [ranking](market-ranking.csv), [schedule](schedule.json), [opportunity ledger](opportunity-ledger.csv), [counts](opportunity-summary.json), [plans](trade-plans.json).

## C. Analytical workstreams

**SMC:** reused causal swings/BOS/CHoCH, extended equal-high/low references, opposing-hour continuation veto, meaningful known-swing qualification for reversals and structural target/invalidation references. Separate native SMC ablation: five trades, +0.687792 USDT, versus router-only nine/+1.089457. The old structure control loses -1.018965 USDT. There is no demonstrated SMC economic improvement. An unused equal-level diagnostic initially self-matched a pivot; original source is preserved, the bug is corrected and regression-tested, all admission artifacts remain byte-identical, and native router replay matches all trade fields. [Correction](metadata-correction.json), [admission verification](metadata-admission-verification.json).

**ICT:** prior UTC day and completed 8h-session boundaries; raids/reclaims; displacement >=0.8ATR; causal three-candle FVG with four-bar lifetime; structural shifts and premium/discount location. No stock-market kill-zone assumption. The separate ICT policy rejected all 42 shortlisted candidates and executed zero trades. Logic and known-at values are implemented and tested, but economic contribution and entry/management benefit are unmeasured. This abstention is retained without threshold tuning.

**Volume profile:** prior 96 completed 15m candles, excluding the signal candle; fixed 10bp log bins, 70% adjacent-bin value area, POC/VAH/VAL and volume-node diagnostics. Historical input is explicitly **OHLCV typical-price volume proxy**, not exact volume at price. Profile evidence changes admission/target room; its native ablation makes three trades/+0.565607 USDT, all VWAP. Real captured profiles use executed base volume at actual observed prices; native footprints are reused. No equal-fidelity historical claim or inherent POC edge is made.

**Order flow:** signed Gate public USDT WebSocket contracts, event/receipt clocks, multiplier conversion, ID deduplication, ordering/invalid-event/reconnect coverage, observed-cutoff aggregation, aggressive buy/sell, delta/window CVD, imbalance, price response and native price footprints. Official WS aggressor semantics are documented in [compatibility](source-compatibility.md). Both recipes and directions have explicit confirmation/contradiction tests. Missing coverage yields UNKNOWN. BTC observed captures/replays and actual closed-candle NO_TRADE shadow decisions are retained; SOL generalization and invalid-feed handling are documented below. Prospective economics remains **UNMEASURED**. No OHLCV delta is manufactured.

Observed/replayed corpus: **444 valid normalized trades** across two BTC and two SOL captures, eight complete observed windows and two partial windows. The first SOL sample rejected six zero-size events and remained PARTIAL. A subsequent sample with the documented decimal-size header had 47 valid trades, no invalid events and three complete observed windows. This does not establish venue losslessness or historical economic contribution. All actual completed-candle shadow assessments were NO_TRADE. See [orderflow summary](orderflow-summary.json) and [forward captures](forward).

## D. Actual native economic results

1,000 USDT starting equity, <=25 USDT notional per position, 1x, maximum two positions. Native fee 0.06% per side and exported signed funding. The +10bp/side column adds modeled spread/slippage to native turnover without refilling orders. Source-funding qualification follows sectionE.

| Policy | Trades | Native net USDT | +10bp/side net | Mean net R | Verdict |
|---|---:|---:|---:|---:|---|
|IntegratedM0V1|0|+0.000000|+0.000000|—|INSUFFICIENT OR UNAVAILABLE EVIDENCE|
|IntegratedM1V1|0|+0.000000|+0.000000|—|INSUFFICIENT OR UNAVAILABLE EVIDENCE|
|LiquiditySweepReversalV1|86|-2.259367|-6.293016|-0.0848|REJECTED UNDER TESTED ASSUMPTIONS|
|RouterICTV1|0|+0.000000|+0.000000|—|INSUFFICIENT OR UNAVAILABLE EVIDENCE|
|RouterOnlyM1V1|9|+1.492089|+1.073423|0.4848|PROMISING BUT UNQUALIFIED|
|RouterOnlyV1|9|+1.089457|+0.671195|0.3596|PROMISING BUT UNQUALIFIED|
|RouterProfileV1|3|+0.565607|+0.421519|0.4601|PROMISING BUT UNQUALIFIED|
|RouterSMCV1|5|+0.687792|+0.454012|0.3665|PROMISING BUT UNQUALIFIED|
|StructureAwareSweepV1|21|-1.018965|-2.014912|-0.1524|REJECTED UNDER TESTED ASSUMPTIONS|
|VWAPTrendContinuationV1|30|+0.959708|-0.434571|0.1416|PROMISING BUT UNQUALIFIED|

Recipes within the routed portfolio:

| Policy/recipe | Trades | Native net | +10bp/side net | Mean net R | Mean directional exit move |
|---|---:|---:|---:|---:|---:|
|RouterOnlyV1/sweep|6|+0.523849|+0.249677|0.3093|0.5851%|
|RouterOnlyV1/vwap|3|+0.565607|+0.421519|0.4601|0.9153%|
|RouterOnlyM1V1/sweep|6|+0.897339|+0.622792|0.4865|0.8348%|
|RouterOnlyM1V1/vwap|3|+0.594750|+0.450631|0.4814|0.9595%|

Both recipes and the selected portfolio are **PROMISING BUT UNQUALIFIED** in the small router-only development sample. The strict integrated portfolio and each strict integrated recipe have zero trades/net 0 and **INSUFFICIENT OR UNAVAILABLE EVIDENCE**. The frozen sweep and old structure control are **REJECTED UNDER TESTED ASSUMPTIONS**. No policy is ECONOMICALLY QUALIFIED.

NetR uses initial underlying stop risk plus the declared0.35% planned cost allowance. Native net includes modeled fees and native exported funding; +5/+10/+20bp turnover stress is separate. MFE/MAE use only fully intermediate completed candles, excluding entry/exit candles to avoid crediting post-stop favorable wicks. They are conservative incomplete-path diagnostics. Native stop-before-ROI fixture ordering is tested; ambiguous candle outcomes do not prove actual exchange sequencing.

Router M0/M1 closed-trade drawdown is0.491691 USDT; completed-close equity accounting gives maximum mark-proxy drawdown0.863065 USDT. This is not true exchange account drawdown:15m futures closes proxy marks and aggregate funding is booked at final exit. Pair/direction/closed-hour regime contributions, holding times, win/loss means, profit factor, MFE/MAE in% andR, force exits, funding and friction are in [economic results](economic-results.json) and [native-fill ledgers](trade-ledgers).

Thirteen joint-market calendar-week blocks, 2,000 resamples and fixed seed describe development uncertainty. M0 interval is[-0.566409,+2.965013]USDT; the M1 native interval is[+0.065525,+3.186288]. Nine trades, inspected history, overlapping coins/positions, few blocks, stationarity assumptions and the native funding defect prevent independent economic qualification even when an interval is positive.

## E. Management and independent funding finding

Strict integrated M0/M1 abstained. A separate pre-outcome [management supplement](../../research/bonus/management-supplement.json) compares identical available router admissions. **Nine matched opportunities, three native partial exits, delta +0.40263199USDT**, one reduced loss, one saved-profit case, one reduced winner/earlier harmful exit. Native fee difference +0.00024252 USDT. Both recipes have actual native trades; all actual partials in this sample are long, with short partial behavior covered by native callback fixtures.

One partial at 1 price-risk R, minimum-size checks, open-order inhibition, native fill-state transitions, cost-breakeven and confirmed-structure tightening, persisted tighten-only stops, duplicate callbacks, five-minute expiry, frozen targets and 4/8h holds are exercised. Restart checking reconstructs sanitized custom state; a full persistent native database/process recovery with real incomplete exchange fills has not been qualified.

**Independent accounting has two distinct outcomes.** Decimal fill accounting reconciles all 163 records to native exports (maximum per-trade residual<6.1e-9USDT). Separately, source-event funding/quantity accounting finds **two M1 trades outside plausible funding bounds** at exact-clock partial/funding boundaries: ETH August 20 and XRP August 25. Native funding re-applies a boundary event after the partial. The raw native results are preserved, not silently corrected.

For ETH, native funding is -0.002278794USDT; source rate*mark*held quantity permits[-0.001139397,-0.0005696985] depending on exact-clock fill priority. M1 total native net remains **+1.49208851**; source-funding net bounds are **[+1.4934139964,+1.4941491077]**. This is a model/accounting defect despite its small magnitude. M1 stays disabled for persistent paper until the pinned engine lifecycle is fixed and revalidated. [Decimal reconciliation](independent-reconciliation.json), [source funding audit](source-funding-audit.json), [matched management](management-comparison.json).

October 1–30 coarse versus5m detail: one router trade per policy, all four runs net **-0.10955840USDT**. This checks a small observed opportunity subset, not general fill realism or all partial/funding cases. [Detail comparison](detail-comparison.json).

## F. Futures risk

Illustrative versioned research budget:0.25% position risk,0.5% open/pending risk,1% daily equity loss reference; not owner-approved operating limits. Evaluator calculates underlying stop/cost risk, notional, contract units, margin,1/10/20x native stop conversion, current public margin tiers/maintenance deductions, buffered isolated liquidation distance, available equity/unrealized PnL, pending risk and correlated exposure. Missing tiers/account inputs and loss/clearance breaches reject. At fixed notional, leverage changes margin and native stop ratio, not price PnL. [Actual current-tier scenarios](risk-scenarios.json).

Native research entries remain1x and <=25 USDT. Callback account review adds completed-close unrealized PnL and reserves open/pending exposure, failing closed on unavailable marks. Its daily reference remains realized-balance based, not a complete midnight account-equity reconstruction. Current tiers are not backdated as historical facts. The separate evaluator is not an owner-approved or activated20x execution gate. Stops cannot guarantee protection through gaps, liquidation or outages.

## G. Chronology and causality

Protocol/thresholds were registered before new strategy outcomes. Later bounded management and detail registrations are explicit; only the frozen VWAP parent outcome was known at the management supplement. No admission threshold changed in response to returns. Source-hash snapshots and amendments are preserved. The equal-level annotation correction has zero candidate/plan impact and a field-for-field fresh native replay.

Closed-hour merges, strict right-confirmed pivots, reset-on-gap state, prior-day/session references, bounded prior profile windows and orderflow event/receipt cutoffs are tested. Native lookahead sampled nine router signals with no detected biased entries, exits or indicators. This is bounded evidence, not a universal leakage proof or independent validation.

Prospective registration: November 9 05:30–November 16 05:30 Asia/Colombo (00:00UTC boundaries). The previous November 1–8 reserved experiment remains untouched. Bounded current observations are development mechanics only. No complete historical trade archive, point-in-time full-exchange roster or reliable historical news feed was available.

## H. Economic verdict

**No demonstrated profitability and no promotion.** The positive routed subset is small and already inspected; the stricter integrated/ICT policies do not provide economic observations. The frozen sweep is negative, the frozen VWAP turns negative under +10bp/side friction, and the prior structure control remains negative. Added SMC/profile selectivity reduces trade frequency and total net versus router-only; this does not establish incremental edge. M1 improves this nine-trade sample while exposing a real native funding defect. Genuine order-flow profitability impact is unmeasured.

## I. Verification and acceptance

Final primary regression: **97 PASS,0 failures/errors/skips**. Ten main native variants, four native detail runs, one exact nine-trade native replay, native lookahead, actual public REST acquisition/scanner calls, genuine WS captures/replays, illustrative real-tier risk calls and independent Decimal/source-funding audits were executed. See [test log](tests-final.txt), [native results](native-results), [replay verification](native-replay-verification.json), [refusal probes](refusal-probes.json), [artifact hashes](artifact-hashes.sha256). The isolated rerun reproduced eight policies and matched every field of154 trade records. Two remaining policies were blocked by repeated public Gate metadata HTTP503, after a resolved local VFS disk-startup failure. Primary results were preserved. See [isolated verification](isolated-reproduction-verification.json) and [retry log](isolated-reproduction-resume.txt).

Earlier failures remain visible: proxy conflict/CA trust, generated and stale strategy staging, mistaken liquidation test expectation, native ROI fixture normalization, missing reporter candle type, funding source column assumption, invalid-event replay handling, and the unused equal-level annotation defect. They were corrected; native funding boundary charges remain an unresolved pinned-engine defect. See [failure records](failures) and the retained native failure logs.

| # | Requirement | Status | Evidence / material limit |
|---:|---|---|---|
|1|Actual opportunity selection|PARTIAL|583-contract current scan; causal reranking within five historical survivors; no full point-in-time universe/spreads.|
|2|Condition-aware two-recipe routing|PASS|ADX-dependent recipe choice, ten plans/nine native fills, both recipe ledgers.|
|3|Causal SMC decisions/control|PASS|Distinct structure ablation, old negative control, corrected metadata, prefix and native replay tests.|
|4|Distinct ICT logic/evaluation|PASS|Prior boundaries, displacement/FVG/location qualification;42 shortlisted vetoes, zero executions; no economic benefit claim.|
|5|Volume profile decisions/evaluation|PASS|POC/VAH/VAL/nodes, prior-window timing, three native trades; historical proxy and observed trade profiles separated.|
|6|Genuine orderflow acquisition/features|PASS|Real public WS signed-contract capture, native footprints, unit/provenance/coverage checks and raw replay.|
|7|Orderflow economic outcome/forward path|PASS|Explicit UNMEASURED economics, registered future interval, bounded callable shadow path and real NO_TRADE assessments.|
|8|Actual integrated trade plans|PARTIAL|Complete actual router/SMC/profile plans and lifecycle; fully integrated policy produces no TRADE plans under frozen rules.|
|9|Native M0/M1 lifecycle tests|PARTIAL|Nine matched trades/three partials and long/short pending-state fixtures; two source-funding failures; full persistent DB recovery unqualified.|
|10|Realistic leverage/equity risk|PARTIAL|Native1x gate and current-tier1/10/20x evaluator; full midnight MTM reference/historical tiers/operational leveraged gate unqualified.|
|11|Native Freqtrade backtests|PASS|Ten primary variants, four detail runs, fresh exact replay; zero-trade policies included.|
|12|Complete economic accounting|PARTIAL|Percent/R/cost/fill/portfolio ledgers and independent checks; M1 native funding defect and incomplete intrabar/actual-equity paths remain explicit.|
|13|Rejected/unselected evidence|PARTIAL|All92 route-ready parent candidates, full rank ledger and exact-clock native-parent matches; identical-new-management counterfactuals unavailable for every exclusion.|
|14|Causality/leakage verification|PASS|Closed candles/pivots/prior profiles/observed ticks, prefix tests, nine-signal native lookahead; bounded scope.|
|15|Reusable existing-role skills|PARTIAL|Three SKILL.md packages plus four static contract cases; no actual OpenBot model invocation or host isolation qualification.|
|16|Earlier laboratory preserved|PASS|329/329 prior files byte-identical; original operational guards unchanged; no advanced paper allowlist.|
|17|Reproduction/evidence/one PR|PARTIAL|One stacked PR, hashes and commands;8/10 isolated reruns match154 trade records, final2 blocked by Gate HTTP503. All10 primary runs and separate9-trade replay completed.|

## J. Delivery and next gate

Branch: `codex/bonus-opportunity-recipes`; base: `codex/session-3-market-intelligence-economics` / `48f34bcd51d080204c3e4bf90ec4b014a3319dd5`. The owner delivery and PR header give the exact final commit SHA and PR link. Nothing is merged. The [operator runbook](../../docs/operations/bonus.md) contains exact commands and output paths.

OpenBot Director responsibility: use the existing Market Researcher, Risk/Operations Reviewer and Director instructions on sanitized exports; preserve decision IDs/as-of clocks; resolve evidence disagreements; journal valid losses separately from decision/execution failures; enforce read-only host/API isolation before automation. An agent recommendation is never an engine gate. No new model service was added.

Persistent-paper responsibility, requiring separate owner authorization: repair/revalidate native partial funding and incomplete-fill lifecycle, prove native DB/process restart recovery and owner-host uptime, supply reliable quote clocks and sanctioned point-in-time inputs, reconstruct full midnight mark-to-market account equity/pending exposure, freeze an owner-approved operating risk budget, and independently evaluate the reserved future recipes. Keep M1 and leveraged operation disabled pending that work. No credentials, paid subscriptions, financial transactions, live/testnet orders, persistent paper deployment or GitHub merge was performed.
