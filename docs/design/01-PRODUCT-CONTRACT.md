# 01 — Product Contract, Scope and Success

## Mission and user

**Mission:** create the **smallest understandable** OpenBot-directed, Freqtrade-powered crypto-perpetual **research and paper-trading** lab that can evaluate a small number of testable trading mechanisms under explicit costs and uncertainty.

**User:** a beginner in programming and trading. Ordinary operation must require no coding. A straightforward dashboard, alerts, a one-page strategy summary, a start/stop procedure and clear evidence grades are mandatory.

## Decisions already proposed (not owner-finalized)

- Primary trading/research engine: **Freqtrade**, pinned after proof; FreqUI for dashboard.
- Orchestrator: **OpenBot Lab** in an isolated non-credentialed environment.
- One active deterministic paper strategy at a time; a trend-continuation baseline first, VWAP candidate only after hypothesis freeze.
- Three *logical* workers: Director, Market Researcher, Risk/Operations Reviewer. Combine into fewer instantiated agents if OpenBot's actual runtime requires it.
- Data scope: Binance USDⓈ-M USDT perpetual markets as a research target **subject to access and lawful-use review**; test first on synthetic/offline fixture, then specifically authorized sources.
- Execution mode in MVP: strictly **dry_run / paper**. No live mode, keys, deposits or testnet trading tasks.

## In scope for the five-session maximum

1. Verified installation/compatibility of Freqtrade/FreqUI, technical tools, and one isolated OpenBot read-only bridge.
2. Cheap broad market filters; small shortlist; reproducible, point-in-time technical measurements.
3. One baseline and at most one research candidate with mechanically specified entries, exits, constraints and reasons.
4. Repeatable backtest reporting with cost stress, chronology and lookahead guards.
5. Synthetic paper lifecycle and, if safe and economically justified, real-market **public-data-driven dry run** without real orders.
6. Basic owner manual, health checks, evidence ledger and operation recovery steps.

## Out of scope, even if a model suggests it

- Live-money trade execution, credential management, exchange-side live stop deployment, leverage automation, fee-tier negotiation.
- Homemade market-making engine, nanosecond sniper engine, full L2/L3 tape processing, cloud microservice stack, complex custom UI.
- Ten simultaneously active strategies, agent-written live strategy changes, mass hyperoptimization, unlimited coin scanning.
- Autonomous OpenBot changes to position sizing, allowed markets, operational mode or risk limits.
- Guaranteed win rate, 'proven profit' based solely on backtests, cherry-picked screenshots or short paper runs.

## Functional success versus economic success

| Level | Meaning | Required evidence |
|---|---|---|
| L0 | Design reviewed | Owner accepts boundaries and data approach |
| L1 | Runnable lab | Reproducible startup, restricted tool invocation, synthetic lifecycle, dashboard and logs |
| L2 | Strategy worth investigating | Preregistered causal backtest, fees/funding/slippage stress, adequate independent opportunities and no obvious overfit |
| L3 | Forward-paper validated | New unseen opportunities collected after freeze; meaningful stability and cost/fill diagnostics |
| L4 | Live-ready | **Not in five-session scope**; separate security, legal, execution/stop and owner acceptance |

**The five-session promise is a conditional attempt at L1 and initial L2 testing, not guaranteed L2/L3.** Real economic findings may require more data and elapsed calendar time.

## Legacy AstraBot relationship

**Do preserve:** independent evidence culture, risk conservatism, as-of timing, full transaction costs, source provenance, stop rules and readable engineering journal. The old synthetic OpenBot integration report proves a *limited marked fixture* workflow existed, not that our new lab is deployed.

**Do not migrate by default:** old 17-package architecture, all A01–A10 mandatory simultaneously, bespoke exchange gateway, old M4 detector, old draft/unmerged PR chain, unqualified strategy registry, PostgreSQL or custom dashboard. Each reuse requires a measured case.

**Critical governance change:** the old charter required per-entry owner approval for all exposure. The new MVP permits unattended **simulated** entries by one owner-approved, fixed paper strategy; **this is not authorization for live entries**. A future live project must separately decide whether to restore per-entry approval, a one-use plan, or stop live development.

## What the product must communicate

Always show `environment` (SYNTHETIC/BACKTEST/PAPER), `strategy_version`, `market_data_age`, `source_fidelity`, `candidate_state`, `position_state`, assumed fees/costs, and whether any performance is actually validated. A strategy cannot show 'profitable' based merely on a winning recent paper trade.

## Owner acceptance items

Owner must approve: host OS/compute, permitted data feeds/rights, initial exchange market eligibility, spending cap, paper risk ceilings and license usage (especially OpenBot). The design may be circulated before these decisions; implementation cannot silently infer them.
