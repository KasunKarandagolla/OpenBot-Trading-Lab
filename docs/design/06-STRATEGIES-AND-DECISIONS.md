# 06 — Strategies, Decision Rules and Research-to-Paper Promotion

## Why one strategy first?

We need to identify **which mechanism**, if any, adds value. Running VWAP, ICT, profiles, trends and order-flow as an opaque ensemble would make failures impossible to diagnose. Start with a reproducible benchmark and **at most one challenger**.

## Proposed playbook A — simple trend baseline

**Research hypothesis (not validated):** trend-following entries after controlled pullbacks might outperform random/time-matched exposure on sufficiently liquid futures over a defined horizon.

**Inputs:** completed 1h trend context, completed 15m structure, completed 5m trigger, price/volume, ATR; spread if a genuinely observed source exists.

**Exact strategy definition is deliberately unapproved.** In Session 2, freeze numerical parameters and operational choices in a preregistration *before* opening evaluation outcomes:

- Market list, long/short eligibility, session/timezone, timeframes and indicator parameters.
- Entry: what is a pullback and what precisely counts as a confirmed reclaim.
- Stop: structural/ATR rule fixed *at the signal*, floor/ceiling in ticks and invalidation.
- Exit: timeout/ROI/stop and whether any partial profit or trailing behavior exists.
- Cost model, funding assumption, max concurrent trades, no-entry periods, stale-data guards and cooldown.
- Whether a signal may retry an unfilled order; one clean decision path, not discretionary re-entry.

**Reason for not writing numerical parameters here:** inventing EMA periods, RSI thresholds or 2R targets before hypothesis comparison would pretend that we had qualified them. The Session 2 strategy card must contain executable values and get versioned.

## Proposed playbook B — VWAP continuation challenger

A separate, controlled variation could test session-VWAP reclaim **only if** its anchor, typical/close price convention, market regime and entry/stop logic are frozen. VWAP's popularity is not evidence of profitability. Do not add SMC and order flow simultaneously; they are separately testable context layers.

**SMC liquidity-sweep reversal** is an alternative research hypothesis if the baseline is structurally unsuitable, not a third automatically deployed strategy. Old M4 work is not qualified; importing it would violate the 'no unearned complexity' reset.

## Strategy card (mandatory release artifact)

Each strategy has `id`, `version_sha`, `hypothesis`, `eligible_symbols`, `source_rights`, `timeframes`, `warmup_bars`, `indicators_and_parameters`, `known_at_semantics`, `entry_long`, `entry_short`, `stop`, `target/exit`, `timeout`, `max_risk`, `allow_reentry`, `fee_scenario`, `funding_scenario`, `fill_model`, `negative_controls`, `evaluation_split`, `test_run_id`, `owner_decision`.

**A strategy must be deterministic:** two replays of the same version and data should produce the same orders and exit reasons. ChatGPT/OpenBot may propose hypotheses; it cannot change a deployed policy ad hoc based on news, emotions or its own predictions.

## Decision tree

```text
DATA / LICENSE OK?
  No -> NO_TRADE(SOURCE_OR_RIGHTS)
  Yes
  |
CLOSED-BAR / CAUSAL FEATURES READY?
  No -> NO_TRADE(STALE_OR_MISSING)
  Yes
  |
FROZEN PLAYBOOK SAYS ENTRY?
  No -> NO_TRADE(NO_SETUP)
  Yes
  |
COST/STOP/FILL/AVAILABLE RISK ACCEPTABLE?
  No -> NO_TRADE(COST_RISK_OR_PRICE)
  Yes
  |
OPERATING MODE = PAPER, STRATEGY HASH OWNER-APPROVED?
  No -> NO_TRADE(NOT_AUTHORIZED)
  Yes -> FREQTRADE SIMULATED ENTRY / MISSED FILL
```

## How to avoid 'AI cherry-picking'

OpenBot must not inspect future outcomes then 'choose' what strategy would have traded yesterday. Offline strategy selection is a separate documented research comparison; paper strategy is frozen before new observations. If agents propose modifications, save as a new **unqualified** version; test on new/appropriate data without reusing a contaminated holdout.

## Economic qualification ladder

1. **Unit correctness** on deterministic fixtures; verify known-at timestamps and indicator parity.
2. **Development discovery** of plausible opportunity geometry, including costs and nonfills.
3. **Frozen evaluation** on untouched chronological data, with all attempted versions and exclusions recorded.
4. **Cost-stress and sensitivity checks**: maker/taker fees, spread, slippage, funding, worst plausible fills, fewer trades, independent days/market components.
5. **Forward paper** with frozen strategy and real operating issues recorded.

'Profitable proven' is **not** a label available merely after L1/L2. If no qualifying, adequately powered dataset exists, output INSUFFICIENT_EVIDENCE, not GO.

## Paper strategy activation

Owner reviews the exact code hash, configuration hash, data source rights and risk rules, then explicitly selects one approved strategy for **dry-run only**. Operator starts Freqtrade with that configuration. No agent writes `user_data/strategies`, changes config or calls a Freqtrade API that can enter trades during an ongoing run. Strategy switching stops/resets the paper run under a documented change procedure.