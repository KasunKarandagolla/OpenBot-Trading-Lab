# 02 — Runtime Architecture, Trust Boundaries and End-to-End Sequence

## Minimal architecture

```text
                  PUBLIC / APPROVED MARKET DATA
                             |
                Freqtrade/CCXT data ingestion
                             |
            +----------------+------------------+
            |                                   |
     Freqtrade pair filters                 approved history
       (cheap shortlist)                 (backtesting files)
            |                                   |
       approved strategy <---- indicators / analysis adapters
       (fixed version, closed candles, exact data provenance)
            |
       deterministic risk/quality checks
            |
   +--------+---------------+
   |                        |
 NO_TRADE             PAPER decision
   |                        |
   |                 Freqtrade dry-run engine
   |                  | paper fill/exit, SQLite
   +----------+-------+
              |
      REPORT EXPORTER (small, read-only, sanitized snapshot)
              |
      ONE-WAY DATA EXCHANGE / isolated mount
              |
    OPENBOT DIRECTOR ── researcher ── risk/operations reviewer
              |
         owner-facing explanation / operational alerts

                     FreqUI → owner paper monitoring
```

### Operating processes (minimum)

| Process | Owner | Frequency | Network/key privileges |
|---|---|---|---|
| Freqtrade bot | Freqtrade runtime | Loop + closed candles | Public-data network; **no trading keys in MVP** |
| Snapshot/report exporter | Small host-owned job, or manual export initially | Every 5–15 min / on event | Read-only access to paper data; no admin endpoint exposed to agents |
| OpenBot Lab | Isolated research workspace | Scheduled summaries / requests | Read-only *sanitized copy*; no Freqtrade config, DB write, API admin or credential access |
| Owner | Human | On review/action | Can use FreqUI directly in paper environment; live absent |

**Important:** Freqtrade's standard API is *not* a read-only API merely because we intend to call GET. It offers state-changing endpoints. Network and credential isolation must stop an OpenBot process that can run arbitrary commands from reaching it. If isolation cannot be proven, use an **offline file-export workflow**, no OpenBot→Freqtrade network bridge.

## Detailed end-to-end state flow

1. **BOOT/VALIDATE**: load pinned image and versioned paper configuration, verify `dry_run=true`, no keys, permission separation, dataset rights and strategy hash. If any critical condition fails: **STANDBY**.
2. **DATA_READY**: gather current public OHLCV and Freqtrade pairlist summaries. Check closed-bar time, duplicates, gaps, precision, exchange status and age against the per-timeframe freshness SLA.
3. **SCREENED**: filter expensive/unreliable markets cheaply. Store a timestamped shortlist and reasons for reject/accept; avoid future backtest knowledge.
4. **ANALYZED**: calculate versioned, as-of indicators only for screened pairs. No retroactive swings/future candle access. Signal is `UNQUALIFIED` if required feature missing.
5. **CANDIDATE**: a fixed strategy identifies a setup and deterministic entry/stop/target/expiry. No free-text LLM price choice.
6. **RISK_GATE**: apply notional/risk ceiling, already-open paper positions, predicted fees/funding/spread, stale data, stop and minimum reward. Output `NO_TRADE(reason)` if failed.
7. **PAPER_ORDER**: Freqtrade simulates entry under its actual paper-mode behavior. The proposed analytic entry may not match its paper fill; log separately.
8. **MANAGE**: Freqtrade reevaluates paper exits/stops/ROI/timeout. OpenBot may observe but does not have to be online. Do not promise exchange-native protective orders in paper mode.
9. **RECONCILE/EXPORT**: periodically read Freqtrade paper state, summarize fills/exits/P&L, validate monotonic timestamps and record exceptions.
10. **REVIEW/RESEARCH**: OpenBot explains what happened with evidence IDs; owner can approve changes to strategy *between* runs, never AI hot edits of the active strategy.
11. **STOP/RESTART**: halt new paper entries before maintenance, take consistent copy of database/config, restart and compare state; fail safe on mismatch.

## Data contracts (conceptual; v1 fields to be implemented/verified)

**MarketObservation:** `venue`, `symbol`, `market_type`, `timeframe`, `bar_open_utc`, `bar_close_utc`, `observed_at_utc`, `source`, `source_version`, `data_fidelity`, `is_closed`, `data_age_seconds`, `quality`, `values`, `source_id`.

**ScreenedCandidate:** `run_id`, `as_of_utc`, `symbol`, `liquidity_filter`, `spread_filter`, `volatility_filter`, `reasons`, `data_age`, `shortlist_rank`, `screen_config_sha`.

**StrategyDecision:** `strategy_id`, `policy_sha`, `candidate_id`, `evaluated_at_utc`, `bar_available_at_utc`, `side`, `entry_condition`, `entry_price_bounds`, `stop_price`, `target_policy`, `expiry_utc`, `risk_budget`, `estimated_cost`, `result`, `reason_codes`.

**PaperTradeEvent:** `run_id`, `paper_trade_id`, `observed_at_utc`, `entry/exit_state`, `fill_model`, `filled_quantity`, `filled_rate`, `fees`, `funding_assumption`, `pnl_gross`, `pnl_net_modelled`, `strategy_id`, `data_source`.

**DirectorSummary:** `snapshot_hash`, `snapshot_utc`, `current_mode`, `health`, `shortlist`, `paper_positions`, `alerts`, `candidate_summary`, `missing_evidence`; NEVER a command to a live exchange.

For each schema, maintain `event_time` versus `available_at`/`observed_at` when relevant. A historical bar label is not proof of human/owner receipt time. The snapshot exporter must never claim fields the actual Freqtrade API lacks.

## Time zones and causality

All machine timestamps UTC. The user interface may display Asia/Colombo with explicit zone. For decisions on a 5m signal at 12:05 UTC, the 12:00–12:05 bar must have **closed and been observed** before any action; if data arrived at 12:05:03, the recorded decision time is not 12:05:00. No current unfinished candle as if final; no retroactive revised signals.

## Modes and invariant gates

| Mode | Data | Orders | Agent rights |
|---|---|---|---|
| SYNTHETIC | Generated fixture | None; deterministic simulator | Read generated reports |
| BACKTEST | Licensed, approved historical source | Offline simulated | Read result artifacts; cannot alter frozen run |
| PAPER | Approved public market feed; Freqtrade dry-run | Simulated orders only | Read-only snapshots/reports |
| LIVE | Not shipped | **Disabled** | No implementation authority |

**Zero implicit transitions:** A passing backtest cannot automatically activate paper. A passing paper run cannot unlock live. Production switch, if ever pursued, is a separate project with explicit operator acceptance.