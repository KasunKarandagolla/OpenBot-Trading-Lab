# 02 — Market map and multi-timeframe reasoning

## Purpose

Create a **conditional market map**, not an automatic bullish/bearish vote. For intraday futures held under ~15 hours, prioritize 4H/1H context and 15m setup; 5m is optional for near-entry detail. A 4H bearish context does NOT prohibit a carefully qualified short continuation, nor automatically prohibit a countertrend long; it changes the hypothesis, counterevidence, holding plan and risk investigation.

## Step-by-step visual method

1. Mark the chart's time and the last complete candle. Distinguish visible live-bar movement from confirmed close. Do not infer exact pivot timing from sparse x-axis labels.
2. For each timeframe, identify sequence of swing highs/lows, the broad leg, recent correction, potential range limits, and nearest relevant prior price extremes. A higher-low observation is different from a confirmed causal swing with right-side bars.
3. Label regime `TREND_UP`, `TREND_DOWN`, `RANGE`, `TRANSITION`, or `UNKNOWN` with explicit evidence. EMA20/EMA50 direction and VWAP are supporting context, not the definition of confirmed structure.
4. Classify observed sequence as impulsive expansion, controlled pullback, failed excursion/rejection, or unresolved congestion. Define the *specific level* whose acceptance/rejection would falsify the favored hypothesis.
5. Compare 4H → 1H → 15m; explain whether lower-TF movement is (a) higher-TF continuation pullback, (b) early potential reversal, (c) separate range play, or (d) unqualified conflict. Do not require complete alignment if the strategy is explicitly countertrend; require its proper confirmed trigger.
6. State whether a *current* valid recipe trigger exists. Market direction and setup trigger are not the same thing.

## Example — BTC 2026-11-03 exploratory screenshot

At the observed instant, screenshot commentary placed 4H price below bearish EMA20/50, 1H price recovering, and 15m EMA20 above EMA50. This supports `4H trend bearish + short-term rebound`, not a completed 4H reversal. A useful output: `WATCH FOR (a) short continuation at resistance if price and structural trigger satisfy native recipe; OR (b) reversal only if higher-TF evidence improves; CURRENT TRIGGER UNKNOWN`. Do not call every market mismatch NO_TRADE without examining available strategy families. Existing screenshot had forming bars; avoid treating the visual EMA as the completed-bar Gate EMA.

## Example — SOL screenshot

15m above fast/slow EMA while hourly price was below EMA50 is lower-TF recovery, not proof of a liquidity-sweep reversal. The hypothesis needs a known pre-excursion boundary, actual excursion, reclaim and confirmation timing. Report both plausible paths and what would distinguish them.

## Failure modes

- Thinking a single high-volume candle proves 'accumulation.'
- Calling an EMA cross BOS/CHoCH.
- Reading chart scale as exact price without structured verification.
- Equating higher-timeframe bias with a completed entry signal.
- Treating a live-bar bounce as confirmed 1H/4H structure.
