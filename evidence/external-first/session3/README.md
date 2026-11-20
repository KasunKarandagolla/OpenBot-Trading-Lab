# Session 3 — actual Local API and selected causal evidence

Environment: `CODEX_LOCAL_EXCEPTION`. Started from verified remote
`35f459e42b17a05ec041db71614f82624acf3eb8`; clean fresh checkout, all branches
fetched and fast-forward confirmed. No VPN/proxy, geographic switching, alternate
market-data host, API key, purchase, order, trading-account write or scheduler.
The blueprint/implementation-plan bytes remain unchanged.

## Implemented and independently source-verified

Official `https://fapi.binance.com` public inventory, aggregate ticker/book/premium
and bounded selected klines work on this ordinary authorized Local host. Normal
`python3 -m researcher scan now` refreshes them automatically without snapshots.
Binance Cloud's historical 451 is retained separately; it was not bypassed.

The qualification inventory contained **946 source rows / 519 verified eligible
COIN USDT perpetuals / 427 exclusions / zero unresolved rows**. Exact Unicode
names are preserved. INDEX/PREMARKET products are excluded by official class;
unknown classes stay unresolved. Tick/quantity/status/settlement/listing facts are
retained. No explicit multiplier metadata was returned; numeric prefixes are
never interpreted as multiplier facts. The youngest eligible listing was
CTUSDT, 1 October 2026: **no eligible listing younger than 30 days existed in this
snapshot**, so genuine young-contract qualification was not possible.

Independent official turnover selected disjoint **50 lower-half + 50 medium + 7
footer names**. On each 1H and 15M: requested **107**, recognized/returned/scalar
executed **107**, missing/failed **0**, truncated **0**. Each seven-name footer
contained **13 excluded provider fillers**. These are 107/519 qualification
observations per timeframe, not 519 structurally analyzed instruments.
Full CORE, row-specific 300-bar completeness and remote causal methods remain
unqualified. Broad production strategy coverage is **zero**.

Ten official selected samples covered five exact symbols × two timeframes,
300 requested/returned closed bars each: BTCUSDT, ETHUSDT, 1000000MOGUSDT,
1000PEPEUSDT, 我踏马来了USDT. Local source-aligned Decimal checks compared
**46 remote formula evaluations / 920 numeric values** against official data:
**42 formula evaluations / 840 values matched**. These include closed O/H/L
scope checks, close/high/low, base volume, width3, previous extrema, lag,
three-point median and q=.5 quantile, BTC taker-buy base and base delta. This is
independent source reference evidence, distinct from Session 1's unchanged
167 same-Basis-input arithmetic comparisons. It does not qualify general
percentiles, all volume scopes or every contract/timeframe.

## Material failures deliberately retained

- **Four ATR evaluations / 80 values fail the blueprint seed definition.** Basis
  uses first-bar H−L in the n=14 seed; the blueprint implementation requires a
  previous close and n valid TRs. Four alternative-seed evaluations and four
  conditional Wilder recurrence evaluations pass. No remote ATR/CORE production
  promotion occurs. Unit tests preserve these counterexamples.
- Targeted Basis `market_candles` returned HTTP 200 tool errors for
  `我踏马来了USDT` on **both timeframes**, despite successful screen membership.
  Its independent Binance samples and local measurements succeeded. Provider
  support is operation-specific; screen success never certifies candle handles.
- Qualification pulse: ticker 519/519, book 516/519 (three rejected rows), premium
  519/519. Final normal pulse: ticker **518/519**, book/premium **519/519**; YGGUSDT
  ticker row was rejected as invalid/stale. These row faults remain in reports;
  they are not HTTP failures or zero-opportunity evidence.
- No live young-contract sample or explicit multiplier fact existed; no invented
  replacement. Sustainable Basis quota/charged credits and remote historical
  as-of replay remain unknown.

## Implemented, awaiting remote/provider qualification

Shared deterministic measurements cover TR/ATR, normalized width and excluded-
window compression percentiles, efficiency/overlap/displacement, confirmed
swings/ladder, frozen distance/obstacles/touch episodes, quote RVOL, verified bar
aggressor arithmetic, whole-bar Q/V/CVD anchors, aligned relative returns and
lag-trained beta/residuals. These operate only on bounded selected samples.

Frozen-reference F2/F4/F5 transitions, chronological pressure/reclaim/opposing
attempt/rebreak/holds, confirmed swing BOS/CHoCH candidates, and FVG/iFVG
birth/mitigation/failure/retest are executable trial semantics. F1/F3/F6 remain
partial formation/primitives; F7/F8 have primitives only; F9 is not implemented.
No READY/entry/SL/TP or empirical profitability claim is produced.

All nine families and all **31 exact blueprint methods** retain roles,
necessary evidence, dependencies, sequence, interpretation, traps, rivals,
invalidation, provider requirements and honest implementation/fidelity state.
True profile/nodes/footprint/absorption/exhaustion/OI/forced orders/news remain
blocked by their actual source requirements. Keepssy remains DEFINITION_PENDING;
Silver Bullet lacks a qualified primary-source window. OB/breaker/EQH/CRT/AMD/OTE
and statistical reversion are visible but not implemented as full detectors.

## Causal persistence and tests

The selected live run reconstructed 40 boundary references, 59 boundary events
and 200 rival-hypothesis snapshots in memory. A **labeled retrospective metadata
replay** through the final persistent SQLite implementation contains the same
counts and occupies **425,984 bytes**. It contains no candle table. Stable natural
IDs were recomputed after fixing retrieval-dependent IDs; original source-run
hash and this replay distinction are recorded. No prospective discovery claim
or independently annotated real-world detector accuracy is inferred.

The final ledger preserves original scale/availability, rejects causal/identity
violations atomically and survives reopening. All 135 offline tests pass,
including the prior 80 and 55 new numerical, causal, counterexample, API,
recorded-independent-source and persistent-ledger tests. Failed live ATR claims
are expected counterexamples, not hidden by the passing test-suite count.

## Measured cost

| Run | HTTP requests | Response bytes | Sum request ms | Wall ms | p50 / nearest-rank p95 ms |
|---|---:|---:|---:|---:|---:|
| Full bounded qualification | 79 | 2,449,132 | 96,725 | 188,303 | 929 / 3,413 |
| Final normal automatic run | 9 | 1,898,702 | 15,801 | 16,053 | 1,574 / 3,525 |

Qualification includes 14 Binance calls and 65 Basis calls, six screens, two
HTTP-200 tool errors, zero HTTP failures and no screen recovery. Normal includes
four Binance and five Basis calls; no HTTP/tool errors. Local deterministic
processing/report construction is included only in wall time. Actual quota
headers are retained; they are not per-request charged-unit evidence. Basis
charged units were absent, cache hits were zero and cadence is unqualified.

Earlier diagnostics consumed **14 additional provider requests**: one direct
access check; two four-request inventory/pulse diagnostics; one ticker
inspection; one four-request cohort-view failure. Their captured receipts and
measurement gaps are in `diagnostic-receipts.json`. Total explicitly issued
provider requests this session: **102**. Some early byte/latency measurements
were not retained; they remain NULL instead of being estimated.

## Files

- `live-qualification.json`: normalized exact cohort/coverage, independent
  comparisons, selected-source summaries, request receipts, hashes and failures.
- `normal-live-run.json`: final automatically fetched operational run; no source
  payload required as an input.
- `selected-causal-metadata.json`: actual selected event/reference/hypothesis
  metadata replay input, source-run hash and actual persistent size.
- `diagnostic-receipts.json`: early repairs, failures and incomplete measurements.
- `test-results.txt`, `config-validation.json`, `SHA256SUMS.json`: final checks
  and integrity manifest. No secrets/private headers/session handles or runtime
  database files are committed. Full scratch reports remain ignored in work/.

See the [runbook](../../../docs/implementation/SESSION_03_RUNBOOK.md) and
[measurement semantics](../../../docs/implementation/SESSION_03_NUMERICS.md).
Session 4 readiness is **PARTIAL**: live inventory/current data and selected
causal primitives are available; full CORE/remote method equivalence, broad
production coverage, specialist sources, context/ranking and watch resumption
remain unresolved or later work. No new credential/purchase or owner assistance
is currently necessary. PR #24 remains draft.
