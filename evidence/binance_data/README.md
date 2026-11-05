# Binance data-path acceptance

This work independently tests Binance Vision archives and the public USD-M API from the Codex Cloud environment. It does not amend PR #15's historical results, alter strategy parameters, or qualify live execution.

## Current evidence

- [Final acceptance report](run-011/acceptance.json) (with [command output](run-011/acceptance.log)): 49 source archives for eight symbols, 3,983,632 compressed bytes, all checked against Binance's `.CHECKSUM` files. It records exact file URLs and hashes, retrieval times, candle/event ranges, schema, conversion units, actual sample rows and source reconciliation details.
- [Public access and archive-universe results](run-004/access-matrix.json) and [full inventory summary](run-004/archive-universe.json): five USD-M public REST probes, bounded websocket attempt, official archive inventory and its limitations.
- [Contract-rule qualification](run-004/contract-qualification.json): HTTP 451 finding, required field statuses, the fixture-only BTC $50/$25 conflict and fail-closed verdict.
- [First real 5m sample](run-011/sample-5m-record.json): published candle participation fields, exact clock, source archive, retrieval time and hash.
- [Aggregated-trade demonstration](run-011/orderflow.json): real executed-price records, buyer-maker side, IDs, price-volume profile, CVD and kline reconciliation.
- [Focused test output](run-011/focused-tests.log): 23 source-backed tests pass, with no skips. [Broader regression result](run-011/prior-regression.log) records the import failure caused by the unavailable Freqtrade dependency.
- [Cache-reuse log](run-004/cache-reuse.log): 49/49 archives reused after checksum verification; no archive bytes were redownloaded on the repeat run.
- [Storage accounting](run-011/storage.json): compressed sample bytes, local receipt overhead, fixture size, and explicit acquisition caps.
- [Source-backed fixture provenance](../../tests/fixtures/binance_data/provenance.json): short excerpts only; the full archives remain in ignored local storage.

## Results

**Historical archive access: PASS for the registered sample.** 1m, 5m, 15m, 1h, mark-price 1h and monthly funding files were downloaded from `data.binance.vision`; an XRP USD-M `aggTrades` day was downloaded and parsed. Binance's published Futures schema includes quote volume, source trade count, taker-buy base volume and taker-buy quote volume.

**Source consistency: PARTIAL.** On the selected day, 23 of 24 1m→5m, 5m→15m and 15m→1h comparisons were exact. The 1000CATUSDT 1m→5m comparison had 17 OHLC mismatches (17 opens, one high, seven lows; no close mismatch). XRP aggregate trades reconciled to source 5m bars within `max(1e-8, 1e-6 × bar volume)` on 274 of 288 bars; 14 were outside tolerance. The acceptance report retains the mismatching timestamps and values.

The trade archive contained 223,084 aggregate-trade rows and no duplicate aggregate IDs. It supports a reproducible price-volume profile (POC 1.515, VAL 1.5007, VAH 1.5241 at the declared 70% method) and cumulative volume delta of −23,208,135.3 source base-asset quantity units for this UTC day. These describe this acquired record set and make no profitability, institutional-activity or complete-order-book claim.

**Current universe and execution metadata: BLOCKED / UNQUALIFIED.** The public Vision archive index contained 1,080 symbol directories under the USD-M daily-kline prefix. That inventory includes historic, non-USDT and non-perpetual symbols; it does not establish a current eligible count. `exchangeInfo`, ticker, REST candles, funding/mark and order-book probes all returned HTTP 451. A read-only public websocket attempt timed out within its bound. The previous fixture's BTC minimum notional of $50 remains an unqualified fixture observation; it exceeds the research cap of $25, and no risk setting was changed.

## Reproduction

From the repository root:

```bash
python scripts/binance_data.py probe --websocket
python scripts/binance_data.py universe
python scripts/binance_data.py fetch-sample
python scripts/binance_data.py validate-sample
python scripts/binance_data.py show-5m --symbol BTCUSDT --date 2026-10-05 --limit 1
python scripts/binance_data.py orderflow --symbol XRPUSDT --date 2026-10-05
python -m unittest discover -s tests -p 'test_binance_research_data.py' -v
```

The raw source cache is local and Git-ignored. The historical source terms are non-commercial CC BY-NC-SA 4.0; see [the operator guide](../../docs/operations/binance-market-data.md) and Binance Vision's [Dataset Terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md).

The prior PR #15 private archive bundle and `user_data/data/validation_next/` are not present in this workspace. The focused Binance suite ran locally; the PR #15 test module stopped at import because `freqtrade` is not installed. No old test/evidence seal was changed.
