# 07 — Sniper-Style Entries, Paper Orders, Risk and Ongoing Management

## What 'sniper' means in this budget

**Selective, narrow, expiry-bounded entries—not nanosecond precision.** Freqtrade strategies are predominantly candle-driven; a 5m/1m rule plus typical bot loop does not guarantee sub-second execution. We aim for a repeatable, discriminating setup with measured fill assumptions, and skip a trade if price has moved away.

## Entry lifecycle

```text
WATCHING → SETUP_DETECTED → WAIT_CANDLE_CLOSE
     └────────→ INVALIDATED (bad data / setup disappears)
WAIT_CANDLE_CLOSE → PROPOSED_PAPER_ORDER
PROPOSED_PAPER_ORDER → RISK_PASSED → SUBMITTED_TO_PAPER_SIMULATOR
PROPOSED_PAPER_ORDER → NO_TRADE (spread, expiry, cost, stop, capacity)
SUBMITTED_TO_PAPER_SIMULATOR → FILLED_PAPER or TIMEOUT_UNFILLED
FILLED_PAPER → OPEN_PAPER → PARTIAL_EXIT? → CLOSED_PAPER
OPEN_PAPER → STOP / ROI_EXIT / THESIS_EXIT / MAX_TIME_EXIT
```

These are **product-facing logical states**. Freqtrade's actual order/trade object states must be mapped and tested; do not claim it exposes this exact enumeration.

## Pre-entry gate (all pass)

- Approved, versioned deterministic strategy; dry-run mode.
- Data are complete, closed, fresh; exact eligible futures symbol and correct tick/quantity units.
- Expected fill range specified; maximum deviation from identified signal; max age and one-shot expiry.
- Stop is on correct side, within configured min/max stop distance and risk budget.
- Fees, round-trip spread, conservative slippage and funding assumption do not destroy desired geometry.
- Portfolio has capacity; no duplicate same-symbol paper exposure if policy forbids it.
- Risk reviewer findings do not represent an actual capability to override core engine; reject via deterministic checks.

**If precise spread is required but only candles are available, the condition is UNVERIFIED and entry must be prohibited by that policy, or the policy must explicitly use an approved conservative friction assumption.** Do not silently set zero spread.

## Paper risk policy — owner to reaffirm

Proposed conservative defaults retained from legacy research as a **starting bound, not newly approved live policy**:

| Control | Proposed paper bound | Why / implementation note |
|---|---|---|
| Intended initial monetary loss | ≤0.25% of model equity / trade | Must size against entry→stop **plus expected adverse fees/slippage/funding**, not only candle distance |
| Aggregate intended loss | ≤0.50% of model equity | Two concurrent 0.25% risks maximum; concentration considered |
| Concurrent open paper positions | ≤2 | One per symbol; no averaging down / scale-in |
| Daily new-entry halt | 1% modeled account loss | Verify robust implementation; built-in protections may not enforce exactly this daily definition |
| Leverage | ≤2x isolated as proposed ceiling | Futures paper behavior and exchange semantics must be demonstrated; not a profit enhancer |
| Max holding time | 12h from first actual **paper fill**; aim exit by 11h55 | A custom timeout may be needed; clock must not reset on partial exits |
| Order expiry | Bounded and frozen per strategy | Skip after missed entry, do not chase |
| Trailing/partial exits | OFF initially unless mechanically tested | Complexity and per-fill fees need evidence |

**Important:** Freqtrade's out-of-box position-size, leverage and protection settings do not automatically prove every custom monetary-risk invariant above. Session 1/2 must demonstrate which controls are native, which are small wrappers and which remain unsupported. If exact constraints cannot be implemented, don't activate paper entries at risky sizes; use a tiny fixed synthetic stake for acceptance.

## How Freqtrade manages positions

Relevant documented mechanisms include `stoploss`, `minimal_roi`, `custom_stoploss`, `custom_exit`, `custom_roi`, `custom_entry_price`, `confirm_trade_entry`, `check_entry_timeout`, and optional `adjust_trade_position`. Implement the smallest necessary subset. Default disable `position_adjustment_enable` to avoid accidental repeated additions. Never make agent calls inside time-critical callbacks.

**Paper mode:** fills and stop behavior are simulated by the engine. Exchange-native protective orders are a separate live-only implementation matter; paper stops do NOT prove real stop protection. A process outage pauses paper management. The persistent trade DB may recover state but does not execute a trade while the process is off.

## Example trade (invented educational numbers)

- A closed candle at 12:05 UTC satisfies a frozen long setup.
- Permitted entry ≤100.10; stop 99.60; reference target 101.10; expected round-trip gross reward/risk ~2:1 before costs.
- A new quote or simulated engine fill above 100.10 → **cancel/skip**, rather than move stop or chase.
- If filled, paper size respects modeled loss budget and fees; manage stop, take-profit and max time through fixed strategy rules.
- If target and stop both appear within one coarse candle, record ambiguity and rerun with finer data or conservative ordering. Never automatically claim target first.

## No-fill/partial/restart rules

- **Missed entry:** count it separately in opportunity statistics; do not delete it to inflate win rate.
- **Partial fill:** supported actual paper/future-mode behavior to be confirmed; log partial quantity and risk recalculation if available. No assumption that historical candles establish partial fills.
- **Stop triggered while OpenBot offline:** OpenBot need not be running for Freqtrade to perform a paper exit; if the bot itself is stopped, it cannot do so.
- **Exchange/API/data error:** no new entry; notify; preserve trade state and investigate. No automatic script restart loop that blindly repeats a pending order.
- **Daily halt:** block new entries; consider owner/manual closure procedure for any paper positions, separately from entry-block logic.

## Future live trading (excluded)

Would require separate exchange credentials, authenticated owner authorization, exchange-side stops, submission idempotency, reconciliation, liquidation/mark/funding tests, and a single writer with secure host boundaries. No present design statement authorizes a `dry_run=false` switch or API `forceenter`.