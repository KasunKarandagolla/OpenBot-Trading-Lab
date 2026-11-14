# OpenBot provider qualification repair — Session 1.5

Observed in Codex Cloud on 2026-11-13 UTC, beginning from remote branch SHA
`aba986518fda656a5ae3c3d5f78cced594dc4b96`. This is a narrow supplement to
[`Session 1`](../session1/README.md); it does not overwrite Session 1 receipts.

## Outcome

The repair found no qualified replacement for the blocked current inventory and
no independent, timestamp-aligned historical sample. Session 2 remains **NO-GO**.
No Session 2 code, new provider adapter, dataset, credentials, or automated
trading capability was added.

## Source checks

- Binance's official [`binance-public-data` README](https://github.com/binance/binance-public-data/blob/master/README.md)
  documents USD-M klines in daily/monthly archives, with daily data published
  the following day. It identifies USD-M kline files as data from
  `/fapi/v1/klines`; this is historical OHLCV, not a current `exchangeInfo`
  contract inventory. Its documented [`fetch-all-trading-pairs.sh`](https://github.com/binance/binance-public-data/blob/master/shell/fetch-all-trading-pairs.sh)
  helper calls
  `https://fapi.binance.com/fapi/v1/exchangeInfo` directly and strips each
  response to symbol strings; it returns no contract filters and does not
  avoid the Cloud 451. The only archive probe here was a HEAD for
  `BTCUSDT-1h-2026-11-12.zip`, which returned HTTP 404 at 06:03:50 UTC. No data
  file was downloaded, no alternate host/date was tried, and no conclusion is
  made about why the file was missing.
- The published [Binance Vision dataset terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md)
  state that access is free but licensed for specified noncommercial uses under
  CC BY-NC-SA 4.0; they restrict commercial use and require attribution and
  share-alike for redistributed derivatives. This repair retained no dataset or
  data-derived fixture.
- CoinGecko's documented [derivatives ticker endpoint](https://coingecko-api-v3.readme.io/v3.0.1/reference/derivatives-tickers)
  can report derivative exchange tickers and contract type. Its [Demo API
  setup guide](https://support.coingecko.com/articles/9471335603-user-guide-to-sign-up-for-coingecko-demo-api-and-generate-an-api-key)
  requires an owner-created key; the [free plan](https://www.coingecko.com/en/api)
  documents 100 calls/minute and 10,000 calls/month. The API was not called because no
  owner key was configured; its documented scope does not expose the complete
  Binance exchange eligibility, listing age, tick-size, lot-size, settlement,
  or multiplier metadata needed for the required inventory.
- The original Binance `exchangeInfo` HTTP 451 is preserved at
  [`Session 1 evidence`](../session1/README.md). It was not retried. The official
  historical archive and CoinGecko docs were considered only as distinct data
  sources, not as alternate routes to the blocked endpoint.

## Basis evidence and honest limits

The Session 1 live Basis records remain the only actual external-service
observations: targeted 15M/1H candle loads and remote formula calls succeeded;
the explicit footer returned the two requested popular names plus 18 fillers;
the remote arithmetic oracle passed 167 same-source-input comparisons. Those
observations do **not** establish eligible quiet-tail coverage, an independent
data oracle, exact volume units, or sustainable automation cadence. In this
repair, zero quiet-tail partitions were sent because no provenance-bound
eligible instrument list was available.

## Verification

- `python -m unittest discover -s tests -v`: 43 passed, 0 failed, 0 skipped.
- `python -m researcher config validate`: valid; 9 families, 31 methods, 0
  enabled detectors.
- `python -m researcher provider status`: Basis `LIVE_TESTED_NARROW`; screen and
  formula production capabilities remain disabled/unverified; Binance inventory
  remains blocked at HTTP 451.

Machine-readable result and source response details are in
[`provider-qualification.json`](provider-qualification.json). No unredacted
responses or credentials are retained.
