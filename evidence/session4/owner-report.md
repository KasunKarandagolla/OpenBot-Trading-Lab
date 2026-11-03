# Session 4 owner report

**A bounded native paper-capable policy and a substantially broader economic experiment are delivered. No edge is established. The complete fresh-data-to-observed-order vertical slice remains blocked by Gate public-source 503s.**

**WHAT NOW RUNS**

`PaperPolicyV4`, version `structure-execution-v4.0.0`, runs in official pinned
Freqtrade 2026.10 / CCXT 4.5.90 with `dry_run=true`, isolated USDT futures, no
credentials, a 1,000 USDT simulated wallet, 25 USDT maximum initial notional,
two positions and default 1x leverage. Separate reviewed configurations support
native limit and market entries/exits; stops use native simulated market exits.
Freqtrade owns order creation, cancellation, inventory, target/stop/time exits,
SQLite persistence and simulated accounting. No second execution engine or
dashboard was built. Native models remain compatible with FreqUI; authenticated
API operation is a Session 5 task.

The live strategy computes causal market eligibility and lane-specific ranks
from native public candles, then forms VWAP/structure plans. Entry/risk callbacks
fail closed on missing sources, expired plans, stale contract evidence, unknown
account state or invalid geometry. Existing stop/target/time protection remains
independent of new-entry admission. A process or public-price outage cannot
guarantee a stop fill, and a stopped process cannot manage a position.

The native initial stop is installed before custom-stop callbacks. Its ROI ratio
is `-0.025 * leverage`, preserving at most a 2.5% initial price distance at
1x/10x/20x, subject to native inward tick rounding. The reviewed operational
configuration permits **1x only**. Logical stops tighten this bound; the frozen
V3 strategy and its historical `-0.99` results are preserved. Missing geometry
retains the installed bound and requests a native exit. Paper-account consumed
loss events and streak checkpoints commit atomically; injected SQLite failures
roll back both. Backward clocks and missed exposed midnight recovery fail closed.

Real native workers reached RUNNING in limit mode (about 242 seconds), market
mode (about 182 seconds), and a flat-account restart (about 77 seconds). They
produced heartbeats and source/account monitors, then stopped. **All observed
order/trade counts were zero.** Gate public requests returned 503s; no fresh
price qualification or forward fill is claimed. Actual native dry-order methods
separately demonstrated long/short market fills, limit open/cross/fill/cancel and
SQL order recovery using controlled books. Partial fill/remaining-quantity and
funding paths retain the native lifecycle fixtures from the frozen control.

**WHAT IMPROVED**

The historical experiment sampled twenty current active **crypto** Gate swaps,
including all five parent markets. Gate stocks, metals and commodity contracts
are now explicitly excluded by public `contract_type`, with the initial sampling
attempt retained. Fourteen markets had complete 15m, 1h, mark and funding inputs.
Six were excluded before return evaluation because public acquisition failed;
they remain in the coverage ledger. Eligibility requires seven prior complete
UTC days of liquidity, at least 10m USDT estimated daily quote volume and a
240-hour warmup. Evaluation covers August 5–November 3 exclusive: ninety calendar
days, with the last candle opening November 2 at 23:45 UTC. This is a conditional
current-survivor cohort, **not a reconstructed complete historical universe**.

The SMC challenger applies confirmed hourly direction or a causal FVG retest to
continuation, and a meaningful swept boundary followed by displacement or a
confirmed shift/reacceptance to reversal. Swept levels/extremes remain frozen
through the three-bar wait. FVG zones become usable after formation, expire after
eight bars and are not retrospective pivots. Confirmed external/internal levels,
equal liquidity, range location, displacement and profile fidelity are retained
in the opportunity evidence. These definitions do not assert institutional intent.
All fourteen feature prefixes match recomputation without their future suffix.

All portfolios use the same eligible data, native risk/capacity/cooldown, 0.075%
fees per side and actual source funding. Figures below are independently
reconciled USDT, rounded to six decimals. Alternatives are never additive.

| Complete chronological portfolio | Fills | Native net | Additional 10 bp/side |
| --- | ---: | ---: | ---: |
| V3-rule safe reference, broader universe | 82 | +0.923141 | -2.780477 |
| **SMC/structure challenger** | **58** | **+0.943062** | **-1.698115** |
| Closed-hour longer-horizon hypothesis | 236 | -12.528692 | -23.159552 |
| Simple prior-day-liquidity ranking control | 46 | -0.534360 | -2.683244 |
| Reference, constant modeled risk 0.25 USDT | 67 | -0.843846 | -3.138043 |
| Structure, constant modeled risk 0.25 USDT | 49 | -0.788630 | -2.420281 |
| Reference, 1 bp entry trade-through | 78 | +0.663775 | -2.875798 |
| Structure, 1 bp entry trade-through | 56 | +0.960618 | -1.602494 |
| Structure, immediate-open-only limits | 39 | +1.607590 | -0.187742 |
| Structure, native market-candle scenario | 59 | +1.636730 | -1.049003 |

The structure change adds only **0.019921 USDT** versus reference; paired 7-day
block 95% interval **[-3.609562,+3.399682]**. It reduces reversals from 28 fills to
six, while retaining both families. Continuation contributes +0.808799 native
USDT and reversal +0.134263 to the mixed structure portfolio; these are not
standalone portfolio returns. The top three winners supply **43.66%** of positive
P&L. Profit factor is 1.0991 and hourly-mark drawdown about 2.821532 USDT, before
additional friction. Smaller losses/turnover do not establish a better edge.

Eight fixed-seed nulls randomize scanner ranks within identical eligible
decision times, recipe/side and continuation-direction strata. Native setups,
geometry, costs, capacity and exits are unchanged. Reference minus mean null is
**+2.425605 USDT**, paired 95% block interval **[-1.608757,+6.707950]**; conditional
upper-tail rank p is **0.2222**. Ranking value is unestablished. This conditional
null tests ranking, not every component of setup alpha or all market movement.

Reports separate pure stop-R, net/stop-R, cost-inclusive risk R, entry-notional
basis points and USDT. The structure totals are +5.794647 pure stop-R,
-3.731340 net/stop-R and -2.532834 cost-inclusive R. Positive fixed-notional USDT
alongside negative summed R exposes sizing/concentration effects; the negative
constant-risk portfolios reinforce this weakness. Native order quantities,
fees and every retained funding event reconcile independently. There are
**1,855 reconciled modeled trade records**, including an 82-trade exact economic
reproduction, across nineteen native result records.

Chronology, win/loss quantiles, zero-realization days, turnover, exposure,
fee/funding attribution, regime/family/side breakdowns, hourly mark MTM and cost
scenarios are in `economic-report.json`. August/September/October/November are
reported separately. These fixed-rule chronological checks use no later-fold
parameter selection; they remain inspected development/market transfer. The
November 17–December 1 reserved period was neither acquired nor inspected.

**WHAT FAILED / LIMITATIONS**

The longer-horizon hypothesis lost money and is not selected. Added friction
turns every highlighted structure execution alternative negative at 10 bp/side.
The apparent SMC gain is economically tiny and uncertain; opportunity coverage
falls and winner concentration rises. There is no economic promotion.

Native coarse candle touches and 1 bp trade-through cannot prove five-minute
attainability or queue priority. The immediate-open-only scenario removes later
candle entry assumptions through the native engine. Diagnostics retain every
planned opportunity and ambiguous stop/target cases; they do not calculate a
second portfolio. Minute-source acquisition and genuine prospective book/tape
capture were blocked by the public outage. Historical spreads, adverse selection,
account-specific rebates and maintenance-tier changes remain unknown. Maker-fee,
market friction and stop-gap figures are labeled scenarios, not observed fills.

Genuine signed executed-trade normalization, delta/CVD, footprint and observed
volume profiles remain usable and tested. The three bounded prospective Gate
capture attempts are UNKNOWN. Historical flow is UNKNOWN; historical profiles
are OHLCV proxies. No Binance trades were blended into Gate decisions and no
historical order-flow profitability improvement is claimed.

Original private source files were unavailable. Of forty manifest/window
comparisons, **25 reacquired overlap slices match the original SHA256 exactly**.
The other fifteen cannot support row-level timestamp/OHLC/volume/mark or
signal-neighborhood differences without the originals. The report gives counts,
boundaries and explicit UNCOMPUTABLE fields, preserving the original manifests
and all new sources. It does not fabricate a complete reconciliation.

Retained engineering attempts include noncrypto sampling, duplicate initializer
staging, source 503s, a missing native output directory, a contaminated research
account replay, a deferred runtime import and a report funding-column mismatch.
Each research attempt now has a fresh risk DB; real paper restart alone reuses
state. The contaminated zero-fill reference is quarantined. A final independent
reference reproduction restores the same 82 entries and economic result.

Validation: **13 current paper tests, 20 flow/profile/intelligence tests and five
confirmed-structure tests pass**. The frozen parent passes all **32** policy
mechanics tests in its exact checkout. Running those 32 on this changed checkout
produces one expected old source-registration refusal; the other 31 pass. That
original refusal is retained, not hidden as a pass. All parent evidence and
frozen strategies/manifests are unchanged; only reviewed guard compatibility
helpers are extended.

**BEST POLICY**

Frozen reference: **PolicyFixedV3 v3.0.0**, parent `c0ec703`, unchanged and still
economically unqualified. New functional paper candidate: **PaperPolicyV4 /
structure-execution-v4.0.0**, exact module/config review in
`research/session4/paper-release.json` and `guard-review.json`. It is a guarded
bounded paper candidate, not a proven superior strategy. No persistent activation
is authorized or installed. Guard review is explicit; credentials, forced entry,
strategy/config/CLI overrides and exposure expansion remain rejected.

**WHAT REMAINS — SESSION 5**

Restore and hash-check the private backup on the owner host; refresh public
contract metadata and establish healthy native public candles/quotes. Complete
the fresh-source → eligible rank → causal plan → risk admission → observed native
paper order → management → reconciled outcome acceptance. Obtain complete minute
execution inputs and prospective Gate book/tape evidence. Improve the edge using
newly registered data; preserve these losing/uncertain results.

Then complete owner-host authenticated FreqUI, service supervision, recovery,
monitoring/alerts and log/storage rotation. Exposed midnight recovery, API roles
and host isolation need operational acceptance. Persistent operation requires the
separate owner approval reserved for that session. OpenBot integration remains
separately owned.

**EVIDENCE / REPRODUCTION / ROLLBACK**

See [the runbook](../../docs/operations/policy-session4.md) for exact commands,
source restoration, bounded modes and rollback. The 372-file owner backup was
actually restored and hash-verified into an empty directory with zero overwrites;
its 45,464,928-byte archive and SHA256 are recorded in `run-001/private-backup.json`.
All disposable paper workers and the session runner have stopped. No PR was merged or auto-merge
enabled. No live, testnet or demo exchange order, credential, forced entry or
24/7 paper service was used.

**SESSION BUDGET:** Four additional sessions complete including this milestone;
**one remains**. Functional and economic qualifications above define the handoff;
the blocked fresh-source/order acceptance must not be described as complete.
