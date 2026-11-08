---
name: trading-lab-trade-geometry-management
description: Entry, invalidation, stop, target and management research for OpenBot Trading Lab. Use to build cost-aware trade geometry, choose between fixed/partial/breakeven/trailing management, and reject setups that fail after-cost reward or structural logic.
metadata:
  version: 3.0.0-research
---

# Owner and active v3 loading

Owner: `trading-lab-market-researcher`; this is a separate owner-owned research copy. Read [current-contract](references/current-contract.md) before using the restored procedures below, then [playbook reasoning](references/playbook-routing-v3.md) for discovery, competing hypotheses, geometry and challenge. Operational corrections in these references govern old dated examples; no historical result becomes Binance-current evidence. Native installation/injection is NOT_VERIFIED.


# Trade geometry and management

Outcome: a complete, cost-aware plan that can be rejected mechanically, plus a management hypothesis that is compared against doing nothing.

## Geometry contract

Every plan states:

```json
{
  "side": "long",
  "reference_price": 0,
  "entry": {"type": "LIMIT | MARKETABLE_LIMIT | NONE", "min": null, "max": null, "deviation_limit_fraction": null},
  "stop": 0,
  "stop_basis": "structure + buffer",
  "targets": [{"price": 0, "fraction": 0, "basis": "level"}],
  "risk_fraction": 0,
  "reward_fraction": 0,
  "after_cost_rr": 0,
  "expiry_seconds": 300,
  "max_hold_hours": 8,
  "costs": {"fee_bps_per_side": 0, "slippage_bps_per_side": 0, "funding_allowance_bps": 0}
}
```

## Stop rules

- The stop comes from invalidation, not from a preferred dollar amount. Long: below the swing/bar low that would disprove the setup, minus a buffer. Short: above the high, plus a buffer.
- Frozen examples: `stop = low - 0.2*ATR14` long, `high + 0.2*ATR14` short.
- Acceptable risk fraction of price: `0.003` to `0.025` in the frozen research. Outside means `COST_OR_STOP_GEOMETRY`.
- Never widen a stop after entry. Never average down. `position_adjustment_enable` is false in the research config.
- If the structural stop and the risk budget disagree, reduce size or skip. Do not move the stop.

## Entry rules

- Trigger on a completed bar; the signal bar's close is the earliest usable reference.
- Limit entry may deviate at most `min(0.0015, 0.25*ATR/ref)` from reference in the frozen Session 2 callback.
- If price has moved beyond the deviation before the order fills, no fill. Do not chase.
- Expiry is explicit (300 seconds in the frozen research cards). An expired setup is `REJECT`, even if the pattern still looks valid.
- Frozen controls retain their entry rules. Separately declared BACKTEST market-entry comparators are permitted research variants, with explicit next-bar timing and friction stress; they do not activate trading.

## Cost-aware reward/risk

```text
cost_fraction = fee_in + fee_out + slippage_in + slippage_out + funding_allowance
net_risk   = abs(entry - stop)/entry + cost_fraction
net_reward = abs(target - entry)/entry - cost_fraction
after_cost_rr = net_reward / net_risk
```

- Frozen acceptance: `after_cost_rr >= 1.25`.
- The Session 2 cost allowance is `.0012 + .002 + .0003` = 0.0035 (fees + assumed friction + adverse funding) per notional.
- The bonus study used 0.06%/side fees plus actual signed funding, then stress-tested +10 bp/side.
- A 2R gross target is not 2R net. Show both.

## Target rules

- Prefer a real obstacle: prior swing, prior day/session high/low, VAH/VAL, POC. The frozen planner takes the nearest opposing level and uses the 2R fallback only if no level qualifies.
- Target must be before the nearest known opposing obstacle, not beyond it.
- If the nearest obstacle makes `after_cost_rr < 1.25`, the setup is rejected; do not delete the obstacle.
- Funding is not a target adjustment. It is a cost and a timing risk.

## Management comparison

Do not assert that partials, breakeven or trailing "reduce risk" without a matched comparison. Use the same entries, same data and same costs:

| Policy | Rule | Compare against |
|---|---|---|
| M0 | Fixed stop and target, no intervention | Baseline |
| M1 | Partial at a defined R, remainder to target | M0 |
| Breakeven | Move stop to entry after a defined R | M0 |
| Trailing | ATR or structure trail after a defined R | M0 |

Record per matched trade: net before/after, extra fees, earlier harmful exit, reduced loss, reduced winner, saved profit, unmatched entries.

Real evidence (bonus `management-comparison.json`):

- 9 matched trades; M1 vs M0 delta `+0.402632` USDT.
- 1 earlier harmful exit, 1 reduced loss, 1 reduced winner, 1 saved profit.
- Extra fees `0.000243` USDT.
- `M0_unmatched: 0`, `M1_unmatched: 0`.
- The experiment was a separately registered available-opportunity test because the frozen integrated policy abstained.

This is a small, mixed sample. It supports "management changes outcomes and can help or hurt", not "partials are better". A management rule is only accepted with a matched sample, cost accounting and a stated failure case.

## Fill reality

- Native candle backtests assume requested-price fills; they do not prove queue position or real partial fills.
- `fill_limit` in the evidence: "Native candle partial fills tested mechanically; no actual exchange queue or partial-fill history."
- Pending entries consume capacity even before a fill.
- An unfilled limit is a real outcome and belongs in the ledger. Do not silently convert it to a fill at a better price.

## Management failure modes

- Stop moved away to avoid a loss.
- Partial taken so small that fees dominate.
- Breakeven stop hit by normal noise before the thesis resolves.
- Trailing stop calibrated to the wrong timeframe.
- Target removed because it was "about to break".
- Re-entry after a stop without a new setup ID.

## Verification

- [ ] Stop has a structural reason and a buffer.
- [ ] Active v3: `0.0025 <= risk_fraction <= 0.025` or explicit rejection. The 0.003 minimum above is the named historical control only.
- [ ] `after_cost_rr >= 1.25` using the stated cost model.
- [ ] Target is before the nearest opposing level.
- [ ] Expiry and max hold are explicit.
- [ ] Management comparison is matched and includes harmful exits and extra fees.
- [ ] No claim of real fills from a candle simulation.
