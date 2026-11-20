# Session 1 evidence

All observations were made in Codex Cloud on 13 November 2026; machine times are
UTC. These are narrow qualification observations, not discovery or trading
performance. Public endpoints required no credentials. No Local exception,
exchange restriction bypass, paid service or trading API was used.

| Artifact | Meaning |
|---|---|
| `upstream-inventory.json` | Actual PR/head/base state and pinned inspected Git blobs |
| `initial-probe-receipts.json` | Instrumented original public requests, hashes, status, bytes, latency, arguments |
| `basis_*receipt.json`, `binance_docs.receipt.json` | Current documentation/source hashes, actual access status |
| `binance-exchange-failure.json` | Official exchangeInfo's HTTP 451 body, hash bound by receipt |
| `basis_formula_catalog.json`, `basis_variables.json`, `basis_pivot_catalog.json`, `orderflow-schema.json` | Observed function/field schemas; schema availability is not qualified semantics |
| `runtime-samples-001.json`, `sample-clock-and-scope.json` | Actual runtime MCP calls for 5 requested spellings × 2 timeframes; every contract remains independently UNVERIFIED |
| `runtime-footer-001.json`, `finite-footer-coverage.json`, `recovery-footer-coverage.json` | Two requested names / 18 fillers, poisoned pack rejection and finite recovery |
| `oracle-results.json` | 167 independently computed arithmetic comparisons against the same provider's bounded BTC tails; not an independent data-source oracle |
| `runtime-performance.json` | 33 recorded runtime HTTP requests / 251,961 response bytes; measured sample, no throughput or free-cadence guarantee |
| `smoke-report.json` | Actual final narrow smoke, closed 1H cutoff 05:00 UTC, no shortlist, identity/coverage unknown |
| `test-results.txt` | Offline contract/oracle/fault/safety suite output |
| `SHA256SUMS.json` | Exact fixture and evidence file hashes; excludes itself |

Fixtures are under `tests/fixtures/session1`. Raw MCP session headers are **not**
retained. `ref` fields identify candle handles, not authentication. The fixture
oracle stores only the 20-point reduced BTC outputs needed for arithmetic tests.
The small successful footer fixture retains its reported results so fill,
truncation and requested membership can be reproduced. Tests mutate copies to
create adversarial cases, never relabel synthetic changes as live observations.

Original bootstrap page requests had an early scratch-directory failure; those
unretained requests are excluded from measured performance, not treated as zero
cost. The retained exchange access receipt proves 451. No further exchange routes
were explored. Runtime totals are explicitly a subset of all Session 1 traffic.
Provider charged quota units were not returned. The 429/backoff test is synthetic;
no live quota-exhaustion experiment or latency SLA is claimed.

The formula response's informational terminal link said `market=spot` while its
data object said `market=futures` when using a futures handle. Normalization uses
the explicit data object and ignores the link; the inconsistency is retained as
a source limitation. Screen readings were rounded to four decimals (e.g. BTC
width `0.0357` vs formula `0.03574913898358485`), so screen fields cannot support
tick-exact level comparisons without an additional precision contract.

`bars_since(close<0)` and `value_when(close<0,close,0)` returned `defined=0`
without a tail; that is undefined/no observed event, not numeric zero. The pivot
catalogue query returned no entries; delayed-pivot and historical arbitrary
as-of semantics remain unverified. There is no claimed true footprint, true
Volume Profile, exact quote/base-volume reconciliation or historical event-order
qualification. All family/method detectors remain disabled.
