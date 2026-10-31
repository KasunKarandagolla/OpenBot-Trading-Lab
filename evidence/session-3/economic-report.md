# Executed economic findings

Common evaluation August5–October30 2026 UTC, end exclusive; 240 completed hourly warmup bars from July26. Native fee0.06%/side, actual funding, wallet1000USDT, stake<=25USDT,1x,max2. No strategy tuning.

| Strategy | BTC/ETH/SOL trades | Net USDT | XRP/DOGE trades | Net USDT |
|---|---:|---:|---:|---:|
|LiquiditySweepReversalV1|38|1.576780|51|-2.467817|
|StructureAwareSweepV1|7|0.085728|14|-1.104693|
|SweepThinningControlV1|22|1.892937|26|-1.380261|
|TrendPullbackBaselineV1|360|-4.807188|340|-15.513795|
|VWAPTrendContinuationV1|17|0.816408|14|-0.074760|

The structural enhancement has7 development trades,5 active entry days and positive0.085728USDT native net, but loses0.071066USDT at just5 extra bp/side. Parent has38 trades and1.576780USDT, losing0.106237USDT at10bp. The challenger does not show conditional economic improvement: development net per notional-hour is lower than parent and the generic thinning control. In XRP/DOGE it loses1.104693USDT on14 trades and is worse per notional-hour than the parent. Thinning is exposure-normalized, not count-matched; no causal alpha attribution is established.

## s3-development-v1

[Full report](cohorts/s3-development-v1/economic-report.md); [native exports](cohorts/s3-development-v1/native-results/); [full trade ledgers and causal tags](cohorts/s3-development-v1/trade-ledgers/).

- LiquiditySweepReversalV1: fee 1.009810, signed funding -0.001220, PF 1.56760616558166, expectancy 0.041494208684210526, DD 1.0048103499999999, active days 28, status INSUFFICIENT EVIDENCE.
- StructureAwareSweepV1: fee 0.188153, signed funding -0.000859, PF 1.1401454461433498, expectancy 0.012246874285714285, DD 0.51208701, active days 5, status INSUFFICIENT EVIDENCE.
- SweepThinningControlV1: fee 0.581366, signed funding -0.002627, PF 2.4603756967953148, expectancy 0.08604257727272725, DD 0.4475977500000001, active days 19, status INSUFFICIENT EVIDENCE.
- TrendPullbackBaselineV1: fee 9.718767, signed funding -0.017871, PF 0.8799935145404734, expectancy -0.013353299, DD 8.622088980000001, active days 86, status REJECTED UNDER TESTED ASSUMPTIONS.
- VWAPTrendContinuationV1: fee 0.454453, signed funding -0.001549, PF 1.5418251562382932, expectancy 0.048023993529411765, DD 0.66030074, active days 13, status INSUFFICIENT EVIDENCE.

Parent/challenger weekly paired delta interval: {'draws': 2000, 'high_usdt': 0.722802059749998, 'low_usdt': -3.9919540507499995, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof', 'seed': 3103, 'weeks': 13}.

## s3-transfer-v1

[Full report](cohorts/s3-transfer-v1/economic-report.md); [native exports](cohorts/s3-transfer-v1/native-results/); [full trade ledgers and causal tags](cohorts/s3-transfer-v1/trade-ledgers/).

- LiquiditySweepReversalV1: fee 1.498609, signed funding -0.004008, PF 0.6342007793677659, expectancy -0.04838857274509804, DD 3.9890071299999996, active days 28, status REJECTED UNDER TESTED ASSUMPTIONS.
- StructureAwareSweepV1: fee 0.409415, signed funding 0.001522, PF 0.501931539618818, expectancy -0.07890661928571428, DD 1.41297044, active days 8, status REJECTED UNDER TESTED ASSUMPTIONS.
- SweepThinningControlV1: fee 0.762069, signed funding -0.000793, PF 0.6126754669834651, expectancy -0.05308697653846153, DD 2.04627814, active days 17, status REJECTED UNDER TESTED ASSUMPTIONS.
- TrendPullbackBaselineV1: fee 9.960817, signed funding -0.031078, PF 0.7439585041707514, expectancy -0.04562880964705882, DD 17.675933209999997, active days 86, status REJECTED UNDER TESTED ASSUMPTIONS.
- VWAPTrendContinuationV1: fee 0.412076, signed funding 0.001816, PF 0.964577872473573, expectancy -0.005339982857142856, DD 1.29584379, active days 13, status REJECTED UNDER TESTED ASSUMPTIONS.

Parent/challenger weekly paired delta interval: {'draws': 2000, 'high_usdt': 4.422056700999999, 'low_usdt': -2.800778814, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof', 'seed': 3103, 'weeks': 13}.

Every point estimate is descriptive. Thirteen calendar-week blocks include zero-trade weeks and resample all markets jointly, with2000 draws/seed3103. Few dependent weeks, partial boundary weeks and possible nonstationarity prevent a significance claim. Trade count30 is not a qualification gate. Native net equals gross price P&L minus entry/exit fees plus signed funding; residuals are below1e-5USDT. Costs are never subtracted twice. Friction draws down chronological closed-trade equity; native account drawdown is separately retained. Forced window exits are included and excluded in separate metrics. Regimes are prior-completed hourly ADX/EMA labels at entry, not hindsight calendar labels.

No untouched holdout exists. The old calendar is inspected DEVELOPMENT; additional current surviving XRP/DOGE are shared-calendar market TRANSFER. A prospective Nov1–Nov8 cohort is registered before outcomes, has no results, and refuses acquisition before end. No live or paper promotion.
