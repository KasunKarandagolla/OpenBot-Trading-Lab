# Session 6A — analytical engine and source contracts

CODEX_CLOUD / SOL. Repository `KasunKarandagolla/OpenBot-Trading-Lab`, integration
branch `feature/external-first-market-researcher`, draft PR #24. Starting fetched
remote/local head: `ed0f63e8610ba2b34d734ff449d2de6156cfad2c`. The generated Cloud
checkout initially had only main's fetch refspec; the approved branch was fetched
explicitly and checked out without changing main or pending files. No concurrent
writer, reset, force operation, merge, trading operation or downstream integration.

The [full implementation matrix](SESSION_06A_MATRIX.md) has every one of the
27 measurement IDs, F1–F9, the exact 31 method names and all 13 pack contracts.
[Machine-readable contracts and verification](../../evidence/external-first/session6a/README.md)
are in the existing evidence tree. These are implementation/oracle results,
not fresh live provider qualification or a prospective opportunity report.

## What is executable

- `measurements.py`: confirmed same-anchor CVD divergence, past-only close
  residual dispersion, persistent lag-trained OOS residuals, dated exact-perp
  sectors, OI/base/mark decomposition, funding kind/interval/basis and catalysts.
  Reuses Decimal `numerics.py`, instrument identity, economics and context.
- `specialists.py`: strict typed tape/envelope adapters, actual executed weighted
  first/second moments, complete price bins, POC/70% contiguous VA with lower-price
  ties, MEAN3/separation3 nodes, contiguous naked-POC first revisits, diagonal
  footprint/stack reducers, observed aggression/response, exhaustion and witnessed
  sampled liquidations. OHLC or partial tape cannot impersonate these facts.
- `family_engine.py`: actual formation reducers for all nine families, mirrored
  directions and rivals/NULL, early stages before confirmation, original frozen
  references, later response/acceptance, invalidation/expiry and explicit unknowns.
  F2 and F5 cannot both certify the same no-reclaim impulse. F9 remains POST_SHOCK
  absent witnessed coverage. Fixed seven-day reference TTLs are declared research
  definitions, not calibrated lifetime claims.
- `method_engine.py`: all 31 method contracts, including actual BOS/CHoCH/MSS,
  compact full-candle OB base → displacement → later BOS birth, same-ID breaker,
  FVG/iFVG/revisit, contextual OTE, preselected CRT, experimental 00–08 UTC crypto
  AMD, auction/value and strict specialist reducers. M14 has a tested timezone/DST
  adapter but no fabricated canonical timing; M15 has no invented rule.
- `pack_contracts.py`: restricted typed expression DAG with arity/field/lag/window
  validation, exact closed cutoff, fixed seed/warm-up, units/encoding/precision,
  finite null handling and dependency ordering. Two 12-column CORE contracts,
  isolated quote participation, approach/pressure, quiet-location and controlled
  correction packs. There are 33 distinct registered column definitions compiled
  for both TFs, plus three typed source-adapter pack contracts. They reuse Basis
  MCP and PartitionEngine; no alternative architecture or arbitrary formula input.
- `engine_capabilities.py` and `method_registry.py`: independent implementation,
  code-oracle, source, formation, whole-universe and empirical flags. Legacy
  production gates retain their historical scope and each row exposes its new
  analytical implementation separately. Ordinary `scan_market_research` actually
  invokes the selected analyzer and disabled/qualified Route A adapter. The latter
  is tested with explicitly synthetic scoped qualification; no new live gate was
  enabled. Professional interpretation/shortlisting remains Session 2's work.
- Ordinary broad operation now schedules both existing price TFs before the
  separate optional quote-RVOL calls. Optional MCP errors/zero baseline/budget
  omissions do not erase price rows. The existing 26-call ceiling is unchanged;
  optional coverage may therefore be partial and is reported separately.
- Immutable `Bar`, `Reference` and `StructuralEvent` IDs are memoized without
  changing their hash inputs, serialization or first-availability semantics.
  No candles or historical feature warehouse were added to SQLite.

## Verification and regressions

The inherited suite passed **237/237** before edits. The final exact totals and
runtime are retained in `evidence/external-first/session6a/test-results.txt` and
`verification.json`; no inherited fixture, assertion or skip was weakened.
New controlled cases test all family positives/negatives, OB born only at BOS,
actual MSS context, fake inverse gaps, F5 without reclaim, distinct episodes,
source/tick/clock/TF identity, beta/OI side traps, no-event/short/zero history,
optional failure isolation, strict tape, true profile ties/nodes, DST, and
append-future invariance across all families and all method results.

All 14 genuine Session 5.5 selected histories are replayed through the complete
new analyzer using the original response hashes, availability and recorded
Session 5 instrument ticks. These prove bounded source reconstruction runs, not
all-method event positives, current opportunities or full-inventory coverage.
The authentic replay exposed a shock first retrieved after reference expiry;
it now reports STALE explicitly instead of constructing an impossible reference.
F1 retains an observed zone approach when the response moves away from the zone.
CRT uses the latest predeclared UTC session rather than an expired oldest candle.
The old native ATR seed, export precision, positive-pressure, quote alias,
Unicode targeted-tool, cutoff, HTTP200/isError, denial/429 and filler regressions
remain in the unchanged inherited suites and receipts.

Offline reproduction, with no network:

```bash
python -m unittest discover -s tests -v
python -m researcher config validate
python -m researcher analytics contracts --output work/analytical-contracts-001.json
git diff --check
```

## Exact Local Session 3 probes — do not run from Cloud

Only on the owner's already authorized normal Local environment, fetch this
branch and run the fixed registered probe, one symbol/TF per invocation:

```bash
python -m researcher analytics local-oracle --environment CODEX_LOCAL --symbol BTCUSDT --timeframe 1h --output work/6a-btc-1h-001.json
python -m researcher analytics local-oracle --environment CODEX_LOCAL --symbol ETHUSDT --timeframe 15m --output work/6a-eth-15m-001.json
python -m researcher analytics local-oracle --environment CODEX_LOCAL --symbol 1000PEPEUSDT --timeframe 1h --output work/6a-prefix-1h-001.json
python -m researcher analytics local-oracle --environment CODEX_LOCAL --symbol 我踏马来了USDT --timeframe 15m --output work/6a-unicode-15m-001.json
```

Select the actual current quiet/young exact contract from live official metadata
for the remaining bounded cohort. A numeric prefix is not multiplier proof.
Each invocation uses public official exchangeInfo and one selected ≤300-bar kline
sample, then one Basis bounded candle handle and up to 33 registered tail
evaluations (45 Basis HTTP ceiling). It validates exact identity/start/closed
cutoff and stops denial or schema failure. No host rotation, proxy, dataset
download, secret, purchase or automatic production promotion is involved.
Missing `--environment CODEX_LOCAL` is rejected before any I/O. No such probe was
executed from Cloud. Source lists:

- Official `https://fapi.binance.com/fapi/v1/exchangeInfo` and selected `klines`;
  existing depth/OI/funding adapters keep their own endpoint/source contracts.
- Existing `https://www.basischarts.com/api/mcp`: recorded `market_candles`,
  `formula_evaluate`, `screener_run` schemas in Session 5.5 evidence.
- Actual executed specialist tape, witnessed liquidation sampling, dated exact
  perp sectors and original publisher inputs need separately permitted providers;
  no undocumented or fictitious endpoint has been proposed.

## Budget and truth boundaries

At the **historical** 519-contract snapshot and 50/request: 11 partitions, two
CORE packs22 logical calls; optional participation22; approach/pressure22;
all three layers66. Optional quiet-location22 and correction22 additional calls
if explicitly requested/capacity available. Three specialist packs remain scoped
source adapters, not 31 all-universe scans. These are scenarios, not charged quota
or sustainable cadence. New remote packs are disabled until independent Local
source oracle qualification. Existing 16 scalar/three narrow-mask qualifications
remain narrower than the new CORE/family/method contracts.

Offline selected analyzer CPU/wall measurements, source hashes and sample counts
are in `authentic-engine-timings.json`. They describe this Cloud CPU, not remote
live scan latency. New in-memory source history stays ≤300 bars per selected
symbol; existing runtime ceilings remain five symbols/ten kline calls. Outputs
retain compact reference/event metadata and one current scalar cache, not an
all-market historical store. No new live storage/quota/latency claim is made.

## Ready for Cloud Session 2

- [x] Same branch, immutable specifications, inherited tests retained.
- [x] Measurements, 9 family reducers, named-method and strict specialist code,
  finite/sparse compiler and actual runtime registration are reviewable.
- [x] Complete source/definition/coverage matrices; no scalar-to-method promotion.
- [x] Exact executable Local qualification probe and source list.
- [ ] Cloud Session 2: use the new formation/rival evidence for professional
  interpretation, query prioritization, multi-route nominations, permitted
  specialist orchestration, candidate economics and intelligent shortlisting.
- [ ] Local Session 3: fresh source/timing/multiplier/Unicode/clock proof, full
  source oracles, representative young/tail evidence, clean-checkout live tests
  and only then the separately conditional one-way read-only integration.
- [ ] M14 primary-source canonical timing/sequence and crypto applicability;
  M15 creator's operational reference/event order/timeframe/invalidation rules.
  The owner was asked for the Keepssy primary source; this does not block the
  implemented independent algorithms. No API key or paid service is needed for
  the enabled public subset.

**Release decision: offline implementation checkpoint; production PARTIAL.**
No prospective all-coin causal recall, qualified new live handoff, profitable
forecast, source entitlement or complete live method coverage is claimed. PR #24
must remain draft; no merge or downstream connection. Publication SHA/remote
equality and observed CI links are recorded in the session's final handoff.
