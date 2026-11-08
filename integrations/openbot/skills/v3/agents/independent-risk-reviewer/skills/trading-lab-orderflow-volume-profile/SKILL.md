---
name: trading-lab-orderflow-volume-profile
description: Genuine executed-trade order flow, footprint and volume-profile interpretation with strict source-fidelity labels for OpenBot Trading Lab. Use whenever a packet mentions order flow, delta, CVD, footprint, POC, value area, HVN/LVN or absorption, and to reject OHLCV proxies dressed as real flow.
metadata:
  version: 3.0.0-research
---

# Owner and active v3 loading

Owner: `independent-risk-reviewer`; this is a separate owner-owned research copy. Read [current-contract](references/current-contract.md) before using the restored procedures below, then [playbook reasoning](references/playbook-routing-v3.md) for discovery, competing hypotheses, geometry and challenge. Operational corrections in these references govern old dated examples; no historical result becomes Binance-current evidence. Native installation/injection is NOT_VERIFIED.


# Order flow and volume profile

Outcome: a flow/profile statement whose fidelity is provable from the source, or an explicit `UNAVAILABLE`. Never a confident story built on candle colour.

## Fidelity ladder

| Level | Source | Permitted claims | Forbidden claims |
|---|---|---|---|
| `TRADE_PRINTS` | Venue executed trades: price, size, timestamp, aggressor side | Signed volume, delta, CVD, footprint, absorption at a price | Completeness unless start/end and sequence continuity are proven |
| `ORDER_BOOK` | Venue L2 snapshot/stream | Resting depth, imbalance, spread, book pressure | Executed volume, absorption that already happened |
| `OHLCV` | Aggregated candles | Total volume, range, candle body/wick | Buy vs sell volume, delta, footprint |
| `OHLCV_PROXY` | Profile or flow estimate from candles | A labelled approximation (e.g. typical-price volume-at-price) | "Volume profile", "POC", "value area" without the proxy label |

Promotion from one level to the next requires new source evidence, not a better narrative.

## Required provenance fields for `TRADE_PRINTS`

Every flow packet must state:

```json
{
  "symbol": "BTC/USDT:USDT",
  "venue": "binance",
  "endpoint": "public futures trades",
  "requested_from_utc": "ISO-8601Z",
  "requested_to_utc": "ISO-8601Z",
  "received_at_utc": "ISO-8601Z",
  "first_execution_utc": "ISO-8601Z",
  "last_execution_utc": "ISO-8601Z",
  "raw_sha256": "hex",
  "raw_rows": 0,
  "distinct_ids": 0,
  "duplicate_ids": 0,
  "contract_multiplier_base_per_contract": 0,
  "quantity_unit": "base asset after multiplier",
  "aggressor_semantics": "VALIDATED | UNVALIDATED | UNKNOWN",
  "coverage_status": "FULL_WINDOW | PARTIAL_COVERAGE | UNKNOWN",
  "coverage_reasons": [],
  "signed_delta": null
}
```

Rules:

- `aggressor_semantics: UNVALIDATED` forces `signed_delta: null`. Do not use CCXT's sign convention as proof when the venue schema does not define taker mapping.
- A single bounded page is `PARTIAL_COVERAGE` even with zero duplicates. Missing trade-ID continuity means you cannot assert a complete window.
- Quantity semantics are venue-specific and mandatory. Binance USD-M kline base and quote volumes are published separately; do not apply a Gate multiplier. Raw contract counts require their own multiplier. The recorded Gate BTC proof used `0.0001 BTC/contract`.
- `received_at_utc` is not `last_execution_utc`. A recent download of old prints is stale flow.
- Never infer liquidations from prints unless the venue flags them.

## Worked rejection (real evidence)

The 2026-10-31 Gate BTC sample contained 62 distinct prints, 11.6346 BTC, zero duplicate IDs, and a 56-second execution span. It still could not support delta:

- `aggressor_semantics: UNVALIDATED`
- `coverage_status: PARTIAL_COVERAGE`
- `buy_aggressor_btc: null`, `sell_aggressor_btc: null`, `signed_delta_btc: null`
- `strategy_feature_eligible: false`

The correct output is `UNKNOWN`, not "mild buying pressure". This is the reference example for every flow review.

## Genuine flow metrics (only when eligible)

- `delta = buy_aggressor_base - sell_aggressor_base` over a stated window.
- `CVD` is the cumulative sum of delta across contiguous windows; a gap resets or breaks the series, it does not interpolate.
- Footprint: bid/ask volume per price bin per window. Do not merge bins across different tick sizes.
- Absorption: heavy traded volume at a level with little price progress, measured against a stated window and ATR.
- Exhaustion: declining delta magnitude with continuing price trend, or divergence between price high/low and CVD.

All of these require complete coverage. Partial coverage supports only "observed prints", never "the market did X".

## Volume profile

Two distinct products:

1. **Genuine traded-volume-at-price** — requires `TRADE_PRINTS` with sizes and a defined window. Label `TRADED_VOLUME_AT_PRICE`.
2. **OHLCV typical-price proxy** — the repo's `advanced_features.volume_profile` uses `(high+low+close)/3` and candle volume over 96 bars, log bins of width 0.001, 70% value area. It must be labelled `OHLCV_TYPICAL_PRICE_PROXY_NOT_TRADED_VOLUME_AT_PRICE`.

Proxy rules from the frozen implementation:

- Use only the prior 96 completed bars; the signal candle is excluded.
- Profiles exist only when the 96-bar window spans exactly one day; otherwise `NaN`.
- POC is the highest-weight bin; VAH/VAL expand from POC until 70% of volume is covered, deterministic lower-price tie-break.
- HVN is a bin at or above the 80th percentile of bin weight; LVN at or below the 20th.
- `vp_known_at` is the row timestamp at/after which the profile is usable; never earlier.

Interpretation limits:

- POC/VAH/VAL are reference levels, not magnets or guarantees.
- A close above VAH is acceptance only if it holds on a completed bar and is not a one-bar wick.
- Thin LVN travel is a hypothesis about speed, not proof of a move.
- Do not combine a proxy profile with genuine delta and call the result "confirmed".

## Output block

```json
{
  "flow_fidelity": "TRADE_PRINTS | ORDER_BOOK | OHLCV | OHLCV_PROXY | UNAVAILABLE",
  "profile_fidelity": "TRADED_VOLUME_AT_PRICE | OHLCV_TYPICAL_PRICE_PROXY_NOT_TRADED_VOLUME_AT_PRICE | UNAVAILABLE",
  "window": {"from_utc": null, "to_utc": null},
  "coverage": "FULL_WINDOW | PARTIAL_COVERAGE | UNKNOWN",
  "metrics": {},
  "eligible_for_strategy": false,
  "reasons": [],
  "unknowns": []
}
```

## Verification

- [ ] Aggressor semantics are validated by venue documentation or a reproducible mapping test.
- [ ] Coverage boundaries and trade-ID continuity are addressed.
- [ ] Contract multiplier applied; units stated.
- [ ] `signed_delta` is null whenever side or coverage is unproven.
- [ ] Proxy profile carries its full label and cannot be cited as real volume-at-price.
- [ ] No liquidation, iceberg or institutional-intent claim without direct evidence.
