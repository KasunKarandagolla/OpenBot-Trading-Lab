# 01 — Hosted chart acquisition, modality, identity and synchronization

## What an accepted chart packet must establish

- Exact **venue/contract**: e.g. `BINANCE:BTCUSDT.P`, verified as Binance USD-M linear USDT perpetual, not spot/index/another exchange. If chart source symbol differs from execution venue, label it as cross-venue context, never native execution evidence.
- Interval and anchor: 4H/1H/15m/5m; candle opening-time convention, exchange/chart timezone, last COMPLETE candle, whether a live partial candle is drawn, and requested visual range.
- `chart_source`, `tool_name`, `provider_request_id` (if provided), `request_utc`, `receipt_utc`, `provider_event_utc` (if provided), image URL expiration when known, image SHA256, size/dimensions, indicator parameters, known chart delay/quote type, overlay visibility.
- Unknown timestamps are JSON `null`; never serialize `UNKNOWN`, empty text, a local timezone guess, or a receipt timestamp copied into the request/event field. Enforce JSON Schema date-time formats at validation time. A research candidate is ineligible until decision time, request time, receipt time, and last-closed-bar time are valid and available.
- Model image delivery: record that a tool actually passed accessible pixels (binary or accessible attachment) to the vision inference. An image URL or an MCP success message **is not proof** the model saw pixels. A URL-only negative control must make no visual claims.
- Asynchronous captures: use actual end-to-end window (first request start to last response receipt), not just each individual 4–6-second call. If numerical quote retrieved minutes later, never retro-stamp it as an earlier quote.

## Historical provider options and current tradeoffs

The CHART-IMG pilot below is historical; its advertised quotas are not verified current offers. Default to the already implemented local renderer and no paid services.

- CHART-IMG Basic: publicly advertised 50 requests/day, 1/sec, 800×600, 3 max parameters, watermarked; confirm actual account limits. v2 advanced screenshot or prebuilt MCP wrapper. No guaranteed historical time travel.
- Cross-venue derivatives read-only MCP can supplement a chart; it cannot make the screenshot match Binance USD-M tick-for-tick.
- The original hosted-only pilot restriction is historical. Reuse the existing Matplotlib renderer; no second renderer or browser automation is needed. Existing previously archived entrance charts may be reviewed as historical **if and only if** freeze integrity passes.

## Rendering rules

Ask for a clean price/structure chart first, then optionally a second overlay panel if budget and task justify it. At 800×600, require only visible indicators; never claim hidden or partially loaded studies. EMA20/EMA50 formula, warmup, source candles, session VWAP anchor, volume semantics and forming-bar inclusion may differ across chart and Freqtrade. Verify the source of any chart value used quantitatively.

## Historical cutoffs

A genuine historical cutoff image must show no candle after decision time. Future price paths and outcomes are forbidden inputs to pretrade judgments. If hosted provider only returns today's chart: use it for real-time shadow analysis; do not call it historical backtesting. For legacy casebook, archive existing cutoff screenshots separately from `*-path.png` outcome panels and inspect them for post-cutoff leakage before use.

## Failure handling

Unknown/wrong symbol, rate limit, expired URL, hidden overlays, missing pixels, model text-only mode, ambiguous candle timestamp, asynchronous multi-TF window: return a labelled missing-data reason; don't silently swap instruments/providers. Credentials only through secure configuration, never in evidence packets, prompts, URLs or git.
