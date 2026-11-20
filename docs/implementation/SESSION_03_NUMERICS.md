# Session 3 measurement semantics

Design authority: finalized blueprint §6–9. Implementation version
`causal-trial-3.0.0`; trial definitions are not calibrated trading settings.
All local functions are for at most five selected verification instruments,
with at most 300 bars per instrument/timeframe. No market-wide candle scanner
or historical candle store is implemented. Broad remote CORE and production
strategy predicates remain disabled until the relevant independent oracles pass.

## Common source and time contract

`numerics.Bar` holds exact native venue identity and Decimal O/H/L/C, base volume
V, USDT quote volume Q, taker-buy base BV and quote BQ, trade count, timeframe,
bar-open milliseconds, source-response hash and receipt UTC. Supported selected
intervals are 1H and 15M. All price results use source precision without rounding;
current official tick is retained as the resolution for frozen reference buffers.
Historical tick changes are not inferred from current metadata.

The official kline inclusive close must equal open + interval − 1 millisecond.
Internally, end is the exclusive interval boundary. `validate_bars` rejects
forming/future bars, nonpositive or inconsistent prices, negative volume, taker
volume exceeding totals, unsupported units, duplicates, out-of-order/missing bars,
and source receipt before close. A required current sample must end exactly at
the frozen cutoff. Short listing history remains explicit rather than padded.
Zero volume is separate from invalid data; division by zero returns UNKNOWN/None.

Geometric confirmation time is the latest required closed bar. Earliest source
publication remains UNKNOWN when not supplied. Actual receipt is a conservative
known-by/available-by bound for newly retrieved history. Reconstructed historical
events do not become prospective discovery records. If an actual recorded
`available_at` exists, evaluation excludes it before that time. No arbitrary
historical Basis replay is claimed.

## Deterministic calculations

| Function / ID | Fields, lookback and warm-up | Formula and units | Interpretation and limitations |
|---|---|---|---|
| `true_ranges` / VOL1 | H,L plus prior C; ≥2 bars | max(H−L,abs(H−Cprev),abs(L−Cprev)); price units; first value NULL | Includes gaps; first bar cannot invent previous close |
| `wilder_atr` / VOL2 | O/H/L/C; n+1 bars; n=14 | Seed = mean(TR[1..n]); thereafter ((n−1)ATRprev+TR)/n; price units | Exactly n valid TR observations requiring prior close; first-bar H−L is a different seed. Remote ATR is not silently relabeled equivalent |
| `normalized_width` / VOL3 | Last n H/L/C, tick; n=16 default | (maxH−minL)/max(C,tick); ratio | Closed current window; width alone is not historical compression |
| `past_percentile` / VOL4 | Exactly W prior finite values; W=128 | (count(previous<x)+0.5 count(previous=x))/W; [0,1] | Low means compressed. Ties fixed; short baseline raises INSUFFICIENT_HISTORY |
| `compression` | 2n+W−1 bars; n=16,W=128 needs 159 | Compare current width with W preceding width windows ending before the entire measured n-bar window | Earlier baseline windows may overlap one another; none overlaps measured window. No false neutral percentile for missing history |
| `efficiency` / PATH1 | n+1 closes; n=16 | abs(Ct−Ct−n)/sum(abs(adjacent close changes)); ratio | Zero denominator NULL; no direction or standalone trend claim |
| `overlap` / PATH2 | Two H/L, tick | Intersection length / max(min(two ranges),tick); ratio | Price geometry, not volume value |
| `displacement` / PATH3 | Current O/H/L/C, prior C, prior ATR | TR/ATRprev; abs(C−O)/max(H−L,tick); (C−L)/max(H−L,tick); signed progress/ATR | Uses the prior volatility scale. A wick alone is not initiative |
| `confirmed_swings` / LVL1 | Closed H/L; l,r∈{2,3,4}; at least l+r+1 | High strictly above left and ≥ right; low strictly below left and ≤ right | Earliest tied extreme wins. Known at right-confirming close, never pivot time |
| `swing_ladder` / LVL5 | Two confirmed highs and two lows | HH/HL or LH/LL comparisons; mixed/unknown explicit | Full trend/pullback still needs causal impulse and defended reference |
| `distance` / LVL3 | Price, frozen zone and original positive ATR | max(lo−p,p−hi,0)/ATRref | Zero inside zone; does not establish readiness |
| `first_obstacle` / LVL3 | Same-instrument pre-known, available, unexpired references | Closest positive directional distance to near zone edge; price units and reference ID | No arbitrary targets. Missing valid opposing reference = NULL. Caller supplies only active, unconsumed references from ledger |
| `touch_episodes` / LVL4 | Closed bar intervals, frozen zone/ATR/buffer | First overlap starts episode; later entirely separated bar retreat ≥0.5 ATR rearms | Consecutive hugging is one visit. No intrabar retreat ordering invented |
| `relative_quote_volume` / VOLU1 | Current Q plus 32 preceding Q | Qt/median(Qprev32); ratio | Prior-only baseline; zero denominator NULL; no accumulation claim |
| `bar_delta` / FLOW1 | Verified matching V,Q,BV,BQ | deltaB=2BV−V; deltaQ=2BQ−Q; deltaQ/Q if Q>0 | Native base and USDT units kept separate. Exchange-reported bar aggregation, never footprint or absorption |
| `anchored_value` / VALUE1,FLOW1 | Complete contiguous whole bars from explicitly predeclared anchor | sumQ/sumV; sum(2BQ−Q) | Exact whole-bar first moment where fields verified; no exact second moment/profile. Current implementation rejects post-hoc or incomplete anchors, including retrospective pivot anchoring |
| `relative_return` / REL1 | Exactly aligned timestamp/timeframe series; h+1 bars | ln(Casset,t/Casset,t−h) − ln(Cbench,t/Cbench,t−h) | Relative log return; not beta or sector neutrality |
| `lag_trained_beta` / REL2 | Aligned n+2 bars; n=32 prior returns | β=cov(asset,benchmark)/var(benchmark); α=mean(asset)−βmean(benchmark); later residual | Training ends before current evaluation. Zero benchmark variance NULL. Sector residual remains unsupported without dated ≥5-peer mapping |

All calculations operate locally only on the bounded selected verification
sample. `selected_measurements` makes insufficient history explicit; malformed
source input is rejected before measurement rather than converted into a signal.
Remote equivalents are exercised through the existing registered Basis formula
probe interface; a passing arithmetic or sampled-source check does not enable
production packs, freeze vendor handles or certify market-wide history.

Unimplemented numerical claims remain visible: FLOW2 confirmed same-anchor
price/CVD divergence, VALUE2 standardized residual dispersion, true price-bin
profile VALUE3, sector REL3, OI native/base/USD decomposition, actual forced-order
history and calibrated shock/market-context interpretation. No candle proxies
are published under those specialist names.

## Frozen references and executable causal trial definitions

`structures.Reference` freezes native identity, timeframe, type, bounds, original
ATR, tick, direction, creation, known-at, first recorded availability, validity
limit and original source IDs. IDs depend on defining facts; later retrieval
cannot create a new level. Reference bounds/ATR/known-at are immutable. Seven-day
swing/FVG validity is a conservative reconstruction limit, not a calibrated
universal watch TTL. Expiry, consumption and invalidation are recorded separately.

For an upper boundary, b=max(2 ticks,0.15 ATRref). Outside means C>hi+b; inside
means C<lo−b; excursion means H>hi+b. Lower boundaries mirror inequalities.
Two independent visits establish trial pressure; a crossing candle cannot create
its own prior pressure. F2 requires pressure → outside close → two later outside
closes. A true reclaim contradicts that straight-breakout attempt.

F4 requires the original boundary → excursion → by-close/later reclaim → a later
opposing attempt with ≥0.25 ATR progress; the supported initiative subclass also
requires TR/ATRref≥1.2 and body/range≥0.5. This does not claim a full MSS unless
swing hierarchy/context independently exists. Same-bar excursion and reclaim are
OHLC geometry; the path, stop executions and tick sequence remain unknown.

F5 requires the same original excursion/reference → reclaim → later opposing
attempt → later rebreak → two further outside closes. No reclaim or no later
opposing attempt means no F5. F2/F4/F5/F6/NULL remain rival hypotheses, sharing
one price-evidence cluster. Support describes current formation facts, never
future profitability or READY admission. A later return after accepted holds
records acceptance failure rather than retaining stale support.

`swing_breaks` uses only previously confirmed, unexpired swings. BOS requires
prior ladder context; an opposing break is CHoCH_CANDIDATE; context-free breaks
remain SWING_BREAK_UNCLASSIFIED. `formation_candidates` implements partial F1
confirmed-impulse/pullback geometry, F3 known quiet baseline then displacement,
and F6 price-only primitives. Defended response, rotation, room/economics and
production remote qualification remain incomplete and are labeled accordingly.

`gap_lifecycle` births the raw 3-bar non-overlap gap at third close, tracks later
bar-overlap mitigation, requires two buffered distal closes for accepted breach,
then a subsequent opposite-side retest for an iFVG candidate. Reacceptance across
the opposite edge invalidates that inverse. Meaningful displacement/minimum-width
subclass is separate from raw geometry. No absent-trade or institutional-intent
claim follows. Full penetration history from coarse bars remains a bar proxy.

## Metadata ledger and method coverage

`ResearchLedger` uses SQLite transactions, foreign keys and indexed append-only
reference/event/hypothesis/lifecycle records. It stores no candle arrays. Duplicate
writes are idempotent; changed bounds, source IDs, known-at or event payloads fail.
Later retrieval preserves first recorded availability. Cross-reference events,
unknown supporting IDs, backwards event order and backdated lifecycle records
fail atomically. Terminal references remain in audit history and disappear from
active queries only at the actual terminal time. File-backed ledgers are confined
to ignored `work/`; runtime databases are never committed.

The single `discovery_specs.json` registry retains the exact 31 blueprint method
names/roles/definitions/caveats. Every method now additionally supplies necessary
evidence, dependencies, sequence, interpretation, traps, rivals, invalidation,
provider requirements and honest implementation/fidelity status. Keepssy remains
DEFINITION_PENDING; Silver Bullet lacks a qualified primary-source window. True
profile, nodes, footprint, absorption, exhaustion, OI, forced orders and news
remain blocked by their required sources. Current bookTicker is only top-of-book;
premiumIndex is current mark/predicted funding context with unknown actual period.
