---
name: trading-lab-opportunity-screening
description: Reproducible cheap-to-expensive crypto-futures opportunity screening for OpenBot Trading Lab. Use to turn a broad liquid-contract universe into a ranked shortlist with explicit eligibility, regime, setup and cost rejection reasons.
---

# Opportunity screening

Outcome: a deterministic shortlist that spends agent attention only on symbols a frozen strategy could actually trade, with every rejection explained.

## Funnel

| Stage | Question | Cheap evidence | Output |
|---|---|---|---|
| A. Eligibility | Is this a supported, live, liquid linear USDT perpetual? | Exchange metadata, 24h ticker, spread | Eligible / rejected with code |
| B. Context | Is there enough closed history and a usable regime? | 15m and 1h closed candles, ATR, EMA, ADX | Regime label or `UNKNOWN` |
| C. Setup | Does a frozen recipe trigger at this as-of? | Strategy features and trigger predicate | `SETUP` / `NO_SETUP` |
| D. Economics | Does the geometry survive costs and risk? | Entry, stop, target, fees, funding, spread | `QUALIFIED` / `COST_OR_STOP_GEOMETRY` |
| E. Portfolio | Is capacity and correlation acceptable? | Open positions, cluster exposure, daily risk | `ADMIT_FOR_REVIEW` / `PORTFOLIO_BLOCK` |

Do not skip from A to D. A liquid coin with no setup is not an opportunity.

## Stage A rules (scanner-v1)

- Venue: Gate; market type linear USDT-settled perpetual only.
- `contract_type` must be explicitly empty; exclude TradFi categories, premarket, delisting, unknown age and non-crypto.
- 24h quote volume at least 10,000,000 USDT.
- Observed spread at most 0.20% (`max_spread_ratio: 0.002`).
- Ticker age at most 180 seconds; missing venue timestamp means `UNKNOWN`, not fresh.
- Missing volume or spread means `EXCLUDE`; never assume a favourable value.
- Native candidate cap 60; exporter cap 20; minimum contract age 30 days.
- Record the scanner version, snapshot ID and as-of. Tomorrow's pair list must not rewrite yesterday's backtest shortlist.

## Stage B regime labels

Use closed 1h candles only. Defaults below come from the frozen research cards; changing a threshold creates a new version.

- `TREND_UP`: EMA20 > EMA50 and ADX14 >= 20, with higher closes.
- `TREND_DOWN`: EMA20 < EMA50 and ADX14 >= 20, with lower closes.
- `RANGE`: ADX14 <= 30 without a sustained EMA separation; failed breakouts are more plausible here.
- `TRANSITION`: EMA separation and ADX disagree, or the last structure event is unconfirmed.
- `UNKNOWN`: insufficient warm-up, stale data, missing closed bars or a timestamp gap.

Regime is context, not a signal. A reversal recipe in a strong trend is a lower-quality candidate even if the candlestick looks clean.

## Stage C setup

- Apply the exact frozen recipe. Do not blend recipes or add discretionary indicators.
- A setup exists only when the trigger bar is complete and all required inputs are known by `as_of_utc`.
- SMC pivots are known only after the confirming right-hand bar; see the market-structure skill.
- If the recipe says `NO_SETUP`, stop. Do not manufacture a reason to keep the symbol.

## Stage D economics

Compute net reward/risk, not gross:

```text
cost_fraction = (fee_in + fee_out + slippage_in + slippage_out + funding_allowance) / 10000
net_risk_per_unit = abs(entry - stop) + entry * cost_fraction
net_reward_per_unit = abs(target - entry) - entry * cost_fraction
net_RR = net_reward_per_unit / net_risk_per_unit
```

Reject when `net_RR < recipe_minimum`. The frozen cards use a minimum of 1.25 for the VWAP and sweep recipes and a 2R target request; treat those as versioned examples, not universal law.

## Stage E portfolio

- One position per symbol unless the policy explicitly allows more.
- Cap concurrent positions and aggregate intended loss.
- Treat BTC, ETH and large-cap alts as correlated when they share the same impulse; do not double the same beta and call it diversification.
- Existing pending entries consume capacity even before a fill.
- If capacity or correlation is unknown, return `WATCH`, not `ADMIT`.

## Ranking

Sort by, in order:

1. Eligibility (`PASS` before `UNKNOWN`; rejections last).
2. Recipe fit (exact trigger before near-miss; near-miss is `WATCH`).
3. Net reward/risk after costs.
4. Freshness and source quality.
5. Symbol, for deterministic tie-break.

Do not rank by 24h percentage gain, social attention or an LLM confidence score.

## Worked examples

- A contract with 12M USDT volume, 0.15% observed spread and a 40-second-old venue ticker passes A. If its 1h ADX is 34 and EMA20 is far above EMA50, a failed-breakout reversal is `WATCH` at best, not a qualified short.
- A contract with 25M volume but a null venue timestamp is `EXCLUDE / TICKER_TIMESTAMP_UNKNOWN`. It does not become eligible because the local file was written recently.
- The recorded 2026-10-31 current report rejected BTC, DOGE and the rest of its shortlist with `TICKER_TIMESTAMP_UNKNOWN`. That is a valid zero-opportunity outcome.
- A liquid symbol with a clean sweep but a stop so wide that net reward/risk is 0.9 is rejected with `COST_OR_STOP_GEOMETRY`; it is not promoted because the pattern "looks strong".

## Output table

| Symbol | A | B regime | C setup | D net RR | E portfolio | Decision | Reason codes |
|---|---|---|---|---|---|---|---|

Every row needs a source ID and as-of. A zero-row result is a successful screen, not a failure.

## Verification

- [ ] Same snapshot and rules produce the same shortlist and order.
- [ ] Missing spread/volume/timestamp yields `UNKNOWN` or `EXCLUDE`.
- [ ] No spot, TradFi, premarket or unknown-age contract survives.
- [ ] No historical shortlist is reconstructed from today's universe.
- [ ] Rejections are retained with codes.
- [ ] No trade recommendation is produced by the screen alone.
