# 03 — Market Data Acquisition, Refresh, Storage and Retention

## Principle

**Observe many markets cheaply, retain few at detail, download history only on explicit approval.** The lab is not a perpetual tick-data warehouse.

## Three different data paths

| Path | What arrives | How used | Storage |
|---|---|---|---|
| A — broad scanner | Exchange-reported 24h ticker/volume, listed status, possibly spread and funding where available | Choose shortlist; each field has its own source/time/units | Cache in RAM or time-stamped small JSON; expire at next scan |
| B — paper strategy | Latest completed 5m/15m/1h OHLCV for eligible pairs, optional mark/funding as supported | Freqtrade signals/exits | In-memory provider + paper DB; bounded rolling data cache; **do not assume Freqtrade auto-archives all live candles** |
| C — research/backtest | Explicitly approved historical candles, optional associated funding/mark series | Chronological backtesting | Freqtrade files (typically Feather); pinned manifest and checksums |

### Does it keep downloading forever?

The live paper engine polls exchange data while running. Historical `download-data` is a **separate commanded process**, not necessarily the same as paper-mode polling. We control the pairs, dates, timeframes, refresh and retention. Market-data terms, region availability, rate limits and exchange rules must be reviewed first. No automatic downloads of all historical Binance Vision archives.

### Recommended initial timeframes

- **Broad scan:** e.g. every 15–30 minutes; actual exchange rate-limit policy controls cadence.
- **Context:** 1h / 15m candles, optionally 4h, for shortlisted markets.
- **Trigger:** 5m closed candles. **1m or trade/footprint optional later**, not promised in the MVP.
- **Paper trading loop:** Freqtrade default process cadence can be seconds; do not confuse loop frequency with genuinely new closed-candle information.

Sampling is a *proposal*, not a claim these feeds are always available or synchronized.

## Source and readiness checks

For each required series, verify market type and symbol mapping (`BTC/USDT:USDT` in Freqtrade/CCXT futures notation), source, UTC availability, bar interval, expected bar count, duplicates, gaps, closed status, nonfinite prices/volume, quote units, price precision and freshness. `READY` requires all inputs for that policy; otherwise do not open new paper positions on that symbol.

- **No backfilling gaps with made-up candles.** Historical gaps become excluded windows; live gaps block new entry while risk monitoring continues.
- **No OHLCV-as-order-flow.** Candle close direction is not true aggressor-side delta. A profile reconstructed from candles is approximate.
- **No unknown mark/funding.** A futures backtest lacking appropriate funding/mark assumptions is incomplete and must be labeled as such.
- **No future-adjusted markets.** Historical universe membership must come from historical evidence, not only today's listings, where the test depends on universe selection.

## Local directory contract (proposed)

```text
trading-lab/
  configs/                       # versioned PUBLIC configuration and strategy policies
  research-manifests/            # source/license/date/pair/timeframe/hash table
  freqtrade-user-data/
    strategies/                   # pinned source and versions
    data/                         # approved downloaded research candles ONLY
    backtest_results/             # deterministic outputs, CSV/JSON reports
    tradesv3*.sqlite              # paper DB: ACTUAL name/config to be verified on install
  exports/                        # immutable, sanitized, small snapshots for OpenBot
  openbot-readonly/               # copies ONLY, no symlinks to configs/secrets
  backups/                        # protected, non-agent-accessible snapshots
  logs/                           # bounded/rotated logs
```

**Implementation nuance:** actual Freqtrade file names differ with version/launch options; list them during Session 1 and pin the configuration. Do not rely on the illustrative database basename.

## Retention policy (proposed; no deletion of audit evidence)

| Asset | Retain | Deletion / backup rule |
|---|---|---|
| Broad scan cache | Latest 1–7 days if summaries useful | Rotate automatically; no historical source archive created |
| Detailed recent candle cache | Minimum warm-up + approved short horizon | Measured size cap, erase only reproducible dispensable data |
| Approved backtest datasets | Until experiment/reproduction decision | Keep manifests/hashes permanently; purge originals only if contract permits and approved |
| Paper trades/decisions | Persistent across restarts | Back up on each release and daily; do not truncate for space |
| OpenBot reports | Bounded recent + decision artifacts | Remove raw redundant chat content under privacy policy |
| Raw tick/orderbook | **OFF by default** | Enable only with source rights, economics justification and measured size |

## Capacity model — do not invent precise GB figures

At 10 pairs × 30 days × 1m, the theoretical maximum is **432,000** minute-bars before gaps. Multiply by measured serialized bytes/bar on the installed version, plus storage for other timeframes, funding/mark, backtests, DB and backups. Before scaling, measure actual dataset sizes, disk free, upload/backup time and rate limits. Set a quota *after measurement*, not an arbitrary 'unlimited' archive plan.

## Data rights gate (mandatory)

Binance Vision datasets published under August 2026 terms are CC BY-NC-SA 4.0/noncommercial by default and commercial usage requires separate authorization. **Freqtrade's downloader does not waive dataset terms**. Exchange REST/API data is a separate contractual route; investigate venue terms and lawful intended use—do **not** assume REST data is automatically commercially licensed. The MVP's synthetic fixture requires no external market data. Licensed/noncommercial research may be proposed only after owner authorization.

## Failure behavior

Stale market feed → no new paper entry; retain paper position state; alert. API rate limit → backoff; don't bypass. Disk near full → stop history capture/backtests; alert before affecting paper state. DB damaged → halt, restore verified backup and compare. Missing lawful source → synthetic-only proof; economic gate BLOCKED.