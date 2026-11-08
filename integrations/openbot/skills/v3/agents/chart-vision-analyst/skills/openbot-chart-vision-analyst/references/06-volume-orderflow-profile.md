# 06 — Volume, executed trade flow, volume profile and auxiliary futures context

## Separate what the model sees from what the feed truly measures

1. Candle volume: aggregated executions during a candle; **does not** prove buyers or sellers were aggressive, and not necessarily native quote-currency volume.
2. Genuine signed aggressor delta/CVD: requires venue trade tape with taker-side semantics, coverage, instrument multiplier and timestamps. A screenshot's green volume bars are not CVD.
3. Volume Profile POC/VAH/VAL/HVN/LVN: a trade-derived volume-at-price distribution is higher fidelity than distributing OHLCV typical-price proxies; label proxy calculations honestly.
4. Order-book imbalance/walls: standing liquidity is ephemeral and can cancel. A static heatmap isn't an executed fill; walls may be spoofed or stale.
5. Open interest/funding/liquidations: derivative-market state, not direct buy/sell truth. Rising OI + price up has multiple causes; estimated liquidation prints are not a complete census.

## Historical provider research and current supplementary checks

Provider advertising in this preserved paragraph is historical/unverified, not a current availability claim. Binance USD-M venue coverage, timestamps and contracts must be verified before use.

- MarketTrace MCP advertises live (approximately 30-second refresh) BTC, ETH, SOL, BNB, XRP, DOGE, HYPE, ZEC, ENA; aggregated Binance, Bybit, OKX, Hyperliquid data. **Mixed venues; verify Binance USD-M coverage**. It exposes current state, historical conditions, CVD, profiles, footprint, OI and funding. Respect coverage, `age_seconds`, partial history, base units and per-venue availability. Exchange mismatch means `CROSS_VENUE_CONTEXT`; never cite as native Binance USD-M trade flow.
- Coinfuty MCP advertises free keyless derivatives OI/funding/liquidation/history and may serve broader screening. Its age/venue coverage and exact endpoint must be verified at runtime. Do not add both sources just to decorate the report.
- Lab existing modules: `research/intelligence/intelligence_orderflow.py`, `research/intelligence/intelligence_profile.py`, and `research/bonus/orderflow.py`. When enough verified native data exist, prefer those; `OHLCV_PROXY` stays explicit.

## Reasoning method

Ask a **specific** question before fetching extra evidence: e.g., 'Does rising price into nearby resistance show improving aggressor demand, or price rising on weaker aggressive buying?' Then obtain the minimal scoped data, check venue/coverage and compare time windows using common cutoffs. Correlation or divergence is descriptive, not a universal reversal trigger. Do not claim absorption or liquidation-driven failure without a suitable print/book source.

## Useful but unproven pairings

- Price breaks an established boundary + increasing OI and participation: could suggest fresh trend exposure; still needs confirmation and cost/target room.
- Price advances + declining CVD: possible divergence, but could arise from passive absorption; classify as `CONTRADICTION/UNKNOWN`, not automatic short.
- Sweep into trade-derived high-volume node: plausible reaction location, but node placement, time window and normalized units must be stated.
- Wide spread/thin book near proposed entry: execution-feasibility warning independently of directional chart quality.

## Decision contribution

Return `data_source`, `venues`, `asof`, `age`, `coverage`, `units`, `directional_interpretation` (possibly null), `contradicts_visual_thesis`, `what_it_cannot_prove`. Missing data never become supportive confluence by default. Count how often extra data changes a research assessment; test it separately from vision itself.
