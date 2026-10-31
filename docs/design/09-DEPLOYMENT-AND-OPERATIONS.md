# 09 — Deployment, Daily Operation, Uptime, Backup and Incident Response

## Intended environment

Start **locally on the owner's existing computer**. Docker is preferred for a reproducible Freqtrade install, especially on Windows; verify Docker compatibility, memory, disk, UI networking and actual exchange access in Session 1. OpenBot should use a separate OS environment with no trading-admin reachability. VPS/always-on server is a *later cost decision* after the economic gate.

## Three deployment stages

### Stage 0 — Synthetic proof, zero external market access

- Install pinned Freqtrade release + FreqUI/installed indicator dependencies.
- Use a tiny locally generated, explicitly `SYNTHETIC` sample and dry-run/backtest execution path as supported; demonstrate indicator output and NO_TRADE/fill/exit cases.
- Run the isolated OpenBot with only a sanitized report copy; show that it cannot access or mutate engine config, database, API or private directories.
- Run with **no API keys**, no live exchange credential files and no network-based historical download.

### Stage 1 — Licensed historical research

Only if owner explicitly approves a data source, its permitted use, retention and spend. Verify market/timeframe, mark/funding where required, version/hash. Pre-register experiments, perform backtests and archive artifacts. No switch to live trading.

### Stage 2 — Public-data-driven paper pilot

Only after strategy and runtime gates. Confirm public API jurisdiction/terms/rate limits. Start Freqtrade with `dry_run=true` and a separate paper DB. FreqUI is available only on `127.0.0.1` or via owner-controlled private access. OpenBot receives read-only snapshots. Record daily operations and at least a predetermined forward observation period before any economic conclusion.

## Beginner operator procedure (the goal, not currently tested commands)

**Morning/evening check (under 5 minutes):** open FreqUI, verify PAPER banner and engine status, see open simulated trades/available risk, check last-data freshness, read the Director's summary and alarms, review any data/legal/strategy change request. No manual trade needed for routine paper signals.

**Start:** check approved policy/config hashes, confirm `dry_run=true` and empty exchange credential fields, ensure disk/network/clock and report exporter healthy, launch pinned environment, verify FreqUI, verify a test snapshot arrives in OpenBot. On a mismatch, do not trade/paper-start.

**Pause:** use owner-authorized paper-engine controls, not an OpenBot instruction; stop new entries while ensuring intended paper position exit behavior is understood. `pause/stop` may not flatten existing positions automatically; verify actual Freqtrade behavior.

**Stop for maintenance:** block entries, inspect open paper positions, take a consistent backup, stop the engine, verify clean process exit. If paper positions were open when stopped, mark loss of supervision explicitly.

**Restart:** verify source/strategy/config hashes and mode, restore/open DB, compare open paper position count and last events, verify no duplicate actions, then allow new entries.

## Health service-level intentions (initial targets, not measured claims)

| Signal | Proposed alarm trigger | Safe response |
|---|---|---|
| Bot heartbeat | No fresh heartbeat for >2 normal loops | Disable new entries; owner alert; check host |
| Candle freshness | Last fully closed expected bar absent/stale | No new entries for affected symbols |
| Report exporter | Last snapshot >2 export intervals old | OpenBot shows STALE; engine independent |
| Low disk | <15% free or actual cap reached | Stop capture/backtest; preserve DB |
| DB write error | Any unhandled persistence failure | Halt paper run, back up, investigate |
| Unexpected API exposure | Admin API reachable from OpenBot/Internet | Emergency isolation; gate FAIL |
| Non-paper config | `dry_run` false / credentials present | Refuse startup; critical incident |
| Model outage or malicious tool call | Agent cannot produce grounded summary / forbidden operation attempted | Disconnect agent, preserve Freqtrade isolation |

## Required backups

Daily consistent paper DB backup; strategy source and config version hashes; research source manifests; selected experiment outputs. Periodic restore test, not just copy test. Exclude personal credentials and large transient raw data from the OpenBot workspace. Backups should be encrypted/private where appropriate and not in the public GitHub repository.

## Incident procedures

- **Market API unavailable:** no new simulated entries; maintain state, alarm; don't fill gaps.
- **Freqtrade process dies:** record gap; restarting may restore DB but cannot retroactively simulate stops in real time. Do not treat missed period as validated trading history.
- **OpenBot unavailable:** paper engine continues if healthy, owner reports pause; no new policy changes.
- **Unmatched simulated position:** stop new entries; reconcile using FreqUI/database and event list.
- **Owner laptop sleeps:** paper monitoring stops; choose conscious manual operation schedule instead of promising 24/7.
- **Backtest unexpectedly good:** stop promotion; inspect lookahead, too-few-trades, cost model and source rights.

## Reporting and ongoing cost

Weekly operator record: uptime, stale-data minutes, paper opportunities/signals/fills/nonfills, paper P&L before/after modeled costs, model calls, disk growth, manual interventions and strategy hash. Monthly cost statement includes host, model, data and any paid add-ons. Stop new paid capacity above explicit owner cap.

## Minimum operator manual deliverable

One page with buttons/screenshots appropriate to the *installed version*, location of data and logs, who to contact for an API/key incident, clean shutdown/restart, evidence export and an unmistakable PAPER-only banner. Do not publish screenshot instructions until the product has been installed and observed.
