# Session 6A offline analytical implementation evidence

This directory contains no newly fetched market data. The original Local-obtained
fixtures and response hashes remain in Sessions 3/4/5/5.5. Controlled trade, bin,
OHLC and qualification vectors in `tests/test_session6a.py` are explicitly
SYNTHETIC tests, never current observations or operational feeds.

- `implementation-contracts.json`: the runtime registry's complete 27 measurement,
  nine family, 31 method and 13 pack contracts, with orthogonal flags.
- `baseline-tests.txt`: inherited 237 tests before changes.
- `test-results.txt`: final current test suite, including all original tests.
- `verification.json`: final local/config/immutable/safety verification and exact
  counts. Source qualification and full-universe flags remain false.
- `authentic-engine-timings.json`: bounded offline replay of all 14 genuine
  Session 5.5 selected histories, linked by their original response hashes and
  recorded instrument ticks; CPU/wall observations only, no live latency claim.
- `SHA256SUMS.json`: hashes of this compact evidence package, excluding itself.

Use [the runbook](../../../docs/implementation/SESSION_06A_RUNBOOK.md) and
[full matrix](../../../docs/implementation/SESSION_06A_MATRIX.md) for exact code,
test and source-dependency paths. No Cloud Binance probe, paid/provider purchase,
account credential, order, scheduler or downstream integration occurred.
