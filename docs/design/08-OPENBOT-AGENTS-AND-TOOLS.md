# 08 — OpenBot Director, Three Logical Agents and Bounded Tools

## Role design

**Goal:** spend agent cognition on investigation and explanation, **not** on repetitive numerical computation or mechanical protection. Five sessions cannot afford a complex multi-agent platform.

| Role | Inputs | Outputs | Forbidden |
|---|---|---|---|
| Director | read-only scan/strategy/position summary; reviewer notes | plain-language decision brief, research task priorities, owner-facing alerts | order placement, live activation, editing engine config |
| Market Researcher | approved candidate data, indicators, previous backtest reports | evidence-linked context analysis and hypothesis suggestions | changing active strategy, cherry-picking evaluation outcomes, downloading prohibited data |
| Risk/Operations Reviewer | paper positions, run health, assumed cost/risk fields | anomaly flag, clear NO_TRADE reasons, outage incident report | claiming simulated protections are real; using admin API to close/open positions |

Three **logical** roles, not automatically three paid persistent models. Session 1 measures whether one OpenBot director with two prompted role skills suffices. Additional resident agents need a cost/benefit result.

## Agent invocation contract

One **read-only** tool/reporter exposed to the agent workspace is preferable to numerous arbitrary MCP connections. Proposed allowlisted operations:

```text
get_lab_health() -> HealthSnapshot
get_latest_scan(limit<=20) -> ScanSnapshot
get_market_features(symbol,as_of) -> FeatureSnapshot
get_research_report(strategy_id,run_id) -> BacktestReport
get_paper_positions() -> SanitizedPaperPositions
get_recent_events(limit<=50) -> EventSummary
```

Actual tool names, schema and transport are **not yet implemented or verified**. There should be no `set_leverage`, `forceenter`, `start_live`, `edit_strategy`, `download_history` or raw shell-to-Freqtrade functions in agent tools.

## Critical OpenBot trust boundary

The reviewed OpenBot preview declares `danger-full-access` and `approvalPolicy: never`: agents can run commands and read local files. This means **calling an agent 'read-only' in its prompt is insufficient**. Enforce isolation *outside the model*:

1. Run OpenBot in a distinct OS user/VM/sandbox with no access to Freqtrade's config, SQLite writable volume, secrets, Docker socket or host admin credentials.
2. Give only sanitized report copies via a one-way output directory; never mount paper database writable, even for convenience.
3. Block network reachability to the Freqtrade admin API from the OpenBot environment. Prefer no agent-facing endpoint at all in Session 1.
4. If the host cannot support meaningful isolation, use owner-mediated **manual export/import** for research; automated agent integration is a NO-GO until secured.
5. Use explicit max-size, schema-validated and timestamp-verified reports; never obey instructions embedded in untrusted market/news/web content.
6. Review OpenBot's **noncommercial license** for the intended use and planned future profit-making deployment. Obtain appropriate authorization or replace the coordinator.

## Director workflow

1. Wake by a bounded schedule (e.g. every 15min) or manual 'summarize now'.
2. Read latest signed/versioned scan and paper health snapshot; check snapshot age and validity.
3. Ask the Researcher for interpretation only if data present and a selected strategy is in research scope.
4. Ask the Reviewer about open paper risk/alerts; never assume an unanswered role is consent.
5. Produce a concise owner report with **source, as-of time, strategy version, status, reason codes, pending actions and uncertainty**.
6. Record note as commentary; source of truth remains Freqtrade database and immutable evidence snapshots.

## Proposed high-level role instructions (not security enforcement)

**Director:** “You are the OpenBot Trading Lab research coordinator. Use only the provided verified reports. Clearly label synthetic/backtest/paper; quote evidence IDs. You have no authority to place or modify orders, authorize live mode, change risk or fetch unapproved data. If evidence is absent, report UNKNOWN and ask the owner.”

**Researcher:** “Evaluate only frozen research hypotheses using supplied as-of features. Separate indicators from strategies, alternative explanations from established facts, and testing versus unseen evidence. Do not infer order flow from OHLCV or repair gaps with estimates.”

**Reviewer:** “Compare Freqtrade paper run outputs with limits/health fields. Flag stale data, risk breaches, missing fees, inconsistent timestamps, pending orders or unsuccessful restarts. Recommend a pause; do not assert actual exchange-side protection.”

## Example summary

```json
{
  "environment": "PAPER",
  "snapshot_utc": "2026-10-31T10:15:00Z",
  "engine_state": "RUNNING",
  "strategy_version": "trend-baseline-not-yet-qualified",
  "shortlist": 6,
  "open_paper_positions": 1,
  "alerts": [],
  "director_message": "One paper position is being monitored by Freqtrade. No independently verified profitability claim.",
  "evidence_id": "example-do-not-use-in-production"
}
```

This is a **shape example**, not an actual bot output or a certified API schema.

## Agent failures

OpenBot offline: paper engine can continue; owner report unavailable. Agent hallucination: discard text; never mutates strategy, Freqtrade state or risk. Missing report: summary UNKNOWN and alert. Unexpected external tool installation: deny. Prompt injection from web/market notes: treat as untrusted data and require independent checks.