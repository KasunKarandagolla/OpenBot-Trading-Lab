# Session 6B — Cloud completion of deterministic research

CODEX_CLOUD / SOL, owner completion Session 2 of 3. Repository
`KasunKarandagolla/OpenBot-Trading-Lab`, branch
`feature/external-first-market-researcher`, PR #24 remains draft.
Starting fetched remote SHA: `9b8128abc0868ff9e086c85b07c79367c27bd5af`.
The generated checkout originally tracked only main; the approved branch was
explicitly fetched and safely checked out. Clean baseline, one writer, no reset,
force push, merge, trading write or downstream integration. The immutable
blueprint/plan hashes still validate. Final publication SHA/CI are in the handoff.

## Working path and reproduction

`python -m researcher scan now` calls the existing `scan_market_research`.
It executes inventory/identity checks → source-qualified packs or legacy price
fallback → A/B/C nomination union → BTC/ETH/breadth context → protected selected
history → Session 6A families/methods → `formation_cards` → bounded equivalent
questions → first-obstacle/economics → family fronts/Pareto review → atomic
watches/negative records/versioned report/read-only export.

No second demo pipeline, whole-market local history, new model, paid dependency,
daemon or trading interface was introduced. Ordinary Local operation still uses
the existing official/Basis adapters. In Cloud use only these offline sources:

```bash
python -m unittest discover -s tests -v
python -m researcher config validate
python -m researcher scan now --replay synthetic-6b --db work/control.sqlite --output work/control-cold.json
python -m researcher scan now --replay synthetic-6b --db work/control.sqlite --output work/control-warm.json
python -m researcher scan now --replay retained-session5 --db work/retained.sqlite --output work/retained.json
python -m researcher show results --db work/control.sqlite
python -m researcher show watches --db work/control.sqlite
python -m researcher show coverage --db work/control.sqlite
python -m researcher provider status
git diff --check
```

Output paths must be new JSON files under `work/`. Inspection opens SQLite with
`mode=ro`. Runtime DBs/full reports stay ignored. `research_shortlist` is a
versioned standalone body with a hash calculated without its `payload_sha256`.
`handoff_export` retains its existing `openbot.research-handoff.v1` contract;
`replay_export` resolves all cited facts and re-evaluates admission without I/O.
No consumer is connected. Compact watch/negative records retain original event
IDs/source hashes and resolve through the atomic metadata ledger.

## Actual evidence and limitations

See [ordinary CLI measurements](../../evidence/external-first/session6b/ordinary-cli-verification.json),
[generated synthetic handoff](../../evidence/external-first/session6b/synthetic-handoff.json),
[resource scenarios](../../evidence/external-first/session6b/resource-scenarios.json) and
the [exact 27/9/31 matrix](SESSION_06B_MATRIX.md).

| Before | After | Qualification boundary |
|---|---|---|
| New analyzer output primarily stopped at selected diagnostics; review cards used older F2/F4/F5 | All nine actual timelines feed family-specific review with original references, simultaneous rivals and NULL | No new live family certification |
| 31 method diagnostics but narrow review roles | Applicable method roles/results and strict specialist initiators are traceable in cards; all 31 × TF coverage rows retained | 18 offline-oracle / 11 source-dependent / 2 definition-pending |
| Specialist contracts/native OI only; no generic certified feed | Independently scoped registry validates complete envelopes before B initiation; genuine retained native depth and synthetic B-only scan verified | No new live third-party feed/entitlement installed |
| No normal-CLI controlled positive | Two CONDITIONAL_FOR_DEEP F4 hypotheses for one native control contract, distinct 1H/15M references, declared economics and complete export | SYNTHETIC_TEST; no live opportunity claim |
| No normal retained-provider replay command | Same ordinary pipeline replays five original selected contracts/price responses | AUTHENTIC_RETAINED_REPLAY; historical 519 denominator disclosed separately |
| Repeated missing-source questions | Equivalent fact/absence caching; retained run has 40 distinct source-gap audits and 81 consolidated planner records for 4,239 hypothesis links | No speculative API/model calls |
| Optional cost conflict not planned explicitly | Exact partitions and omissions; 22 CORE +22 participation +22 approach =66, under historical 26-cap only four optional calls remain after CORE | Quota/throughput/rights remain UNKNOWN |
| Older watch could disappear from newly proposed pivots | Original covered watch references reopen; uncovered originals retain SOURCE_COVERAGE_LOST/GAP_UNOBSERVED | Never invent a past READY |

Frozen synthetic invocation: 2 conditional hypotheses, 8 watches, 4 near misses,
2 invalidations, zero unreviewed symbol/TF questions. Cold 1.816s scan CPU/wall
scope, warm 0.071s; zero market HTTP and zero LLM. Warm native-history replay
calls fall from eight to zero. References/events/hypotheses/watch revisions remain
8/28/30/8; DB 405,504→413,696 bytes. Times are Cloud measurements of offline
processing before final persistence/JSON writing, not provider latency.

Retained invocation: five dated source identities; both price TFs evaluate 5/5;
eight selected symbol/TF histories are reconstructed. Zero handoffs, 404 watches,
89 near misses, 713 invalidated hypothesis records, two omitted symbol/TF questions.
BTC/ETH 4H is explicitly unavailable; no quote/depth/fees were fabricated. Scan
15.848s, metadata DB 17,485,824 bytes; zero market HTTP. These are retrospective
graph results, not 404 prospectively useful discoveries or a false-positive/recall
study. The large retained watch set remains an empirical usefulness question.
All 14 genuine Session 5.5 histories separately traverse interpretation in tests
using original timestamps/hashes/ticks. No new candles were downloaded.

The old 903 omissions/507 names were a different live 519-contract observation;
they are not a matched before/after recall comparison with this five-name replay.
Protected live review remains two alt symbols with a causal slot plus rotating
watch/quiet/contrary/audit/specialist capacity. All other questions remain explicit
budget omissions. C audit samples non-nominated names where present; no recall
estimator or success probability is claimed.

## Decisions, economics and durability

EARLY remains legitimate before later confirmation. Family-specific completion
paths use actual 6A events, not a renamed aggregate score. Same-reference rival
invalidations cannot invalidate a surviving primary. Reference-defining shock/
value observations are distinguished from subsequent events. The interpreter
does not infer institutions, footprints, OI side or liquidation causes.

BTC/ETH context can simultaneously show trend, range, compression, HTF decision,
shock and disagreement. Breadth has synchronized return denominators, median,
MAD/IQR and ETH-minus-BTC leadership; sectors remain UNKNOWN without a dated
mapping. Context changes question ordering, with matched allowance and identical
alt nominations; it cannot veto direction. Source-backed bullish BTC/bearish alt,
bearish BTC/bullish alt and disagreement controls pass.

Economics uses the first pre-known opposing obstacle. Consumed or expired first
obstacles are never replaced by a farther favorable one. Spread, native lot/
min-notional and displayed depth retain their actual source scope. Fee, extra
slippage and funding bounds remain explicit declared scenarios; actual personal
tiers, future impact/funding and price arrival within 15h remain unverified.
The frozen resolution cushion is separate from observed friction. Only factual
qualified bounds can yield READY/FAST; declared bounds yield CONDITIONAL. FAST
uses the primary's recency/proximity, not a newer sibling event. No entries,
stops, targets, sizing, orders or calibrated success odds are produced.

The existing ledger schema/single-writer transaction and one current scalar cache
are preserved. Shared graph fragments merge before chronological upsert. A newly
reconstructed old event can be inserted only with genuinely later availability;
the default strict `ResearchLedger.record` API is unchanged. Earlier snapshots,
event identities and availability are never rewritten. Complete qualified selected
history can mark interval reconstruction; it never certifies timely past action.
Incomplete history remains GAP_UNOBSERVED. Nested warm-report deltas avoid copying
the full report repeatedly. Crash rollback, identity quarantine and read-only
inspection remain tested.

## Source activation and resource gates

`QueryPlanner.ResearchSources` defaults to no new qualified provider. Exact
symbol/venue/TF/window/units/rights/freshness and independent receipts gate every
operation. Providers cannot install callables or permissions. Equivalent queries
share facts, while geometry-dependent depth is bound to reference, direction and
first obstacle. Each answer declares the alternative decisions before I/O.
Equivalent unavailable operations share an explicit absence state. Query and byte
budgets are bounded; no source is called merely because its method name exists.

After actual Local verification, an operator-reviewed
`openbot.source-qualifications.6b.1` manifest under `work/` can be passed with
`scan now --qualifications work/local-source-qualifications.json`. It must cite
hashed successful Local numeric artifacts, separate
`openbot.formation-oracle.6b.1` chronology/coverage checks, rights, exact native
contracts/TFs, validity and current pack hashes. Numeric-only receipts cannot
promote a live detector. Certificates can scope packs/families/methods independently
without modifying interpretation or comparison code. No live certificate is shipped.

The 519/50 scenario has 11 partitions: CORE22, participation+22, approach+22;
quiet/correction each add22. The versioned planner also reports 100/1,000-symbol
scenarios and insufficient/known/unknown quota. Its byte/latency estimates reuse
explicit retained receipts with a stated constant-payload assumption; new 12-column
sizes, cardinality scaling, cold/warm p95 and sustainable quota are unmeasured.
Actual Basis transport retains 40 HTTP ceiling including handshake; the narrow
causal phase is capped by remaining transport after broad work. Optional failures
cannot erase CORE. Plan A: qualified full CORE; plan B: only qualified scalars plus
protected watches/exceptions/audits, honestly partial. No broad local candles.

## Verification and final Local Session 3 checklist

Inherited 295 tests pass; 36 new tests cover the ordinary positive path, all nine
interpreter positives, all method rows, strict B-only/genuine retained specialist,
A-only/C-only/union, contexts, equal budgets, actual decision-changing quote query
and cache, first obstacle/economics, all14 retained histories, immutable exports,
warm counts, gap coverage, source/clock failures and no network/order/model calls.
The complete final test receipt, configuration/reference checks and clean-checkout
verification are retained in the evidence directory. No inherited assertion or
fixture was weakened, deleted or skipped. The previously observed ~6-second
clock regression remains a Local qualification gate; simulated recovery does not
prove the owner's host clock or eliminate that real observation.

Only the owner's normal authorized Local machine should perform the following:

1. Fetch the final published feature SHA; keep PR24 draft and one writer. Run the
   full suite/config validation and inspect saved schema/manifest hashes.
2. Refresh genuine official inventory/book/depth/precision metadata; select quiet,
   young, multiplier and exact Unicode contracts without symbol guesses.
3. Run the existing registered numeric probes, one selected symbol/TF per command:

   ```bash
   python -m researcher analytics local-oracle --environment CODEX_LOCAL --symbol BTCUSDT --timeframe 1h --output work/6b-btc-1h.json
   python -m researcher analytics local-oracle --environment CODEX_LOCAL --symbol ETHUSDT --timeframe 15m --output work/6b-eth-15m.json
   python -m researcher analytics local-oracle --environment CODEX_LOCAL --symbol 1000PEPEUSDT --timeframe 1h --output work/6b-multiplier-1h.json
   python -m researcher analytics local-oracle --environment CODEX_LOCAL --symbol 我踏马来了USDT --timeframe 15m --output work/6b-unicode-15m.json
   ```

   Use exact current quiet/young IDs for additional bounded probes. Each command
   retains the existing 300-bar/45-Basis-HTTP bound; it cannot auto-promote a pack.
4. Prove actual two-pack 1H/15M numeric and semantic full-universe scope, sparse/
   finite nulls, cutoff, tick precision, all partitions and original formation
   causality. Retain separate independent formation/source-coverage proofs; only
   then authorize the exact qualified certificate. M14/M15 stay pending unless
   primary canonical definitions actually become available.
5. Verify provider free rights/permission, actual charged/remaining quota, 429,
   cold/warm payloads and p50/p95 without a burst or paid assumption. Enable only
   available lawful specialist feeds with strict venue/window fidelity.
6. Run live `scan now`, quoted room/friction/horizon and contrary/quiet/young cases;
   verify current economics at export, gaps, interruption/resume and the original
   host UTC issue. Record prospectively sampled non-nominated cases. A zero live
   shortlist is valid under explicit coverage; a nonzero one is not guaranteed.
7. Inspect the already understood read-only export against the actual separate
   Deep Analyst. Only after source/semantic/economic/clock gates pass, connect the
   one-way consumer. It may decline without any callback or trading side effect.

**Status: deterministic on-demand workflow works offline; production PARTIAL.**
Zero Cloud Binance or other market-provider HTTP. No additional Cloud Binance
session, paid source, downstream connection or production GO is implied.
