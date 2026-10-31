# Session 1 — functional research foundation

**VERIFIED IN CODEX CLOUD, 2026-10-31 UTC. EXPLORATORY / UNQUALIFIED economics.**

Base/main SHA: `2343053ce68f6fff4525c5b67771ea445deb3779` (fetched and unchanged at session start). Clean starting tree; dedicated branch `codex/session-1-functional-foundation`. No AstraBot migration, orders, trading credentials, paid services, OpenBot bridge, automatic merge or later-session execution.

## Acceptance

| ID | Status | Actual proof and practical limit |
|---|---|---|
| S1-01 | PASS | Official Docker image 2026.10 pinned by immutable digest; actual version/config/native commands in `commands-and-results.txt`, `version-manifest.json`. |
| S1-02 | PASS | Bundled FreqUI 3.2.1 static HTML/JS/CSS HTTP 200; unauthenticated protected endpoint 401; login and native research-history/result HTTP 200, 386 trades. `ui-http-smoke.json`, `ui-verification.md`. Graphical owner-browser rendering REQUIRES OWNER-HOST VERIFICATION. |
| S1-03 | PASS | Actual public Gate USDT perpetuals BTC/ETH/SOL; 12 validated files, 1,201,184 bytes; 96 days, no observed OHLCV gaps/duplicates/bad bars. Source decision, acquisition receipt and `market-data-manifest.json`. Repeat acquisition sealed hashes identical. |
| S1-04 | PASS | Native VolumePairList/SpreadFilter plus bounded public metadata exporter: 583 eligible current crypto contracts, 20 shortlisted. Actual volume/bid/ask/spread in `scan-snapshot.json`; no trading process/order in scan. |
| S1-05 | PASS | Frozen `TrendPullbackBaselineV1` 1.0.0 and protocol hashes; exact card, long/short/no-setup, future-append and deterministic tests. |
| S1-06 | PASS | Native real-data futures backtest, July 30–October 30 UTC, 386 trades. Original native JSON retained, `native-backtest-result.json`; unmodified native ZIP remains local because it embeds source candle data. |
| S1-07 | PASS | `trade-ledger.csv`, `backtest-summary.json`, `backtest-report.md`; -6.5165487 USDT, 8.62208898 USDT maximum drawdown; explicit fees/funding and extra-friction scenarios. |
| S1-08 | PASS | Guard rejects live/credentials/unsafe overrides before engine; authenticated running paper API reports dry_run=true, max 2, configured stake 25, force_entry=false; no exchange credential environment variables forwarded. `paper-http-smoke.json`, `shutdown-verification.json`. |
| S1-09 | PASS | All requested operator actions exercised: doctor, scan, download, backtest, report, ui-up/down, paper-up/down, logs, test. One-container Cloud runner used for research due VFS disk constraints; UI/paper Compose services separately started/stopped. Beginner README/native equivalents. Owner-host install/long-running reliability still REQUIRES VERIFICATION. |
| S1-10 | PASS | [PR #1](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/pull/1) opened against main from this dedicated branch. Implementation commit `4815f1593df17d279f8d3104a53e995088280c47`; final evidence-link commit is the PR head. No merge/auto-merge. |

## Evidence levels

- **CODE EXISTS:** pinned Compose, four public mode configs, guard, native strategy, bounded scanner/data/report adapters, command wrapper, targeted tests and beginner runbook.
- **EXECUTED SUCCESSFULLY / VERIFIED IN CODEX CLOUD:** source-reviewed public acquisition (twice), sample validation/hashes, actual scan, native backtest/trades/report, 25 tests, 40-signal native lookahead diagnostic, FreqUI authenticated research APIs and short no-key paper startup/stop.
- **REQUIRES OWNER-HOST VERIFICATION:** OS/Docker installation, browser rendering, source access/jurisdiction, restart with open paper trades, consistent backup/restore and persistent operation. No Cloud result establishes 24/7 or profitability.
- **FAILED then repaired:** missing required disabled-service config fields; proxy/CA propagation; VFS concurrent container disk exhaustion; original July 1 window outside Gate's recent-10,000-bar limit; validator adaptation to native funding schema/UTC units. Exact representative failures are retained in command evidence. Strategy parameters were never optimized.
- **OUTSIDE SESSION / NOT QUALIFIED:** independent economic validation, commercial rights and OpenBot integration remain deferred; no future session is authorized.

## Result and preservation

Original strategy was frozen at `frozen-at.txt`; source hash stayed unchanged. Before any backtest result, an API-retention failure required a documented window correction and new protocol hash (`window-correction.md`). Current config/protocol hashes: `config-and-strategy-hashes.json`, `freeze.sha256`.

Native fees 0.0006 per side (research assumption), actual signed funding -0.0224773 USDT. Geometric pre-fee/pre-funding price P&L +3.91112 USDT; reconstructed fees 10.405191444 USDT. Reconciliation residual <0.000001 USDT. Additional friction worsens the result. No claimed economic GO or independent validation.

Raw datasets, original ZIP with embedded market-change candles, runtime credentials/configs, logs/caches and SQLite stay untracked. Small original native result JSON/derived trade ledger and manifests are committed. Immutable local sample is separated from disposable paper cache. All temporary UI/paper processes stopped; paper had zero open simulated positions at inspection. Operator stop produced native SIGINT exit 130 with application-shutdown-complete log, not a startup failure.

A transient Cloud exec-server outage occurred during the manual paper smoke. The same workspace was restored; the paper process was then inspected and explicitly stopped. No missing interval is represented as validated paper trading performance.
