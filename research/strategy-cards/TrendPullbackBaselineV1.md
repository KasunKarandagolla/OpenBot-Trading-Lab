# TrendPullbackBaselineV1 — 1.0.0 — EXPLORATORY / UNQUALIFIED

Hypothesis: a simple trend pullback/reclaim may provide a useful benchmark for later research. Profitability is unknown. Exact source/protocol SHA256 values and freeze time: `evidence/session-1/freeze.sha256`, `frozen-at.txt`. No optimization or challenger in this session.

- Contracts: Gate linear USDT-settled BTC/USDT:USDT, ETH/USDT:USDT, SOL/USDT:USDT; long and short. A static familiar-current-contract universe, with survivorship and point-in-time selection limitations. Today's scan does not change the backtest.
- Timeframe: completed 15m candles, Freqtrade signals enter on a later bar. 1h downloaded for context/audit, not used by this version. 200 startup candles; four full days outside the evaluation window. No negative shifts, centered windows or future-confirmed labels.
- Indicators: TA-Lib EMA(close,20), EMA(close,50); ATR(high,low,close,14), using TA-Lib exponential/Wilder conventions. ATR/close must be in [0.001,0.03] inclusive, close >0 and volume >0. These are provisional engineering thresholds for dead/extreme bars, not fitted alpha.
- Long: EMA20 > EMA50; prior close <= prior EMA20; current completed close > current EMA20. Short: EMA20 < EMA50; prior close >= prior EMA20; completed close < EMA20. Every comparison uses its corresponding bar.
- Exit: long when EMA20 < EMA50; short when EMA20 > EMA50; native stoploss -2% and ROI +3% from entry. Native engine determines fill/order priority. `custom_exit` requests exit once current time minus original trade open time >=12 hours. Evaluation cadence, unfilled orders and outages can delay actual simulated exit; no hard wall-clock guarantee.
- Fixed leverage 1x; 25 USDT stake, 1,000 USDT simulated wallet, at most two positions. Native Freqtrade prevents simultaneous stacked positions per pair. Position adjustment, DCA, trailing and partial exits disabled. Native two-candle per-pair cooldown enabled by backtest `--enable-protections`; 5-minute entry timeout for paper limit orders. No exchange-side stops.
- Approximate price-only stop loss: 0.50 USDT per 25 USDT position (0.05% of starting wallet), before costs/gaps. Exact 0.25% per-trade and 0.50% aggregate monetary-risk ceilings, concentration and a 1% daily new-entry halt are NOT implemented or guaranteed. No autonomous exposure expansion.
- Costs: native fee 0.0006 each entry and exit, a conservative research assumption, not a verified account tier. Actual downloaded funding and mark data used through Freqtrade; completeness recorded separately. Additional 5/10/20bp per-side friction sensitivities do not change native fills. No true historical order book, queue, latency or liquidation qualification.

Initial requested July 1 start was outside Gate's 10,000-bar REST retention. Before examining any result, the window was corrected to download July 26–October 30 and evaluate July 30–October 30, 2026 (UTC, exclusive end). Strategy parameters did not change. See `window-correction.md`.

Paper stops/exits run only while Freqtrade and the host work. They do not establish real exchange protective orders. No independent validation or promotion to live is authorized.
