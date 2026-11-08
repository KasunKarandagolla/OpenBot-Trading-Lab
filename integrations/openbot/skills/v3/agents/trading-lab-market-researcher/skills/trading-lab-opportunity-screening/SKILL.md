---
name: trading-lab-opportunity-screening
description: Reproducible cheap-to-expensive crypto-futures opportunity screening for OpenBot Trading Lab. Use to turn a broad liquid-contract universe into a ranked shortlist with explicit eligibility, regime, setup and cost rejection reasons.
metadata:
  version: 3.0.0-research
---

# Owner and active v3 loading

Owner: `trading-lab-market-researcher`; this is a separate owner-owned research copy. Read [current-contract](references/current-contract.md) before using the restored procedures below, then [playbook reasoning](references/playbook-routing-v3.md) for discovery, competing hypotheses, geometry and challenge. Operational corrections in these references govern old dated examples; no historical result becomes Binance-current evidence. Native installation/injection is NOT_VERIFIED.


# Opportunity screening

Outcome: a reason-coded shortlist of interesting and developing setups as well as completed triggers. Never discard a developing hypothesis merely because the frozen control has no current trigger.

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

- Venue: Binance public USD-M; market type linear USDT-settled perpetual only. The prior Gate-only eligibility fields are historical.
- Current Binance status=TRADING, contractType=PERPETUAL, quoteAsset=marginAsset=USDT; exclude unsupported/noncrypto/premarket instruments. Historical listing status and age are UNKNOWN unless sourced. The old Gate empty-contract_type rule does not apply.
- Current scanner: 24h quote volume at least 5,000,000 USDT (old Gate 10M threshold is historical).
- Current scanner: observed spread at most 10 bps (old Gate 20bps threshold is historical). Missing historical spread stays UNKNOWN; archive research eligibility does not imply execution clearance.
- Ticker age at most 180 seconds; missing venue timestamp means `UNKNOWN`, not fresh.
- Missing volume or spread means EXCLUDE from CURRENT execution clearance; never assume a favourable value. Historical archive WATCH may retain UNKNOWN spread with research eligibility only, never execution qualification.
- Current context budget 24–40 symbols, deep shortlist 3–6. The historical 60/20/30-day limits do not replace current contracts.
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
- A TRIGGER_CANDIDATE exists only when the trigger bar is complete and all inputs are known by as_of. A DEVELOPING/WATCH setup can exist earlier with frozen location and conditions.
- SMC pivots are known only after the confirming right-hand bar; see the market-structure skill.
- If the recipe says `NO_SETUP`, do not invent a trigger. A distinct, named developing challenger may remain WATCH with pre-known levels, explicit conditions and expiry; preserve both records.

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
