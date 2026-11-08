# 05 — Failed breakout / sweep reversal versus trend continuation

## Why this module matters

The Lab's latest fixed policy had 39 reversal fills and a negative modeled net contribution. A prior OpenBot-style contradiction study found one XRP long 'sweep' that would have been better rejected because the reclaim was marginal in a fresh bearish impulse—but that single helped case was not statistical evidence. Both false rejections and false approvals must be counted.

## Required sequence

1. A significant boundary existed **before** the excursion: prior 20-bar extreme, prior-day extreme, confirmed swing or clear range boundary. Display/cite it.
2. Price genuinely breaches the boundary, with enough extent to matter versus ATR/precision, but not an arbitrary new post-hoc threshold.
3. Price re-enters the range or rejects the breakout under the **frozen recipe's exact candle-close/wick rule**.
4. The higher timeframe does not show a fresh confirmed directional expansion that invalidates a countertrend fade. A lower low in a fresh bear impulse is not magically a liquidity reversal.
5. Available target room toward range midpoint/VWAP/known opposing level is sufficient after execution costs; do not use distant fixed 3R when nearer resistance blocks feasibility unless the declared policy explicitly treats obstacles otherwise.
6. Stop logically beyond sweep invalidation, time cap (historical 4h reversal) and realistic limit fill constraints.

## Analysis templates

**Valid-looking, needs test:** Upper boundary known before T; wick beyond; completed close back under; decreasing acceptance above; opposing structural level nearby; cost room and after-cost RR not yet verified. `WATCH` until numeric gates pass.

**Invalid:** Prior boundary drawn only after T; high-volume upside breakout holds above boundary; tiny return just below immediately previous candle high in higher-timeframe bull impulse. This is not enough to call 'failed breakout'.

**Ambiguous:** A reclaim visible on live 15m bar but no completed close; use `UNQUALIFIED`, not a forced call.

## Opposite-scenario requirement

Always state what would make **continuation** more likely than **reversal** (e.g. sustained acceptance beyond boundary, displacement aligned with 1H, no genuine re-entry), and what would invalidate reversal. Do not identify winners retrospectively by selecting favorable thresholds from the outcome panel.
