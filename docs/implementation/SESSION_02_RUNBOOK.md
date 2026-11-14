# Session 2 — on-demand external discovery, R0 partial release

Python 3.11+, standard library only. Run from the repository root:

```bash
python -m researcher config validate
python -m researcher provider status
python -m researcher scan now --output work/discovery-001.json
python -m unittest discover -s tests -v
```

The output file must be new and below ignored `work/`; no overwrites or symlink
traversal. Exit 0 with `operation_status=PARTIAL` means finite observations were
received, not full discovery qualification. Exit 2 means no valid observation
or input/output validation failure. A malformed supplied inventory is rejected;
it is never silently replaced by the provisional cohort.

## What actually runs

One Session 1 `BasisMCP` client and MCP session perform two explicit screens:
`CORE_1H` and `CORE_15M`, version `2.0.0-partial.1`. Only their isolated
`NORMALIZED_WIDTH_3` **observation probe** runs:
`(highest(high,3)-lowest(low,3))/close`. Its current closed window includes the
last closed bar. A three-bar normalized width is not a historical compression
percentile, significant boundary, causal SMC/ICT pattern or opportunity signal.

The expression has Session 1 schema and same-source arithmetic evidence. Small
15M/1H live formula samples exercised the five spellings; independent source
accuracy remains unverified. All full CORE packs, strategy detectors and
method-specific formulas stay disabled. The report preserves every missing
CORE output and all 9 families / 31 methods with zero qualified evaluations.
No shortlist or stage is fabricated from width alone.

Without an official inventory, the exact requested cohort is `BTCUSDT`,
`ETHUSDT`, `SOLUSDT`, `FILUSDT`, `1000PEPEUSDT`, provenance-bound to the Session 1
sample receipts. They are **provisionally identified names**, not five verified
eligible contracts or a quiet-tail sample. Any other supplied inventory member
is explicitly `UNVERIFIED_PROVIDER_SYMBOL_SCOPE` and not sent automatically.
Providing complete inventory does not by itself qualify broader provider scope.

Partitions preserve input order and exact spelling, maximum 50; the provider's
minimum universe is 20 (50 for larger partitions), with limit 60. Provider-added
rows are excluded. The engine validates echoed formula/rules, scope, counts,
finite readings, identities, closed-bar opens and a frozen per-timeframe cutoff.
The cutoff is `floor(run_start / timeframe)`; source bar open + timeframe must
equal it. Advancing across a bar boundary mid-run does not move the cutoff.
Stale or later observations fail admission rather than joining mismatched times.

## Inventory import

Owner assistance is needed to establish the complete denominator. Supply a
fresh, full official `exchangeInfo` JSON response captured through an independently
lawful, authorized source, plus this separate provenance JSON. Do not send keys.

```json
{
  "schema_version": "openbot.inventory-source.v1",
  "source_kind": "OWNER_OFFICIAL_SNAPSHOT",
  "source_url": "https://fapi.binance.com/fapi/v1/exchangeInfo",
  "captured_at_utc": "REPLACE_WITH_ACTUAL_UTC_CAPTURE_TIME",
  "authorized_capture": true,
  "lawful_source_statement": "REPLACE_WITH_ACTUAL_AUTHORIZED_SOURCE_AND_CAPTURE_METHOD",
  "complete_exchange_info": true,
  "payload_sha256": "REPLACE_WITH_SHA256_OF_EXACT_EXCHANGEINFO_FILE_BYTES",
  "max_age_seconds": 86400
}
```

The example is a template, not qualification evidence. `complete_exchange_info`
is the owner's explicit attestation that no rows were filtered or truncated.
Never set it true for a third-party list. Preserve the raw official response
bytes; `sha256sum work/exchangeInfo.json` computes the content hash. The adapter
does not verify geographic authorization on the owner's behalf; the source
statement documents the owner's actual lawful access. No Local/alternate-host
instruction is provided to work around the existing Binance denial.

```bash
python -m researcher scan now \
  --inventory work/exchangeInfo.json \
  --inventory-provenance work/inventory-source.json \
  --output work/discovery-with-inventory-001.json
```

Schema validation rejects duplicate JSON keys/symbols, invalid numbers, rules
and times. The TTL must be 1–86,400 seconds and is rechecked when a cached
inventory object is reused. A stale snapshot is provisional. Eligibility needs
explicit `PERPETUAL`, quote `USDT`, settlement (`marginAsset`) `USDT`, status
`TRADING`, official `underlyingType=COIN`, price tick and LOT_SIZE rules.
Unknown classifications or required fields keep that row provisional and the
universe partial. Known ineligible contract types/settlements/statuses are
excluded with reasons. A complete source file with unresolved rows is not a
verified complete eligible universe.

Listing time and explicit `contractMultiplier` are retained when supplied;
otherwise they stay null with unsupported-field labels. Numeric symbol prefixes
are never parsed as multiplier facts. Full source capture time/hash, exact
native symbol, eligibility subset, provisional members and excluded rows remain
in the report. No alternative inventory source has passed independent
qualification; `InventorySources` is the shared registration interface for a
future reviewed adapter, not an arbitrary payload trust switch.

## Remaining source dependencies

The recorded Binance 451 stops its direct inventory and aggregate
ticker/book/premium adapters on this Cloud host. No route retry, proxy/VPN
change or Local exception occurred. Aggregate current-observation adapters and
their time/unit contracts exist, but current cheap-market coverage is zero.
No alternative was promoted; the prior source review establishes that a
CoinGecko Demo key alone cannot solve the authoritative inventory gap. No new
API key is requested.

For the genuine tail test, the owner also needs a contemporaneous lawful
official `/fapi/v1/ticker/24hr` snapshot with capture time, raw-file SHA-256 and
authorization statement. `normalize_market` validates it and
`independent_tail_cohort` requires a complete, fresh, verified inventory plus
complete positive-turnover observations. It selects lower/medium liquidity
members independently of provider boards or global direction, preserving
verified young/multiplier examples where available. It plans a full 50-name
partition plus a smaller footer; **the actual Session 2 tail test sent zero
partitions**. A second independent full cohort remains a production gate.
The helper is a qualification contract; no extra tail network command is enabled
before these inputs and provider permission are verified.

For an independent numerical oracle, supply a small permitted historical sample
with documented license/retention permission, source venue/contract, UTC bar-open
and close semantics, capture time/hash, field/volume-unit definitions and closed
OHLCV/quote/taker fields: about 65 closed 1H and 65 closed 15M bars for BTC, ETH
and representative quiet/young/multiplier examples where available (at most five
symbols). This is a bounded verification sample, not market-wide history. ATR
seed/warm-up, prior extrema/range, volume and timestamp checks remain unqualified
until a real aligned independent sample passes. Synthetic and same-Basis-input
fixtures verify deterministic code only.

## Coverage, faults and budgets

Reports separate `eligible_contracts` (null if unknown), provisional inventory,
planned/not-requested names, requested/recognized/evaluated/returned/matched,
missing/failed, fillers, source cutoffs, response hashes, formula revision,
fidelity, precision and quota. Recognized IDs are proved only by returned rows;
aggregate vendor counts never allocate proof to missing identities. Evaluated
means validated **provider-reported scalar execution**, with input history and
source accuracy still unverified; `valid_remote_core_evaluated` stays zero.
`complete=false` preserves absent per-row history attestation. The evidence
window denotes the last output bar, not a certified full historical window.

Every initial and recovery attempt remains auditable. Bounded bisection may
recover a truncated/tool-error partition; final coverage uses the effective
disjoint leaves so recovered failures do not double-count. Sparse or optional
formula packs are never mixed with the finite baseline. Missing IDs remain
missing. HTTP 200 tool errors remain errors; empty results establish no absence
of opportunities.

Defaults: serial requests, minimum one second between screen starts, 8 logical
screen attempts including at most 2 recovery calls, 16 total HTTP requests
including handshake, 25-second HTTP timeout, 2 MiB per response and 8 MiB screen
byte budget. HTTP 403/451/429 stops the route for the run. Retry-After is retained;
no automatic retry occurs before it. Actual charged quota units remain null,
and the one-second pace is a local safety bound, not a qualified free-service
cadence. All scheduled/continuous operation remains disabled.

## Nomination and later-session boundary

Typed routes preserve boundary/pressure, compression/expansion, trend/pullback,
breakout/sweep, relative anomaly, transition/shock, previous watch, quiet tail,
new listing, specialist and value-location entry points. They validate source
evidence IDs, exact symbols, fidelity and chronology, keep NULL/rival hypotheses,
and preserve frozen reference known-at fields. Context is not an eligibility
input. They cannot certify READY/FAST or true specialist claims; no specialist
source is registered. Watch persistence, frozen-reference lifecycle, causal
detectors, context interpretation, remaining-room analysis and Deep Analysis
shortlisting are later responsibilities and were not started here.

No dependencies, trading service, execution API, trading credential, candle
store, ledger database or scheduler was added. The five research MCP operations
remain the only permitted tools; arbitrary expressions and write tools remain
rejected. The old `scan smoke` and bounded Session 1 qualification commands remain
available. Raw scratch output stays in ignored `work/`; curated Session 2
evidence is under `evidence/external-first/session2/`.
