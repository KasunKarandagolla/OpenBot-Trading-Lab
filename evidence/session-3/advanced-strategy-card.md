# StructureAwareSweepV1 — research only

Hypothesis fixed in f0d3d1e; engineering-only tuple/dtype corrections qualified and frozen in367808d before any new strategy outcome. Strategy1.0.0 extends byte-identical LiquiditySweepReversalV1/PlaybookRiskV1. Exact source SHA256s: freeze.sha256 and each native-result provenance. No threshold or market exclusions changed after outcomes.

15m signal candle completes before entry at next candle open. Preserve parent: strictly prior20-bar range, wick excursion0.1–1.0ATR beyond low/high, completed close reclaim/rejection; rejection wick>=1.5*max(body,0.1ATR); relative volume>=1.2 versus prior20 bars; ATR14/close[0.001,0.025]; completed-hour ADX<=30; finite, continuous source and valid hourly context.

Add only structural eligibility:

- Strict left2/right2 confirmed pivots on15m and1h. Ties are not pivots. The prior confirmed swing must be known by signal candle open, never backdated to pivot time. Previously confirmed levels can remain useful sweep references after a break; proximity does not assert resting liquidity.
- Long: absolute difference between prior20 low and prior confirmed swing low<=0.5ATR. Short: symmetric high test.
- Hourly structural direction must be defined UP/DOWN. Reject long when hourly DOWN and ADX>=25; reject short when hourly UP and ADX>=25. Parent ADX<=30 remains. This permits a counter-direction reversal at lower hourly ADX, symmetrically.

All other risk and entry mechanics inherited unchanged: signal-close limit reference, maximum deviation min(0.15%,0.25ATR/reference), five-minute signal age/order timeout, no repricing/chase; stop beyond signal extreme by0.15ATR; stop-distance[0.003,0.025]; target native net ROI2x initial price risk; admission2*risk/(risk+0.0035)>=1.25. Reserve0.12% roundtrip assumed native fees+0.20% extra friction+0.03% adverse funding in sizing; report extra reward friction separately. Native emergency stop3%; max hold4h; cooldown2bars; 1x; <=25USDT; max2; no DCA/pyramiding. The exact1% mark-to-market daily account halt is NOT ENFORCED: inherited halt uses UTC realized closed-trade net<=-10USDT only. Gaps/costs/outages can exceed intended loss.

A separate deterministic SHA256(symbol|signal timestamp) even-parity parent thinning control uses identical risk. It is not an alpha strategy or count-matched randomized experiment. Report exposure-normalized rates and weak attribution explicitly.

No FVG, order block, hidden-stop, liquidation or aggressor-delta feature is used. No paper authorization. Missing data/unknown structure produces NO_TRADE. Paper expiry and simulated candle fills do not prove real fills or queue priority.
