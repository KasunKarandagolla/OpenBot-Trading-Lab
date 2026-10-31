# Session3 economic comparison — WARMUP_CORRECTED_DEVELOPMENT

20260805-20261030 UTC, end exclusive. Native fee0.06% per side, actual funding, wallet1000, stake<=25,1x,max2.

| Strategy | Trades | Net USDT | PF | DD USDT | Fees | Funding | +5bp | +10bp | +20bp | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
|TrendPullbackBaselineV1|360|-4.807188|0.8800|8.622089|9.718767|-0.017871|-12.906160|-21.005132|-37.203077|REJECTED UNDER TESTED ASSUMPTIONS|
|VWAPTrendContinuationV1|17|0.816408|1.5418|0.660301|0.454453|-0.001549|0.437697|0.058987|-0.698434|INSUFFICIENT EVIDENCE|
|LiquiditySweepReversalV1|38|1.576780|1.5676|1.004810|1.009810|-0.001220|0.735271|-0.106237|-1.789254|INSUFFICIENT EVIDENCE|
|StructureAwareSweepV1|7|0.085728|1.1401|0.512087|0.188153|-0.000859|-0.071066|-0.227861|-0.541449|INSUFFICIENT EVIDENCE|
|SweepThinningControlV1|22|1.892937|2.4604|0.447598|0.581366|-0.002627|1.408465|0.923993|-0.044950|INSUFFICIENT EVIDENCE|

Parent/challenger net delta: {'net_delta_usdt': -1.49105181, 'paired_weekly_delta_interval': {'low_usdt': -3.9919540507499995, 'high_usdt': 0.722802059749998, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}, 'exposure_aware_comparison': {'LiquiditySweepReversalV1': 0.0007624812588003364, 'StructureAwareSweepV1': 0.0002259724210071605, 'SweepThinningControlV1': 0.0016408466699148225}, 'control_interpretation': 'Predeclared deterministic half-thinning control, same parent/risk/cost/window. Exposure-normalized, not count-matched; differing exits and capacity mean no causal alpha estimate.'}

## TrendPullbackBaselineV1

Expectancy -0.013353299; distinct active days 86; loss streak 16; exposure 57911.052205 USDT-hours; turnover 16197.944750; break-even extra bps/side -2.967776291495253; net excluding best3 -7.034385.

Pairs {'BTC/USDT:USDT': -5.19257588, 'ETH/USDT:USDT': 1.0058173799999999, 'SOL/USDT:USDT': -0.6204291399999997}; directions {'long': {'trades': 184, 'net_usdt': -1.14030168}, 'short': {'trades': 176, 'net_usdt': -3.66688596}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 209, 'net_usdt': -5.320786340000001}, 'TREND_DOWN': {'trades': 73, 'net_usdt': -3.80608073}, 'TREND_UP': {'trades': 78, 'net_usdt': 4.31967943}}; hold-minute quantiles {'0': 0.0, '0.25': 191.25, '0.5': 435.0, '0.75': 720.0, '0.95': 720.0, '1': 720.0}; net R {'0': -0.9054440409821681, '0.25': -0.3275462525592355, '0.5': -0.17669818455365416, '0.75': 0.10898433322888434, '1': 1.2822985910950764}; forced-end exits {'trades': 0, 'net_usdt': 0, 'net_excluding_forced_usdt': -4.80718764}.

Weekly block interval {'low_usdt': -15.04193396875, 'high_usdt': 5.463866782749991, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross 4.92945000 minus fees plus funding reconciles to net with residual 0.0000000149.

## VWAPTrendContinuationV1

Expectancy 0.048023993529411765; distinct active days 13; loss streak 3; exposure 1299.255880 USDT-hours; turnover 757.421130; break-even extra bps/side 10.77878418839464; net excluding best3 -0.154333.

Pairs {'BTC/USDT:USDT': 0.14471860999999997, 'ETH/USDT:USDT': 0.24552746, 'SOL/USDT:USDT': 0.42616182}; directions {'long': {'trades': 7, 'net_usdt': 1.33593146}, 'short': {'trades': 10, 'net_usdt': -0.51952357}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 4, 'net_usdt': -0.09242639999999996}, 'TREND_DOWN': {'trades': 8, 'net_usdt': -0.10806317000000001}, 'TREND_UP': {'trades': 5, 'net_usdt': 1.01689746}}; hold-minute quantiles {'0': 15.0, '0.25': 45.0, '0.5': 120.0, '0.75': 300.0, '0.95': 480.0, '1': 480.0}; net R {'0': -0.8400612912013078, '0.25': -0.7773263000953051, '0.5': 0.2683567412509383, '0.75': 1.2845940380517051, '1': 1.4266634918629597}; forced-end exits {'trades': 0, 'net_usdt': 0, 'net_excluding_forced_usdt': 0.81640789}.

Weekly block interval {'low_usdt': -0.68553334775, 'high_usdt': 2.2649418075, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross 1.27241000 minus fees plus funding reconciles to net with residual 0.0000000092.

## LiquiditySweepReversalV1

Expectancy 0.041494208684210526; distinct active days 28; loss streak 6; exposure 2067.958933 USDT-hours; turnover 1683.016910; break-even extra bps/side 9.368770572839937; net excluding best3 0.199237.

Pairs {'BTC/USDT:USDT': 0.35434521, 'ETH/USDT:USDT': 0.09761197000000002, 'SOL/USDT:USDT': 1.12482275}; directions {'long': {'trades': 21, 'net_usdt': 0.09401587999999994}, 'short': {'trades': 17, 'net_usdt': 1.4827640500000001}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 25, 'net_usdt': 1.9642081699999998}, 'TREND_DOWN': {'trades': 4, 'net_usdt': 0.38438132}, 'TREND_UP': {'trades': 9, 'net_usdt': -0.7718095599999999}}; hold-minute quantiles {'0': 0.0, '0.25': 60.0, '0.5': 172.5, '0.75': 240.0, '0.95': 240.0, '1': 240.0}; net R {'0': -0.881508028720145, '0.25': -0.7588416086313446, '0.5': -0.013684553422686138, '0.75': 1.2162918954399762, '1': 1.5037264683175906}; forced-end exits {'trades': 1, 'net_usdt': 0.00407427, 'net_excluding_forced_usdt': 1.57270566}.

Weekly block interval {'low_usdt': -1.2122482165000001, 'high_usdt': 5.098987670749999, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross 2.58781000 minus fees plus funding reconciles to net with residual 0.0000000173.

## StructureAwareSweepV1

Expectancy 0.012246874285714285; distinct active days 5; loss streak 3; exposure 379.374260 USDT-hours; turnover 313.588620; break-even extra bps/side 2.733776499925283; net excluding best3 -0.611708.

Pairs {'ETH/USDT:USDT': -0.32873741, 'SOL/USDT:USDT': 0.41446552999999997}; directions {'long': {'trades': 5, 'net_usdt': 0.12570931999999996}, 'short': {'trades': 2, 'net_usdt': -0.039981199999999995}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 7, 'net_usdt': 0.08572811999999996}}; hold-minute quantiles {'0': 0.0, '0.25': 45.0, '0.5': 210.0, '0.75': 240.0, '0.95': 240.0, '1': 240.0}; net R {'0': -0.8028163217052077, '0.25': -0.6763645123400948, '0.5': -0.4685873404860741, '0.75': 0.7503450423939543, '1': 1.3397519671432838}; forced-end exits {'trades': 0, 'net_usdt': 0, 'net_excluding_forced_usdt': 0.08572811999999996}.

Weekly block interval {'low_usdt': -0.79767399, 'high_usdt': 1.395952800249999, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross 0.27474000 minus fees plus funding reconciles to net with residual 0.0000000068.

## SweepThinningControlV1

Expectancy 0.08604257727272725; distinct active days 19; loss streak 3; exposure 1153.634118 USDT-hours; turnover 968.943310; break-even extra bps/side 19.536093396423777; net excluding best3 0.601047.

Pairs {'BTC/USDT:USDT': 0.29877485, 'ETH/USDT:USDT': 0.77420902, 'SOL/USDT:USDT': 0.8199528300000001}; directions {'long': {'trades': 10, 'net_usdt': 1.1232711499999999}, 'short': {'trades': 12, 'net_usdt': 0.76966555}}; causal hourly regimes {'RANGE_LOW_ADX': {'trades': 13, 'net_usdt': 2.00605411}, 'TREND_DOWN': {'trades': 2, 'net_usdt': 0.6251517600000001}, 'TREND_UP': {'trades': 7, 'net_usdt': -0.7382691699999999}}; hold-minute quantiles {'0': 0.0, '0.25': 75.0, '0.5': 150.0, '0.75': 240.0, '0.95': 240.0, '1': 240.0}; net R {'0': -0.881508028720145, '0.25': -0.37280468660883315, '0.5': 0.2808922028799826, '0.75': 1.286070881460186, '1': 1.396596151034444}; forced-end exits {'trades': 1, 'net_usdt': 0.00407427, 'net_excluding_forced_usdt': 1.8888624299999999}.

Weekly block interval {'low_usdt': -0.34628569, 'high_usdt': 4.724751242749998, 'weeks': 13, 'draws': 2000, 'seed': 3103, 'method': 'IID calendar-week blocks, joint markets; descriptive stationarity assumption, few blocks, not significance proof'}. Gross 2.47693000 minus fees plus funding reconciles to net with residual 0.0000000047.

- Inspected DEVELOPMENT or shared-calendar TRANSFER, no untouched holdout.
- Calendar week resampling assumes exchangeable weeks; few dependent blocks, no statistical qualification.
- 15m requested-price fills, no queue/partial fills/historical spreads.
- UTC realized-loss halt excludes unrealized losses; full account daily halt NOT ENFORCED.
- Prospective evidence requires code/data freezes before outcomes; no automatic promotion.
