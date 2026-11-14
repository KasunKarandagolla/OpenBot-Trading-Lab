# Session 4 — evidence-aware research review

**CODEX_CLOUD; implemented increment, production qualification PARTIAL.** This is
Session 4 of six. Session 5 retains complete on-demand orchestration, durable
watches/restart/gap recovery; Session 6 retains bounded usability and cleanup.

From the repository root, Python 3.11+; no added packages or credentials:

```bash
python -m researcher config validate
python -m researcher provider status
python -m researcher review replay-session3 --output work/review-s3-001.json
python -m unittest discover -s tests -v
```

`review replay-session3` verifies the original Session 3 evidence hashes, reuses
its frozen references/events and produces typed research review, context,
planner decisions, watches/invalidations and an empty research shortlist. Its
mode is **AUTHENTIC_REPLAY**, with original evaluation/availability timestamps;
it performs zero HTTP requests. It is not live operation, prospective discovery,
or an operator-provided JSON dependency. The ordinary `scan now` still calls
real public APIs where lawfully accessible. Cloud returned 451 once in this
session; that route was stopped, with no alternate host/location/route retry.
The transport preserves required inherited host settings without route overrides.

The separately opt-in qualification command sends real public Basis requests:

```bash
python -m researcher review probe-precursors --output work/precursors-001.json
```

It uses one read-only MCP client and a 45-HTTP-request ceiling, two selected
BTC 300-bar remote handles, registered short-tail formulas and six serial explicit
partition screens, two ETH ATR experiments and up to six exact-start seed calls. It never downloads a universe of candles. All output must be
new JSON under ignored `work/`; overwrites/symlink traversal remain rejected.
A PARTIAL output is successful observation with visible gates; a completely
blocked probe returns exit 2. It does not retry the denied Binance route or
promote formulas automatically. As retained independent observations age out of
the remote 20-value tails, their overlap can legitimately become zero.

## Implemented contracts and boundaries

- `research.Fact`: exact instrument, source/hash, measurement/units, timeframe,
  window end, known/available/received times, freshness, verdict, qualification,
  fidelity and LIVE/AUTHENTIC_REPLAY/SYNTHETIC mode. Unknown is never a negative.
- `context`: qualified BTC/ETH 4H and 1H slots; causal selected-benchmark swing
  ladder, impulse/shock trial producer; synchronized 16-bar return breadth,
  median/MAD and outperform-BTC fraction on an explicit evaluable denominator.
  Absent qualified HTF histories, missing constituents and absent dated perp
  taxonomy stay UNKNOWN. Rolling tickers cannot become HTF structure. The
  current replay has UNKNOWN qualified context and a neutral agenda.
- Context can order research questions for F1, F6/F4, F2/F3 or F9; it cannot delete
  nominees, change direction eligibility or manufacture facts. Equal-budget
  studies retain all unreviewed IDs. Current studies establish deterministic
  fairness, **not empirical discovery lift** or a validated priority advantage.
- `query_planner`: lexicographic necessary fact/contradiction policy, exact
  contract/venue/timeframe/window/units, allowlisted reads, rights/history/freshness
  rejection, separate broad/targeted/exception/watch pools, lower-cost equivalent
  queries, validated cache and unchanged-WATCH suppression. Adapter injection is
  the integration boundary; no specialist adapter is enabled. An unresolved
  necessary fact stops unrelated evidence chasing. No source => UNKNOWN; an
  actual quota/budget omission => NOT_REVIEWED_BUDGET. Defaults: 0/4/1/1 pools,
  2 MiB declared response budget, at most eight steps per investigation. Provider
  transport limits remain independently enforced; these are local ceilings,
  not measured vendor quota entitlements.
- Three routes remain distinct: A qualified remote structural, B qualified
  specialist, C watch/quiet/exception/audit. A is currently blocked by remote
  causal predicate qualification. B accepts only explicitly qualified scoped
  capabilities; its default registry is empty. C can preserve real dated
  references and low-width questions without mover-rank or BTC-alignment gates.
- `candidate_review`: typed observation/event/reference/rival/disposition cards;
  exact contract/reference/event-window dedupe preserving initiators/methods;
  NULL plus real opposing hypotheses; distinct same-reference F2/F4/F5 chronology.
  Other family detectors retain their original partial/blocked states. A stage
  is not determined by a distance threshold. Every stage's necessary evidence
  appears in `STAGE_REQUIREMENTS`. READY/FAST require a supported qualified current
  sequence, current verified active identity, significance, a pre-known first
  opposing obstacle, fresh price/spread/depth, actual fee evidence, declared
  slippage/funding bounds and demonstrated relevance within 54,000 seconds.
- Room freezes the first valid opposing reference before the initiating window;
  it does not skip a consumed obstacle for a farther one. Room units are price
  geometry, not a promised profit or executable target. Distinguish ROOM_UNKNOWN,
  ROOM_EXHAUSTED, ECONOMICS_UNKNOWN, HORIZON_UNCERTAIN and measured unfavorable
  friction. Point price/spread/depth age is capped at 30 seconds for admission;
  identity metadata is capped at one day. Existing source-specific TTLs also apply.
- Admission uses explicit significance/urgency/contradiction Pareto comparisons,
  records same-family versus cross-family comparisons, preserves incomparable
  cases and considers declared exposure diversity. Room and economics are
  necessary safeguards; unlike price distances are not forced into a score.
  No vendor-score or BTC-direction ranking criterion exists. At most five
  handoffs, with all watches, invalidations, late cases, capacity near-misses and
  not-reviewed items retained. Multiple price observations remain one cluster.
- The compact Session 3 SQLite metadata ledger and immutable IDs remain reused
  interfaces. No new candle table, runtime DB artifact, scheduler or recovery
  claim is added. Persistent admission/watch wiring belongs to Session 5.
- One original, minimal reasoning skill at
  `.agents/skills/market-research-review/SKILL.md`; reviewed pinned older OpenBot
  skills and current-contract first. Reused reasoning concepts, imported no old
  code/text, conflicting top-volume funnel, regime veto or execution interfaces.
  No standalone license was found in the inspected tree; no external package
  was installed. Default/model calls zero; optional LLM integration unimplemented.

## Real source qualification in this session

See `evidence/external-first/session4/qualification.json` and its checksums.

- One ordinary Cloud Binance inventory request: HTTP **451**, 224 bytes, 722 ms.
  No further Binance requests, route bypass, account or credential use.
- **52 Basis HTTP requests**, including three MCP handshakes; total session
  **53 requests / 373,822 response bytes / 52,346 ms summed request durations**.
  p50 774 ms; nearest-rank p95 3,260 ms. One HTTP failure (451), one HTTP-200 tool
  failure (Unicode alternative). No quota charged units were returned. Separate
  probe wall times were not instrumented; no wall-time/cadence SLA is inferred.
- Twelve registered formulas executed for BTC on both 1H and 15M: normalized
  width16; quiet width / past-only median; exact past-only quiet percentile;
  prior 16-bar high/low; upper/lower rolling distance; efficiency16; gross
  progress16; **base** RVOL32; TR fraction; explicit TR/rma ATR experiment.
  The percentile uses 128 windows ending 16–143 bars ago; the measured 16-bar
  window is excluded and ties count half. Required history is 159 closed bars.
  A rolling high is a boundary proxy, not a frozen significant level. TR fraction
  is an ATR-independent displacement precursor, not a normalized shock detector.
- An additional explicit ATR experiment on ETH 1H/15M brought the retained-source
  comparisons to **98/98 matched** across **22 feature/timeframe evaluations**;
  **four other evaluations** (quiet median ratio and base RVOL, both timeframes)
  lack sufficient independent retained inputs. Comparison timestamps are exact
  retained Local oracle times, not fresh Cloud Binance observations. Remote
  partition readings are rounded to four decimals; they are not tick-exact.
- Of the 98 matches, **four** compare long-warm-up explicit TR/rma outputs to
  retained 300-bar independent ATR values. History starts differ: this is warm-up
  convergence evidence, **not exact seed equivalence**. All **four original
  atr(14) evaluations / 80 comparisons** reproduce their failures; original
  first-bar H-L seed and conditional recurrence evidence remains preserved.
  Raw initial seed bars were not retained in the curated Session 3 evidence.
  `ATR_REMOTE_UNQUALIFIED` remains for broad production; full CORE stays disabled.
- A further exact-start experiment sized a current Basis handle to start at the
  first of the 20 independently retained BTC HLC records. **Explicit TR/rma
  matches the 14-valid-TR seed and five later recurrences on both 1H/15M: 12/12**.
  Native atr(14) fails those same 12 values and matches the first-bar H-L variant.
  This is a tested remote seed remedy for the two sampled BTC cases, not an
  all-contract/ETH or arbitrary replay qualification. The registered explicit
  formula is retained; native atr(14) is never silently substituted. See
  `atr-seed-experiment.json`. The original four/80 failures remain regressions.
- New live screens on dated independently selected cohorts, per timeframe:

| Remote scalar | Requested/evaluated/returned/matched | Failed | Fillers excluded | Historical 519 not requested |
|---|---:|---:|---:|---:|
| quiet percentile | 50/50/50/50 | 0 | 0 | 469 |
| gross progress16 | 50/50/50/50 | 0 | 0 | 469 |
| upper rolling distance | 7/7/7/7 | 0 | 13 | 512 |

  Distinct requested scope is **107 per timeframe**, not 107 evaluations of every
  formula or 519 structural evaluations. Historical inventory: 946 source rows,
  519 eligible, 427 excluded. Current Cloud eligibility denominator is **null**;
  inventory freshness/active identity was not revalidated. Full CORE/method
  evaluations remain **0**, with reasons per formula/contract/timeframe. Original
  independent-tail width results remain separate authentic Session 3 evidence.
- Quiet questions: **4 on 1H, 20 on 15M** at the predeclared .25 trial percentile
  band. All are PREMATURE, formation unsupported, UNKNOWN due to absent qualified
  frozen-reference/eligibility inputs. No opposite-direction or rank filter.
- `我踏马来了USDT`: original market_candles failures on both timeframes preserved.
  One supported formula-by-symbol alternative on 1H also returned an HTTP-200
  MCP_TOOL_ERROR. Successful screens still do not qualify targeted history.
- No additional specialist qualified. Previously denied specialist routes were
  not retried; no credential, paid plan or trial dependency was introduced. True
  VP/footprint/absorption/exhaustion/OI history/observed liquidations/catalysts
  remain unavailable. Bar aggressor delta is still bar evidence only.
- Historical causal review: **40 references, 37 watches, 3 invalidations, 0 READY
  handoffs**. Planner records UNKNOWN rather than asking today's live API to
  repair an unsupported historical-as-of query. All 31 methods/nine families
  remain visible with their real states. Empty shortlist does not mean no market
  opportunities exist.

## Validation and remaining gates

184 tests pass, zero failures/skips (original 135 preserved, 49 new). Coverage
includes original causal/oracle/integration tests plus typed source clocks,
1H/15M/4H, independent retained formulas, four ATR failures, unknown/mixed context,
contrary admission, specialist scope, quiet questions, equal budgets, planner
rights/cache/units/quota, room/first-obstacle exhaustion, stale friction and the
0–5 no-execution handoff. Config and immutable blueprint/plan validation pass.
Synthetic READY fixtures demonstrate contracts only, not live method certification.

P0/P1/P3 and G1/G2/G8 remain **PARTIAL**: lawful Cloud Binance access, ATR seed equivalence beyond sampled BTC cases, full causal remote CORE/history attestation, current
all-universe source/method coverage and sustainable quota are unqualified. G3,
G4, G5 and G7 have deterministic/source-regression evidence at the stated scope.
G6 durable operation is Session 5, not claimed here. G9 requires pushed remote
SHA and observed CI; exact delivery identifiers are in the handoff.

Owner help: **NONE for this delivered implementation**. To clear the live source
qualification gate, a separately authorized runtime with independently lawful
Binance access must run one bounded same-start/same-cutoff official-vs-Basis
sample: BTC/ETH × 1H/15M, 300 bars maximum, preserving the first 15 raw selected
bars plus final comparisons, explicit TR/rma and every precursor (especially base
RVOL/quiet-median baseline). Then BTC/ETH 4H × two selected samples can verify HTF
joins within the same five-symbol/ten-call cap. This is a small GitHub-synced
qualification handoff, not permission to change IP/location or bypass a denial;
no Local operation was launched here. No manual operational snapshot is requested.

Session 5 readiness: **PARTIAL**. Next dependency-ready work is to connect these
review primitives, source capability gates and the existing metadata ledger to
the read-only on-demand orchestration; implement watch persistence, replay/gap
recovery and failure-aware reports. Keep source-blocked capabilities disabled
while that work proceeds. Do not insert a diagnosis-only session or compress
Session 6 without its quality gate.
