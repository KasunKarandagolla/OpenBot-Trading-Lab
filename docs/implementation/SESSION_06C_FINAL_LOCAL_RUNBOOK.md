# Session 6C Local completion programme — A/B verified, C acceptance pending

Current C code/real failure/verification record:
[combined acceptance](SESSION_06C_COMBINED_ACCEPTANCE.md). Interactive operation:
[operator steps](SESSION_06C_OPERATOR.md). The corrected native Windows receipt
reader awaits one coordinated owner app submission; no final completion or
source-limited final publication is claimed. Earlier phase records below remain
historical evidence, not current activation permission.

Current: A pushed/verified at `8a7e61b`, both CI success; owner approved strict
Phase B bounds. Actual existing native Researcher/model and complete skill load
are verified;12/12 corrected response citations validate. Combined acceptance
remains Phase C, source scope PARTIAL. Read the [native review and operator
steps](SESSION_06C_NATIVE_REVIEW.md) and [impact inventory](SESSION_06C_INTEGRATION_IMPACT.md).
The original standalone checkpoint record below is retained as history.

CODEX_LOCAL / SOL, 2026-11-14. Started from fetched feature SHA
`0034faec6a15690c67a3526eafdf94cd46490b62`, fast-forwarded from the older Local
checkout. One writer; branch `feature/external-first-market-researcher`; PR #24
remains draft. Main remains `2343053ce68f6fff4525c5b67771ea445deb3779`.

This is a **standalone PARTIAL checkpoint**, not final programme completion or
permission to activate an LLM/downstream consumer. Phase B requires the owner's
approval of the remaining source/formation scope. No subagent, skill, model,
execution or trading module has changed in Phase A. Runtime LLM calls: zero.

## Actual source results

Fresh official exchangeInfo returned 946 records: **519 eligible** crypto USD-M
USDT perpetuals and 427 explicitly excluded. Exact native symbols, tick/lot,
listing metadata and source hashes are preserved. All 519 lack an explicit
contract-multiplier field; a number prefix is not a multiplier assertion.
Newest eligible CTUSDT was listed October 1, approximately 44 days before this
run; no currently eligible listing under 30 days was available for a real young
cohort. Young/short-history behavior retains independent offline tests.

Registered CORE row coverage:

| Probe | Evaluated | Failure/recovery |
|---|---:|---|
| CORE_15M | 519/519 | All explicit eligible partitions passed |
| CORE_1H initial | 200/519 | Provider HTTP200/isError asked readers to wait about a minute |
| CORE_1H recovery | 319/319 remaining | Serial fresh run after cooldown, same 14:00 UTC closed-bar cutoff; union 519/519, no missing IDs |
| Independent quiet 50 | 50/50 | First attempt hit busy response; later serial probe passed |
| Independent medium 50 | 50/50 | Passed |
| Final footer seven | 7/7 | Thirteen liquid filler rows explicitly excluded |

These are remote row/finite-value proofs, not 519 independent candle oracles or
full family certification. Only bounded selected histories were downloaded.
Both full CORE TFs also returned BTC/ETH/FRAX/1000PEPE/native Unicode in a separate
five-symbol screen. Unicode `我踏马来了USDT` remains unsupported by Basis's targeted
`market_candles` operation while official selected klines and remote screens
work. This is operation-specific; the eligible contract is not deleted.

Independent arithmetic compared 33 registered fields ×20 closed tail values
on BTC1H, ETH15M, 1000PEPE1H and quiet FRAX15M, **660 comparisons per sample**.
Exact source starts, closed cutoffs, quote units and formula hashes are retained.
BTC/ETH/prefix samples passed their recorded compiler revisions; after discovering
zero-amplitude NULL propagation, the corrected optional correction formula was
rechecked in the complete FRAX sample. No later hash is substituted into earlier
receipts. Explicit TR/rma14 matches the selected same-start oracle. This does not
erase the older native `atr14` seed mismatch or establish infinite-history ATR.

Ten independent authentic historical source episodes support selected F2/F4/F5
chronology (M05): frozen confirmed pivot, original reference, excursion/reclaim,
later initiative, rebreak and later holds. Negative prefixes distinguish break
without holds, reclaim without later initiative and no-reclaim-not-F5. Actual
later retrieval/availability stays later; none is represented as a past READY or
a prospective live positive. The formation proof deliberately has
`source_coverage_verified=false`; it cannot authorize a whole family/method.

All **27 measurements, F1–F9 and 31 methods** are audited in
[SESSION_06C_MATRIX.md](SESSION_06C_MATRIX.md). Counts remain 18 offline-oracle,
11 source-dependent and two definition-pending (M14/M15). True profile, footprint,
absorption, complete witnessed liquidations, dated sectors and original-publisher
catalysts have no newly qualified feed. No proxy silently supplies them.

## Repairs demonstrated by real failures

- Compacted repeated percentile expression branches and flattened the long sum
  after Basis rejected the original formula at its 128-level nesting limit.
- Kept local variable declarations outside scalar export multiplication; the
  initial scaled expression otherwise failed with an unsupported `=` character.
- Renamed reserved correction variable `e`; made an inactive zero-amplitude
  divisor finite after actual quiet FRAX yielded NULL instead of no-event zero.
- Validated the oracle's explicitly requested up-to-300-bar window while keeping
  the ordinary narrow observation limit at 65.
- Isolated numerical columns and retained diagnostic arithmetic on aligned closed
  history when a clock check fails; temporal failure still prevents qualification.
- Decoded the versioned scaled analytical columns correctly, including sentinel
  UNKNOWN semantics; cached immutable registered expressions.
- Accepted observed minute-rounded official 24h ticker windows up to one minute
  shorter as well as longer, preserving both exact endpoints. No conversion to
  synchronized closed-bar breadth occurs.
- Recognized the actual HTTP200/isError provider busy response as
  `PROVIDER_BUSY_COOLDOWN`, retained its receipt and stopped later Basis reads in
  the same run. The tool's wait suggestion is not mislabeled HTTP Retry-After.
  No automatic retry loop, free-key rotation, proxy or host change was added.

Original failed receipts remain under ignored `work/session6c/`, with compact
public hashes and summaries in `evidence/external-first/session6c/`.

## Clock resolution

Before owner intervention, repeated Binance `/fapi/v1/time` samples placed server
time outside the host request interval by approximately two seconds. Immediately
after Windows synchronization, the clock was still settling. Later **all three
Windows and all three WSL samples** placed server time within their own
`[request_start, response_receipt]` brackets. WSL offset intervals were roughly
[-60ms,+348ms], [-60ms,+220ms], [-61ms,+239ms], including network uncertainty.
No exact NTP accuracy beyond these brackets is asserted. The owner changed the
Windows clock; this session neither restarted WSL nor rewrote source timestamps.

## Ordinary CLI and resources

The final-code clean snapshot ran the normal `provider status` and `scan now`
commands against actual Local public sources, using a separate research SQLite.

| Run | Scope/outcome | Actual resources |
|---|---|---|
| Initial Local cold | 15M precursor519/519; 1H500/519; causal1H369/519; zero handoffs, 364 watches | 60 HTTP, 5,109,401 response bytes, 180.164s |
| Final-code cold | 15M precursor519/519; 1H300/519, provider busy; causal0/519; zero handoffs, 385 watches, 96 near misses, 731 invalidations | 41 HTTP (21 Basis/20 Binance), 4,353,867 response bytes, 117.310s; p95 4,030ms; DB16,867,328 bytes |
| Same-cutoff warm | Same frozen market evidence and watch identities; refreshed current official observations | 4 Binance HTTP, 0 Basis, 0 history calls; 1,809,205 bytes, 6.100s; DB16,932,864 bytes |
| Later 14:45 restart | Both precursor TFs519/519; quote15M50/519; zero handoffs; 451 watches; 210 explicit GAP_UNOBSERVED entries | 47 HTTP; 4,823,934 bytes; 150.728s; DB33,447,936 bytes;1 interrupted attempt recovered |

All final cold aggregate ticker/book/premium source-health rows accepted 519/519.
Optional quote participation and causal/family work have explicit provider/budget
omissions. An empty shortlist does not establish absence of opportunities.
The full new CORE probes are not falsely reported as enabled ordinary production
packs. Current certificates still gate them; no flags were manually flipped.

Actual charged Basis units/remaining allowance and sustainable cadence are
UNKNOWN. The publisher advertises keyless/free-key allowances; the measured
exchange-read busy message constrains this keyless session independently. Public
anonymous access does not establish contractual bulk reuse rights. On-demand
only; no scheduler or paid entitlement was assumed.

The real-process transaction-interruption test used a copy of the earlier live
research database: an uncommitted cache deletion rolled back after abrupt exit23,
with original references/events/snapshot/cache hash intact. This is an actual
SQLite process-termination test, not a claim that a network scan was interrupted.
The later ordinary CLI restart records observed gaps without backdating action.
All361 shared watch IDs retained original first-seen, known-at and available-at.
No gap claims prospective repair. Source quota/budget still omitted causal work.

## Watch noise and prospective interpretation

Authentic retained replay reproduced zero admissions, 404 watches, 89 near misses
and 713 invalidation records. Its watches occupy **four** of the five inventory
names across both TFs: 404 unique reference IDs, 396 unique exact directed levels,
588 rival interpretations, 163 references with multiple interpretations. Eight
same-level entries have different birth episodes; they are not duplicate IDs.
There were zero expired references under the declared seven-day TTL, but 321
references were known over15h and98 over72h ago. These are historical monitors,
not404 timely opportunity alerts. Every watch lacked qualified current sequence,
first-obstacle/fresh-price and economics; 323 lacked complete family sequence.

No independent labeled outcome sample supports fitting new thresholds to reduce
these numbers. No detectors or contrary/quiet lanes were suppressed. Inspect by
native symbol/TF and original reference, preserving level age and rival families.
Prospective audit timestamps, eligible/evaluated sets, baseline names and sampled
non-nominated inclusion probabilities are retained; outcomes remain pending.
No recall, false-alert rate, profitability or early lead-time claim is made.

## Verification and scope

The inherited baseline passed **331 tests**, zero failures/skips. The final
standalone regression suite adds10 tests for actual source defects; final exact
results and clean-code hashes are in the evidence verification record. All
inherited tests are retained. Immutable blueprint/plan bytes and main are checked.
The final-code snapshot passed341 tests in572.722s, zero failures/skips; config
validation passed. The earlier331-test inherited baseline took544.180s.
Changed production files are only `analytical_probe.py`, `basis.py`, `market.py`,
`observations.py`, `pack_contracts.py`, `screening.py`; other changes are focused
tests, evidence and this documentation. No skill or subagent edits occurred.

Blueprint §16/17 and Appendix B: identity/clock PASS at observed time; numeric
selected oracle and explicit whole-universe row probes PASS within scope;
methodology/specialist completeness, prospective usefulness, sustainable budget
and actual runtime agent/downstream acceptance remain PARTIAL/PENDING. No
automatic production activation follows a numeric match.

## Operator steps

```bash
git fetch origin
git switch feature/external-first-market-researcher
git pull --ff-only origin feature/external-first-market-researcher
python3 -m researcher provider status
python3 -m researcher scan now --output work/operator-run-001.json
python3 -m researcher show results
python3 -m researcher show watches
python3 -m researcher show coverage
```

Run again on demand later. Use a new output filename; the research database
persists reference identity and actual gaps. An unchanged closed-bar input reuses
evidence and refreshes point data. A provider busy response ends that run's Basis
reads; honor its cooldown before another on-demand attempt. Never supply trading
credentials. Source/model configuration, if later approved, belongs in environment
or ignored local configuration, never Git or chat. The selected command remains
`python3 -m researcher analytics local-oracle --environment CODEX_LOCAL --symbol
BTCUSDT --timeframe 1h --output work/operator-oracle-001.json` (at most300 selected
bars;45 Basis HTTP cap). Avoid simultaneous independent Basis probes.

## Before Phase B

Publish/verify Checkpoint A and both CI triggers first. Ask the owner to approve
strict interpretation of source-correct supported evidence with unsupported full
methods and no unqualified admissions, or require additional source certification
before connection. Then inspect the actual existing OpenBot agent/backend and
produce its smallest allowed-diff list. A missing real backend/entitlement requires
a concrete secure owner setup request. No new subagent or wider framework rewrite
is authorized. Phase B/C and the final result remain unfinished at this checkpoint.
