---
name: trading-lab-market-regime-structure
description: Regime, SMC/ICT, VWAP and price-structure interpretation for OpenBot Trading Lab, including the approved strongest-contradiction checkpoint. Use to explain why a setup is or is not suitable, and to distinguish a failed breakout from continuation in an opposing impulse.
metadata:
  version: 3.0.0-research
---

# Owner and active v3 loading

Owner: `astrabot-lead`; this is a separate owner-owned research copy. Read [current-contract](references/current-contract.md) before using the restored procedures below, then [playbook reasoning](references/playbook-routing-v3.md) for discovery, competing hypotheses, geometry and challenge. Operational corrections in these references govern old dated examples; no historical result becomes Binance-current evidence. Native installation/injection is NOT_VERIFIED.


# Regime and price structure

Outcome: a causal, timestamped explanation of the setup, plus the strongest evidence against it and whether that evidence invalidates the trade or only requires caution.

## Allowed inputs

- Closed 15m candles and closed 1h context, with an explicit venue timestamp and `features_known_at_utc`.
- Frozen indicators from the recipe: EMA20/50, ADX14, ATR14, relative volume, session VWAP.
- Confirmed structure events with their `known_at` time.
- Qualified order flow or profile fields only with their fidelity label; otherwise `UNAVAILABLE`.

Do not recompute a feature from a screenshot. Do not use an indicator value whose warm-up or timestamp is unknown.

## Regime card

| Label | Evidence | Preferred research | Avoid |
|---|---|---|---|
| `TREND_UP` | EMA20 > EMA50, ADX14 >= 20, higher closes | Pullback continuation, VWAP reclaim | Blind mean-reversion shorts |
| `TREND_DOWN` | EMA20 < EMA50, ADX14 >= 20, lower closes | Rally-failure continuation, VWAP rejection | Blind dip buying |
| `RANGE` | ADX14 <= 30, EMA flat, boundaries respected | Failed-breakout reversal | Chasing mid-range breakouts |
| `TRANSITION` | Signals disagree; last BOS/CHoCH unconfirmed | `WATCH` | High-conviction entries |
| `UNKNOWN` | Missing/stale data, short warm-up, gapped bars | `NO_TRADE` until repaired | Any inferred regime |

These thresholds are the frozen research defaults, not universal market laws. A new threshold is a new strategy version.

## Causal structure rules

- **Swing high/low:** current chart structure uses strict unique 2L/2R; pivot i is known only at i+2 close. Legacy three-bar pivots remain historical frozen-recipe features and must carry their own version.
- **BOS:** a close beyond a confirmed swing, not a wick. **CHoCH:** the first close through the prior opposing structure after a sustained leg.
- **FVG:** known at the close of the confirming bar; invalidation is a separate event time.
- **Order block:** a zone is not "known" because it is drawn later. Record detection time and invalidation time.
- **Equal highs/lows:** require two distinct confirmed pivots within the frozen tolerance (the research code uses 0.1 ATR); one pivot is not liquidity.
- **No repainting:** append-future-candles must not change a historical label. If the library repaints, reject it for active use.

SMC and ICT describe structure and known levels. They do not prove institutional intent, stop hunting or hidden orders.

## VWAP rules

- Anchor at 00:00 UTC for a UTC daily VWAP; state the anchor in the output.
- Current chart VWAP = cumulative published quote_volume / cumulative base_volume. Historical typical-price `(high+low+close)/3` remains a separately labeled frozen-control approximation.
- Current chart requires a complete UTC session prefix. The eight-bar minimum is a historical recipe parameter; never substitute it for source completeness.
- Use closed bars only. A live partial bar is `UNAVAILABLE`.
- Candle VWAP is an approximation; it is not tick VWAP or executed-volume-at-price.

## Strongest-contradiction checkpoint

This is the only TradingAgents-derived method approved for use. It is a reasoning checkpoint, not a debating persona and not a trading authority.

1. State the primary thesis in one falsifiable sentence.
2. Search deliberately for the strongest opposing evidence across structure, regime, momentum, volume/flow, costs and scheduled events.
3. Classify the contradiction:
   - `INVALIDATES`: a premise of the thesis is false, the key level was reclaimed/closed through, the opposing impulse is fresh and expanding, or the after-cost geometry no longer clears the recipe minimum.
   - `CAUTION`: the thesis survives, but size, confirmation or timing must be more conservative.
   - `NONE`: no material opposing evidence after a stated search.
4. If `INVALIDATES`, return `NO_TRADE` (or `WATCH` only if a future confirmation is explicitly defined). Do not average the contradiction into a confidence score.
5. If `CAUTION`, state the exact confirmation that would upgrade the decision.

### Failed breakout vs continuation in an opposing impulse

Ask these in order:

1. **Excursion:** did price trade beyond the prior boundary by a meaningful fraction of ATR? The sweep recipe uses 0.1 to 1.0 ATR.
2. **Reclaim:** did the bar close back inside the prior range? A wick without a close is not a failed breakout.
3. **Rejection quality:** is the rejecting wick at least 1.5x the real body (or 0.1 ATR minimum in the frozen test)?
4. **Participation:** is relative volume at least 1.2x the prior 20-bar denominator excluding the current bar?
5. **Opposing impulse:** is the larger-timeframe move a fresh, expanding impulse (higher highs/lows, rising ADX, price holding beyond VWAP) or a mature move losing momentum?
6. **Location:** is the reversal attempt at a known boundary with room to the nearest obstacle, or in the middle of the opposing leg?

Decision:

- Close back inside + rejection + participation + weak opposing regime => genuine failed breakout, reversal is researchable.
- Price accepts beyond the boundary, holds there, and the opposing impulse is fresh => continuation, not reversal. Do not label it a sweep.
- Reversal attempt inside a strong opposing impulse without a confirmed structure shift => `NO_TRADE` or `WATCH`; never a heroic countertrend entry.
- If the data cannot distinguish the two, `UNKNOWN`; do not choose the more attractive story.

## Source-grounded example

`StructureAwareSweepV1` produced 7 development trades and +0.085728 USDT on BTC/ETH/SOL, but lost 1.104693 USDT on 14 XRP/DOGE transfer trades and turned negative (-0.071066 USDT) at only 5 bp extra friction per side. The strongest contradiction therefore `INVALIDATES` any claim of a robust structural edge: the apparent gain is small, sample-limited, market-dependent and cost-fragile. It is not merely a caution to size down.

## Output

Return the contract decision object, plus:

- `regime` with evidence and `known_at`.
- `structure_events` with type, level, `known_at`.
- `contradiction` and the exact opposing evidence IDs.
- `unknowns`.
- `execution_authority: NONE`.

## Verification

- [ ] Every structure event has a confirmation time after the bar that created it.
- [ ] Appending future candles changes no historical label.
- [ ] VWAP anchor, warm-up and bar state are stated.
- [ ] The strongest contradiction is specific, not "market may go down".
- [ ] Failed breakout and continuation are explicitly distinguished.
- [ ] No claim of institutional intent from a chart pattern.
