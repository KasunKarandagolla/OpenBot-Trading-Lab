# 09 — Triggering chart vision throughout the trade cycle

The **same specialist** can be summoned at different stages, with different inputs and strict authority. An agent is not needed to poll every bar; the Director/Researcher or owner calls it on demand or existing deterministic events request advisory research. Avoid blocking protective exits on model response.

| Stage | Invocation reason | Questions to answer | Authority |
|---|---|---|---|
| Cheap shortlist | 1–3 numerically promising instruments | Is structure coherent? Which playbook would be worth investigating? What would falsify the interpretation? | L0 research; no ranking gate in engine |
| Pre-entry WATCH | approaching defined VWAP/level or anticipated trigger | Does the developing structure fit continuation or failure? What opposing scenarios exist? | L0; can prepare context, cannot extend entry expiry |
| Trigger / limit order pending | new completed trigger, proposed price | Is location reasonable and is there a visible contradiction? Does provider latency make analysis obsolete? | L0; native admission unchanged |
| Filled position | requested by owner/Director, material verified structural event | Does the original thesis remain plausible? Has a new obstacle formed? | L0; no stop changes or force-exit |
| Partial profit / 1R favorable | point-in-time management review | Would partial, breakeven or structural trailing help? Counterfactual only, require future result measured later | L1 simulated only; no position adjustment |
| Invalidation / exit | deterministic thesis exit, stop or target | Can visible structure explain current exposure? Report deviation from frozen plan | L0; native exit executes independently |
| Post-trade | after final exit | Compare originally visible facts to later path, classify mistake vs valid losing trade, propose single future hypothesis | Review only; post-exit data cannot rewrite initial analysis |

## A management challenger must be PREDECLARED

The frozen policy remains baseline. Candidate management modifications (partial at verified obstacle, structural tightening after confirmed pivot, earlier time exit) should be versioned and run over identical trades with same native fill, fee and risk assumptions. Previous Lab partial/breakeven/trailing challenger performed worse on its matched cohort; don't adopt by intuition. Test long/short, minimum amounts, duplicate callbacks, pending exit orders, restart and partial fills with native Freqtrade capabilities where available; otherwise mark `NOT_EXECUTED_NATIVE`.

## Simulation and authority separation

A recorded `vision_suggested_move_stop` or `vision_suggested_take_partial` is **not** an actual order. L1 simulated outcome must be computed from predeclared deterministic counterfactual rules over available chronological data; not from an LLM imagining what price did. Each hypothesis keeps event ID, decision cutoff, full initial stop/target geometry, requested adjustment, actual capability to place order under native constraints, later path and cost treatment. If ambiguity in candle path, use conservative ordering and label it. Do not assume static chart images can reveal intra-bar fill priority.

## Operational failure behavior

If image API fails, vision reply is late, or MCP data are stale: original native trading protections continue; Director records `VISION_UNAVAILABLE`, no retroactive veto. For 5m entry expiry, process vision in pretrigger WATCH or after expiry as review, never give the model authority to stretch the window. No continuous 24/7 vision service or scheduled screenshots unless separately approved.
