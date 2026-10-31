# Operator demonstration — EXECUTED IN CODEX CLOUD

The same official pinned image was pulled and reused through one disposable runner. Initial startup needed the current session proxy/CA, stored only in ignored Cloud override files. First metadata attempt failed because CCXT rejects simultaneous httpProxy and httpsProxy. Removed the redundant HTTP option; TLS verification stayed enabled. Public metadata and bounded native download then succeeded. No demo credential environment bindings were forwarded.

Executed commands and results:

| Interface | Actual result |
|---|---|
| Native download equivalent of research-download | exit 0; all 12 actual series, then range sealing/validation; exact Session 1 hashes |
| `./scripts/lab.sh research-download` with retained data | expected exit 2; existing sample preserved, no extra requests |
| `./scripts/lab.sh doctor` | exit 0; official 2026.10, safe configs and original freeze |
| `./scripts/lab.sh test` | exit 0;48 tests including unchanged25 foundation cases |
| `./scripts/lab.sh research-all` | exit 0 twice;386/17/39 native trades; replay ledgers identical |
| `./scripts/lab.sh compare` | exit 0 repeatedly; identical comparison/summary/risk JSON hashes |
| compare with raw reads and subprocesses forbidden | exit 0; no access occurred; derived files suffice |
| `./scripts/lab.sh strategy-info VWAPTrendContinuationV1` | exit 0; full card and current source/config hashes |
| `./scripts/lab.sh strategy-info LiquiditySweepReversalV1` | exit 0; full card and current source/config hashes |
| `./scripts/lab.sh research-lookahead` | initial 1.0.0 run exit 0,17/20 signals no bias; final 1.0.1 CSV-append export failure retained; fresh-output rerun recorded in lookahead-results.md |

Cloud commands use the local `LAB_EXEC_CONTAINER=openbot-s2-runner` option; normal owner commands use Compose. This variable selects an existing no-key runner and never changes the research protocol. No UI or persistent paper instance was started in Session 2. Baseline remains the only approved paper selection; challenger `trade` commands are rejected.

Read `comparison-report.md`, per-strategy `trade-ledger.csv`, `callback-events.jsonl`, `initial-risk-ledger.json`, native result JSON and provenance for trades/costs. Feature-level candidates are distinct from order events. Sweep has 40 qualified feature signals but 39 trades: SOL's 2026-09-21 01:30 UTC opportunity followed a SOL stop at 01:15 and fell within the native two bar cooldown. No expired/canceled native orders were observed; historical fill realism is unqualified.

Rollback/stop: `paper-down`, `ui-down`, preserve SQLite/private config/both source samples, then check out Session 1 head. Never delete the only copy of the raw sample. Owner-host installation, source eligibility, graphical UI, pending-order restart/partial fills and continuous operation require local verification.
