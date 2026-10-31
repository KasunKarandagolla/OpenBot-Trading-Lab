# Session3 economic comparison — SHARED_CALENDAR_MARKET_TRANSFER

20260805-20261030 UTC, end exclusive. Native fee0.06% per side, actual funding, wallet1000, stake<=25,1x,max2.

| Strategy | Trades | Net USDT | PF | DD USDT | Fees | Funding | +5bp | +10bp | +20bp | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
|TrendPullbackBaselineV1|340|-15.513795|0.7440|17.675933|9.960817|-0.031078|-23.814476|-32.115157|-48.716518|REJECTED UNDER TESTED ASSUMPTIONS|
|VWAPTrendContinuationV1|14|-0.074760|0.9646|1.295844|0.412076|0.001816|-0.418156|-0.761552|-1.448345|REJECTED UNDER TESTED ASSUMPTIONS|
|LiquiditySweepReversalV1|51|-2.467817|0.6342|3.989007|1.498609|-0.004008|-3.716658|-4.965499|-7.463182|REJECTED UNDER TESTED ASSUMPTIONS|
|StructureAwareSweepV1|14|-1.104693|0.5019|1.412970|0.409415|0.001522|-1.445872|-1.787051|-2.469410|REJECTED UNDER TESTED ASSUMPTIONS|
|SweepThinningControlV1|26|-1.380261|0.6127|2.046278|0.762069|-0.000793|-2.015319|-2.650376|-3.920491|REJECTED UNDER TESTED ASSUMPTIONS|

Parent/challenger net delta: {'net_delta_usdt': 1.3631245400000003, 'paired_weekly_delta_interval': {'low_usdt': -2.800778814, 'high_usdt': 4.422056700999999, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}, 'exposure_aware_comparison': {'LiquiditySweepReversalV1': -0.0009538838690049207, 'StructureAwareSweepV1': -0.0016523999128995335, 'SweepThinningControlV1': -0.0012461262428093852}, 'control_interpretation': 'Predeclared deterministic half-thinning control, same parent/risk/cost/window. Exposure-normalized, not count-matched; differing exits and capacity mean no causal alpha estimate.'}

## TrendPullbackBaselineV1

Expectancy -0.04562880964705882; distinct active days 86; loss streak 27; exposure 51070.122675 USDT-hours; turnover 16601.361500; break-even extra bps/side -9.34489335709002; net excluding best3 -17.761644.

Pairs {'DOGE/USDT:USDT': -11.67946516, 'XRP/USDT:USDT': -3.8343301200000006}; directions {'long': {'trades': 175, 'net_usdt': -11.33979937}, 'short': {'trades': 165, 'net_usdt': -4.1739959099999995}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 186, 'net_usdt': -12.78005682}, 'TREND_DOWN': {'trades': 89, 'net_usdt': 0.16562762000000011}, 'TREND_UP': {'trades': 65, 'net_usdt': -2.89936608}}; hold-minute quantiles {'0': 15.0, '0.25': 150.0, '0.5': 322.5, '0.75': 622.5, '0.95': 720.0, '1': 720.0}; net R {'0': -0.9100576891749944, '0.25': -0.49192377201647275, '0.5': -0.23765579667707673, '0.75': 0.14775084793861762, '1': 1.2848112319150822}; forced-end exits {'trades': 0, 'net_usdt': 0, 'net_excluding_forced_usdt': -15.51379528}.

Weekly block interval {'low_usdt': -32.83175404275, 'high_usdt': 1.4770943640000003, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross -5.52190000 minus fees plus funding reconciles to net with residual -0.0000000003.

## VWAPTrendContinuationV1

Expectancy -0.005339982857142856; distinct active days 13; loss streak 5; exposure 870.522950 USDT-hours; turnover 686.792700; break-even extra bps/side -1.0885345752801385; net excluding best3 -1.591337.

Pairs {'DOGE/USDT:USDT': -0.7941746, 'XRP/USDT:USDT': 0.71941484}; directions {'long': {'trades': 5, 'net_usdt': 0.79745816}, 'short': {'trades': 9, 'net_usdt': -0.87221792}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 2, 'net_usdt': 0.6868358299999999}, 'TREND_DOWN': {'trades': 8, 'net_usdt': -1.10421631}, 'TREND_UP': {'trades': 4, 'net_usdt': 0.34262072000000005}}; hold-minute quantiles {'0': 0.0, '0.25': 37.5, '0.5': 120.0, '0.75': 232.5, '0.95': 362.99999999999994, '1': 480.0}; net R {'0': -0.897449951713516, '0.25': -0.7919245083811298, '0.5': -0.771463636958073, '0.75': 1.1932714097989774, '1': 1.6371193463431613}; forced-end exits {'trades': 0, 'net_usdt': 0, 'net_excluding_forced_usdt': -0.07475975999999995}.

Weekly block interval {'low_usdt': -2.9323696215, 'high_usdt': 3.2911218649999934, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross 0.33550000 minus fees plus funding reconciles to net with residual 0.0000000003.

## LiquiditySweepReversalV1

Expectancy -0.04838857274509804; distinct active days 28; loss streak 7; exposure 2587.125425 USDT-hours; turnover 2497.682200; break-even extra bps/side -9.880429183504612; net excluding best3 -3.926390.

Pairs {'DOGE/USDT:USDT': -2.24592614, 'XRP/USDT:USDT': -0.22189106999999988}; directions {'long': {'trades': 33, 'net_usdt': -1.36501969}, 'short': {'trades': 18, 'net_usdt': -1.10279752}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 39, 'net_usdt': -3.12245679}, 'TREND_DOWN': {'trades': 7, 'net_usdt': 1.05666518}, 'TREND_UP': {'trades': 5, 'net_usdt': -0.4020256}}; hold-minute quantiles {'0': 0.0, '0.25': 37.5, '0.5': 105.0, '0.75': 240.0, '0.95': 240.0, '1': 240.0}; net R {'0': -0.8622953260380565, '0.25': -0.7870429404104647, '0.5': -0.7569360789631353, '0.75': 0.34757316427718976, '1': 1.4905110226971918}; forced-end exits {'trades': 1, 'net_usdt': 0.0182688, 'net_excluding_forced_usdt': -2.48608601}.

Weekly block interval {'low_usdt': -5.93326566275, 'high_usdt': 1.601242944249999, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross -0.96520000 minus fees plus funding reconciles to net with residual 0.0000000014.

## StructureAwareSweepV1

Expectancy -0.07890661928571428; distinct active days 8; loss streak 4; exposure 668.538325 USDT-hours; turnover 682.358600; break-even extra bps/side -16.189327283337526; net excluding best3 -2.217953.

Pairs {'DOGE/USDT:USDT': -1.15328879, 'XRP/USDT:USDT': 0.048596119999999965}; directions {'long': {'trades': 10, 'net_usdt': -2.02068787}, 'short': {'trades': 4, 'net_usdt': 0.9159952}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 14, 'net_usdt': -1.10469267}}; hold-minute quantiles {'0': 0.0, '0.25': 52.5, '0.5': 90.0, '0.75': 210.0, '0.95': 240.0, '1': 240.0}; net R {'0': -0.8578473447842355, '0.25': -0.8039323756570942, '0.5': -0.7746173726634342, '0.75': -0.1623707796583932, '1': 1.3042092362997548}; forced-end exits {'trades': 0, 'net_usdt': 0, 'net_excluding_forced_usdt': -1.10469267}.

Weekly block interval {'low_usdt': -2.6131841222500003, 'high_usdt': 0.3476561294999997, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross -0.69680000 minus fees plus funding reconciles to net with residual 0.0000000002.

## SweepThinningControlV1

Expectancy -0.05308697653846153; distinct active days 17; loss streak 4; exposure 1107.641700 USDT-hours; turnover 1270.114800; break-even extra bps/side -10.867217593244327; net excluding best3 -2.665498.

Pairs {'DOGE/USDT:USDT': -1.4103877200000001, 'XRP/USDT:USDT': 0.030126330000000062}; directions {'long': {'trades': 19, 'net_usdt': -0.58724737}, 'short': {'trades': 7, 'net_usdt': -0.79301402}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 19, 'net_usdt': -1.79213893}, 'TREND_DOWN': {'trades': 6, 'net_usdt': 0.63608554}, 'TREND_UP': {'trades': 1, 'net_usdt': -0.224208}}; hold-minute quantiles {'0': 0.0, '0.25': 30.0, '0.5': 82.5, '0.75': 176.25, '0.95': 240.0, '1': 240.0}; net R {'0': -0.8622953260380565, '0.25': -0.7940543877668871, '0.5': -0.7639957932717815, '0.75': 0.29083182361473214, '1': 1.4905110226971918}; forced-end exits {'trades': 1, 'net_usdt': 0.0182688, 'net_excluding_forced_usdt': -1.39853019}.

Weekly block interval {'low_usdt': -3.59937379, 'high_usdt': 1.1084991652499996, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross -0.61740000 minus fees plus funding reconciles to net with residual -0.0000000012.

- Inspected DEVELOPMENT or shared-calendar TRANSFER, no untouched holdout.
- Calendar week resampling assumes exchangeable weeks; few dependent blocks, no statistical qualification.
- 15m requested-price fills, no queue/partial fills/historical spreads.
- UTC realized-loss halt excludes unrealized losses; full account daily halt NOT ENFORCED.
- Prospective evidence requires code/data freezes before outcomes; no automatic promotion.
