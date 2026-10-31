# LiquiditySweepReversalV1 — frozen research card

Hypothesis: a completed failed breakout beyond a known prior range may mean revert in weaker trend regimes.

Prior20 completed-bar rolling low/high, shifted1. Long: low below priorLow by[0.1,1]ATR, close>priorLow; lower wick>=1.5*max(abs(close-open),0.1ATR); relative volume>=1.2; hourly ADX<=30. Short: high above priorHigh by[0.1,1]ATR, close<priorHigh, upper wick same threshold. Stop low-0.15ATR long/high+0.15ATR short; max holding exit request4h. No retrospective pivots. OHLCV breakout/rejection is not proof of stop orders or liquidation clusters. Otherwise NO_SETUP, INVALID_OR_STALE_DATA or COST_OR_STOP_GEOMETRY; callback rejection reasons preserved.

## Shared execution and risk contract

Version1.0.0, development research only. Gate BTC/ETH/SOL USDT perpetuals, 15m completed bars; 240bar startup including closed1h EMA20/50, ADX14. Hourly open H is usable by the 15m signal closing H+1h; native informative merge. Positive finite OHLCV, contiguous recent21 intervals, valid hourly context no older45minutes. ATR14/close in[0.001,0.025]. Prior20 volume denominator excludes current bar. No inference of real aggressor delta or liquidations.

Trigger is completed signal close, known at date+15minutes. Custom limit reference is that close; admit rates only within min(0.15%,0.25ATR/reference). Five minute expiry from signal availability; native pending-order expiry5minutes; no repricing, retries only on a newly independently valid signal. Invalid/stale geometry blocks sizing/admission. Native15m fills are model-limited and cannot prove five minute queue execution or partial fills.

Stop beyond signal high/low with strategy buffer; allowed adverse entry-to-stop fraction[0.003,0.025]. Freeze geometry after actual fill; native emergency stop3% remains if unavailable, followed by geometry_unavailable exit request. Native custom ROI requests net ratio2*initial price-risk (fee-adjusted ROI execution is native); holding clock begins trade.open_date_utc (native order opening may precede fill, so conservative earlier timeout). No DCA/pyramiding/trailing. Cooldown2bars. Tick/quantity rounding and minimum stake use official engine; do not round up position size to spend risk.

Wallet1000 USDT, leverage1, max2/one per symbol, initial stake<=25. Sizing loss per notional = stop_fraction +0.0012 fees +0.002 assumed roundtrip friction +0.0003 adverse funding allowance. Reject if target_roi/(stop_fraction+costs)<1.25. Initial modeled ceilings2.5/trade and5 aggregate; admission reserves3% emergency stop+costs, giving <=0.8375 per25 stake /1.675 for two. Gaps/outages/funding beyond allowance can exceed modeled loss. Unknown sizing returns0, with admission independently checking notional so native exception fallback cannot bypass cap.

UTC closed-trade net sum<=-10 blocks new entries; error fetching state blocks entries. This realized-loss rule is NOT an exact account mark-to-market daily halt. Native SQLite holds paper trade state; process failure pauses management. Neither challenger is approved/selected for persistent paper; guard rejects paper trade commands. Baseline remains the only prior paper selection. No automatic promotion.

Cohort: exact Session1 July26–October30 data, July30–October30 evaluation end exclusive. Entire cohort is inspected DEVELOPMENT data; no independent holdout. Fees0.06%/side; actual native funding; extra5/10/20bp per side sensitivities subtract turnover costs without refilling or changing drawdown. No threshold optimization.
