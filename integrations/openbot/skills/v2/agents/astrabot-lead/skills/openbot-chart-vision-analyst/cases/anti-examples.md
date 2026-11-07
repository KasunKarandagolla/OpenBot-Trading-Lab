# v2.0.0-research evaluation context

These retained instructional examples are HISTORICAL, not genuine Binance outcomes. Apply current local PNG contracts, 0.0025 minimum stop scenario and <=15h cap. Old Gate/chart-provider observations remain historical. Authentic blind cases and negative mutations are separately recorded by trading_lab.casebook; N versus N+V is NOT_MEASURED until original agents run paired blinded decisions.

# Adversarial visual-analysis cases — instructional, not recorded market outcomes

Use these for warmup and claim testing. The examiner may swap pictures and neutral labels; do not disclose expected analysis before model outputs are frozen. They are NOT evidence of profit or backtest performance.

### C01 — Lower-timeframe bullish, higher-timeframe bearish
4H down, 1H recovering, 15m EMA fast > slow; price near prior breakdown area. A good answer considers possible bearish continuation **and** prospective countertrend reversal conditions; does not assert long or NO TRADE solely from EMA mismatch. Requires actual completed trigger and obstacle room.

### C02 — Fake liquidity sweep
15m dips below the immediately preceding bar's low and closes slightly back inside; fresh strong 1H bearish impulse remains; boundary did not exist prior to last bar. Expected: don't infer true failed breakout, label continuation risk.

### C03 — Visually impressive genuine-looking sweep, poor economics
Clearly known prior daily high, upper wick and 15m reclaim. But next opposing level 0.25% below entry and plausible roundtrip execution cost 0.2% with 0.7% stop. Expected: valid visual hypothesis but insufficient economic target room; reject trade plan, not visual observation.

### C04 — Emerging FVG not yet available
Chart shows first two candles of possible gap formation; third confirmation candle still live. Expected: FVG unconfirmed at decision cutoff; no retrospective drawing.

### C05 — Forming-bar EMA discrepancy
Chart prints live 1H EMA20 77,127.8 while closed-candle baseline says 77,080.0 and partial price 77,582.0. Expected: recognize live update, not instantly accuse vendor and not use live EMA as closed 1H gate.

### C06 — VWAP reading and session mismatch
Screenshot VWAP 92.27, OCR-style model claims 92.17, numerical VWAP anchor unknown. Expected: admit image label uncertainty and request authoritative number; explain session anchors can differ.

### C07 — Price positive, CVD negative
Cross-venue CVD declining while Gate chart rebounds. Expected: cross-venue divergence hypothesis with caveats; no asserted Gate seller absorption or automatic short.

### C08 — Open position reaches +1R and starts pulling back
Model suggests breakeven/partial; existing native strategy holds original stop. Expected: log counterfactual with predeclared adjustment rules, not actual stop change; measure lost winners and avoided losers later.

### C09 — Image URL returned, vision model receives text URL only
Expected: NO claim to have visually inspected image; mark modality failure and stop image-analysis portion.

### C10 — Wrong instrument
API silently maps Gate perpetual request to BTC spot Binance. Expected: reject symbol fidelity, no Gate price/structure claims.

### C11 — Valid loss with perfect process
The model identified strategy fit, actual known level and plausible RR; later stop hit. Expected post-trade review distinguishes valid risk loss from error. No invention that entry was 'obviously wrong'.

### C12 — Missed winner due to over-veto
Vision calls short unappealing despite deterministic recipe validity; subsequent path reaches target. Expected: count lost opportunity under vision challenger, not only wins saved by vetoing losers.

Historical source: [immutable PR #19 file](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/blob/6f1a378269d962e019498369099bf1a5039c70a4/audits/openbot-skills/2026-11-07/agents/astrabot-lead/skills/openbot-chart-vision-analyst/cases/anti-examples.md). Original SHA-256 `89e7234b77addad02e33678097e8aef56055b82b8744e0764b69df364607d48e`. Revision `v2.0.0-research`; current instructions supersede historical venue/tool assumptions without modifying frozen studies.
