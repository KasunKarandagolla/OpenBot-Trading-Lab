# OpenBot Trading Lab — Design Pack v1.0

**Status:** DRAFT FOR OWNER REVIEW — design only; no implementation, installation, dataset acquisition or real-money authorization.  
**Prepared:** 2026-10-31  
**Purpose:** a beginner-operable, agent-directed, reuse-first crypto trading **research and paper-trading** application within a *maximum* of five remaining Codex sessions, conditional on economic and tool gates.

> **One-line contract:** OpenBot coordinates research and explains decisions. Freqtrade/FreqUI scans through supported tools, runs versioned deterministic strategies, backtests and manages **simulated** trades. The owner approves strategic changes. Nothing proves profitability until independent after-cost validation.

## Read in this order

| File | What it answers |
|---|---|
| [00-START-HERE.md](00-START-HERE.md) | Plain-language explanation, boundaries and what is/isn't built |
| [01-PRODUCT-CONTRACT.md](01-PRODUCT-CONTRACT.md) | Goals, scope, success definition and new-vs-old product contract |
| [02-SYSTEM-ARCHITECTURE.md](02-SYSTEM-ARCHITECTURE.md) | Complete wiring, processes, trust boundaries, data contracts and end-to-end cycle |
| [03-MARKET-DATA-AND-STORAGE.md](03-MARKET-DATA-AND-STORAGE.md) | Refreshes, history, data formats, retention, failure modes and rights |
| [04-OPPORTUNITY-SCANNING.md](04-OPPORTUNITY-SCANNING.md) | Cheap scan → shortlist → deep analysis → decisions |
| [05-ANALYSIS-WEAPONS.md](05-ANALYSIS-WEAPONS.md) | Indicator/SMC/profile/order-flow choices and quality gates |
| [06-STRATEGIES-AND-DECISIONS.md](06-STRATEGIES-AND-DECISIONS.md) | How playbooks become reproducible Freqtrade policies |
| [07-ENTRIES-AND-POSITION-MANAGEMENT.md](07-ENTRIES-AND-POSITION-MANAGEMENT.md) | Sniper-style triggers, sizing, stops, targets, paper orders, failures |
| [08-OPENBOT-AGENTS-AND-TOOLS.md](08-OPENBOT-AGENTS-AND-TOOLS.md) | Three agents, tool permission model, prompts, reports and workflows |
| [09-DEPLOYMENT-AND-OPERATIONS.md](09-DEPLOYMENT-AND-OPERATIONS.md) | Beginner setup/operation, uptime, recovery and practical dashboard |
| [10-ECONOMIC-VALIDATION.md](10-ECONOMIC-VALIDATION.md) | How we decide if a strategy has economic value, and when to stop |
| [11-SECURITY-LICENSING-AND-RISK.md](11-SECURITY-LICENSING-AND-RISK.md) | Sandbox, external permissions, no-keys MVP, licensing and residual hazards |
| [12-FIVE-SESSION-DELIVERY.md](12-FIVE-SESSION-DELIVERY.md) | Five-session maximum, tangible deliverables, gates and kill switches |
| [13-ACCEPTANCE-TESTS.md](13-ACCEPTANCE-TESTS.md) | Test catalogue and evidence required before declaring any milestone complete |
| [14-DECISIONS-AND-OPEN-QUESTIONS.md](14-DECISIONS-AND-OPEN-QUESTIONS.md) | Provisional decisions and owner approvals that are still missing |
| [15-SOURCES-AND-PROVENANCE.md](15-SOURCES-AND-PROVENANCE.md) | Official documentation, project-sourced constraints, verification status |
| [16-REFERENCE-CONFIG-AND-SCHEMAS.md](16-REFERENCE-CONFIG-AND-SCHEMAS.md) | Safe illustrative configuration and machine-readable tool payloads |

## Status legend

- **VERIFIED DOCUMENTATION:** a linked upstream source describes a feature; it has **not** yet been demonstrated in our environment.
- **PROPOSED:** architectural decision or target awaiting hands-on testing and owner acceptance.
- **REQUIRES TEST:** compatibility, latency, security, cost or operational behavior not yet demonstrated.
- **BLOCKED:** missing authorization, lawful data rights or validated economics.

## Non-negotiable distinctions

1. A ready-made tool is **not** a profitable strategy.
2. Paper trading is **not** a real exchange position, nor proof that real fills/stops will match.
3. A passing code test is **not** an independent economic result.
4. OpenBot runs with broad host powers in the reviewed preview; **an agent prompt is not a permission boundary**.
5. Old AstraBot research and M4 PRs are preserved; **this pack does not approve merging or migrating them**.
6. Historical data acquisition and future commercial use require explicit legal/source clearance. Do not start downloads merely because Freqtrade supports them.

## Minimum desired user experience

The owner opens FreqUI/OpenBot, sees **market data fresh/stale**, shortlisted coins, a proposed strategy's measurable evidence, ongoing **paper** positions, exits and an understandable reason for each NO_TRADE/entry/exit. The owner can stop new paper entries, review test evidence, and return to a safe stopped state without understanding the codebase.

## Immediate next action

Review [14-DECISIONS-AND-OPEN-QUESTIONS.md](14-DECISIONS-AND-OPEN-QUESTIONS.md) and approve only the **bounded Session 1 isolated tool probe**. Do **not** authorize five sessions at once, start historical archive downloads, or enable live exchange credentials.
