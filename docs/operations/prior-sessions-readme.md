# OpenBot Trading Lab

A **paper-only crypto futures research lab**, built around official Freqtrade and FreqUI. Session 1 adds a real public-data scanner, a frozen baseline strategy and native historical backtesting. No profitable strategy is claimed. OpenBot integration is deferred to Session 4; no agent has an administration bridge.

Read the actual [Session 1 evidence/status](evidence/session-1/manifest.md), [backtest report](evidence/session-1/backtest-report.md), [known gaps](evidence/session-1/known-gaps.md) and [source-use decision](evidence/session-1/source-rights.md). These distinguish successful Cloud execution from owner-host verification. The [original design](docs/design/README.md) remains preserved, with an explicit Session 1 scope correction.

## Install on your computer

Use Docker Engine with Compose v2, Git and Python 3. On Windows, install Docker Desktop with WSL2, enable its WSL integration, and run these commands in your WSL Linux terminal. Owner Windows/macOS/Linux installation has not been verified in Cloud. Keep the computer awake for paper operation.

```bash
git clone https://github.com/KasunKarandagolla/OpenBot-Trading-Lab.git
cd OpenBot-Trading-Lab
git checkout codex/session-1-functional-foundation
python3 scripts/init_runtime.py
docker compose -f deploy/freqtrade/compose.yaml pull
./scripts/lab.sh doctor
./scripts/lab.sh test
```

The official image is pinned to **2026.10 and an immutable SHA256 digest** in Compose. No local application build, paid service, exchange account or exchange API key is needed. `init_runtime.py` creates local UI authentication in `user_data/runtime/api.json`, excluded from Git. Never paste it into chat or commit it. No injected Cloud demo credentials are passed to the engine.

## Run research

First read the [source-use decision](evidence/session-1/source-rights.md). This sample is personal/noncommercial, not cleared for commercial service or raw-data redistribution. Your jurisdiction/network must permit the source. Stop on geographic/access denial; do not bypass it.

```bash
./scripts/lab.sh scan
./scripts/lab.sh download
./scripts/lab.sh backtest
./scripts/lab.sh report
```

`scan` uses native VolumePairList (60 candidates, at least 10m USDT 24h quote volume) and SpreadFilter (at most 0.2% observed spread). A small public CCXT metadata exporter removes noncrypto, premarket, delisting, unknown-age and under-30-day contracts and caps the result at 20. Missing volume/spread excludes a pair. Unknown venue timestamp is labeled UNKNOWN. It fetches metadata and bulk tickers, not deep candles for the market, and cannot place orders. Snapshot: `evidence/session-1/scan-snapshot.json`. No age/volatility alpha claim.

`download` fetches only BTC/ETH/SOL linear USDT perpetuals, 15m/1h futures plus native 1h-labeled mark/funding series, July 26–October 30, 2026 UTC. Funding events have their own 8-hour schedule. Gate currently limits candle requests to the most recent 10,000 points: reproduction can fail once this fixed window ages out. Preserve your local sample. No archive fallback is automatic.

Freqtrade's downloader can return observations beyond the requested end. `seal_data.py` records original hashes/counts and discards only rows outside the frozen UTC sample. It never fills gaps or alters prices. Validation checks timestamps, gaps, OHLCV, contract identity, funding/mark coverage and warm-up; failures block backtesting. Existing research data are preserved: download refuses to overwrite them. To retry a failed partial download, stop activity and move `user_data/data/research` to a local quarantine folder, then rerun download. Do not mix experiments or delete your only retained sample.

`backtest` verifies sample hashes, uses **static BTC/ETH/SOL**, July 30–October 30, 2026 UTC, 25 USDT stakes, 1x, max two positions and a 1,000 USDT simulated wallet. Fee assumption: **0.06% each side**, not a verified account rate. It uses actual native funding observations. Today's scanner is never substituted for historical membership. The [strategy card](research/strategy-cards/TrendPullbackBaselineV1.md) gives exact rules and caveats.

`report` exports native results, per-trade CSV, metrics and additional cost sensitivities into `evidence/session-1/`. A negative result is valid research evidence. A positive result would remain exploratory/unqualified. Reports overwrite the local latest evidence; the committed Session 1 results remain in Git history. No parameter optimization runs.

The dataset is roughly one megabyte for the three-pair sample (actual bytes/counts/checksums in the manifest). The image is about 0.95 GB unpacked; allow several GB for Docker layers/containers, especially with VFS. Download is bounded to three pairs and four series per pair, with rate limiting. No ongoing history job runs after the command ends.

## Open the official FreqUI

```bash
./scripts/lab.sh ui-up
# Open http://127.0.0.1:8080 in your own browser.
./scripts/lab.sh logs
./scripts/lab.sh ui-down
```

Use username `owner` and the password in your private `user_data/runtime/api.json`. In FreqUI connect to the local bot URL, sign in, and open Backtesting/history to inspect the exported run. This service is Freqtrade's supported `webserver` research mode. [UI verification](evidence/session-1/ui-verification.md) states exactly what was observed in Cloud. Owner browser rendering still needs checking.

The API has owner administration capabilities. Host publication is loopback only; keep it away from OpenBot and the public internet. Do not add port forwarding or mount the Docker socket into an agent workspace. UI and paper services share port 8080 and the script stops the other before starting one.

## Explicit paper start and stop

```bash
./scripts/lab.sh paper-up
./scripts/lab.sh logs
./scripts/lab.sh paper-down
```

This starts real-market **simulation only**, with a separate persistent `user_data/paper.sqlite` and disposable `user_data/data/cache/` data path. It does not send exchange orders or need trading keys. Installation, tests, download and backtesting never start persistent paper trading. The startup guard refuses live mode, credentials, environment mode overrides, excess stake/positions and forced entry. This is a mode safeguard, not protection against a hostile host administrator who can replace the image/entrypoint.

Stopping pauses all paper-position management; it does not guarantee simulated positions are closed. Inspect open paper trades in FreqUI first. Existing state survives restart, but downtime cannot retroactively execute exits. Back up SQLite only after paper-down, together with configuration and strategy versions. Do not edit or remove the DB while running. No 24/7 uptime, exact daily-loss halt or exchange protective stops are established.

## Commands and troubleshooting

| Command | Purpose |
|---|---|
| `doctor` | Check Compose, engine version, safe configs and frozen strategy/protocol hashes |
| `scan` | Native live shortlist plus public metadata/observed volume/spread export |
| `download` | Rights-reviewed, fixed-size native download, range restriction and validation |
| `validate` | Recheck actual files and write manifest |
| `backtest` | Verify immutable sample and run official futures backtester |
| `lookahead` | Run native leakage diagnostic; examine sample-size limitations |
| `report` | Export native ledger/metrics and separate extra-friction estimates |
| `ui-up`, `ui-down` | Start/stop authenticated local research webserver |
| `paper-up`, `paper-down` | Explicitly start/stop dry-run process with persistent SQLite |
| `logs` | Last 100 UI/paper log lines |
| `test` | Run focused mechanics/safety tests; synthetic fixtures are not performance |

Direct native/Compose equivalents and Cloud-specific proxy notes: [operations runbook](docs/operations/runbook.md). On exchange errors, inspect the exact response and source eligibility; no automatic venue switch. On auth failure use the local credentials file. On a port conflict stop the other lab service. Do not disable TLS verification. If disk is full, stop/remove only this lab's disposable containers; preserve research files and paper DB.

Rollback: stop ui/paper, retain local data/SQLite and private credentials, then check out the prior approved commit. No automatic merge or follow-on session is authorized.

## Session 2: two causal research playbooks

Check out `codex/session-2-trading-intelligence` for the stacked Session 2 milestone. The [comparison](evidence/session-2/comparison-report.md), [acceptance evidence](evidence/session-2/manifest.md) and [risk report](evidence/session-2/strategy-risks.json) record actual results. The baseline remains frozen. Neither challenger is approved for persistent paper operation.

```bash
# Same Docker image and initialization as above; no exchange keys.
./scripts/lab.sh strategy-info VWAPTrendContinuationV1
./scripts/lab.sh strategy-info LiquiditySweepReversalV1
# Only if the separate Session 2 dataset is absent and Gate still retains this window:
./scripts/lab.sh research-download
./scripts/lab.sh research-all
./scripts/lab.sh compare
./scripts/lab.sh research-lookahead
./scripts/lab.sh test
```

`research-all` verifies both strategy freezes and source hashes, then runs all three through official Freqtrade with a common protocol. `compare` reads saved native results and callback evidence; it does not download data or run trades. Results and full CSV ledgers live under `evidence/session-2/runs/<strategy>/`. Costs, signed funding, per-pair and long/short results, holding times, R estimates and additional 5/10/20 bp friction appear in the comparison JSON. Full native ZIPs stay local because they may embed source data. Source candles stay out of Git.

VWAP continuation uses a UTC daily typical-price VWAP reclaim in an aligned 15m/closed 1h trend. Sweep reversal uses a failed breakout of a strictly prior 20bar range in a weaker 1h ADX regime. Each has explicit ATR/structure stops, fixed 2R native ROI requests, expiring signal-close limit entries and holding-time exits. Cards give every threshold. Tests verify both directions and NO_TRADE cases; they are not market performance.

The reacquired12-file BTC/ETH/SOL sample is byte-identical to Session 1. Preserve both datasets and committed manifests; if Gate's10,000bar window no longer includes July26, stop rather than change dates. Declare a new cohort and rerun all strategies if a future session authorizes it. This entire inspected cohort is DEVELOPMENT data, never an unseen holdout.

The challengers enforce1x,<=25 USDT initial stakes, max 2 native positions, no DCA, a price-deviation gate andfive minute paper order expiry. Intended-risk checks include assumed fees/friction/funding and reserve the3% emergency stop; realized UTC losses of10USDT halt new entries. Exact1% mark-to-market daily account loss, stop fills through gaps, downtime protection and historical five minute queue fills remain unqualified. Stop with `./scripts/lab.sh paper-down`; stopping pauses management and does not close paper positions. Inspect `research/strategy-registry.json` and `configs/paper.json` for the current baseline paper selection. No command promotes a research winner.

A future isolated OpenBot Local reader can receive copies of `research-summary.json`, `strategy-comparison.json` and `strategy-risks.json` from `evidence/session-2/`. These are ordinary derived files. It needs no exchange keys, authenticated admin API, paper DB or writable engine directory. Isolation and automated integration are deferred.

`INSUFFICIENT EVIDENCE` means too few observations; `REJECTED under evaluated assumptions` means this cohort loses; a positive development result remains `UNQUALIFIED DEVELOPMENT RESULT`. None implies future returns. Owner-host Docker/source eligibility, restart behavior and operation while the computer is awake need local verification. Roll back by stopping UI/paper, preserving data/SQLite/private credentials, then checking out `d76b6093796f78ce628943e8252033b34e9958ef`.

## Session3: causal structure and reusable economic research

The additive [Session3 workflow](docs/operations/session-3.md) combines confirmed15m/closed1h structure, existing scanner candidates, historical asof reports and a native structure-aware sweep comparison. [Executed evidence](evidence/session-3/manifest.md) includes two real cohorts, full native trade exports, cost/funding/uncertainty reports and5m execution sensitivity. The enhancement has7 development trades/+0.085728USDT, loses with5bp extra friction per side, and loses1.104693USDT on14 XRP/DOGE transfer trades. No economic edge or paper promotion is established. Prior Session1/2 freezes and evidence are preserved.

```bash
./scripts/lab3.sh structure-check
./scripts/lab3.sh opportunity-scan --cohort s3-development-v1 --as-of 2026-08-25T01:00:00Z
./scripts/lab3.sh opportunity-asof SOL/USDT:USDT 2026-08-25T01:00:00Z
./scripts/lab3.sh economic-compare s3-development-v1
./scripts/lab3.sh validation-report s3-transfer-v1
```

Recorded comparisons need no downloads or raw candles. Historical opportunity reports need the preserved/reacquired source sample. Fresh native runs and new/prospective cohort registration are described in the runbook. Session3 never starts paper, UI, an agent bridge or exchange orders.
