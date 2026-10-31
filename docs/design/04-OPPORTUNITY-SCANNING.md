# 04 — Cheap-to-Expensive Opportunity Scanning

## Objective

The scanner optimizes **attention and computation**, not a standalone trading edge. It should reduce the universe without excluding so many situations that the strategy cannot produce a valid independent sample. Every filter must be versioned and tested.

## Four-stage funnel (planning figures, not promises)

| Stage | Candidate count example | Existing weapon | Decision |
|---|---:|---|---|
| A: liquidity/eligibility | 100–200 → 10–20 | Freqtrade pairlist handlers + CCXT ticker metadata | Eligible/rejected with reasons |
| B: context | 10–20 → 5–10 | TA-Lib/VWAP/trend indicators | Context and regime report |
| C: strategy | 5–10 → 0–3 | Fixed playbook + cost/risk rules | Qualified/rejected setup |
| D: paper execution | 0–3 → 0–1 | Freqtrade dry-run | Deterministic simulated order/no trade |

The broad screening universe and candidate counts are proposed only; a real market may yield **zero**. Start with a small static whitelist for the install test; dynamic scanning is earned after accurate pairlist and data tests.

## Default selection pipeline to prove

1. **Exchange/market identity:** supported USDT-margined perpetual; active status; exclude unsupported settlement/listing/delisting states.
2. **Liquidity:** 24h quote volume above a *versioned, tested* floor; no hardcoded volume guarantee from last-24h figures.
3. **Freshness and cost:** current bid/ask if available, max spread proportional to strategy stop; if unavailable **cannot claim spread passed**.
4. **Volatility:** reject abnormally dead or explosive markets under a versioned rule.
5. **Readiness:** enough closed candles for VWAP/ATR/context; exclude incomplete, late or unverified feeds.
6. **Capacity:** max concurrent positions, concentration and conflicts; selected symbols might already have paper positions.
7. **Optional regime interest:** trend/pullback or range/reversal; do not fit parameters to the evaluation set.

Useful ready-made handlers to investigate: `VolumePairList`, `SpreadFilter`, `VolatilityFilter`, `AgeFilter`, `DelistFilter`, `PrecisionFilter`, `StaticPairList`. Confirm which are supported in the pinned Freqtrade release, exchange and futures mode. Do not build a 200-pair CCXT polling service unless the built-in handlers materially fail.

## Context and strategy selection

**Key rule:** the OpenBot Director does not place bids based on an LLM 'confidence' number. Screening produces structured measurements. A deterministic *versioned* strategy uses closed bars and measured thresholds to produce an entry signal. Agent notes may summarize why a symbol deserves human research attention; they cannot override the signal gate.

**Initial deployment:** one active playbook at a time. Research may compare alternative candidates offline but not launch many active strategies concurrently. A single strategy can process multiple approved pairs without agents computing values repeatedly.

## Snapshot example (illustrative, not a market quote)

```json
{
  "run_id": "scan-synthetic-001",
  "as_of_utc": "2026-10-31T09:00:00Z",
  "environment": "SYNTHETIC",
  "universe_size": 40,
  "shortlisted": [
    {"symbol": "BTC/USDT:USDT", "data_status": "READY", "reason_codes": ["LIQUID", "SPREAD_ASSUMED_SYNTHETIC"], "not_trade_signal": true},
    {"symbol": "ETH/USDT:USDT", "data_status": "READY", "reason_codes": ["TREND_CONTEXT"], "not_trade_signal": true}
  ],
  "rejected_count": 38,
  "source": "synthetic_fixture",
  "verified_for_live": false
}
```

## Scan regression cases

- Zero eligible symbols; all symbols stale; duplicated symbol representations; delisted/perpetual/spot confusion.
- Changing tomorrow's pair list must not change yesterday's backtest shortlist.
- Missing spread must yield UNKNOWN, not a favorable spread.
- Scanner runs twice on same snapshot: same shortlist and ordering if configured deterministic.
- Frequent refresh cannot cause changing strategy activation or position oscillation.
- Rate limits and market API failures do not multiply retries or cause an OpenBot direct trading API call.

## Anti-patterns

No simultaneous full depth + tick + news + ICT scoring for hundreds of markets. No unlimited high-volume coin scans for AI 'opportunities' that a frozen strategy cannot use. No lookahead through future daily ranking; no random change of pair selection rules while comparing strategy results.
