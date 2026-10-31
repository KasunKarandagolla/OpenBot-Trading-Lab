# OpenBot independent master-recipe audit — 1 November 2026

**Verdict: best research candidate identified; economic qualification BLOCKED.** No policy is a proven profitable candidate, paper-ready strategy or live trading recommendation.

Base: PR #4, `codex/bonus-opportunity-recipes`, `91ced4b32315793ddd08e52c80f572b39d76d700`. Work is additive: all **519** pre-existing tracked files and **165** old artifact hashes remain unchanged. No merge, order, testnet, persistent paper, credentials request, paid data or additional session was initiated. Attached audit statements were treated as claims to challenge. The separately named comprehensive prompt was absent; the supplied explicit mission governed this work.

## Acceptance

| Dimension | Status | Evidence and boundary |
|---|---|---|
| Data | **PARTIAL** | Exact five-market source restored; 24-contract samples expose retention/identifier gaps; no full historical universe. |
| Screening | **PARTIAL** | 592 current eligible instruments, 20 shortlisted; all five-market ranking rows reproduced; superiority outside that panel unproven. |
| Strategy interpretation | **PARTIAL** | Actual VWAP/sweep predicates and causal structure replayed. True historical order flow and traded-volume profiles unavailable. |
| Entry | **PARTIAL** | Closed-candle clocks and native fills reproduced; fresh BTC snapshot +20 sequenced updates passed. Historical spreads/queues/fill probability unmeasured. |
| Target | **PARTIAL** | Known obstacles verified. Conservative objective variant harms aggregate results; no validated breakout exception or target superiority. |
| Exit | **PARTIAL** | False early-exit diagnosis survives native development ablation; generalization unproven. |
| Management | **BLOCKED** | M1 source-event discrepancy independently confirmed. Fixture repair passes; full repaired replay, partial fills and restarts unqualified. |
| Economics | **BLOCKED** | All samples remain inspected development. No independent completed holdout, full historical universe or actual execution evidence. |
| Reproducibility | **PASS** | Bounded result: 20 exact source files, 3 original policies field-for-field, 304 comparison trade records reconciled, 519 original files and 165 artifact hashes preserved. |

PASS refers only to its stated bounded scope. No status grants operational approval.

## Data foundation and bounded acquisition

The registered 24-contract source panel is BTC, ETH, SOL, XRP, DOGE, BNB, ADA, AVAX, LINK, DOT, LTC, BCH, TRX, TON, SUI, APT, ARB, OP, NEAR, ATOM, FIL, ETC, WIF and PEPE. These are familiar strata, not a reconstructed point-in-time universe or an unbiased market-cap sample. No unavailable identifier was silently replaced.

The source panel and exact-source checks preceded new strategy outcomes. The initial WS failure left economics explicitly BLOCKED; the collector routing correction and successful sequence probe came later. Two days were sampled: 26 July and 29 October 2026 UTC. Of **240** Gate checks, **161** complete daily candle grids passed, **46** funding samples showed events but remain availability-only, and **33** checks were blocked. Every July 26 5m request hit Gate's documented response: the requested history exceeded its last 10,000-candle limit. Exact `TON_USDT` returned no usable samples. These failures prevent broad historical execution qualification. Sampling two days does not prove continuity across the intervening period, historical funding schedules, historical contract-size changes or listing/delisting membership.

Binance's official published dataset terms were fetched before archive downloads and recognize personal nonproduction historical research. **23/24** October 29 USD-M 15m ZIPs passed SHA256 and full-day candle-grid checks; exact `PEPEUSDT` returned 404. The panel did not substitute a multiplied-token alias. Binance marks, funding, fills and Gate prices were never combined. Rights findings do not establish personal legal entitlement. Raw data remain local and are not redistributed.

The current public Gate metadata sweep found **592** eligible contracts and shortlisted 20 by observed turnover. Bulk ticker clocks remain UNKNOWN and are screening observations only. For shortlisted BTC, a timestamped REST snapshot was bridged to **20 contiguous** buffered WS updates after explicit runtime-proxy routing. Source/receipt clock checks, equal REST/WS depth (20), base-ID bridge and update continuity passed. This is a bounded observation, not persistent feed reliability, full-depth fill proof or an execution permission. Initial collector-routing and native-metadata failures remain in the evidence.

All **20** original five-market 15m/1h/mark/funding files were reacquired with pinned Freqtrade 2026.10 / CCXT 4.5.90. After the original UTC trim, every file matched the old SHA256 byte for byte. Native parent VWAP, parent sweep and Router M0 trades then matched **every original trade field**. Gate remains the sole execution reference.

## Independent challenge of the prior audit

Source candles reproduce **92** routed parent candidates → **50** ranking/screen vetoes → **32** target/cost vetoes → **10** plans → **9** fills. All **46,080** ranking rows and **9,216** decision times, including warmup, were ingested. Selection matched at every time; independent score error was below 1e-16. CSV floating representation explains the tiny absolute quote-volume rounding difference. The evaluation calendar contains 8,256 decision clocks; the native loop processes 8,255 intervals. This arithmetic does not prove full-market discovery.

All nine fill clocks match original parent fills. Original parent management yields **+2.20681621 USDT**, Router M0 **+1.08945652**, a difference of **−1.11735969**. Three early ADX/opposite-direction exits account for **−1.06638069**. This aggregate hides a useful negative example: SOL Aug 25 benefited from the old early exit by **+0.17210320**, while ETH Sep 11 and XRP Oct 2 were harmed. Blanket claims that early exits always fail are rejected.

The 50 rank exclusions contain 46 matched original-parent fills totaling **−3.28635561**; the 32 cost/target exclusions match 32 parent fills totaling **+0.63293686**. Four rank exclusions have no matched parent fill and receive no fictional P&L. Parent exit rules differ, so these are diagnostic opportunity costs, not identical-management portfolio attribution. Pure ranking and pure regime native controls below reduce that ambiguity; their portfolios still differ in admitted opportunities and resulting exposure.

All ten router plans use 2R fallback targets and lack confirmed ICT. True historical order flow is UNKNOWN and profiles are OHLCV typical-price proxies. Three VWAP longs have prior-day highs before 2R. Two of them are strong winners, so a universal prior-high veto is not justified. Price-defined sweeps do not prove actual stop orders, manipulation or institutional intent. Right-confirmed pivots, FVG and displacement labels have causal mechanical definitions; their incremental economic value remains unproven. Strict integrated/ICT policies' zero trades cannot establish an edge.

## Controlled native development comparisons

August 5–October 30 UTC, end-exclusive; 1,000 USDT wallet, 1x, at most 25 USDT initial notional per position and two positions. All policies use native fees of 0.06% per side and venue-specific source funding. Extra friction is a turnover overlay that preserves modeled fills. Drawdown is native closed-trade account equity, not a full midnight/intraday mark-to-market reconstruction.

| Policy | Trades | Net USDT | +10bp/side | +20bp/side | Native closed-equity max DD USDT |
|---|---:|---:|---:|---:|---:|
| Original VWAP | 30 | +0.959708 | -0.434571 | -1.828851 | 1.256935 |
| Original sweep | 86 | -2.259367 | -6.293016 | -10.326666 | 3.917489 |
| Parent VWAP + ranking only | 21 | +1.276269 | +0.306998 | -0.662272 | 1.016560 |
| Parent sweep + ranking only | 39 | +1.238756 | -0.533406 | -2.305568 | 1.301472 |
| Parent VWAP + regime only | 25 | +0.147239 | -1.028550 | -2.204339 | 1.297179 |
| Parent sweep + regime only | 64 | -1.158249 | -4.182118 | -7.205988 | 2.982920 |
| Router minus ranking (geometry retained) | 17 | +0.665254 | -0.144503 | -0.954259 | 0.726735 |
| Original router M0 | 9 | +1.089457 | +0.671195 | +0.252934 | 0.491691 |
| Frozen-invalidation M0 candidate | 9 | +2.155837 | +1.738639 | +1.321440 | 0.491691 |
| Nearest-objective M0 | 4 | +0.345768 | +0.170709 | -0.004350 | 0.297863 |

These are **10 separate portfolios / 304 trade records**, never a combined portfolio. All reconcile from native orders using independent Decimal arithmetic, and all lie within source-event funding quantity bounds. Detailed long/short splits, friction, funding, capital use and descriptive uncertainty are in [comparisons.json](comparisons.json).

The exit candidate changes only the early ADX exit: entries, initial stops, targets and max holding periods remain the control's. Its nine entry keys match exactly and its **+1.06638069 USDT** improvement reproduces the diagnosed three-trade difference, including the SOL harm. Its descriptive IID-bootstrap 95% net interval is approximately **[−0.2511, +4.3461] USDT**. The interval includes zero; no economic qualification follows. Removing its three best winners leaves **+0.27570628**, compared with **−0.36497732** for the old router, but both statistics reuse known history.

Nearest-objective admission reduces fills to four and net to **+0.34576844**, becoming slightly negative at +20bp/side. This conservative gate is rejected as an improvement on this development sample; no posthoc breakout exception was fitted. Ranking helps these development parent portfolios, while ADX regime filtering alone degrades VWAP and does not make sweep profitable. Do not add separate ranking/parent nets together and call them a tradable combined recipe.

## Partial-exit funding and management

Independent source reconstruction confirms **0** Router M0 and **2** Router M1 funding-bound violations. Native internal accounting can reconcile while its funding input is wrong. Pinned native lifecycle methods reproduce a same-clock funding event charged twice after a partial exit, for both long and short fixtures. The experimental event-once mixin values events with the native exchange method and passes both fixtures under an explicit before-exit priority assumption. Native source and old results were not patched.

**M1 remains disabled.** The mixin has an in-memory cursor and is not restart-safe; no full repaired M1 market replay, exchange partial-fill lifecycle, same-clock priority or persistent recovery is qualified. Old M1's +0.40263199 advantage is dominated by one XRP trade; removing it leaves **−0.05879099**. No profitable management claim survives this evidence standard.

Current Gate metadata reports a generic 0.075% taker fee for the five familiar contracts, above the historical 0.06% assumption. A +1.5bp/side sensitivity is reported; current public rates do not reconstruct historical account-tier fees. Historical bid/ask, depth, latency, queue fills, realized leveraged execution, pending-account state, restart recovery and midnight account MTM remain unmeasured.

## Research decision and remaining gate

Use [the complete frozen-invalidation M0 specification](RECIPE.md) as the best **research candidate**, retaining the original router as its control. Structural exit diagnosis is supported in inspected development; profitable generalization is not. No threshold search or optimization was performed. Hypotheses were registered before new native outcomes; the pure regime supplement completed the original attribution hypothesis after eight development results, with no tuned threshold. Mechanical failures and amendments are retained.

The independent prospective interval is **17 November 05:30 through 1 December 05:30 Asia/Colombo** (Nov 17–Dec 1, 00:00 UTC). It is unobserved, uses neither prior reserved interval, and has no scheduler or automatic collection. Before economic qualification: complete a venue-specific broader cohort with point-in-time eligibility, independently observe the frozen holdout, measure execution friction and reconcile operational lifecycle/account risk. Those milestones are **BLOCKED**, not passed by these tests.

See [casebook and 28 figures](CASEBOOK.md), [prioritized root causes](ROOT_CAUSES.md), [reproduction](REPRODUCE.md), [source coverage](source-001/coverage.json), [native funding lifecycle](native-funding-lifecycle.json), and [independent review](independent-review.json).

## Primary sources

- [Gate documented source clocks and book sequence procedure](https://www.gate.com/docs/developers/futures/ws/#order-book-api)
- [Gate public perpetual API](https://www.gate.com/docs/developers/apiv4/en/#futures)
- [Official Binance public archive formats](https://github.com/binance/binance-public-data)
- [Official Binance dataset terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md)
- [Audited PR #4](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/pull/4)
