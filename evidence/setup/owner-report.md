# Setup-driven trading research — owner report

**Decision: reject promotion of setup-v1.1. No after-cost edge was demonstrated.**

The final integrated workflow lost **-1.351729USDT on five trades, all losses**.
The retained frozen V4 structure control earned **+3.473272USDT on 45 trades**
on the same separate Gate source cohort. The new architecture works mechanically,
but its opportunity selection and confirmation did not improve financial results.
The narrower V4 profit is development evidence; its constant-risk +10bp/side
portfolio is **−0.089217USDT**. No strategy is approved for trading.

This branch starts from PR10's verified exact HEAD
`542c0d804185ca28c08453711e421de42a793edc`. All **2,844** starting repository files,
including EMA/V3/V4 strategies, production settings and previous evidence, remain
byte-identical. PR10 stays unmerged. The November17–December1 reserved holdout was
neither acquired nor inspected. No persistent paper/live/testnet service, exchange
order, credential, active leverage increase or paid data subscription was enabled.

## What now works

A separate historical-only policy connects the actual decisions:
causal liquidity eligibility → playbook-specific shortlist → registered reference
and setup events → later completed confirmation → nearest-objective/stop admission
→ native legal sizing and capacity → expiring limit fill → thesis-aware exits.
The plan stores source hashes, known-at timestamps, boundary/extreme, observed
confirmation, stop, objectives, cost geometry, expiry, identity and lifecycle.
Native Freqtrade owns orders, fills, protective stops, inventory and funding.
There is no replacement exchange engine or second portfolio backtester.

Continuation waits at a defended VWAP/hourly structure pullback in coherent1h/4h
trend context. Reversal first registers a meaningful external sweep/reclaim and
then waits for a genuine later frozen-level cross or displacement. Breakout first
registers a completed consolidation break and then requires sustained acceptance
and a retest. Genuine profile rotation accepts only validated executed-price/size
profiles and rejects outside acceptance; candle approximations cannot activate it.

These distinctions affect actions. In the corrected scan, **84,672 market/time
checks →72,741 eligible checks →4,080 distinct setup IDs →17 geometry-qualified
confirmations →5 shortlisted admitted plans →5 native fills**. The four breakout
fills lost0.995202USDT; the one reversal lost0.356527USDT. Strict continuation had
**zero approved/fill trades**. Its synthetic positive/negative cases work, but its
selected historical economics are untested beyond the legitimate NO_TRADE result.
The simpler-trigger comparator contains one continuation fill; that does not
validate the stricter playbook. The shortlist can and did remove otherwise
qualified opportunities. A rising/falling market alone cannot enter.

Nearest-obstacle economics rejected536 confirmation attempts; another21 had
objectives beyond the inherited6ATR bound,120 lacked a credible objective and127
had unacceptable logical stops. The scanner records expired and invalidated
setups rather than silently converting them into new indicator trades. Native
risk/cooldown/lot/capacity/nonfill effects remain distinct from signal rejection.

## Financial comparison

All full-period portfolios use September1–November3,2026 UTC, end exclusive,
Gate linear perpetuals, the same14 current-survivor markets,1000USDT,1x, max2
positions and a25USDT notional ceiling. Native fee:7.5bp per side, plus source
funding. The38bp allowance is admission/risk geometry and is never charged again.
+10bp means an additional hypothetical per-side execution friction. Returns from
alternative portfolios are never added.

| Portfolio | Fills | Native net USDT | Additional10bp/side net |
|---|---:|---:|---:|
| Frozen V4 structure | 45 | +3.473272 | +1.423486 |
| Frozen V4 reference | 55 | +4.160790 | +1.661813 |
| Initial setup v1 | 11 | -2.393378 | -2.909975 |
| Corrected setup v1.1 | 5 | -1.351729 | -1.577966 |
| Same setups, old ranking | 5 | -0.651486 | -0.895595 |
| Simpler armed-location trigger | 52 | +0.474844 | -1.861867 |
| Same entries, fixed3R | 5 | -1.351729 | -1.577966 |
| Same entries, management challenger | 5 | -1.351729 | -1.577966 |
| V4 structure constant risk | 38 | +1.137048 | -0.089217 |
| Setup constant risk | 4 | -0.632065 | -0.769453 |

The final five trades lost **-1.187000USDT before fees**, paid
0.169678 in fees and received0.004949 net modeled funding.
Expectancy is-0.270346USDT/trade; profit factor0, win rate0%, net
stop-R-4.854, native drawdown1.351729USDT,
average hold168min and turnover226.237USDT.
Additional5/10/20bp per side produce−1.464847/−1.577966/−1.804203USDT.
September lost0.795829 and October lost0.555900. Every new primary trade lost;
there is no top-winner dependence concealing a positive primary result.

Selection was worse than old ranking by0.700243USDT and worse than the mean of
three seeded equal-slot nulls. Those nulls have only 0.25 p-value resolution;
they are diagnostics, not a well-powered selection test. Different policies
change available setups, turnover and subsequent capacity. Strict confirmation
was worse than the simpler armed-location trigger; that comparator's small
+0.474844USDT disappears under additional5bp/side. It is not promoted.

Objective-aware versus fixed3R targets and the management challenger produced
**the same five entries and the same native result**. No primary trade reached
its first objective before stop/thesis/time exit; therefore neither target choice
nor partial management supplied measured uplift. Legal partial fills/exits,
remaining quantities, restart deduplication and structure-supported monotone
stop advancement pass native SQLite/order fixtures. Actual historical objective
partials numbered zero; this is not forward/real exchange partial-fill evidence.

On17 geometry-qualified confirmed opportunities, conservative candle first-passage
found3 target-first,9 stop-first and5 neither outcomes for both target variants.
Selection missed3 target-first paths and avoided5 stop-first paths. These are
same-entry barrier diagnostics, separate from complete portfolios; candle paths
cannot establish queue priority or a realizable cash portfolio. Weekly-block
uncertainty and full market/playbook/exit contributions are in economic-report.json.
The primary total's descriptive95% circular seven-day block interval is
[-2.446,-0.422]USDT.
Small, development-selected samples and cross-market dependence limit inference.

## What review corrected and what remains unqualified

The initial v1 matrix is fully retained:21 native portfolios and337 reconciled
trade records at commit5f582a0 / run-001. It lost2.393378USDT on11 primary trades.
Professional review identified the omitted parent6ATR horizon bound; v1.1 restores
it and reruns the finite comparison. This is a disclosed **post-result engineering
correction**, not an independent performance improvement. Pre-outcome review
also corrected already-broken swing confirmations and repeated anchors after gaps.

The final run contains26 native result records
(25 alternatives plus1 exact replay)
and435 reconciled trade records. Across both retained
runs that is47 result records and
772 trade records;
overlapping portfolios/replays are not independent market observations. Every
order quantity, fee, signed source funding event and net PnL reconciles. The final
replay matches all five complete native trade objects exactly.

A real LTC eight-hour executed-trade sample succeeded:14,190 prints in33 bounded
public requests, with volume reconciled against all 32 source 15m candles. The
existing contiguous-bin profile code and input contract return READY. Narrow
historical BTC minute probes also returned actual prints. **Full63-day/14-market
complete reference profiles were not acquired/validated**, so the profile economic
comparison remains NOT TESTED. The sample uses its actual acquisition receipt;
no historical observation timestamp or profile confirmation was invented.
A complete verified reference-tape dataset is the exact remaining dependency.

Real1m candles cover100,800 bars across 14 markets for Oct29–Nov3. The corrected
policy has zero trades in that short detail window; V4 reference has three and
loses0.629080USDT. This does not validate full-period new-policy fill timing.
Trade-through, deterministic25% nonfill and half-allocation alternatives are
complete native scenarios, not observed queue probabilities or partial orders.

Historical exchange membership, delistings, spread distributions, fee tiers and
contract-spec changes remain unknown. Source-reported funding clocks are kept;
valuation uses the preceding source hourly mark OPEN, not an exact settlement
mark or proven venue boundary priority. Intrabar gap tails and exact stop/target
ordering remain unknown; first-passage diagnostics use stop-first ambiguity.
Hypothetical10/20x arithmetic is recorded separately with unchanged structural
stops and monetary-risk caps. Actual execution stays1x. Legacy hourly V4 variants
with24h holding remain untouched and are **not** claimed compliant with the new15h
cap; they were not used as the new policy.

## Tests, operation and next action

**23 new tests pass**, including all 14 real-source prefix checks, genuine profile
sample validation, ordered valid/false setups, conflict abstention, obstacle and
risk vetoes, mode refusal,15h cap and native partial/restart/stop behavior.
Existing structure5/5 and intelligence20/20 pass. Legacy policy31/32 pass; its
one frozen-source registration error reproduces on untouched starting commit
542c0d8. It is recorded, not hidden or repaired by changing frozen evidence.

The three distinct self-reviews are recorded in self-review.md. Playbook specs,
four read-only research skills, schema-validated OpenBot exports, casebook,
source/strategy seals, native archives/private backup and simple replay/rollback
commands are delivered. No OpenBot runtime or trading-admin bridge was installed;
owner-host isolation and persistent operation remain untested.

**Recommended next action: reject setup-v1.1 promotion and retain V4 solely as a
research control.** Selection and confirmation need a separately registered
hypothesis with independent after-cost evidence before any operational promotion.

See [complete portfolios](run-002/portfolio-table.md), [economic report](run-002/economic-report.json),
[entry-time decision casebook](run-002/casebook.json), [self-review](self-review.md),
[playbooks](../../research/setup/playbooks.md) and [restore/replay/rollback](../../docs/operations/setup-research.md).

Private backup: 619 hash-verified files, 88,360,503 bytes; actual restore and fresh-directory hydration both completed with zero overwrites. SHA256 `abde1f5b151b4bec77eb166e285abc57b0538dd1a3fe4467f2a324df6d6beb7a`. All temporary containers are stopped.
