"""Build human-readable reports from independent evidence (no strategy execution)."""
import base64
import csv
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/master-audit'


def load(name):return json.loads((OUT/name).read_text())
def write(name,text):
    path=OUT/name
    content=text.strip()+'\n'
    if path.exists():
        if path.read_text()==content:return
        raise ValueError('preserve report: '+name)
    path.write_text(content)
def number(value):return '—' if value is None else f'{value:+.6f}'


def main():
    review=load('independent-review.json');comparison=load('comparisons.json')
    coverage=load('source-001/coverage.json');book=load('book-002/book.json')
    statuses=[('Data','PARTIAL','Exact five-market source restored; 24-contract samples expose retention/identifier gaps; no full historical universe.'),
              ('Screening','PARTIAL','592 current eligible instruments, 20 shortlisted; all five-market ranking rows reproduced; superiority outside that panel unproven.'),
              ('Strategy interpretation','PARTIAL','Actual VWAP/sweep predicates and causal structure replayed. True historical order flow and traded-volume profiles unavailable.'),
              ('Entry','PARTIAL','Closed-candle clocks and native fills reproduced; fresh BTC snapshot +20 sequenced updates passed. Historical spreads/queues/fill probability unmeasured.'),
              ('Target','PARTIAL','Known obstacles verified. Conservative objective variant harms aggregate results; no validated breakout exception or target superiority.'),
              ('Exit','PARTIAL','False early-exit diagnosis survives native development ablation; generalization unproven.'),
              ('Management','BLOCKED','M1 source-event discrepancy independently confirmed. Fixture repair passes; full repaired replay, partial fills and restarts unqualified.'),
              ('Economics','BLOCKED','All samples remain inspected development. No independent completed holdout, full historical universe or actual execution evidence.'),
              ('Reproducibility','PASS','Bounded result: 20 exact source files, 3 original policies field-for-field, 304 comparison trade records reconciled, 519 original files and 165 artifact hashes preserved.')]
    matrix='\n'.join(f'| {a} | **{b}** | {c} |' for a,b,c in statuses)
    order=['VWAPTrendContinuationV1','LiquiditySweepReversalV1','AuditRankingVWAPV1','AuditRankingSweepV1',
           'AuditRegimeVWAPV1','AuditRegimeSweepV1','AuditRegimeOnlyM0V1','RouterOnlyV1',
           'AuditStructuralCloseM0V1','AuditNearestObjectiveM0V1']
    labels={'AuditRegimeOnlyM0V1':'Router minus ranking (geometry retained)','AuditStructuralCloseM0V1':'Frozen-invalidation M0 candidate',
            'AuditNearestObjectiveM0V1':'Nearest-objective M0','AuditRankingVWAPV1':'Parent VWAP + ranking only',
            'AuditRankingSweepV1':'Parent sweep + ranking only','AuditRegimeVWAPV1':'Parent VWAP + regime only',
            'AuditRegimeSweepV1':'Parent sweep + regime only','RouterOnlyV1':'Original router M0',
            'VWAPTrendContinuationV1':'Original VWAP','LiquiditySweepReversalV1':'Original sweep'}
    byname={r['strategy']:r for r in comparison['policies']}
    table='\n'.join(f"| {labels[n]} | {byname[n]['trades']} | {number(byname[n]['net'])} | {number(byname[n]['extra_bps_per_side']['10'])} | {number(byname[n]['extra_bps_per_side']['20'])} | {byname[n]['native_closed_equity_drawdown_usdt']:.6f} |" for n in order)
    summary=f'''# OpenBot independent master-recipe audit — 1 November 2026

**Verdict: best research candidate identified; economic qualification BLOCKED.** No policy is a proven profitable candidate, paper-ready strategy or live trading recommendation.

Base: PR #4, `codex/bonus-opportunity-recipes`, `91ced4b32315793ddd08e52c80f572b39d76d700`. Work is additive: all **519** pre-existing tracked files and **165** old artifact hashes remain unchanged. No merge, order, testnet, persistent paper, credentials request, paid data or additional session was initiated. Attached audit statements were treated as claims to challenge. The separately named comprehensive prompt was absent; the supplied explicit mission governed this work.

## Acceptance

| Dimension | Status | Evidence and boundary |
|---|---|---|
{matrix}

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
{table}

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
'''
    write('README.md',summary)
    write('status.json',json.dumps(dict(dimensions={a:dict(status=b,scope=c) for a,b,c in statuses},economic_verdict='BLOCKED',candidate='RESEARCH_ONLY_FROZEN_INVALIDATION_M0',live_or_paper_ready=False),indent=2))
    notes={
      'trade-01':'VWAP long agrees with hourly structure. Prior-day high lies before 2R, but this trade wins and exits at the eight-hour cap. The obstacle is a warning, not proof of a hard ceiling.',
      'trade-02':'Meaningful losing continuation: price passed the known prior-day high, failed to reach distant 2R, and stopped. Target/management hypotheses are justified; selling at the hindsight high is not.',
      'trade-03':'Opposite sweep plan appears 30 minutes after the DOGE long while it is open. It did not fill. This is setup churn to investigate, not an actual opposing position or a missed profit.',
      'trade-04':'Winning short reversal against hourly UP structure. A countertrend label alone does not invalidate reversal logic. Parent and router geometry differ slightly.',
      'trade-05':'Negative example for the proposed repair: the original early thesis exit preserved more profit than the parent/new hold. Removing the rule harms this one trade, even though it helps the aggregate.',
      'trade-06':'Winning reversal long against hourly DOWN structure. The old partial reduces its winner, and its M1 funding lies outside source bounds. Neither the partial policy nor hourly alignment can be declared superior.',
      'trade-07':'Premature-exit example: entry already opposes hourly UP structure with ADX below 25. Strengthening ADX can trigger an exit without breaching the frozen signal-bar risk level. Native exit ablation recovers the later parent result.',
      'trade-08':'Meaningful losing reversal: complete pre-exit bars show about 2.088% favorable excursion before basic M0 stops. The old M1 saves profit here and dominates the entire M1 advantage. Exact intrabar/queue execution remains unknown.',
      'trade-09':'Strong winning VWAP long with a known prior-day high before 2R. An indiscriminate obstacle veto discards this winner, illustrating the cost of the conservative target experiment.',
      'trade-10':'Short reversal near the ADX routing boundary. The router exits at a small loss while the identical parent entry later profits. The new exit only removes this regime condition; it does not predict the future path.'}
    casebook=['# Source-candle trade casebook','All ten approved plans are included: nine fills and one unfilled plan. Every entry chart uses only fully closed 15m/1h candles at the decision cutoff. Subsequent paths are separate hindsight charts. Prices are sourced Gate OHLCV, not executable bid/ask. The four rejected examples are illustrative first chronological members of reason × parent-outcome groups, not unbiased performance estimates.']
    html_sections=[]
    for case in review['casebook']:
        identifier=case['case_id'];g=case['plan'];info=case['information_at_entry']
        detail=f"{case['symbol']} | {case['at']} UTC | {case['side']} {case['recipe']} | {case['status']}"
        body=f"Entry reference {g['reference']:.8g}; stop {g['stop']:.8g}; target {g['target']:.8g}; hourly ADX {info['adx_1h']:.2f}, structure {info['struct_direction_1h']}. Router net {number(case['router_net'])}; matched parent net {number(case['parent_net'])} USDT; router exit {case['router_exit'] or 'none'}."
        casebook += [f"## {identifier}: {detail}",notes[identifier],body,
                     f"![Entry information only](charts/{identifier}-entry.png)",
                     f"![Subsequent path — hindsight](charts/{identifier}-path.png)"]
        html_sections.append((identifier,detail,notes[identifier],body))
    for case in review['rejected_examples']:
        identifier=case['case_id'];detail=f"{case['symbol']} | {case['at']} | {case['reason']}"
        note=f"Actual rejected {case['side']} {case['recipe']} opportunity. Frozen-parent same-clock net {number(case['parent_net'])} USDT. Positive controls illustrate missed opportunities; negative controls illustrate avoided losses. This is parent management, not a hypothetical router fill."
        casebook += [f'## {identifier}: {detail}',note,f'![Entry information only](charts/{identifier}-entry.png)',f'![Parent subsequent path — hindsight](charts/{identifier}-path.png)']
        html_sections.append((identifier,detail,note,''))
    write('CASEBOOK.md','\n\n'.join(casebook))
    write('RECIPE.md','''# Ranked, regime-routed M0 with frozen invalidation — research candidate v1

This is the full specification of `AuditStructuralCloseM0V1`, not an economically qualified strategy. SUPPORTED means verified mechanics or bounded development evidence, not an established edge. Generalization of every economic choice below remains HYPOTHESIS. The control is the unchanged `RouterOnlyV1`.

| Step | Complete rule | Evidence label |
|---|---|---|
| Execution venue | Gate USDT linear perpetuals only; metadata must identify active eligible contract, units, precision and limits. Never price Gate fills/funding with Binance data. | SUPPORTED provenance/safety mechanics |
| Broad discovery | On demand, inspect eligible instruments, rank rough turnover/spread observations, cap shortlist at 20 and deep checks at five. Unknown bulk ticker clocks remain unknown. Current snapshots do not reconstruct historical membership. | SUPPORTED bounded observation; historical universe UNMEASURED |
| Historical panel | The tested strategy reranks only BTC, ETH, SOL, XRP, DOGE. Expansion requires verified point-in-time membership and complete venue-specific sources. The 24-name audit is availability only. | SUPPORTED limitation; market-wide superiority UNMEASURED |
| Rank coins | At each completed 15m close: absolute four-hour return relative to BTC (BTC uses its own return) +0.01 × activity ratio capped at 3; require trailing 24h OHLCV quote-volume proxy >=10m USDT; keep top three, deterministic symbol tie break. No signed-suitability variant was fitted. | HYPOTHESIS; formula and causality SUPPORTED |
| Context | Use the last fully closed 1h context. ADX >=25 routes to VWAP parent; below 25 to sweep parent. Hourly structure is recorded; a reversal may oppose it. Regime-alone superiority was not demonstrated. | HYPOTHESIS |
| VWAP entry | Existing parent: valid contiguous/warm data, session VWAP with >=8 session bars and same session; relative volume >=1; hourly ADX >=20; 1h and 15m EMA20/50 align; a genuine VWAP cross; signal low/high within 0.5 ATR of VWAP. Router additionally requires ADX >=25 and top-three admission. Long/short are symmetric. | SUPPORTED interpretation; economic edge HYPOTHESIS |
| Sweep entry | Existing parent: preceding 20-bar level is raided by 0.1–1 ATR, price closes back inside; rejection wick >=1.5 × max(body, 0.1 ATR), relative volume >=1.2, ADX <=30. Router admits only ADX <25 and top-three membership. This is a price-pattern definition, not observed stop-order flow. | SUPPORTED interpretation; economic edge HYPOTHESIS |
| Confirmation fidelity | Right-confirmed structure, FVG/displacement and prior-window profile annotations may describe context. Strict integrated/ICT variants had no fills. OHLCV profile is not traded volume-at-price; missing real trades/delta remain UNKNOWN. | SUPPORTED mechanics; claimed combined SMC/ICT/order-flow profitability REJECTED |
| Entry time/price | Closed 15m decision, five-minute expiry; native proposed-price admission within min(0.15%, 0.25 ATR/reference). Required live quote uses source/receipt clocks and bridged contiguous book updates; spread/depth/mark/funding/tier data must be valid simultaneously. Native historical fills are OHLCV simulations. | SUPPORTED bounded mechanics; historical queue/execution precision UNMEASURED |
| Frozen initial stop | Long: signal low −0.2 ATR. Short: signal high +0.2 ATR. Require price risk 0.3–2.5%, finite and on the loss side. This is a signal-bar risk boundary, not automatically the correct higher-timeframe thesis invalidation. Do not widen after entry. | HYPOTHESIS geometry; immutability SUPPORTED |
| Target room | Research control/candidate freezes 2× initial price-risk distance. Require (reward fraction −0.35%)/(risk fraction +0.35%) >=1.25 at actual proposed rate. Record known prior-day, confirmed swing and proxy value obstacles separately. Do not silently call room feasible merely because it is 2R. | HYPOTHESIS; universal nearest-obstacle gate REJECTED as a development improvement |
| Target uncertainty | A validated continuation/acceptance exception or more realistic target distribution is not established. For executable qualification, missing required target-feasibility evidence means NO NEW ENTRY; the offline control's fixed-2R assumption remains explicit. | UNMEASURED |
| Partial profit | M0 holds full quantity. M1 one-half-at-1R remains disabled: source-event funding fails, same-clock priority unknown, full repaired replay/partial-fill/restart lifecycle incomplete. | M0 mechanics SUPPORTED; operational M1 REJECTED pending reconciliation |
| Breakeven/trailing | No discretionary breakeven or trailing in this M0 candidate. Native initial stop, frozen target and max hold remain. Do not import the old M1 tighten logic into claims about this candidate. | SUPPORTED specification; superior alternatives UNMEASURED |
| Thesis and complete exit | Preserve native target/ROI execution and max hold: VWAP 8h, sweep 4h. Remove the old opposite-structure + ADX condition. A newly closed post-entry 15m close across the frozen risk level is structural-close invalidation; native initial stop will generally act first. Missing geometry exits. | SUPPORTED development diagnosis; replacement's generalization HYPOTHESIS |
| Position risk | 1x, <=25 USDT initial notional/position, <=2 positions, modeled per-position risk <=0.25% and aggregate reserve <=0.5% of equity, no DCA/opposite same-pair position. This is a 1,000 USDT research wallet, not a leverage recommendation. | SUPPORTED tested mechanics; operational capital suitability UNMEASURED |
| Account controls | Require current marks, pending exposure, correlation, margin tiers, native fill/lifecycle state and a real midnight MTM equity baseline before operational admission. Current realized-baseline callback is incomplete; no promotion to paper/live. | UNMEASURED operational completeness |
| NO TRADE | Any missing essential source, stale/unsequenced quote, incomplete/warming candles, ambiguous source units, failed eligibility/risk/account state, no parent setup, rank veto, bad geometry/room, expired plan, conflicting or existing same-pair position means no new entry. UNKNOWN is never silently converted into confirmation. | SUPPORTED fail-closed principle |

The offline development results test this candidate's specific exit change under native candle assumptions. They do not execute the missing live account/quote gates. A complete operational version must pass those gates and the independently observed holdout; no such version is qualified here.
''')
    write('ROOT_CAUSES.md','''# Prioritized root-cause register

| Priority / ID | Actual mechanism and evidence | Action / status |
|---|---|---|
| P0 DATA-01 | Five-survivor test is not full historical discovery; 24-name sample has retention/identifier gaps and no listing/delisting roster. | Implemented bounded public source audit and manifests. Broad economics BLOCKED pending complete venue-correct cohort. |
| P0 FUND-01 | Native inclusive funding interval reprocesses a same-clock event after partial fill; two recorded M1 violations, both fixture directions reproduce double counting. | Experimental native event-once valuation repair passes fixtures; M1 remains disabled. Full market replay, actual priority, partial fills/restart still required. |
| P0 OPS-01 | Account MTM midnight baseline, pending/exchange fills and recovery remain incomplete. | No operational promotion; code is absent from operational allowlist. |
| P1 EXIT-01 | ADX/opposite-hourly condition can strengthen after a countertrend entry without new price invalidation. Three trades aggregate −1.066381 against parent management, but SOL benefits. | Implemented frozen-invalidation M0; same nine entries, native +1.066381 improvement. Development support only. |
| P1 QUOTE-01 | Bulk ticker timestamps absent; initial collector lacked explicit WS proxy routing. | Timestamped REST + equal-depth buffered WS bridge now passes 20 contiguous updates. Initial failure preserved. No persistent reliability/fill claim. |
| P1 TARGET-01 | All router targets are fixed 2R; known prior-day highs intervene. | Implemented conservative nearest-objective ablation. Four fills / weaker aggregate, slightly negative +20bp stress. Reject universal veto as improvement; breakout exception remains unmeasured. |
| P1 SELECT-01 | Absolute relative return conflates strength/weakness and setup direction. Parent-exit rejection diagnostics confound management. | Entire ranking CSV replayed; native ranking-only and regime-only controls completed. Signed suitability remains an untested hypothesis; no threshold search. |
| P1 COST-01 | Native 0.06% fee differs from current public 0.075% generic taker rate; historical spread/depth absent. | Report +1.5/5/10/20bp per-side sensitivity and actual funding. No backdated fee claim or refilled-slippage claim. |
| P2 INTERP-01 | Routed positive trades do not prove ICT/SMC/true profile or order-flow edge; integrated/ICT abstain. | Label source fidelity and unmeasured incremental economics. Retain zero-trade and harmful examples. |
| P2 REGIME-01 | DOGE opposing plan appears within 30m as ADX crosses 25; no opposite fill. | Document setup churn; do not invent a live opposing trade. Hysteresis is untested and was not tuned. |
| P2 REPRO-01 | Original downloader timed out on unrelated metadata and outer-only proxy hostname. | Add native public-futures scope and inherit the container's reachable proxy; exact original source restored. Failures retained. |
''')
    write('REPRODUCE.md','''# Reproduction and evidence boundaries

Use Linux/WSL, Git, Python3, Docker + Compose, and host pandas/matplotlib for figures. Native research runs in official Freqtrade 2026.10 / CCXT 4.5.90, pinned image:

`freqtradeorg/freqtrade:2026.10@sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7`

From the committed audit branch:

```bash
bash scripts/master-reproduce.sh owner-audit-001
```

This creates an independent checkout and output tree under ignored `work/master-reproductions/`. It removes generated outputs only in that new checkout, retaining experiment registrations and every old session artifact. Retained exact source files are copied if present; otherwise public native acquisition runs. Source mismatch, unavailable metadata or changed archive retention fails explicitly. No new quote/trade history is fabricated to obtain a match.

Order: predeclared source preflight → bounded book probe → source acquisition/identity → source preservation and test-source restoration → source-candle review → native funding fixture → ten native development policies → Decimal/source-funding comparisons → full tests → figures. Each collector refuses reused output IDs. The initial audit's failed attempts are retained; a new host need not reproduce a routing failure before the corrected probe succeeds. `master_run_ablations.py --resume` retries only incomplete policies, preserving failed logs/directories and refusing completed unregistered output.

Individual host commands are `python3 scripts/master_preflight.py NEW_ID`, `python3 scripts/master_preservation.py`, `python3 scripts/master_restore_test_sources.py` and `python3 scripts/master_charts.py`. Native commands are `scripts/master_native.py acquire`, `scripts/master_verify_sources.py`, `scripts/master_review.py`, `scripts/master_funding_probe.py`, `scripts/master_run_ablations.py`, `scripts/master_compare.py`, and `-m unittest discover -s tests -v`. Run each in the pinned image with repository mounted at `/lab`, working directory `/lab`, the host CA bundle mounted read-only, `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` set to that bundle, and the inherited supported proxy. Do not inject exchange credentials or disable TLS verification. Examples are implemented in the reproduction script.

The optional `scripts/master_current.py` is a bounded, read-only deep analysis of the five recorded shortlisted instruments using existing parent/context components. It emits NO_TRADE for execution because simultaneous quote/account risk approval is absent. It neither starts paper trading nor creates orders. It records computed observations; a full immutable raw current-candle replay is not qualified.

Generated source-candle arrays for plotting are ignored local `work/master-chart-data.json`; the repo retains 28 figures and the numerical casebook. Raw Gate feathers, downloaded ZIPs and native result archives remain local. Public evidence contains hashes, request outcomes, comparison JSON, logs, strategy code and reports. Hash identity proves the original research sources, not entitlement to redistribute them.

Original-source checks preserve all 519 base files and validate all 165 old artifact hashes. `preservation-source.json` lists file hashes. `source-identity.json` lists the 20 source matches. `independent-review.json` includes all 82 rejected signals and all 10 plans. `comparisons.json` includes all ten portfolios, 304 internally reconciled records and source-event bounds; never sum these separate portfolios. Bootstrap seed 4101 / 10,000 draws is descriptive only.

Mechanical config/report and source-review failures are retained alongside their corrected results. The original two native acquisition failures were routing/metadata issues; source availability is established by the corrected successful attempt. The original `book-001` timeout was collector routing; `book-002` is the corrected sequenced observation.

The 17 November–1 December UTC holdout is future and unobserved. No scheduler, extra session, paid resource, merge, paper deployment or live/testnet order is authorized by these commands. Full historical universe, executable queue fills, a repaired M1 lifecycle and operational account MTM remain outside the passed scope.
''')
    with (OUT/'coverage-panel.csv').open('w',newline='') as file:
        fields=['symbol','currently_eligible','gate_july','gate_october','binance_october_15m']
        writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader()
        for metadata in coverage['panel_metadata']:
            symbol=metadata['requested_symbol'];base=symbol.removesuffix('_USDT')
            def status(date):return '; '.join(r['kind']+':'+r['status'] for r in coverage['gate_samples'] if r['symbol']==symbol and r['date']==date)
            # Preserve the initial sample's base-symbol label; actual requested
            # archive paths identify USD-M contract IDs. Later collectors emit
            # the full contract ID consistently.
            archive=next(r for r in coverage['binance_samples'] if r['symbol'] in (base,base+'USDT'))
            writer.writerow(dict(symbol=symbol,currently_eligible=metadata['currently_eligible'],gate_july=status('2026-07-26'),gate_october=status('2026-10-29'),binance_october_15m=archive['status']))
    # A standalone, portable casebook for the user; report tables remain in MD.
    output=Path('/codex/browser/projectless/0010-files-mentioned-by-the-user-uploaded-file-pointe/output')
    if output.is_dir():
        sections=[]
        for identifier,detail,note,body in html_sections:
            def picture(kind):
                data=base64.b64encode((OUT/'charts'/(identifier+'-'+kind+'.png')).read_bytes()).decode()
                return f'<img alt="{identifier} {kind}" src="data:image/png;base64,{data}">'
            sections.append(f'<section id="{identifier}"><h2>{html.escape(identifier+": "+detail)}</h2><p>{html.escape(note)}</p>{picture("entry")}<details><summary>Show subsequent price path and outcome (hindsight)</summary><p>{html.escape(body)}</p>{picture("path")}</details></section>')
        document='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>OpenBot independent audit casebook</title><style>body{max-width:1150px;margin:30px auto;padding:0 20px;font:16px/1.6 system-ui;color:#203141;background:#f8fafb}section{background:white;padding:22px;margin:25px 0;border:1px solid #dbe3e8;border-radius:12px}img{width:100%;height:auto}summary{cursor:pointer;padding:12px;background:#edf2f6}h1,h2{line-height:1.25}nav a{margin-right:15px;display:inline-block}</style><h1>OpenBot independent source-candle casebook</h1><p><strong>Economic qualification BLOCKED.</strong> Ten approved plans (nine filled, one unfilled), four illustrative rejected controls. Each entry figure uses only information available at its decision cutoff. Later paths are hidden separately and explicitly contain hindsight. No actual queue-fill, market-wide superiority or profitable strategy claim.</p><nav>'+' '.join(f'<a href="#{i}">{i}</a>' for i,_,_,_ in html_sections)+'</nav>'+''.join(sections)+'</html>'
        (output/'OpenBot_Audit_Casebook.html').write_text(document)
    print('Reports built from independent evidence')


if __name__=='__main__':main()
