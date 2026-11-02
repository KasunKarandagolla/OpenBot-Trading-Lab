# Additional Session 1 of 5 — working native research foundation

**Delivered:** one coherent real-public-data → native cheap scan → bounded closed-data research → frozen candidate plan → official Freqtrade backtest → independent economic/funding report → sanitized OpenBot export → safe stopped-state startup workflow. **Economics remain unqualified.** No merge, persistent owner-host trading, paid dependency, exchange key or real/testnet order.

The exact five-PR stack was refetched. Main is `2343053ce68f6fff4525c5b67771ea445deb3779`; the reviewed cumulative parent is PR #5, `29c07b80e8d3b15fb60f097a84eee30d730ffa40`, branch `codex/independent-master-audit`. All five PRs remained open. The new branch is `codex/additional-1-unified-research`, targeting that parent. [Exact branch SHAs](branch-provenance.json).

## Executed system

Use [the beginner runbook](../../docs/operations/foundation.md) and [Session 2 interfaces](../../docs/operations/foundation-session2-handoff.md).

```bash
docker compose -f deploy/freqtrade/compose.yaml pull
./scripts/lab-foundation.sh run owner-research-001
```

The complete executed final run is [session1-003-command.txt](session1-003-command.txt). It uses final code and no source amendment, repeats all six native portfolios, and **reuses the preserved 20-file sample without historical redownload**. The development run `session1-002` retains the original acquisition, explicit mechanical amendments, all faults, independent known-defect replay and full test evidence. `session1-001` retains the first access/configuration failures. Source data/native ZIPs stay private, while actual derived JSON/CSV/results/logs are committed.

| Requirement | Observed outcome and evidence |
|---|---|
| Engine and Compose | Official Freqtrade 2026.10 digest `sha256:0cc4b6dc9b16e0516d27efae1765e925da7d6aea5c8f3c3825930ffe3098d7c7`, CCXT 4.5.90; native version/config safety and Compose validation pass. [Environment](session1-003/environment-checks.json). |
| Venue access | Native CCXT Binance USD-M `exchangeInfo` returns **HTTP 451 restricted location**; no workaround. Gate public candles/funding/metadata work. [Exact errors](session1-003/venue-access.json). No Binance prices/funding/fees enter Gate economics. |
| Recent preserved sample | Five declared Gate linear USDT perpetuals; September 21–November 1 UTC source interval, October 1–November 1 UTC evaluation, end exclusive, 240 hourly warm-up. **20 files / 922,296 bytes**; 15m/1h futures, hourly mark, real funding events. All hashes, UTC/interval/OHLCV/funding coverage pass. [Manifest](session1-003/data-manifest.json), [validation](session1-003/data-validation.json), [source reuse](session1-003/source-reuse.json). |
| Old source loss | Initial prior raw paths were absent. Bounded native recovery matched **all 20 original hashes**; only absent test-source copies restored. No old evidence or preserved source overwritten. [Recovery](session1-002/prior-source-recovery.json). Private bundles for both cohorts are provided separately; [actual private restore smoke](source-restore-smoke.txt) verifies 20 recent files. |
| Cheap current universe | Existing native VolumePairList/SpreadFilter: **586 metadata-eligible**, 36 native candidates, **17 final shortlisted**, five deep checks. Explicit liquidity and metadata rejects remain. [Scan](session1-003/scan.json). Current membership is not historical discovery. |
| Current recipe/side research | Twenty recipe/side records across five markets: ten WATCH, ten REJECT; overall NO_TRADE. Quotes carry real source and receipt clocks; a current REST snapshot does not prove WS continuity or account risk. [Current assessment](session1-003/opportunities.json). |
| Actual historical plans | Existing causal top-three ranking/regime/parent recipe produces **28 parent opportunities, 27 explicit vetoes and one admissible plan**. Entry/stop/target/expiry, contrary evidence and gaps are retained. [Historical ledger](session1-003/historical-opportunities.json), [casebook](session1-003/casebook.json). Post-decision paths are labeled outcomes, not entry features. |
| Native research comparison | Six real portfolios / 198 native trade records per run, never additive returns. Independent order/fee/funding reconciliation and source-event bounds pass. [Economic report](session1-003/economic-report.json), [native results](session1-003/native-results/), [trade CSVs](session1-003/trade-ledgers/). |
| Exit repair | M0 inherits the audited frozen-price invalidation; original rank/entry/stop/target/hold parameters remain. Original router one fill **−0.11694800** versus repaired M0 same entry **+0.50352528 USDT**. This is one inspected development trade, not generalization. |
| Funding repair | Native before-exit event-once subclass passes both long/short synthetic partial lifecycle fixtures. Full exact-source old-market replay reproduces all nine old native trades/three partial exits and both violations; corrected replay keeps all entry keys and has **zero** source-bound violations. [Replay comparison](session1-002/funding-replay/comparison.json), [independent order reconciliation](funding-replay-reconciliation.json). Persistent partial-fill/restart behavior remains unqualified. |
| News/macro | Thin existing-library adapter for Fed, BLS, BEA, official Binance/Gate references and all five requested publishers. 105 bounded context records, including 43 official schedule entries in the retained-source parse; headlines remain unverified, clearance UNKNOWN, coverage partial. [Final briefing](session1-003/event-briefing.json), [original-source reparse](session1-002/event-briefing-reparsed.json). No confirmed incident or automatic trading signal is inferred. |
| OpenBot preparation | **48 records**, schema-validated, bounded under 1 MB, sanitized and published as ordinary read-only files. [Reader snapshot](session1-003/openbot/research-snapshot.json), [manifest](session1-003/openbot/manifest.json), [schema](../../research/foundation/openbot.schema.json). Current/historical environments and expired plans stay distinct. Actual OpenBot invocation/isolation remains unverified. |
| Lookahead | Native exit 0, no detected bias in **9 VWAP**, **20 sweep**, **1 M0 router** signals. M0's pinned native CSV is header-only, while its retained native text table reports the one checked signal. The summary records this discrepancy. [Summary](session1-003/lookahead-summary.json). Very small/inspected samples do not prove universal absence of leakage. |
| FreqUI | Static HTML/assets, unauthorized 401, authenticated version/history/result with actual 162-trade native baseline pass. Server stopped; auth overlay removed. Graphical browser rendering unobserved. [Smoke](session1-003/ui-smoke.json). |
| Dry-run prerequisites | Native keyless `dry_run=true`, initial state STOPPED, disposable SQLite, zero simulated trades, clean stopped process. Native SIGINT exit 130 is expected. [Smoke](session1-003/dryrun-smoke.json). No persistent paper start. |
| Tests | **117 tests pass**, no errors/failures/skips after exact prior-source restoration. Includes all 106 prior cases plus 11 new native funding/event/restore/reader/safety cases. [Full result](session1-002/tests-final.txt). Final wrapper also runs the current-cohort focused tests with its own run ID. |

## Native October economics

| Strategy | Trades | Native net USDT |
|---|---:|---:|
| TrendPullbackBaselineV1 |162|−6.38710333|
| VWAPTrendContinuationV1 |9|−0.44946448|
| LiquiditySweepReversalV1 |24|−0.72529188|
| RouterOnlyV1 control |1|−0.11694800|
| FoundationRouterM0V1 |1|+0.50352528|
| FoundationRouterM1V1 |1|+0.42626324|

Wallet 1,000 USDT, 1x, initial positions <=25 USDT, max two; common native fee **0.075%/side** is a conservative scenario, above observed current public generic **0.05%/side**. Historical account fee tier is UNKNOWN. Actual Gate funding events use native mark-open valuation. Additional 1.5/5/10/20 bp per-side turnover sensitivities are separate from native P&L and do not refill trades or simulate queue/slippage. Per-pair/side contributions, fees, funding, drawdown, holding/exits and worst/best losing/winning examples remain in the economic report and full ledgers.

The old exact-source funding-only comparison holds the original recipe, exits, schedule and **0.06%/side** assumption fixed: native control +1.49208851 versus event-once +1.49341400 USDT. Two original violations become zero. This small correction is accounting, not evidence of a new trading edge. It is not mixed with the October comparison.

The inherited plan's 0.0035 total entry-cost allowance is intentionally frozen. At the 0.00075 fee scenario, retaining the original 0.002 friction and 0.0003 adverse funding components would total 0.0038. This discrepancy is disclosed rather than silently retuning entry thresholds to change historical outcomes. Native fees/net/stresses are accurate for their stated scenario; operational plan admission must reconcile that allowance before promotion. See [complete implemented recipe and cost boundaries](../../docs/operations/foundation.md#recipe-and-cost-interpretation).

## Retained faults and remaining gates

Resolved mechanical faults: initial wrong Binance CCXT market-scope option (not proof of exchange denial), native async/sync CA inheritance, funding-package/CLI name collision, absent old source test, too-short 30-second stopped-state smoke timeout, and a reader guard falsely rejecting a public headline containing “password.” Original failures and source-hash amendments remain; the final complete run uses corrected code. The later genuine Binance 451 remains a venue access blocker. The native inherited-strategy lookahead CSV discrepancy remains documented with the actual text result.

No economic promotion: current-survivor membership, inspected history, one routed October trade, OHLCV limit fills, unknown historical depth/queue/news/receipt clocks and no completed independent holdout limit inference. Operational account midnight MTM/pending exposure, same-clock venue funding priority, native persistent partial-fill/restart recovery, source-sequenced current quotes, owner-host/browser checks and actual OpenBot host isolation remain open. The source bundle's private backup must leave this ephemeral workspace. No schedule observes the audit's reserved future holdout.

All prior baseline/VWAP/sweep source/config freezes and all old evidence remain byte-identical. The only deliberate parent-file edits are the root README (prior text retained in a separate operations document) and the Market Researcher instruction checkpoint. All **469 entries across four prior artifact manifests** pass. [Artifact preservation](artifact-preservation.json); complete parent file preservation and final integrity hashes are recorded beside this index.

Stop/rollback: stop owner UI/paper services if present, preserve private source bundles/SQLite/config and return to parent `29c07b80e8d3b15fb60f097a84eee30d730ffa40`. Exact commands, manual reader import and Session 2 interface boundaries are in the linked runbooks. This session does not install TradingAgents, a dashboard, new engine, agent swarm/execution bridge, paid source or tick archive.
