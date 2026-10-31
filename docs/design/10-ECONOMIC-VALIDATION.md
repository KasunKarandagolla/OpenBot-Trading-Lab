# 10 — Economic Feasibility, Experiment Design and Honest Profit Claims

## The project's primary business question

Does a **specific, frozen strategy** produce a genuine positive after-cost advantage on sufficiently liquid perpetual futures, after accounting for nonfills, timing uncertainty, concentration and regime changes? The trading application can operate perfectly and still fail this question.

## Evidence classification

| Class | Example | What it proves | What it does NOT prove |
|---|---|---|---|
| Code/unit test | VWAP returns expected value | Calculation works for a fixture | Trading profitability |
| Synthetic backtest | Made-up price trajectory | Signal/stop/exit code follows a contract | Real market performance |
| Historical development test | Licensed, seen price series | Hypothesis exploration | Independent predictive edge |
| Frozen unseen test | Predeclared holdout after version freeze | Some out-of-sample generalization | Future real fills and stable advantage |
| Forward paper | New live public observations, simulated fills | Operational signal frequency and modeled returns | Actual exchange execution or commercial data rights |
| Real small-capital experiment | Not authorized in this MVP | Real execution economics if later permitted | Long-run guaranteed profitability |

## Minimum experiment protocol

1. **Specify one hypothesis and one baseline.** Baselines should include buy-and-hold/exposure-adjusted, time/side-matched random entries, and simple published alternatives where relevant, evaluated on the same instruments/costs/periods.
2. **Register exact code and data versions** before outcome inspection: strategy code SHA, filters, universe, training/evaluation time windows, fees/funding/slippage and sample-size threshold.
3. **Acquire only rights-cleared sources.** Record license, field fidelity, receipt/availability semantics, source hash, excluded dates and dataset provenance. No data = no market-economics experiment.
4. **Chronological split:** development / validation / untouched test. Purge leakage near boundaries at least as long as the maximum holding horizon and any feature lookback requirement; no feature uses future revised values.
5. **Full ledger:** record *all* planned opportunities including rejected, unfilled and cost-blocked; never report filled winners as if they were all intended signals.
6. **Cost stress:** exchange maker/taker fee cohorts, spread, slippage, funding, order timeouts, stop gap/worst-case outcomes, conservative stop-first ambiguity, liquidation risk where relevant.
7. **Measure dependence:** events across correlated crypto markets share market shocks. Report independent UTC days and market components, not just number of trades. Show uncertainty/intervals via appropriate blocked time-series methods.
8. **Compare to baseline and reject weak policies.** Measure net return in units of initial modeled monetary risk (net_R), expectancy, drawdown, win/loss geometry, fill survival, exposure, turnover and dependence on one regime/coin.
9. **No moving goalposts:** unprofitable outcomes cannot be 'fixed' by unlimited threshold search on the same period. Log each hypothesis/version tried; freeze a new evaluation cohort before retesting.
10. **Forward validation:** a historical winner is still unqualified for real money until new paper outcomes arrive under the frozen policy and operational behavior is demonstrated.

## No invented numerical GO gate

We have **not** selected a defensible fixed minimum trades, Sharpe or net_R lower-bound threshold for this new MVP. Reusing the old project's 100-signal/30-day gates may be a useful comparison, not automatic scientific sufficiency for every strategy. Before opening unseen data, owner/research lead must preregister appropriate power/sensitivity and economic materiality assumptions.

**Reject arbitrary shortcuts:** `Sharpe>1.5`, 70% win rate, '2:1 R:R', a few green days or a positive in-sample backtest are not sufficient for promotion. Market conditions can make a profitable-looking strategy fail. Fees reduce apparent edge; optimized portfolios share risk and opportunity constraints.

## What Freqtrade backtesting does and does not model

Official Freqtrade docs indicate backtests use simplified intra-candle ordering and assume requested-price fills without slippage if within candle range. More detailed timeframes can improve some simulations but do not create true order-book fills. Therefore record **built-in backtest results** and **independent conservative fill/cost sensitivity** separately. Do not assume a custom entry price will actually fill in the market at that rate. Use Freqtrade `lookahead-analysis` and independent append-future tests, especially for SMC indicator packages.

## Funding / derivatives accounting

Perpetual P&L must include correct side, position notional, leverage-independent loss calculation, maker/taker fees, spread/slippage, funding and mark/index nuances. Funding schedules and mark data require correct source clocks; missing data leads to an incomplete result, not a guessed favorable zero. A position's initial risk unit is *actual modeled monetary loss including costs*, not simply stop-distance percent.

## Failure criteria and disciplined decisions

| Trigger | Project-manager action |
|---|---|
| Data licence unresolved | No historical acquisition; use synthetic-only proof; economic gate BLOCKED |
| Candidate loses after realistic costs | Reject candidate, preserve artifacts; don't integrate deeper |
| Too few independent trades | INSUFFICIENT_EVIDENCE, not success or broad strategy failure |
| SMC/indicator repainting | Reject use in active strategy until fixed causally |
| Lookahead-analysis flags unresolved | NO-GO for backtest claim |
| Out-of-sample effect vanishes | Rejection / revise hypothesis in genuinely new dataset; do not tune holdout |
| Paper run fails operational safety | Stop paper, repair bounded defect; no expansion |
| Candidate passes gates | Optional next budget decision: forward paper; live not approved |

## Economics scorecard output

An audit-friendly single strategy report must show: `run_id`, `source/data rights`, `window dates`, `markets`, `fee/slippage/funding scenario`, `strategy/config hashes`, `number of raw candidates`, `passed signals`, `unfilled`, `completed`, `independent days/blocks`, `net_R distribution`, `drawdown`, `gross-vs-net`, `baseline comparison`, `confidence interval method`, `leakage checks`, `caveats`, `GO/NO-GO/INSUFFICIENT`, `decision owner`.

## Reuse of old lessons

The legacy AstraBot S04 result rejected VT4 under its fixed development test; that does not automatically falsify a new trend/VWAP playbook. It *does* teach us to count structural payoff geometry, independent days, cost survival and controls before expensive engineering. No transfer of the old strategy's purported performance to this new system.