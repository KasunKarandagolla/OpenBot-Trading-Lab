# Session 2 real-market comparison — DEVELOPMENT ONLY

Gate BTC/ETH/SOL linear USDT perpetuals, 2026-07-30 through 2026-10-30 UTC end exclusive; wallet1000, stake<=25, max2, 1x. Native fee0.06% each side, actual funding. No threshold tuning.

| Strategy | Trades (L/S) | Net USDT | Expectancy | PF | Max DD USDT | Fees | Signed funding | +5bp | +10bp | +20bp | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| TrendPullbackBaselineV1 | 386 (198/188) | -6.516549 | -0.016882 | 0.8517 | 8.622089 | 10.405191 | -0.022477 | -15.187542 | -23.858534 | -41.200520 | REJECTED under evaluated assumptions |
| VWAPTrendContinuationV1 | 17 (7/10) | 0.816408 | 0.048024 | 1.5418 | 0.660301 | 0.454453 | -0.001549 | 0.437697 | 0.058987 | -0.698434 | INSUFFICIENT EVIDENCE |
| LiquiditySweepReversalV1 | 39 (21/18) | 1.751484 | 0.044910 | 1.6305 | 1.004810 | 1.037392 | -0.000414 | 0.886991 | 0.022498 | -1.706488 | UNQUALIFIED DEVELOPMENT RESULT |

## TrendPullbackBaselineV1

Distinct entry days: 92; per pair: {'BTC/USDT:USDT': -5.55257935, 'ETH/USDT:USDT': -0.5329479000000004, 'SOL/USDT:USDT': -0.4310214499999998}; direction net: {'long': {'trades': 198, 'net_usdt': -1.99799148}, 'short': {'trades': 188, 'net_usdt': -4.51855722}}. Gross price P&L 3.911120; net minus gross-fees+funding residual 0.0000000439. Mean gross 0.010132435233160656; win/loss payoff {'average_win_usdt': 0.32539765930434783, 'average_loss_usdt': -0.1621301827306273}. Holding-minute quantiles {'0': 0.0, '0.25': 180.0, '0.5': 427.5, '0.75': 720.0, '0.95': 720.0, '1': 720.0}; exits {'exit_signal': 229, 'max_hold_12h': 112, 'roi': 31, 'stop_loss': 14}. Turnover 17341.9857 USDT, notional-hours 61717.0257. Net without best three trades -8.743746. R matched trades 0; R quantiles None. Callback decisions {}. Native rejected/timeout/cancel counts 312/0/0. Coarse stop/target overlap None (diagnostic reference-price target, not exact net-ROI execution price).

## VWAPTrendContinuationV1

Distinct entry days: 13; per pair: {'BTC/USDT:USDT': 0.14471860999999997, 'ETH/USDT:USDT': 0.24552746, 'SOL/USDT:USDT': 0.42616182}; direction net: {'long': {'trades': 7, 'net_usdt': 1.33593146}, 'short': {'trades': 10, 'net_usdt': -0.51952357}}. Gross price P&L 1.272410; net minus gross-fees+funding residual 0.0000000092. Mean gross 0.07484764705882337; win/loss payoff {'average_win_usdt': 0.2581312866666667, 'average_loss_usdt': -0.18834671125}. Holding-minute quantiles {'0': 15.0, '0.25': 45.0, '0.5': 120.0, '0.75': 300.0, '0.95': 480.0, '1': 480.0}; exits {'stop_loss': 7, 'roi': 6, 'max_hold_8h': 4}. Turnover 757.4211 USDT, notional-hours 1299.2559. Net without best three trades -0.154333. R matched trades 17; R quantiles {'0': -0.8358042017823454, '0.25': -0.7755351990858845, '0.5': 0.2683521914332089, '0.75': 1.2790215345591331, '1': 1.419648990701019}. Callback decisions {'ACCEPTED': 17}. Native rejected/timeout/cancel counts 0/0/0. Coarse stop/target overlap 0 (diagnostic reference-price target, not exact net-ROI execution price).

## LiquiditySweepReversalV1

Distinct entry days: 29; per pair: {'BTC/USDT:USDT': 0.35434521, 'ETH/USDT:USDT': 0.27231589, 'SOL/USDT:USDT': 1.12482275}; direction net: {'long': {'trades': 21, 'net_usdt': 0.09401587999999994}, 'short': {'trades': 18, 'net_usdt': 1.6574679700000001}}. Gross price P&L 2.789290; net minus gross-fees+funding residual 0.0000000221. Mean gross 0.07152025641025629; win/loss payoff {'average_win_usdt': 0.22647155, 'average_loss_usdt': -0.14620774473684212}. Holding-minute quantiles {'0': 0.0, '0.25': 60.0, '0.5': 180.0, '0.75': 240.0, '0.95': 240.0, '1': 240.0}; exits {'max_hold_4h': 17, 'stop_loss': 11, 'roi': 10, 'force_exit': 1}. Turnover 1728.9861 USDT, notional-hours 2160.3004. Net without best three trades 0.373941. R matched trades 39; R quantiles {'0': -0.877999408123653, '0.25': -0.7558892931113164, '0.5': 0.01040343828006294, '0.75': 1.1533944883644578, '1': 1.4990903407695515}. Callback decisions {'ACCEPTED': 39}. Native rejected/timeout/cancel counts 0/0/0. Coarse stop/target overlap 0 (diagnostic reference-price target, not exact net-ROI execution price).

- No independent holdout, no economic qualification or automatic promotion.
- 15m limit fills are within-candle simulations; five-minute expiry cannot establish historical queue fills.
- Friction stresses deduct additional turnover costs without resimulating fills or drawdown.
- Risk controls rely on assumed stop/friction/funding allowances; gaps/outages can exceed them.
- UTC realized-loss halt excludes unrealized account losses; full daily-loss ceiling NOT ENFORCED.
- Current surviving BTC/ETH/SOL only; correlated days are not independent samples.

Fewer trades alone are not success. Status thresholds are descriptive: fewer than30 trades means insufficient evidence; nonpositive larger samples rejected for this cohort; positive samples remain unqualified development. No significance/power claim is made. See signal-counts.json for feature-level opportunities and strategy-risks.json for enforced versus limited controls.
