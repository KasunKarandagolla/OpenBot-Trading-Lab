# Public source decision — checked 2026-10-31 UTC, before historical acquisition

**Decision: ALLOW this bounded personal, noncommercial research sample via Gate's public REST API; no redistribution of raw data and no commercial clearance.** No Binance Vision archive is used.

Sources reviewed with the web connector (executor requests to the web pages returned 403; public API returned 200):

- https://www.gate.com/legal/user-agreement — sections 1.1, 2.4–2.6, 2.11 and 16.1–16.2. Covers API use; limited personal/noncommercial permission; retains IP rights; prohibits unauthorized scraping and restricted-location use. The owner's location and local law must permit access. Network reachability alone is insufficient. No assertion of owner-host eligibility is made.
- https://www.gate.com/gate-api — developer resources explicitly describe historical data for backtesting/data analysis, including USDT perpetuals.
- https://www.gate.com/docs/developers/apiv4/en/ — public market queries require no trading authentication; private trading routes are separate. Use official Freqtrade/CCXT rate limiting and stop on access denial/429. No scraping, geographic workaround, account, key or order.
- https://github.com/gateio/rest-v4 — official source documentation corroborates the public/private distinction and API base https://api.gateio.ws/api/v4.

Scope: BTC/USDT:USDT, ETH/USDT:USDT, SOL/USDT:USDT; 2026-07-26 inclusive to 2026-10-30 exclusive; 15m/1h futures and native funding/mark downloads. Local retention for this experiment; immutable hashes retained. No explicit market-data retention period was identified in the reviewed material. Retain locally only while needed; recheck terms before reuse. The agreement does not establish a transferable data license. Raw candles stay out of Git. Published output contains derived metrics, small scan observations and reproduction details only. Commercial use, redistribution or customer-facing service needs separate written rights review/permission.

This is a scoped engineering source-use assessment, not a conclusion about all jurisdictions or future trading use. No paid service. User authorized this real-data research session explicitly.

Other venue probes: Binance fapi exchangeInfo HTTP 451; Bybit instruments HTTP 403; OKX instruments/docs/terms HTTP 403. These sources were not used. Gate and Bitget public metadata HTTP 200; Gate selected after source review. Kraken futures metadata HTTP 200, not selected. No history downloaded from rejected candidates.
