# Baseline real-market backtest — EXPLORATORY / UNQUALIFIED

Native Freqtrade 2026.10, Gate USDT perpetuals BTC/ETH/SOL. Evaluation 2026-07-30 00:00 UTC to 2026-10-30 00:00 UTC (end exclusive). Data starts July 26 for 200-bar warm-up. Static current surviving universe; no historical dynamic VolumePairList. Strategy frozen before outcome inspection; no tuning.

- Trades: 386; wins 115, losses 271, draws 0; win rate 0.2979274611398964.
- Net modeled profit: -6.51654870 USDT (-0.651655% of initial 1,000 wallet).
- Native max drawdown: 0.008603972968347171 of account; 8.622088980000001 USDT.
- Average/expectancy: -0.016882250518134717 USDT/trade; profit factor 0.8516852028347884 (null if undefined).
- Distinct entry UTC days: 92 (correlated crypto trades are not independent samples).
- Geometric price P&L before fees/funding: 3.91112000 USDT; reconstructed entry+exit fees: 10.40519144; native signed funding: -0.02247730.
- Reconciliation residual: 0.0000000439 USDT.
- Fees: 0.0006 per side, conservative research assumption, not verified exchange account rate.
- Wallet 1,000 USDT; fixed 25 USDT stake; 1x; max 2 positions; protections enabled.

## Additional spread/slippage sensitivity

| Extra basis points per side | Additional cost USDT | Net profit USDT |
|---|---:|---:|
| 0 | 0.000000 | -6.516549 |
| 5 | 8.670993 | -15.187542 |
| 10 | 17.341986 | -23.858534 |
| 20 | 34.683971 | -41.200520 |

These are extra costs beyond native fees/funding, not measured historical spreads or a new fill simulation. Holding quantiles, exit counts and per-pair contributions are in [backtest-summary.json](backtest-summary.json). Full native trade/result JSON and CSV are retained. Research files/checksums, gaps and funding/mark coverage are in [market-data-manifest.json](market-data-manifest.json).

- Candle backtest assumes requested-price fills; no measured historical spread/slippage, order-book depth, latency or outage model.
- Extra friction is a postprocessing sensitivity only; it does not change fills, sequencing or drawdown.
- Current surviving static BTC/ETH/SOL contracts; historical universe membership not reconstructed.
- 1x leverage fixed; liquidation accuracy not validated. No independent holdout or economic qualification.
- No exact 0.25%/0.50% monetary-risk or 1% daily-loss halt guarantee. Paper stops require running process.
