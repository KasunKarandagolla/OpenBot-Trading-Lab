# Evaluation rubric — compare real execution evidence, not fluency

## Eligibility/factual categories

Score independently, with raw counts and trace IDs:

1. `pixel_seen_proof` — actual pixels delivered, verified symbol/timeframe; URL-only negative control.
2. `image_reading` — independently check visible legends, EMA/VWAP/price, candle order, live-bar status. Count exact transcription errors.
3. `source_alignment` — contract/venue matches, as-of and closed candles, data delay/coverage; mismatches must be identified.
4. `structure_claims` — BOS, CHoCH, sweep, FVG or order block only if rule and cutoff support; rate unsupported jargon separately.
5. `opportunity_analysis` — both long/short where plausible, nearest obstacle, meaningful invalidation, recipe fit and NO TRADE/WATCH correctness relative to **rules**, not subsequent P&L.
6. `risk/economics` — avoids inventing fill, target, stop, funding, leverage or liquidation details; correctly handles late signal.
7. `operational` — error handling, number of chart calls, actual latency, cash cost, free quota use, modality failures.

## Controlled comparisons

Use paired chronological cases, identical evidence and model budget, pre-frozen prompts and verdicts. Main arms:

- **N (numeric-only)**: standard Market Researcher + existing strategy evidence.
- **V (vision added)**: identical numeric evidence + real chart pixels + Chart-Vision specialist output.

For richer data, record optional ablation:

- **N+D**: numeric baseline + external futures context, no images.
- **V+D**: identical enriched context + vision.

This prevents attributing MarketTrace/Coinfuty incremental data value to a screenshot. If resources are limited, prioritize the N versus V pair, with the *same* source data except image modality; evaluate auxiliary MCP separately.

## Decisions and outcomes

Freeze for each arm `TRADE/NO_TRADE/WATCH` hypothetical recommendation plus a **precise, testable** reason. Keep deterministic native strategy trades unchanged. Evaluate vision rejection as potential **avoided loss AND missed winner**, with unfilled cases and time/portfolio exposure. Score P&L/net pure stop-R, cost-inclusive R, after-cost bp, drawdown, number of trade proposals, nonfills, realized-versus-hypothetical and uncertainty. No 'success rate' based on only vetoed losers. Zero changes or zero trades can still be a truthful outcome, not proof of improvement.

## Evidence grades

- `FUNCTIONAL`: real image acquisition, modality proof and report-to-Director verified.
- `ACCURATE`: repeated fact checks with independently inspected pixels and source data, low hallucination frequency.
- `ADDITIVE`: paired analyses show specific incremental decisions supported by evidence.
- `ECONOMIC`: native/sound forward results after costs and uncertainty show a credible advantage (much stronger than a small pilot).

A few cases can justify further research, not prove edge. Historic model replay may be contaminated by model prior knowledge even with cutoff pixels, so emphasize prospective shadow observations. No universal trade-count threshold.
