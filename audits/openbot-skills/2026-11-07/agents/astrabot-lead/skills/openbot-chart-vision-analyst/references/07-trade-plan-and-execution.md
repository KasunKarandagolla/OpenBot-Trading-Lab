# 07 — Translate a visual thesis into a *research* trade plan, not an order

## The Lab's non-negotiable chain

Valid market → strategy-eligible context → completed trigger → feasible entry → structurally meaningful invalidation → realistic target and holding period → after-cost admission → independent risk check → native Freqtrade decision. Chart vision can annotate these; it cannot replace exact numeric or economic gates.

## Entry timing

Distinguish signal candle open, close, `decision_available_utc`, request time, chart response time, intended native order time, fill and expiry. A purported 'sniper entry' has no value if the entry would be expired by the time image reasoning returns. The historic Lab limit reference was signal close, 5-minute expiry, with no chase; **do not revive an expired trigger**. If the model is too slow, use it pre-trigger for WATCH context or post-trade analysis.

## Market vs limit

Market-order research: likely immediate but spread/slippage/impact and taker fees; no guaranteed price.
Limit-order research: specified reference, queue uncertainty, adverse selection and opportunity cost of nonfills. Candle range touching limit is not proof of a passive fill. Follow position/order states from native Freqtrade, not imagined screenshot changes. Both must pass minimum size, precision and liquidity checks.

## Stops and invalidation

A **logical stop** sits past the structure that falsifies the thesis (sweep extreme, pullback swing etc.), with declared ATR/volatility buffer. A **protective native stop** remains governed by Freqtrade and may be hit or gap. Never widen/shift an existing live stop because the chart looks attractive. Define condition for thesis exit separately from emergency protection. The model must not scale stop width by 'desired leverage'.

## Targets and holding fit

Identify *nearest known obstacles first*: prior extrema, confirmed swing, midpoint, anchored VWAP, source-verified profile levels. A 3R target may be infeasible within a 4h/8h planned hold even when algebra is attractive. Don't invent precise price levels by visually measuring pixel offsets. Send conditional obstacle **regions** to a numeric validator, freeze exact levels only in deterministic policy context.

## Economic check

Do not claim 'profitable' without fees (maker/taker), spread, slippage, signed funding, fill probability sensitivity and realistic portfolio constraints. Compare conventional pure-stop R, cost-inclusive R and USDT, do not mix them. Visual certainty never substitutes for missing contract specs, liquidation clearance or risk budget.

## Output

`visual_hypothesis`, `native_recipe_version`, `trigger_observed_or_pending`, `entry_reference_numeric_source`, `stop_basis`, `target_obstacles`, `expiry`, `hold_cap`, `execution_concerns`, `risk_review_status`, `simulation_only`. Null unsupported values. Suggested numeric levels are non-binding until independently validated.
