# Setup research v1: four trading mechanisms

These are frozen, unqualified research rules. The executable definitions are
`setup_features.py`, `SetupPolicyV1.py` and `protocol.json`. Completed15m bars
confirm entries, completed1h bars interpret the market, completed4h bars supply
broad directional bias, and complete prior UTC days/8h sessions supply external
levels. A pivot is available only after its two right-side bars close. A source
gap invalidates active setups. Genuine executed flow remains UNKNOWN.

## A: defended VWAP/structural continuation

The hypothesis is resumption after an orderly correction of a prior impulse.
Require directional confirmed1h structure, hourly ADX>=20 and aligned completed4h
EMA20-minus-EMA50 bias. Indicators support the structural condition; they cannot
create the setup. Identify the previous completed15m session VWAP (UTC midnight,
HLC3 weighted by base volume, at least8 session bars) or a confirmed1h protected
swing. The previous close must be on the trend side. A pullback extreme must
touch within0.5ATR, close no worse than0.25ATR through the zone, and follow an
impulse of at least1ATR measured against the prior six-bar extreme.

Freeze that location and protected pullback extreme. Within four later bars,
require a directional candle closing through the preceding bar's high/low,
relative volume>=1 and a close back beyond the zone. Refuse entries farther
than2.5ATR from it, or when hourly structure/4h alignment no longer supports it.
Stop beyond the protected extreme plus0.2ATR. Use the nearest favorable confirmed
local/hourly swing or prior day/session extreme. Refuse a poor first objective;
never bypass it for an attractive distant3R. Two closes at least0.15 signalATR
adverse to the frozen zone plus opposing local structure invalidate the thesis.
Preferred holding limit8h; the global limit remains15h. A VWAP session/side gets
one attempt, avoiding repeated trades on small recrosses.

## B: genuine profile range rotation

The hypothesis is inward rotation after rejection of an excursion from accepted
value. The completed hourly context must be balanced: ADX<25 and prior20-hour
range width<=8 hourlyATR. Inputs must contain executed prices and base amounts,
unique IDs, event/receipt timestamps, exact pair/venue, a bounded complete
reference-session coverage receipt and its hash. The source window ends before
the setup. `setup_profile.verified_profile` reuses the existing contiguous-bin
profile implementation; OHLCV proxies cannot satisfy this contract.

Freeze VAL/VAH/POC before an edge excursion. Require at least0.1ATR outside an
edge, close reacceptance and a later directional/inward completed close within
four bars. Stop beyond the rejection extreme plus0.2ATR. Choose the nearest
credible inward obstacle among verified POC/opposite edge, frozen session VWAP,
range midpoint and confirmed structural/day/session barriers. Two completed
adverse closes outside the frozen boundary invalidate rotation. Hold<=6h.
Do not fade accepted breakouts, enter near the middle, infer genuine delta from
candle color, or claim that printed volume establishes resting liquidity.

Missing complete historical tape => UNKNOWN / NO_TRADE / economic NOT TESTED.
A latest1000-print public sample validates real price/size input handling; its
partial coverage cannot establish a complete historical reference profile.
Synthetic complete-profile fixtures test decision mechanics only.

## C: external sweep/reclaim reversal

The hypothesis is reversal after a failed external-boundary excursion. References
are complete prior day/8h session extremes or confirmed hourly swings known
before the excursion. Require the previous close inside, an excursion0.1..1ATR
outside, and a completed reclaim. Freeze the sweep extreme and the opposing
local swing that was already known before the sweep. On a later bar within four
bars, require a directional close plus either a break of that frozen swing or
>=0.8ATR displacement with relative volume>=1.2. A wick alone cannot enter.

Stop beyond the registered sweep/persisting extreme plus0.2ATR. Opposing swings,
frozen VWAP, an established range midpoint and prior session/day boundaries are
objective candidates; take the nearest favorable obstacle. Two adverse closes
beyond the failed boundary invalidate reversal. Hold<=4h. A reversal is allowed
against a broad trend only through this independently qualified mechanism.
No hidden-stop, liquidation or institutional-intent claim is inferred. The FVG
retest variant is not enabled or economically tested in v1.

## D: breakout, acceptance and retest

The hypothesis is continuation after balanced trade becomes accepted beyond its
boundary. Require the same completed hourly balance definition as B. Freeze its
prior20-hour high/low when a completed15m candle breaks it by>=0.1ATR with relative
volume>=1.2. The preceding close must be inside. Within eight later bars require
at least two consecutive completed closes outside, a retest within0.35ATR, a
directional completed candle and relative volume>=1. Refuse extension>2.5ATR.

The stop lies beyond the protected breakout/retest extreme plus0.2ATR. A return
more than0.5ATR into the former range invalidates the developing setup; two
adverse completed closes beyond the frozen boundary invalidate an open thesis.
Use the nearest confirmed structural/day/session objective. No projected range
extension can displace an intervening obstacle. Hold<=8h. A failed breakout
cannot be relabeled as continuation; reversal requires its own new sequence.

## Shared admission and management

Logical stops must be0.3..2.5%; after-cost RR must be>=1.25 using a38bp roundtrip
allowance. That allowance sizes/gates risk and is never charged again as an
actual fee. Actual native fees/funding and separate slippage stresses are
reported independently. Entry is a five-minute, price-window-bounded limit;
no repricing/chasing. Current survivor-universe eligibility uses complete prior
daily/7day quote-volume estimates>=10M and10days of warmup. Historical membership,
spread and contract-spec changes remain unknown. Stage-specific top3 shortlists
use distance to defended zones/external levels/consolidation boundaries and
participation; old-ranking and equal-slot deterministic nulls are controls.

Simultaneous competing confirmed playbooks on one pair/time abstain. Native
Freqtrade enforces portfolio capacity, legal lots, risk, margin, cooldown and
fills. Research uses1000USDT,1x, two positions and25USDT notional ceiling. Constant
risk targets0.25USDT with that same ceiling. No active leverage is increased.

Full exit at the first objective is the control. The independent management
challenger uses exactly the same admitted initial plans: one-third at the first
objective, then the registered second objective when present. Lot/minimum
constraints may prohibit the partial. A stop can advance only after a partial
and a new postfill confirmed swing itself supports a stop beyond fee/friction/
funding-adjusted breakeven. No automatic1R breakeven or generic ATR trail.
Stops never widen, including after-fill/restart refreshes. The first-fill clock
never resets;15h is a hard cap even if a malformed plan requests longer.

No live, testnet or persistent paper activation is possible through this policy.
OpenBot receives evidence copies only; narrative confidence cannot alter gates.
