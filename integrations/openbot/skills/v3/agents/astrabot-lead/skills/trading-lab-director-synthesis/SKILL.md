---
name: trading-lab-director-synthesis
description: Director synthesis, journaling and owner reporting for OpenBot Trading Lab. Use to reconcile researcher and risk-reviewer evidence, preserve NO TRADE, report opportunities and paper outcomes without overclaiming, and maintain a mistake and hypothesis ledger.
metadata:
  version: 3.0.0-research
---

# Owner and active v3 loading

Owner: `astrabot-lead`; this is a separate owner-owned research copy. Read [current-contract](references/current-contract.md) before using the restored procedures below, then [playbook reasoning](references/playbook-routing-v3.md) for discovery, competing hypotheses, geometry and challenge. Operational corrections in these references govern old dated examples; no historical result becomes Binance-current evidence. Native installation/injection is NOT_VERIFIED.


# Director synthesis and owner reporting

Outcome: a short, decision-useful brief in which every claim is attributable and no-trade is reported as a normal, successful outcome.

## Authority boundary

- No order placement, no leverage/config changes, no engine start/stop, no admin API, no Docker socket.
- Do not override a Risk Reviewer `VETO` or `UNKNOWN`. A researcher's enthusiasm is not an appeal.
- Do not present an agent recommendation as an executed trade.
- The deterministic engine is the safety layer. Your report describes; it does not authorize.

## Decision reconciliation

Before any owner-facing recommendation, build one row per decision:

| Field | Rule |
|---|---|
| Decision ID | Must match researcher and reviewer packets |
| As-of | All three packets use the same as-of; otherwise `STALE` |
| Researcher | TRADE / WATCH / NO_TRADE with thesis |
| Risk | PASS / VETO / UNKNOWN with codes |
| Fidelity | source label and freshness |
| Contradiction | NONE / CAUTION / INVALIDATES |
| Final | see table below |

| Researcher | Risk | Contradiction | Final |
|---|---|---|---|
| TRADE | PASS | NONE or CAUTION | `ELIGIBLE_FOR_PAPER_REVIEW` (not an order) |
| TRADE | PASS | INVALIDATES | `NO_TRADE` |
| TRADE | VETO | any | `NO_TRADE` |
| TRADE | UNKNOWN | any | `NO_TRADE` / `WATCH` with missing fields |
| WATCH | any | any | `WATCH` |
| NO_TRADE | any | any | `NO_TRADE` |

An `ELIGIBLE_FOR_PAPER_REVIEW` item still needs the deterministic engine and owner-approved runtime. Never write "trade placed".

## Contradiction handling

The Director does not average conflicting views into a confidence score. State:

1. What the researcher claims.
2. The strongest opposing evidence and its class.
3. Whether the reviewer's numbers agree.
4. Which premise fails, if any.
5. The decision and the exact condition that would change it.

If the researcher and reviewer disagree on a number, the reviewer's recomputation wins until the researcher shows the error. If both are unsupported, `UNKNOWN`.

## NO TRADE is a result

Report a zero-opportunity screen as success when the rules were applied correctly. Example: the recorded 2026-10-31 current report rejected its entire shortlist with `TICKER_TIMESTAMP_UNKNOWN`. The correct brief is "no eligible opportunity; all candidates lacked a venue timestamp", not "the scanner failed".

Do not pressure the team to find a trade because the report looks empty.

## Owner brief format

Keep it under one screen unless the owner asks for detail.

```markdown
# Trading Lab brief — <as-of UTC>

## Bottom line
One sentence: eligible for paper review / watch / no trade / operation blocked.

## Opportunities
| Symbol | Recipe | Final | Why | Expires |
|---|---|---|---|---|

## Risk and data
- Risk decisions: PASS x, VETO y, UNKNOWN z
- Stale/missing: ...
- Blockers: ...

## Positions and performance (paper only)
- Open: ...
- Closed since last brief: ...
- Net after modeled costs: ... (no profitability claim)
- Unfilled/expired: ...

## News and operations
- Scheduled events inside holding windows: ...
- Verified incidents: ...
- Unverified reports: ...

## What changed since last brief
...

## Next action
One concrete action with an owner if required.
```

## Performance reporting rules

- Separate gross and after-cost results.
- Include fees, funding, slippage assumption and sample size.
- Include unfilled and rejected opportunities; a fill-only ledger is misleading.
- Never annualize a small sample. Never call a positive sum "profitable" without an economic qualification.
- Use the repo's verdict vocabulary: `PROMISING BUT UNQUALIFIED`, `REJECTED UNDER TESTED ASSUMPTIONS`, `INSUFFICIENT OR UNAVAILABLE EVIDENCE`.
- Real reference: `VWAPTrendContinuationV1` +0.959708 USDT over 30 trades was still `PROMISING BUT UNQUALIFIED`; `LiquiditySweepReversalV1` -2.259367 over 86 trades was `REJECTED UNDER TESTED ASSUMPTIONS`. Quote both the number and the verdict.
- A strategy that turns negative at +10 bp/side is cost-fragile; say so.

## Journal

Maintain four ledgers, append-only:

1. **Decisions** — ID, as-of, inputs, researcher, reviewer, final, reason codes.
2. **Mistakes** — what was wrong, when discovered, affected decisions, correction.
3. **Missed opportunities** — setup seen, why not taken, what would have qualified it.
4. **Hypotheses** — proposed change, expected effect, test design, status.

Every journal entry needs a timestamp and a link to evidence. Do not rewrite history after an outcome; append a correction.

## Weekly operator record

- Uptime and stale-data minutes.
- Signals, eligible proposals, fills, nonfills, expiries.
- Paper P&L before/after modeled costs.
- Risk vetoes by reason code.
- Model calls and disk growth if exported.
- Manual interventions.
- Strategy/config hashes.

## Escalation language

| Situation | Owner message |
|---|---|
| Missing data | "No decision; X is missing/stale. No action." |
| Risk VETO | "Blocked by risk: <code>. No action." |
| Unexpected `dry_run=false` | "STOP. Non-paper configuration detected. Isolate the runtime." |
| Possible key exposure | "STOP. Preserve logs, disconnect, revoke externally." |
| Unverified incident | "Unverified report; not used for a decision." |

## Verification

- [ ] Final decision follows the reconciliation table.
- [ ] No VETO or UNKNOWN was overridden.
- [ ] Every number has an evidence ID and as-of.
- [ ] NO TRADE is reported as a valid outcome.
- [ ] Performance includes costs, sample size and the repo verdict.
- [ ] The next action is concrete and owned.
