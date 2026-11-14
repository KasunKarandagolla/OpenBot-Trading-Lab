# Session 3 — live integration and selected causal research

Python 3.11+, standard library only. From a fresh checkout:

```bash
python3 -m researcher config validate
python3 -m researcher scan now --output work/live-001.json
python3 -m unittest discover -s tests -v
```

`scan now` now automatically refreshes the official Binance inventory and
aggregate ticker/book/premium data on the operator's authorized ordinary host,
then reuses the existing Basis client for the five-name narrow observation path.
`scan live` is an alias. No key or manually prepared JSON file is required.
The old owner-snapshot path remains available only when explicitly supplied with
`--inventory` and `--inventory-provenance`; it is not an operational prerequisite.
The Python `scan_now` function retains the Session 2 observation scaffold for
compatibility; the CLI routes ordinary no-snapshot execution through `scan_live`.

Normal output is a **partial research report**, not a qualified shortlist.
Inventory/current observations are operational. Full CORE and all production
strategy/method detectors remain disabled. The narrow width3 observation is not
historical compression or a supported causal setup. No scheduling or trading
operations exist in this component.

## Explicit bounded qualification

```bash
python3 -m researcher scan qualify --output work/qualification-001.json
```

This command fetches current APIs automatically and independently selects two
disjoint 50-name lower/medium-turnover partitions and a seven-name footer from
the verified exchange universe. Both timeframes use the existing partition
engine, one Basis MCP session, registered formulas and serial request budgets.
The cohort view is explicitly a partial subset; the enclosing report retains
the actual full exchange denominator. This is a qualification probe, not implicit
production enablement or a full-universe scan.

At most five symbols receive 300 closed official klines on each of 1H and 15M:
at most ten history calls. BTC/ETH plus quiet/native-spelling examples are chosen
from verified metadata. Young contracts are included if actually present;
numeric prefixes are never interpreted as multiplier evidence. The observed
inventory had no eligible contract younger than 30 days and no explicit
contractMultiplier facts, so those tests remain unexercised/unsupported.

The same selected data feeds Decimal numerical checks and retrospective causal
reconstruction. No market-wide local candle engine/database is built. The
production detector flags stay false regardless of a successful probe. The
report preserves unsupported specialist requirements and NULL/rival hypotheses.

## API and failure policy

Only fixed official public endpoints are allowed: `exchangeInfo`, `ticker/24hr`,
`ticker/bookTicker`, `premiumIndex`, bounded `klines`. GET only, no authentication,
no redirects, no alternate hosts, and the official adapter disables proxy use.
403/451 and 418/429 stop all Binance routes for that run. No denial retry or
location change occurs. Each new on-demand invocation on its intended authorized
host performs its own access check; the historical Cloud denial remains recorded
separately from Local's successful evidence. A denied/unreachable official source
produces an explicit blocked report with no provisional/fabricated replacement.

The official adapter has 20 total request budget, 25-second HTTP timeout and
2 MiB response cap. Short in-memory caching uses 300 seconds for inventory,
10 seconds for pulse and 60 seconds for identical fixed-cutoff samples. Reused
responses retain their original timestamps and freshness checks. The qualified
sample client allows at most five names/ten logical history calls. Qualification
uses an 80-request Basis transport ceiling, eight screen attempts and two possible
recovery calls; mandatory serial screen pacing and byte limits are unchanged.
The ceiling is a safety budget, not an estimate of free entitlement/cadence.

Actual `x-mbx-used-weight-1m` observations and Retry-After are sanitized in receipts.
These headers are not per-call charged weights and may vary across upstream
services. Basis charged units were not returned. Sustainable hourly/15M operation
remains unqualified. The returned 24h ticker interval is minute-aligned and can
be almost 60 seconds longer than 24h; exact interval and units are retained.
It must never be joined as a synchronized completed-bar cross-section.

## Causal metadata and persistence

The qualification runner writes only compact frozen reference/event/hypothesis
metadata to ignored `work/research-metadata.sqlite`. SQLite snapshots are
append-only/idempotent; later retrieval reuses original scale/availability.
Database files, caches and runtime candle output are never committed. Persistent
watch recovery, gap repair, ranking and full handoff integration remain later
work packages. The ledger is not a trading database and has no order interface.

[Measurement semantics](SESSION_03_NUMERICS.md) specify formulas, warm-ups, units,
causal timing and limitations. Every 31-method registry row includes role,
necessary evidence, dependencies, chronology, traps, rivals, invalidation and
provider/fidelity status. F2/F4/F5 and FVG/iFVG have executable trial transitions;
F1/F3/F6 are partial formation/primitives; F7/F8 have numerical primitives;
F9 is not implemented. Specialist and undefined methods stay visible and disabled.

## Actual Local results and remaining gates

See [curated evidence](../../evidence/external-first/session3/README.md).
The normal live command succeeded with 519 verified eligible contracts and
518 valid ticker observations (one row rejected) and 519 valid book/premium
observations in that final normal run.
The distinct qualification run requested/evaluated 107/107 per timeframe, with
13 footer fillers excluded per timeframe; its book data had three stale rows.
Other tested prices, volumes, lag/extrema/median/odd-median quantile and width
matched independent Binance data within fixed precision tolerances.

Two real failures are retained: Basis ATR matches an alternative first-bar H−L
seed, not the blueprint previous-close-required seed; targeted `market_candles`
failed for `我踏马来了USDT` on both timeframes although its screen rows succeeded.
Do not treat tool-level HTTP 200 failures as zero opportunities or promote
those capabilities. Four ATR formula checks fail blueprint equivalence, while
four conditional recurrence and alternative-seed checks pass. The 135 passing
unit/integration/evidence tests explicitly preserve those live failures.

Session 4 may use the live inventory/current data and selected causal primitives.
Full CORE remote equivalence, full-universe coverage, remote causal method packs,
actual young-contract qualification, unsupported specialist sources and sustainable
quota remain required gates. Context interpretation, query planning, room/ranking,
shortlist integration and watch resumption remain assigned to later packages.
No owner credential or purchase is currently required. Next Cloud work must
fetch the exact Session 3 pushed SHA and recheck its own lawful provider access;
Local success is not proof that the Cloud's denied route is now accessible.
