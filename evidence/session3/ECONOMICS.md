# Native economic results — Session 3

All results are historical research on previously studied Binance data. Nothing is activated. Each row is a separate portfolio; do not add overlapping rows.

| Run | Fills L/S | Net USDT | Extra 10 bp/side | Max native drawdown USDT |
|---|---:|---:|---:|---:|
| final-w1-breakout | 8/6 | -1.63158549 | -2.29769646 | 1.63158549 |
| final-w1-breakout-touch | 8/7 | -1.73641530 | -2.45251411 | 1.73641530 |
| final-w1-early | 27/54 | -5.36415946 | -9.29872922 | 5.36415946 |
| final-w1-immediate | 11/7 | -0.80382485 | -1.67008296 | 1.12948546 |
| final-w1-reversal | 6/10 | -0.83997989 | -1.60625613 | 1.20327382 |
| final-w1-reversal-touch | 6/10 | -0.83997989 | -1.60625613 | 1.20327382 |
| final-w1-sweep | 13/22 | -3.34944843 | -5.00960843 | 3.38138141 |
| final-w1-trend | 25/24 | -1.04588113 | -3.45657765 | 2.14662037 |
| final-w1-vwap | 1/1 | 0.24681422 | 0.14720352 | 0.00000000 |
| final-w2-breakout | 4/7 | 0.46518605 | -0.06441358 | 0.50740842 |
| final-w2-reversal | 1/9 | 1.17423944 | 0.70702591 | 0.20667050 |
| final-w2-sweep | 17/8 | 0.72077216 | -0.47989015 | 0.73187007 |
| final-w2-trend | 17/31 | -2.37767433 | -4.70912595 | 2.37767433 |
| final-w2-vwap | 2/3 | -0.51022874 | -0.76029496 | 0.63541581 |

Two weekly runs per main strategy (wallet resets; no compounding):

| Strategy | Fills | Net USDT | Extra 10 bp/side | Judgment |
|---|---:|---:|---:|---|
| BreakoutAcceptanceRetest | 25 | -1.16639944 | -2.36211004 | REJECTED_UNDER_TESTED_ASSUMPTIONS |
| SweepReclaimReversal | 26 | 0.33425955 | -0.89923022 | UNQUALIFIED_COST_FRAGILE |
| TrendPullbackBaselineV1 | 97 | -3.42355546 | -8.16570360 | REJECTED_UNDER_TESTED_ASSUMPTIONS |
| VWAPTrendContinuationV1 | 7 | -0.26341452 | -0.61309144 | REJECTED_UNDER_TESTED_ASSUMPTIONS |
| LiquiditySweepReversalV1 | 60 | -2.62867627 | -5.48949858 | REJECTED_UNDER_TESTED_ASSUMPTIONS |

Native `ledger.json`, `orders.json`, `terminal.json`, `summary.json`, ZIP export and independent source-arithmetic audit are retained for every run. Challenger R uses the actual fill and frozen structural stop. Controls have separate `control-initial-bound-r.json`; their custom plan is not reconstructed from an incomplete export.

The second reversal week is positive. The combined reversal research result turns negative with 10 bp extra per side. The breakout retest loses overall; its immediate-entry comparator loses less in week one. The early-reclaim reversal loses substantially more. These are development observations, not evidence of edge or a recommendation to trade.

Historical metadata use a later public snapshot; actual historical account fee tiers, book spread, queue, impact, exact settlement mark and real partial fills remain unqualified. Funding events are independently recomputed from pinned sources using (actual entry fill, exit] and same-hour mark opens. No native original Risk receipt exists.
