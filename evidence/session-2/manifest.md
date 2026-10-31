# Session 2 — functioning trading intelligence with unqualified development economics

**CODE IMPLEMENTED / EXECUTED IN CODEX CLOUD / TESTED.** Two independently registered Freqtrade strategies, real all-strategy backtests and deterministic comparison are delivered. No profitability qualification or paper promotion.

Base: Session 1 implementation head `d76b6093796f78ce628943e8252033b34e9958ef`, still OPEN/unmerged PR #1. Main remains `2343053ce68f6fff4525c5b67771ea445deb3779`. Dedicated branch `codex/session-2-trading-intelligence`; stacked PR base `codex/session-1-functional-foundation`. No merge/main edit.

Official Freqtrade 2026.10 image digest preserved; Python 3.14.10, CCXT 4.5.90, Pandas 3.0.6, NumPy 2.5.4, TA-Lib 0.8.2. No new dependencies. Linux Cloud execution; one disposable runner, no forwarded exchange/demo credential bindings or persistent paper process. See version-manifest.json/runtime-safety.json.

Real sample: lawful bounded Gate public REST reacquisition after finding no retained raw data/mount. All 12 files / 1,201,184 bytes match Session 1 byte for byte. Download July 26–October 30, evaluation July 30–October 30 UTC end exclusive, BTC/ETH/SOL linear USDT perpetuals. Futures 15m/1h plus actual mark/funding. Same noncommercial/no-raw-redistribution rights scope; original results/manifests untouched. Entire sample is inspected DEVELOPMENT data.

| Strategy | Trades | Native net USDT | PF | Expectancy USDT | Max DD USDT | +20bp/side net | Research status |
|---|---:|---:|---:|---:|---:|---:|---|
| Baseline | 386 | -6.516549 | 0.8517 | -0.016882 | 8.622089 | -41.200520 | REJECTED under evaluated assumptions |
| VWAP continuation | 17 | 0.816408 | 1.5418 | 0.048024 | 0.660301 | -0.698434 | INSUFFICIENT EVIDENCE |
| Sweep reversal | 39 | 1.751484 | 1.6305 | 0.044910 | 1.004810 | -1.706488 | UNQUALIFIED DEVELOPMENT RESULT |

Wallet 1,000, configured stake cap 25, 1x, max 2, native protections, fee 0.06% each side, actual signed funding. Detailed fees/funding/friction/directions/pairs, payoff/outliers, holding/exits, R and turnover: [comparison-report.md](comparison-report.md), [strategy-comparison.json](strategy-comparison.json). Native JSON, CSV ledgers, feature candidates and callback decisions: runs/<strategy>/. Full native ZIPs/raw candles stay local.

## Acceptance

| ID | Actual status | Evidence / limit |
|---|---|---|
| S2-01 | TESTED | Original 25 foundation tests pass; Session 1 source/config/evidence unchanged |
| S2-02 | EXECUTED / TESTED | Both new strategies loaded and traded in official 2026.10 |
| S2-03 | TESTED | Exact VWAP/hour/range/volume/causality vectors |
| S2-04 | TESTED | Mechanical bullish/bearish/NO_TRADE fixtures for both; actual L/S trades |
| S2-05 | TESTED within native model | Entry deviation, 5-minute expiry/paper quote invalidation, fixed stops, 2R ROI and hold requests; no historical queue proof |
| S2-06 | TESTED within documented limits | <=25, 1x, max2/one-symbol/noDCA, cost-inclusive intended risk; full daily mark-to-market halt NOT ENFORCED |
| S2-07 | EXECUTED / TESTED | Baseline386/VWAP17/sweep39 on identical cohort; repeated ledgers identical |
| S2-08 | EXECUTED / TESTED | Native result JSON and full trade CSV/costs retained |
| S2-09 | EXECUTED / TESTED | Common fees/funding plus separate 5/10/20bp extra friction |
| S2-10 | EXECUTED / TESTED with sample limits | Append-future tests and native no-bias17/20 signals; thin VWAP sample |
| S2-11 | EXECUTED / TESTED | research-all/compare/strategy-info; doctor/test/lookahead and retained-data refusal |
| S2-12 | CODE IMPLEMENTED | Focused stacked PR submission; final link/receipt recorded after creation |

The core trading-intelligence milestone is demonstrated. Extended paper risk qualification, independent economic validation, owner-host pending-order/partial-fill/restart/browser/uptime and OpenBot isolation remain unqualified or OWNER-HOST VERIFICATION REQUIRED. Challengers are research-only; original baseline paper selection unchanged. The daily halt is realized closed-trade UTC P&L <=-10 only, not full account mark-to-market loss. Stops/limits are simulated and unavailable while the process is offline.

## Evidence index

- experiment-ledger.md; experiment-protocol.json; source-data-manifest.json; acquisition-output.txt
- strategy-vwap-card.md; strategy-sweep-card.md; freeze.sha256; freeze-before-first-outcome.sha256; freeze-amendment.json
- comparison-report.md; strategy-comparison.json; research-summary.json; strategy-risks.json; signal-counts.json
- test-results.md; test-output.txt; replay-verification.json; compare-verification.json
- lookahead-results.md; lookahead-summary.json; native-lookahead-vwap.csv; native-lookahead-sweep.csv
- economic-limitations.md; known-gaps.md; operator-demonstration.md; commands-and-results.txt

Faults preserved: initial Cloud conflicting-proxy options; fixture constructor errors before outcomes; callback fallback fault hardening without parameter changes; native Pandas CSV-append export failure resolved with fresh derived files. No threshold search. First outcome/source snapshot remains commit `d7a609bdb564f5e1d7b69f10b5241d5ab571c2b1`.

Reproduce: initialize runtime, pull pinned image, inspect strategy-info, acquire exact cohort only if absent/available, research-all, compare, research-lookahead, test. Preserve raw files and original manifests. If the rolling source window ages out, stop and declare a separately versioned cohort before any future rerun. Stop UI/paper before backups; rollback to Session 1 head while retaining DB/data/private config. No automatic merge or subsequent session.
