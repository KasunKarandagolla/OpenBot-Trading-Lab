# Session 5 — on-demand remote research and durable watches

**Environment: CODEX_LOCAL. Date: 2026-11-14 (Asia/Colombo). Release: PARTIAL.**
This is the authorized Session 5 implementation, not a diagnosis-only session.
Full CORE, broad production family detectors and the complete 31-method source
exit gate remain unqualified. Do not describe the price-precursor pass as complete
structural discovery, or assign these source/causal gaps to Luna.

## Operator command

Python 3.11+ and the standard library; measured here on Python 3.12.3. No packages,
keys, trading account, prepared inventory JSON, trial subscription or daemon:

```bash
python3 -m researcher config validate
python3 -m researcher provider status
python3 -m researcher scan now --output work/research-001.json
```

The same command works in a separate process later. Default state is the existing
`work/research-metadata.sqlite`, upgraded from the Session 3 schema. `--db` selects
another research database under `work/`. `--json` prints the full report; otherwise
the CLI prints a concise coverage/watch/cost summary. Output JSON must be new under
`work/`; publication is atomic and never overwrites an existing file. SQLite is
the authoritative atomic metadata record if writing an output file fails.

`scan now` and the existing `scan live` alias use **one** `scan_market_research`
function in `discovery.py`. The explicit owner-snapshot compatibility path and
older Python trial interfaces remain recovery/test interfaces. Ordinary operation
never needs them. `scan qualify` now runs the bounded Session 5 selected CORE/seed
probe; it records evidence and does not automatically change capability flags.

## What a run actually does

1. Validate configuration, immutable reference hashes and pinned qualification.
   Obtain the SQLite writer transaction; an interrupted prior attempt is marked
   `INTERRUPTED`, with no invented successful cutoff.
2. Freeze UTC run start and independent last-closed 15M/1H/4H cutoffs. Refresh
   official Binance exchangeInfo, rolling ticker, bookTicker and premiumIndex.
   Preserve exact symbols, COIN/perpetual/USDT settlement/status/listing/filter
   facts, exclusions, missing rows and source hashes. Prefixes are not multipliers.
3. Run the registered **15 price columns plus one optional quote-RVOL column** through the existing Basis
   client, explicit partitions and PartitionEngine. The 15M pass runs first.
   Each partition has at most 50 requested names, lookback 300, limit 60. Footer
   fillers are excluded. Validate every column, exact identity, echoed expression,
   counts, finite values and actual closed source cutoff.
4. Keep independent pressure/shock questions, historical-quiet questions,
   positive/negative relative exceptions, new listings and saved watches. These
   are precursor questions, not supported complete family formations. Specialist
   route B remains unavailable: there is no qualified specialist runtime source.
5. Obtain six selected BTC/ETH histories (1H, 15M and 4H), construct real benchmark
   ContextCards and synchronized remote-return breadth/dispersion. Sector context
   stays UNKNOWN without a dated exact-perp mapping. Context orders investigation,
   never direction eligibility. Watch, exception and structural allocations share
   at most **two selected alts / four further history calls**. Omitted questions
   retain `NOT_REVIEWED_BUDGET`; rotating ties are not a recall/profitability study.
6. Reuse the frozen reference/event/hypothesis and review engines on those small
   selected histories. Reopen original references without changing their ATR,
   bounds or first availability. Add targeted EQH/EQL trials from two confirmed
   pivots, first-pivot frozen ATR/tick tolerance and intervening retreat; the pool
   becomes known at second confirmation. This is inferred liquidity geometry.
   Retain F2/F4/F5 same-reference chronology, FVG/iFVG and bounded F1/F3/F6/F7/F8/F9
   watch facts. F7 is complete UTC-session whole-bar Q/V, not a true profile or
   weighted variance; F8 training precedes evaluation; F9 says POST_SHOCK, never
   witnessed liquidations without a covered source.
7. Refresh selected current book/premium observations before review. Actual
   midpoint/spread can be cited; top-of-book is not depth, and current funding is
   not a certified future bound or account fee tier. The planner stops at missing
   necessary facts instead of requesting unrelated specialist trivia.
8. Apply existing room/economics, source/stage, Pareto/diversity and maximum-five
   admission rules. No source-backed fee/depth/slippage/funding/horizon package or
   complete production causal pack is presently enabled. Thus the measured empty
   shortlist means **incomplete admission/causal coverage**, not no opportunities.
9. Atomically save coverage, sanitized request receipts, references, events,
   hypotheses, watch revisions, output hashes and verified *scope-specific*
   cutoffs. Emit shortlist, watches, near misses, invalidations, budget omissions,
   source health, costs and time gaps. No Deep Analyst connection is required.

## Numerical qualification and operation-specific limits

`core.py` declares exact expressions, units, history, baseline exclusion, tie
semantics, export scaling and source-window semantics. The qualified subset is:
explicit TR/rma ATR14, normalized width16, past-only quiet percentile (128 windows,
entire current 16-bar window excluded, ties half), efficiency16, gross progress16,
prior high/low16 and distances, TR/previous close, closed close, displacement using
prior ATR, body fraction and two fixed-T-minus-8-boundary episode-start proxies.
Those visit proxies are not significant frozen boundaries, full separated-retreat
pressure or ordered F2/F4/F5 predicates. Rolling bounds are explicitly proxies.

Native Basis `atr(14)` remains rejected. The original four evaluations / 80 failed
values and Session 4 exact-start failures remain regressions. Session 5 explicit
TR/rma passes eight identical-start long windows and eight short windows on
BTC/ETH/1000PEPE/quiet FRAX × 1H/15M. Short windows preserve initial NULLs, the
14-valid-TR seed and six finite values; long tails preserve 20 values each.
This is **selected window-start semantics**, not an infinite-history ATR promise.

A real new defect was found and repaired: screener numeric exports round to four
decimals. Unscaled ATRs/small prices can become zero. Registered expressions now
export ×100,000,000, then decode, with declared tolerance. The scaled close column
also validates very small prices without trusting the rounded ordinary `last`.
All **160/160** current selected scalar checks pass (5 symbols × 16 × 2 tf).
Unicode `我踏马来了USDT` participates successfully in these screens and has independent
Binance oracle data; Basis **targeted market_candles still fails on both tf** with
HTTP 200/MCP tool errors. Operation-specific support is never generalized.

The original `quoteVolume` expression returned MCP_TOOL_ERROR. The supported
`quote_volume` spelling matches independent native USDT quote-volume RVOL. A finite
validity encoding keeps zero baseline UNKNOWN separately from genuine zero RVOL;
missing participation does not disable the other price columns or price families.
One exploratory alias call used the provider default 999-bar remote window and
was not qualifying evidence; the final client requires a bounded loaded reference.
All qualifying windows are at most 300 bars. A new positive-pressure trial exposed
`high[0]`/`low[0]` not behaving as current fields: zero-only samples had missed this.
The explicit-current-field remedy passes 16 independent pressure-tail evaluations
(320 values, including 45 positive values), alongside the 16 ATR evaluations.
Both failed pressure-expression trials remain recorded, never relabeled as passes. True profile,
price-bin footprint/absorption, OI direction, complete liquidations and unspecified
primary-source methods remain UNKNOWN/UNSUPPORTED. Young and official multiplier
cohorts were absent/unproven in the real qualification; their simulations are not
live qualification. All 31 methods and F1–F9 remain visible with explicit states.

## Persistence, gaps and resource boundaries

Schema version 5 adds run attempts/snapshots, watch revisions, exact evaluated
symbol sets per verified cutoff and **one bounded current scalar cache** to the
existing ledger. Historical snapshots do not retain whole-market scalar rows or
candles. Unchanged-bar snapshots store compact deltas. Selected causal metadata,
source receipts, output hashes and immutable origins remain auditable.

Immediate repeats still require fresh official inventory/current source access.
Within 300 seconds and the same cutoffs, identity/configuration and source scope,
the closed-bar evidence and watches are reused without Basis/history/LLM calls.
Retained partial failures remain visible; reuse does not turn them into passes.
A different bar, identity, capability revision or expired cache triggers new work.

Only a source-covered scope advances its last verified observation cutoff. Failed
attempts never do. Missed closes are `GAP_UNOBSERVED`; current hindsight candles
cannot establish timely historical discovery/actionability. Watch gaps retain
the last viable reference. No arbitrary Basis historical-as-of repair is claimed.
Delisted/changed identities are archived/quarantined, never silently renamed.
Corrupt/foreign/future-schema databases are rejected without replacement. SQLite
savepoints compose with the outer transaction, and crashes roll back all metadata.
No terminal reference may be resurrected on a later selected reconstruction.
If host UTC regresses behind a completed receipt, preserve the raw timestamps,
record clock uncertainty and use the maximum observed known-by bound for atomic
metadata ordering. This never changes bar cutoffs or source times, establishes
historical actionability, or permits READY admission under clock uncertainty.

Limits are local safety ceilings, **not provider entitlements**: 26 serial screen
attempts including two bounded recoveries; 40 Basis HTTP calls including handshake;
20 Binance transport requests; five maximum selected symbols, ten selected history
calls and 300 bars each. The normal selection uses four unique symbols / ten calls.
403/451/418/429 stop the route; Retry-After is preserved, never slept through for
an automatic denial retry. HTTP 200 + isError is failure. No provider-as-of option
has qualified: a source advancing beyond the frozen cutoff is rejected, even if a
partition succeeded numerically. Running near a boundary can therefore be PARTIAL.

Recorded development pass: 519/519 requested/evaluated/returned on each tf for the
then-15 columns. Its zero-offset pressure qualification was later revoked and
repaired using positive events; protocol coverage is not mathematical proof. Earlier runs include 517/519 1H and 0/519
15M after cutoff advancement, then partial MCP failures (300/519 and 319/519).
The failure evidence is retained. A separate-process repeat used four official
requests, zero Basis/history calls, 1,808,644 response bytes and 6.342 seconds.
These were development-run measurements; clean-checkout measurements and exact
final tests are recorded in the evidence directory and PROGRESS.

Charged units, daily free quota, sustained automation rights and sustainable cadence
remain UNKNOWN. Request bodies/URLs and response bytes are measured separately;
private headers and request-header bytes are not retained. At 519 names, **scenario
assumptions only**: 11 partitions/tf; both tf hourly = 528 screens/day; both every
15 minutes = 2,112/day; 1H hourly plus 15M each quarter-hour = 1,320/day, excluding handshake,
retries, context and enrichment. No scheduling is enabled or quota promise made.

## Verification and remaining release work

Run `python3 -m unittest discover -s tests -v`, config validation and
`git diff --check`. Curated live/failed-trial, source/schema, resource and explicitly
SIMULATED gap evidence lives in `evidence/external-first/session5/`. The original
184 tests remain intact; new tests cover exact source seeds/initial samples,
scaled multi-column export, filler/clock mismatch, atomic file/DB rollback,
restart/cache idempotency, bounded scalar retention, gaps/outage/recovery,
delisting/changed identity, new listings, zero ATR/volume and EQH confirmation.

**Owner assistance now: NONE for the supported subset.** Do not collect an exchange
key to hide absent fees/specialists. Full CORE and remote ordered family/method
compiler/source qualification, actual source-backed admission facts, genuine
specialists and sustainable provider rights remain Sol responsibilities. They
are not implementation work for Session 6 Luna. Luna's dependency-ready scope is
bounded status/help/report presentation and operator documentation only, preserving
these gates. Keep PR #24 draft; no main merge or trading authority.
