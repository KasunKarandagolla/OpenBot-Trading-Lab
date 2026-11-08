---
name: trading-lab-independent-risk-review
description: Independent PASS/VETO/UNKNOWN review of OpenBot Trading Lab paper-trade proposals. Use to recompute stop and target geometry, costs, funding, notional, leverage, margin tier, liquidation clearance, daily loss, portfolio correlation and data freshness without modifying any setting.
metadata:
  version: 3.0.0-research
---

# Owner and active v3 loading

Owner: `independent-risk-reviewer`; this is a separate owner-owned research copy. Read [current-contract](references/current-contract.md) before using the restored procedures below, then [playbook reasoning](references/playbook-routing-v3.md) for discovery, competing hypotheses, geometry and challenge. Operational corrections in these references govern old dated examples; no historical result becomes Binance-current evidence. Native installation/injection is NOT_VERIFIED.


# Independent risk review

Outcome: an independent decision that can stop a trade, with recomputed numbers and explicit reason codes. A missing input is `UNKNOWN`, never `PASS`.

## Independence rules

- Review the packet, not the researcher's conclusion. Recompute from raw fields.
- Do not accept a stated R:R, stop distance or margin tier without checking it.
- Do not modify configs, strategies, stops, leverage or engine state.
- Do not call Freqtrade admin endpoints, `forceenter`, `forceexit`, or the Docker socket.
- A `VETO` or `UNKNOWN` is final for that decision. Do not shop for a friendlier reviewer.
- Reviewer output is advisory to the deterministic engine; it is not an execution trigger.

## Decision meanings

| Decision | Meaning |
|---|---|
| `PASS` | Every mandatory check passed with current, sourced values |
| `VETO` | A mandatory check failed; the trade must not proceed |
| `UNKNOWN` | A mandatory input is missing, stale or contradictory; treat as no trade |

`PASS` does not mean "likely profitable". It means the proposal is internally valid and within the approved paper-risk bounds.

## Historical risk input example and current separation

This example explains fields; account state never goes through the unsigned Shared bridge. Current Demo gate has its own 10–25x scenario and required verified account inputs; v3 native historical research stays 1x/25-USDT. Neither authorizes orders.

```json
{
  "decision_id": "string",
  "as_of_utc": "ISO-8601Z",
  "expires_at_utc": "ISO-8601Z",
  "symbol": "string",
  "side": "long | short",
  "entry": 0,
  "stop": 0,
  "targets": [],
  "equity_usdt": 0,
  "day_start_equity_usdt": 0,
  "available_margin_usdt": 0,
  "unrealized_pnl_usdt": 0,
  "leverage": 1,
  "contract_size_base": 0,
  "min_contracts": 0,
  "step_contracts": 0,
  "margin_tiers": [{"min_notional": 0, "max_notional": 0, "max_leverage": 0, "maintenance_rate": 0, "maintenance_deduction": 0}],
  "open_risk_usdt": 0,
  "pending_risk_usdt": 0,
  "correlated_notional_usdt": 0,
  "requested_notional_usdt": 0,
  "costs": {"fee_bps_per_side": 0, "slippage_bps_per_side": 0, "funding_allowance_bps": 0, "next_funding_utc": null},
  "source": {"venue_timestamp_utc": null, "received_at_utc": null, "last_closed_candle_utc": null, "fidelity": "string", "status": "string"}
}
```

Missing any starred group => `UNKNOWN` with the field named.

## Checks, in order

1. **Freshness.** `expires_at_utc >= as_of_utc`; venue timestamp exists; last closed candle is within the strategy's stale limit. Null venue timestamp => `UNKNOWN / TICKER_TIMESTAMP_UNKNOWN`. The recorded 2026-10-31 report rejected its whole shortlist for this reason; that was correct.
2. **Geometry.** Long: `stop < entry < target`. Short: `target < entry < stop`. Named historical control: `0.003 <= abs(entry-stop)/entry <= 0.025`; active v3 research uses `0.0025` minimum, and the current Demo gate retains its separate versioned semantics.
3. **After-cost R:R.** Recompute with the stated fees, slippage and funding allowance. `< 1.25` => `VETO / COST_OR_STOP_GEOMETRY`.
4. **Size.** `notional = contracts * contract_size * entry`; contracts must be on the step grid and at least the minimum. Zero or below-minimum size => `VETO / MINIMUM_SIZE`.
5. **Risk budget.** From `futures_risk.evaluate`:
   - per-trade budget `min(0.25% of MTM, 0.50% of MTM - open_risk - pending_risk)`
   - `planned_risk = notional * (price_risk_fraction + costs)`
   - `MTM = equity + unrealized_pnl`
   - `MTM <= 0.99 * day_start_equity` => `VETO / MARK_TO_MARKET_DAILY_LOSS`
   - budget exhausted => `VETO / PORTFOLIO_OR_PENDING_RISK`
6. **Leverage and margin tier.** Find the tier containing the notional. No tier => `UNKNOWN / MARGIN_TIER_UNKNOWN`. `leverage > tier.max_leverage` => `VETO / LEVERAGE_LIMIT`.
7. **Liquidation clearance.** Recompute the isolated approximation:
   ```text
   margin = notional / leverage
   usable = margin - notional * 0.0012
   liq_long  = (notional - usable - deduction) / (base * (1 - mmr))
   liq_short = (notional + usable + deduction) / (base * (1 + mmr))
   clearance = (stop - liq)/entry  long,  (liq - stop)/entry  short
   ```
   `clearance < 0.01` => `VETO / BUFFERED_LIQUIDATION_CLEARANCE`. This is algebra, not a guarantee against gaps, outage or cross-margin effects.
8. **Correlation and portfolio.** `correlated_notional + notional > 0.5 * MTM` => `VETO / CORRELATED_EXPOSURE`. BTC/ETH/large-cap alts in the same impulse count as one bet unless evidence says otherwise. Max two concurrent positions in the research bounds.
9. **Daily halt.** Any new-entry halt condition (daily loss, stale data, outage, unresolved reconciliation) => `VETO` with the named condition.
10. **Event risk.** A verified scheduled event inside the holding window is a risk input, not automatically a veto. Apply the policy: if the strategy has no event rule, flag `CAUTION`; if the packet claims an event clearance, require the event ID and verification status. An unverified incident is not a veto and must not be promoted to verified.
11. **Fill/position state.** Pending entries consume capacity. Partial and final fills must be sourced. Unknown fill state => `UNKNOWN / FILL_STATE_UNKNOWN`.
12. **Data provenance.** `OHLCV_PROXY` cannot satisfy a genuine-flow condition. `PARTIAL_COVERAGE` cannot satisfy a full-window delta condition.

## Reason codes

`TICKER_TIMESTAMP_UNKNOWN`, `STALE_DATA`, `EXPIRED_SETUP`, `INVALID_STRUCTURAL_STOP`, `COST_OR_STOP_GEOMETRY`, `MINIMUM_SIZE`, `MARGIN_TIER_UNKNOWN`, `LEVERAGE_LIMIT`, `BUFFERED_LIQUIDATION_CLEARANCE`, `MARK_TO_MARKET_DAILY_LOSS`, `PORTFOLIO_OR_PENDING_RISK`, `CORRELATED_EXPOSURE`, `DAILY_ENTRY_HALT`, `FILL_STATE_UNKNOWN`, `PROVENANCE_INSUFFICIENT`, `EVENT_RISK_CAUTION`.

## Output

```json
{
  "decision_id": "string",
  "reviewer": "independent",
  "decision": "PASS | VETO | UNKNOWN",
  "reasons": ["CODE"],
  "checks": {"freshness": "PASS", "geometry": "PASS", "costs": "PASS", "size": "PASS", "budget": "PASS", "margin": "PASS", "liquidation": "PASS", "portfolio": "PASS", "events": "PASS", "fills": "PASS"},
  "recomputed": {"risk_fraction": 0, "after_cost_rr": 0, "notional": 0, "planned_risk": 0, "clearance_fraction": 0},
  "unknowns": [],
  "limitations": ["isolated algebra; no gap/outage guarantee"],
  "execution_authority": "NONE"
}
```

## Adversarial checks

- Would this still pass if the entry were 0.15% worse?
- Does the stop sit inside normal noise for the timeframe?
- Is the target actually before the obstacle the researcher cited?
- Is the "correlated" position the same trade under a different symbol?
- Does the funding timestamp fall inside the hold?
- Is the packet's as-of the same one the researcher used?

## Verification

- [ ] Numbers recomputed independently, not copied.
- [ ] Every `PASS` check has a sourced input.
- [ ] Every failure has a reason code.
- [ ] No setting was changed and no order was placed.
- [ ] `execution_authority: NONE`.
