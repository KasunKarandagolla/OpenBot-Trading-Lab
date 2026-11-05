# Binance historical research data

This interface acquires and validates Binance Vision USD-M public archives. It does not submit orders, call private account APIs, start a collector, or make strategy or profitability claims.

## Beginner commands

Run these commands from the repository root. The fixed acceptance sample is eight symbols on **2026-10-05 UTC**, plus October 2026 monthly funding files. It is capped at 20 MiB per archive and 32 MiB total.

```bash
python scripts/binance_data.py probe --websocket
python scripts/binance_data.py universe
python scripts/binance_data.py fetch-sample
python scripts/binance_data.py validate-sample
python scripts/binance_data.py show-5m --symbol BTCUSDT --date 2026-10-05 --limit 1
python scripts/binance_data.py orderflow --symbol XRPUSDT --date 2026-10-05
python scripts/binance_data.py cache-info
```

Expected output includes public REST response codes, the number of historical archive symbol directories, verified archive counts and hashes, multi-timeframe mismatch counts, one participation-rich five-minute row, and aggregate-trade volume-at-price results. `cache-info` reports the locally cached source ranges. The archive directory count is not a count of currently tradable contracts.

Use `fetch-one` only for a bounded additional archive:

```bash
python scripts/binance_data.py fetch-one --kind klines --symbol BTCUSDT --timeframe 1m --date 2026-10-05
python scripts/binance_data.py fetch-one --kind aggTrades --symbol XRPUSDT --date 2026-10-05 --max-archive-bytes 5242880
python scripts/binance_data.py fetch-one --kind fundingRate --symbol BTCUSDT --month 2026-10
```

Every source is checked against Binance's adjacent `.CHECKSUM` file before caching. A reused cache file is rechecked against the current official checksum; changed or corrupt bytes cause an error and are left in place for inspection. The default cache is `user_data/data/binance_verified/`, which is ignored by Git. Use a new sample date or a new cache directory for a separate acquisition. Do not raise byte limits for broad downloads without an explicit bounded plan.

If an acquisition stops on an HTTP, checksum or schema error, keep the receipt and error output, correct the source/date or choose a new `--cache` directory, then rerun the bounded command. The tool will not silently replace a corrupt cached archive. To roll back this code change, revert its commit; the ignored source cache stays local and is not part of the repository rollback.

The converter in `scripts/validation_next_prepare.py` keeps Freqtrade's existing six-column `date, open, high, low, close, volume` Feather inputs. It writes a distinct research sidecar with source open/close milliseconds, availability time, quote volume, published trade count, taker-buy and derived taker-sell base/quote quantities, market identity, timeframe, source URL and archive hash. Sidecars do not change strategy signals or old sealed evidence.

## Field meanings and timing

Binance's published USD-M kline columns are `open_time, open, high, low, close, volume, close_time, quote_volume, count, taker_buy_volume, taker_buy_quote_volume, ignore`.

- Timestamps are Unix milliseconds in UTC. The candle is available at `close_time + 1 ms`, which is the interval end. Higher-timeframe values are only exposed after that time.
- `volume` and taker-buy base quantity use the source symbol's published base-asset quantity. `quote_volume` and taker-buy quote quantity use the quote asset (USDT for this sample). For multiplier-style symbols such as `1000BONKUSDT`, the archive does not qualify the historical contract multiplier, so do not silently convert contract units into underlying-token units.
- `count` is the source kline's number of trades. The same-position field in a mark-price kline is not executed trade count and is labeled separately.
- Taker-sell quantity is derived as source total minus source taker-buy quantity after checking both are nonnegative and taker-buy does not exceed total. The result is participation evidence at bar level, not individual signed prints.
- Binance USD-M `aggTrades` records publish aggregate trade ID, price, quantity, first/last constituent trade IDs, transaction timestamp and `is_buyer_maker`. `true` means the buyer was maker and the seller was taker (aggressive sell); `false` means buyer taker (aggressive buy). Aggregated trades can combine fills and are not level-2 history.
- The Volume Profile sample groups actual aggregate-trade quantity by exact executed price. POC is the maximum-volume bin (ties choose lower price). Value area starts at POC and expands through adjacent observed price bins by the larger next volume until reaching 70% of observed volume (ties choose lower price). CVD is accumulated aggressive-buy minus aggressive-sell quantity. These are data demonstrations only.
- Funding `calc_time` milliseconds are preserved exactly. Holding-interval assignment uses `entry < calc_time <= exit`; a funding event exactly at entry is excluded because the archive cannot establish position ordering at that millisecond. Hourly mark candles are not an exact settlement mark.
- 4h context is resampled from completed 1h bars. The derived 4h bar becomes usable only at its 4h close.

## Evidence and known limits

The real acceptance records and access matrix are in [`evidence/binance_data/README.md`](../../evidence/binance_data/README.md). Current results are **PARTIAL**: all 49 sample archives passed Binance's published checksums, but one symbol's 1m/5m OHLC reconstruction differed, and some aggregate-trade buckets did not reconcile to source 5m totals within the declared tolerance. See the source-level counts and exact values in the acceptance JSON.

The registered set contains BTC, ETH, SOL, XRP, DOGE, BNB and the first two alphabetically selected `1000*USDT` symbols with the four daily intervals present on the registered date. The selection does not use strategy outcomes. The environment could enumerate 1,080 USD-M daily-kline archive symbol directories; it could not verify which are current, active, USDT perpetuals. Only the eight registered symbols were downloaded and validated as samples.

Every tested `fapi.binance.com/fapi/v1` public REST endpoint returned HTTP 451 with Binance's message that service is unavailable from a restricted location. The separate official historical archive host worked. A short public websocket attempt timed out; this does not establish its cause or future-host access. There is no verified current or historical exchange-info snapshot in this session. Contract ticks, steps, minimum notional, contract size, status, onboarding/delisting, fees and execution constraints remain unqualified for the historical periods. Execution validation must fail closed when these records are missing.

The earlier BTC fixture observation ($50 minimum notional versus a $25 research position cap) is only a public CCXT test-fixture value with no verified effective period. It is not established as a January 2026 or current Binance rule. The risk cap was not changed.

Binance Vision Dataset Terms v1.0 grant a **CC BY-NC-SA 4.0 non-commercial** license, prohibit commercial use absent separate written terms, and require attribution and share-alike for redistributed derivative data. See <https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md>. The committed fixtures are short attributed excerpts; full downloaded archives stay in the ignored local cache.

Focused tests use source-backed archive excerpts and can run without Freqtrade:

```bash
python -m unittest discover -s tests -p 'test_binance_research_data.py' -v
```
