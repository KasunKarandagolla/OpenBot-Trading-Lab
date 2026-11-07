# 04 — VWAP/trend continuation: visual confirmation and disciplined contradiction

**Frozen code wins.** For any actual study name the exact PolicyFixedV3/continuation version and retrieve its native eligibility results. The descriptions below explain *how to evaluate* the existing strategy; do not silently replace thresholds.

## Core hypothesis

When a sufficiently developed trend has real participation, a controlled pullback toward a meaningful dynamic reference (session VWAP / EMA) may lead to renewed continuation. A chart's attractiveness alone does not establish a positive after-cost edge.

## Visual investigation

- Confirm higher timeframe EMA direction and structural swings, BTC context when relevant, trend strength/participation from completed data. If 1H remains bearish and 15m is bouncing, explore **short** continuation near rejection/obstacle as well as the less mature reversal idea.
- Show an actual sequence: trend leg → controlled pullback → location near VWAP/EMA → stabilization/reclaim → breakout/rejection confirmation. State what part is seen and what part is still pending.
- Examine volume behavior in advance of the trigger: directional expansion versus corrective retreat, and avoid labeling raw volume as buy/sell delta.
- Check if price is extended so far from VWAP/EMA that a 'sniper entry' would instead chase an already advanced move.
- Identify nearest opposing structural level, prior-day high/low, confirmed swing, range boundary, profile node (if sourced) before asserting feasible target.
- Examine whether the target room, holding cap (historical 8h continuation), stop distance and entry expiry plausibly fit the motion; exact economics belong to structured data.

## Candidate output

`trend_direction`, `pullback_type`, `vwap_relationship`, `trigger_observed_or_pending`, `higher_tf_contradiction`, `nearest_obstacle`, `invalidating_event`, `missing_confirmations`, `recipe_version`, `evidence_ids`.

## Counterexample

A fast green candle crosses VWAP while 1H still shows strong bearish displacement. Without a controlled pullback and completed confirmation, 'VWAP reclaim' may be a countertrend bounce, not long continuation. Consider conditional short continuation only if its actual trigger later qualifies. No blind rejection and no blind long.

## Management warnings

Do not automatically move stops to breakeven or take one-third at 1R as a default. Previous matched management challenger underperformed in the Lab; a different plan must be frozen and tested separately. Present continuation-thesis invalidation as a **research signal**, distinct from emergency stop safety.
